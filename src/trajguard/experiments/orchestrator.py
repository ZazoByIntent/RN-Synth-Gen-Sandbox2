"""Experiment orchestrator: YAML → validated run graph → results (design §2.2 module 9)."""

import csv
import hashlib
import inspect
import itertools
import json
import math
import os
import subprocess
import time
import tracemalloc
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from pyproj import Transformer

from trajguard.attacks.attribute import attribute_report
from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.attacks.membership import membership_report
from trajguard.attacks.reconstruction import reconstruction_report
from trajguard.datamodel import AttackResult, CleanTrajectory, MatchedTrajectory, MetricValue
from trajguard.datasets.base import DatasetLoader
from trajguard.datasets.cleaning import CleaningConfig, clean, haversine_m
from trajguard.datasets.split import split_by_user
from trajguard.evaluation.metrics import LinkageRate, SampledMetric, TopKAccuracy, evaluate
from trajguard.evaluation.utility import UTILITY_METRICS
from trajguard.experiments import builtins as _builtins  # registers first-party implementations
from trajguard.experiments import registry
from trajguard.maps.base import RoadNetwork
from trajguard.matching.base import MapMatcher, match_many
from trajguard.privacy.base import PrivacyMechanism
from trajguard.privacy.geoind import GeoIndistinguishability
from trajguard.reporting.plots import (
    headline_rows,
    is_share_metric,
    plot_by_epsilon,
    plot_by_knowledge,
    plot_mechanisms,
    plot_runtime,
    target_sort_key,
)
from trajguard.reporting.results_schema import ResultRow, write_results_csv
from trajguard.reporting.tradeoff import TradeoffPoint, plot_tradeoff
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator

_ = _builtins  # imported for its registration side effects

# Attacks the run loop can actually drive. Reidentification is the reid-shaped
# contract (no constructor args, run(matched_pool, aux)); reconstruction gets its
# own preparation (noisy vs true point sequences in projected metres, mechanism
# params handed to the attacker per design §6.3) and runs only against
# geo_indistinguishability arms; poi_inference reads each protected arm's released
# clean GPS pool against the raw pool, matched per user; membership_inference runs
# LiRA against each fitted synthetic_generators arm with same-class shadows.
_ORCHESTRATOR_ATTACKS = frozenset(
    {"reidentification", "reconstruction", "poi_inference", "membership_inference"}
)


class ConsistencyError(ValueError):
    """Raised when a config pairs a map with a dataset from a different region (design T1)."""


# --- resolved config (manual validation, no pydantic/Hydra) ---------------------


@dataclass(frozen=True)
class AttackSpec:
    """One configured attack: its registry name, attacker knowledge, and targets."""

    attack_type: str
    known_points: tuple[int, ...]  # empty for families without a known-points knob
    distance: str
    target_scopes: tuple[str, ...]
    motion_m: float | None = None  # reconstruction only: fixed curvature-prior scale (m)
    poi_params: tuple[tuple[str, Any], ...] = ()  # poi_inference only: stay-point knobs
    threshold_m: float | None = None  # poi_inference only: localised-user cutoff (m)
    mia_params: tuple[tuple[str, Any], ...] = ()  # membership only: LiRA knobs
    fprs: tuple[float, ...] = ()  # membership only: TPR@FPR operating points


@dataclass(frozen=True)
class MechanismSpec:
    """One mechanism variant: registry id plus grid-expanded single-value params."""

    mech_id: str
    params: tuple[tuple[str, Any], ...]  # sorted (key, value) pairs

    @property
    def ref(self) -> str:
        """Human-readable arm label used in pool refs, result ids, and reports."""
        if not self.params:
            return self.mech_id
        return self.mech_id + ":" + ",".join(f"{k}={v}" for k, v in self.params)


@dataclass(frozen=True)
class RunConfig:
    """A fully validated experiment configuration."""

    exp_id: str
    seed: int  # run seed: mechanism noise, attacker knowledge, bootstrap resampling
    split_seed: int  # population seed: user subsample + train/test/shadow/attack split
    output_dir: Path
    cache_dir: Path
    protected_dir: Path
    map_source: str
    map_region: str
    map_bbox: tuple[float, float, float, float]
    map_crs: str
    map_dir: Path
    dataset_id: str
    dataset_path: Path
    dataset_native_region: str
    max_users: int | None  # keep all trajectories of at most this many users; None = all
    cleaning: CleaningConfig
    matcher_id: str
    radius_m: float
    gps_error_m: float
    k_candidates: int
    min_match_score: float
    fractions: dict[str, float]
    mechanisms: tuple[MechanismSpec, ...]
    generators: tuple[MechanismSpec, ...]  # synthetic_generators arms (same shape)
    attacks: tuple[AttackSpec, ...]
    metric_names: tuple[str, ...]
    top_k: int
    utility_names: tuple[str, ...]
    utility_grid: tuple[int, int]  # (n_rows, n_cols)
    bootstrap_n: int
    bootstrap_ci: float
    measure_memory: bool  # trace each attack's peak memory (metrics.memory, default on)
    attack_time_budget_s: float  # per-invocation runtime budget, report §6.6 (X = 300 s)
    export: tuple[str, ...]
    plots: tuple[str, ...]


def _req(d: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise ValueError(f"config: missing required key {ctx}.{key!r}")
    return d[key]


def _attack_specs(attacks: list[dict[str, Any]]) -> tuple[AttackSpec, ...]:
    """Validate the ``attacks`` config section; unsupported values fail loudly."""
    specs: list[AttackSpec] = []
    for i, a in enumerate(attacks):
        ctx = f"attacks[{i}]"
        attack_type = str(_req(a, "type", ctx))
        scopes = tuple(str(s) for s in a.get("target_scope", ["raw"]))
        unknown_scopes = set(scopes) - {"raw", "protected", "synthetic"}
        if unknown_scopes:
            raise ValueError(
                f"config: {ctx}.target_scope {sorted(unknown_scopes)} unsupported; "
                "expected a subset of ['raw', 'protected', 'synthetic']"
            )
        if attack_type == "reconstruction":
            # The attacker's knowledge is the arm's mechanism parameters (design
            # §6.3), supplied by the run loop — only the optional curvature prior
            # is configurable here. Reid-style knobs are a config mistake.
            attacker = a.get("attacker", {})
            unknown_keys = set(attacker) - {"motion_m"}
            if unknown_keys:
                raise ValueError(
                    f"config: {ctx}.attacker keys {sorted(unknown_keys)} unsupported for "
                    "reconstruction (epsilon/unit_m come from the mechanism arm)"
                )
            if set(scopes) != {"protected"}:
                raise ValueError(
                    f"config: {ctx}.target_scope must be ['protected'] for reconstruction, "
                    f"got {list(scopes)}"
                )
            motion = attacker.get("motion_m")
            specs.append(
                AttackSpec(
                    attack_type=attack_type,
                    known_points=(),
                    distance="dtw",
                    target_scopes=scopes,
                    motion_m=float(motion) if motion is not None else None,
                )
            )
            continue
        if attack_type == "poi_inference":
            # The attack brings its own stay-point knobs (design §6.4); reid-style
            # attacker keys (known_points/distance) have no meaning for stay-point
            # clustering and are a config mistake. threshold_m parameterises the
            # localised-user fraction in the report, not the attacker.
            attacker = a.get("attacker", {})
            allowed = {"dwell_s", "radius_m", "home_hours", "work_hours", "tz_offset_h"}
            unknown_keys = set(attacker) - allowed
            if unknown_keys:
                raise ValueError(
                    f"config: {ctx}.attacker keys {sorted(unknown_keys)} unsupported for "
                    f"poi_inference (expected a subset of {sorted(allowed)})"
                )
            if set(scopes) != {"protected"}:
                raise ValueError(
                    f"config: {ctx}.target_scope must be ['protected'] for poi_inference, "
                    f"got {list(scopes)}"
                )
            scalar_keys = ("dwell_s", "radius_m", "tz_offset_h")
            params: dict[str, Any] = {k: float(attacker[k]) for k in scalar_keys if k in attacker}
            for key in ("home_hours", "work_hours"):
                if key in attacker:
                    hours = tuple(int(h) for h in attacker[key])
                    if len(hours) != 2:
                        raise ValueError(
                            f"config: {ctx}.attacker.{key} must be [start_hour, end_hour], "
                            f"got {attacker[key]}"
                        )
                    params[key] = hours
            threshold = float(a.get("threshold_m", 200.0))
            if threshold <= 0:
                raise ValueError(f"config: {ctx}.threshold_m must be > 0, got {threshold}")
            specs.append(
                AttackSpec(
                    attack_type=attack_type,
                    known_points=(),
                    distance="dtw",
                    target_scopes=scopes,
                    poi_params=tuple(sorted(params.items())),
                    threshold_m=threshold,
                )
            )
            continue
        if attack_type == "membership_inference":
            # LiRA's knobs are the shadow count and the subsample rate; the shadow
            # models themselves are same-class generators built per arm by the run
            # loop, so reid-style keys (and shadow hyperparameters) are a config
            # mistake. fprs sets the TPR@FPR operating points of the report.
            attacker = a.get("attacker", {})
            allowed = {"n_shadow", "subsample"}
            unknown_keys = set(attacker) - allowed
            if unknown_keys:
                raise ValueError(
                    f"config: {ctx}.attacker keys {sorted(unknown_keys)} unsupported for "
                    f"membership_inference (expected a subset of {sorted(allowed)})"
                )
            if set(scopes) != {"synthetic"}:
                raise ValueError(
                    f"config: {ctx}.target_scope must be ['synthetic'] for "
                    f"membership_inference, got {list(scopes)}"
                )
            mia: dict[str, Any] = {}
            if "n_shadow" in attacker:
                mia["n_shadow"] = int(attacker["n_shadow"])
            if "subsample" in attacker:
                mia["subsample"] = float(attacker["subsample"])
            fprs = tuple(float(f) for f in a.get("fprs", [0.001, 0.01]))
            if not fprs or any(not 0.0 < f < 1.0 for f in fprs):
                raise ValueError(
                    f"config: {ctx}.fprs must be non-empty fractions in (0, 1), got {list(fprs)}"
                )
            specs.append(
                AttackSpec(
                    attack_type=attack_type,
                    known_points=(),
                    distance="dtw",
                    target_scopes=scopes,
                    mia_params=tuple(sorted(mia.items())),
                    fprs=fprs,
                )
            )
            continue
        attacker = _req(a, "attacker", ctx)
        known = tuple(int(k) for k in _req(attacker, "known_points", f"{ctx}.attacker"))
        if not known:
            raise ValueError(f"config: {ctx}.attacker.known_points must not be empty")
        specs.append(
            AttackSpec(
                attack_type=attack_type,
                known_points=known,
                distance=str(attacker.get("distance", "dtw")),
                target_scopes=scopes,
            )
        )
    return tuple(specs)


def _canon_param(value: Any) -> Any:
    """Canonicalize numeric parameter values so YAML ``1`` and ``1.0`` mean the same arm."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return float(value)
    return value


def _variant_specs(
    entries: list[dict[str, Any]], section: str, canon: bool = True
) -> tuple[MechanismSpec, ...]:
    """Validate a ``{id, params}`` config list and expand list-valued params into a grid.

    Mechanism params are canonicalized (YAML ``1`` == ``1.0``) because they feed cache
    keys; generator params are kept verbatim (``canon=False``) — they go straight into
    constructors that may require real ints (e.g. the Markov ``order``).
    """
    specs: list[MechanismSpec] = []
    for i, m in enumerate(entries):
        ctx = f"{section}[{i}]"
        mech_id = str(_req(m, "id", ctx))
        params = m.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"config: {ctx}.params must be a mapping")
        grid: dict[str, list[Any]] = {}
        for key, value in params.items():
            values = value if isinstance(value, list) else [value]
            if not values:
                raise ValueError(f"config: {ctx}.params.{key} must not be empty")
            grid[str(key)] = [_canon_param(v) if canon else v for v in values]
        keys = sorted(grid)
        for combo in itertools.product(*(grid[k] for k in keys)):
            specs.append(MechanismSpec(mech_id, tuple(zip(keys, combo, strict=True))))
    return tuple(specs)


def load_config(path: str | Path) -> RunConfig:
    """Parse and validate an experiment YAML into a RunConfig (manual validation)."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError("config: top level must be a mapping")

    exp = _req(raw, "experiment", "")
    mp = _req(raw, "map", "")
    ds = _req(raw, "dataset", "")
    cl = _req(raw, "cleaning", "")
    mm = _req(raw, "map_matching", "")
    sp = _req(raw, "split", "")
    metrics = _req(raw, "metrics", "")
    bbox = tuple(float(x) for x in _req(mp, "bbox", "map"))
    if len(bbox) != 4:
        raise ValueError("config: map.bbox must have 4 values")

    scheme = str(sp.get("scheme", "by_user"))
    if scheme != "by_user":
        raise ValueError(f"config: split.scheme {scheme!r} unsupported; only 'by_user' exists")

    reporting = raw.get("reporting", {})
    export = tuple(str(f) for f in reporting.get("export", ["csv"]))
    unknown_formats = set(export) - {"csv"}
    if unknown_formats:
        raise ValueError(
            f"config: reporting.export {sorted(unknown_formats)} unsupported; only 'csv' exists"
        )
    plots = tuple(str(p) for p in reporting.get("plots", []))
    known_plots = {"tradeoff", "by_epsilon", "by_knowledge", "mechanisms", "runtime"}
    unknown_plots = set(plots) - known_plots
    if unknown_plots:
        raise ValueError(
            f"config: reporting.plots {sorted(unknown_plots)} unsupported; "
            f"available: {sorted(known_plots)}"
        )

    metric_names = tuple(str(m) for m in _req(metrics, "privacy", "metrics"))
    utility_names = tuple(str(m) for m in metrics.get("utility", []))
    unknown_utility = set(utility_names) - set(UTILITY_METRICS)
    if unknown_utility:
        raise ValueError(
            f"config: metrics.utility {sorted(unknown_utility)} unsupported; "
            f"available: {sorted(UTILITY_METRICS)}"
        )
    if "tradeoff" in plots and "cell_js_divergence" not in utility_names:
        raise ValueError("config: the tradeoff plot needs 'cell_js_divergence' in metrics.utility")
    grid_cfg = metrics.get("utility_grid", {})

    attacks = _req(raw, "attacks", "")
    if not attacks:
        raise ValueError("config: at least one attack is required")
    attack_specs = _attack_specs(attacks)
    mech_specs = _variant_specs(raw.get("privacy_mechanisms", []), "privacy_mechanisms")
    gen_specs = _variant_specs(
        raw.get("synthetic_generators", []), "synthetic_generators", canon=False
    )

    # Plot prerequisites that are knowable before the expensive pipeline: a plot
    # whose axis cannot exist for this config is a config mistake, not an empty file.
    if "by_knowledge" in plots and not any(s.known_points for s in attack_specs):
        raise ValueError(
            "config: the by_knowledge plot needs an attack with attacker.known_points"
        )
    for plot in ("by_epsilon", "mechanisms"):
        if plot in plots and not mech_specs and not gen_specs:
            raise ValueError(
                f"config: the {plot} plot needs at least one privacy_mechanisms "
                "or synthetic_generators arm"
            )

    # Per-attack runtime budget (report §6.6): the author fixed X at 300 s per
    # attack invocation (5 Aug 2026). Exceeding it never fails or trims a run —
    # it flags the invocation in run.json so the scope-reduction rules in
    # docs/RUNNING.md can be applied to the *next* runs of a sweep.
    budget_s = float(metrics.get("attack_time_budget_s", 300.0))
    if budget_s <= 0:
        raise ValueError(f"config: metrics.attack_time_budget_s must be > 0, got {budget_s}")

    # Two seeds (design §6.4 repetitions): split_seed pins the population and the
    # user split; seed drives everything stochastic downstream. Defaulting
    # split_seed to seed keeps single-run configs unchanged, while repetition
    # runs set split_seed explicitly and vary only seed — the split stays put.
    seed = int(_req(exp, "seed", "experiment"))
    split_seed = int(exp.get("split_seed", seed))
    max_users_raw = ds.get("max_users")
    max_users = None if max_users_raw is None else int(max_users_raw)
    if max_users is not None and max_users < 1:
        raise ValueError(f"config: dataset.max_users must be >= 1, got {max_users}")

    return RunConfig(
        exp_id=str(_req(exp, "id", "experiment")),
        seed=seed,
        split_seed=split_seed,
        output_dir=Path(exp.get("output_dir", f"results/{exp['id']}")),
        cache_dir=Path(exp.get("cache_dir", "data/processed")),
        protected_dir=Path(exp.get("protected_dir", "data/protected")),
        map_source=str(_req(mp, "source", "map")),
        map_region=str(_req(mp, "region", "map")),
        map_bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
        map_crs=str(_req(mp, "crs", "map")),
        map_dir=Path(mp.get("dir", "maps")),
        dataset_id=str(_req(ds, "id", "dataset")),
        dataset_path=Path(_req(ds, "path", "dataset")),
        dataset_native_region=str(ds.get("native_region", "")),
        max_users=max_users,
        cleaning=CleaningConfig(
            max_speed_kmh=float(_req(cl, "max_speed_kmh", "cleaning")),
            min_points=int(_req(cl, "min_points", "cleaning")),
            min_length_m=float(_req(cl, "min_length_m", "cleaning")),
            resample_s=float(_req(cl, "resample_s", "cleaning")),
        ),
        matcher_id=str(_req(mm, "matcher", "map_matching")),
        radius_m=float(mm.get("radius_m", 50.0)),
        gps_error_m=float(mm.get("gps_error_m", 20.0)),
        k_candidates=int(mm.get("k_candidates", 8)),
        min_match_score=float(_req(mm, "min_match_score", "map_matching")),
        fractions={str(k): float(v) for k, v in _req(sp, "fractions", "split").items()},
        mechanisms=mech_specs,
        generators=gen_specs,
        attacks=attack_specs,
        metric_names=metric_names,
        top_k=int(metrics.get("top_k", 5)),
        utility_names=utility_names,
        utility_grid=(int(grid_cfg.get("n_rows", 20)), int(grid_cfg.get("n_cols", 20))),
        bootstrap_n=int(_req(metrics, "bootstrap", "metrics").get("n", 1000)),
        bootstrap_ci=float(_req(metrics, "bootstrap", "metrics").get("ci", 0.95)),
        measure_memory=bool(metrics.get("memory", True)),
        attack_time_budget_s=budget_s,
        export=export,
        plots=plots,
    )


# --- pipeline -------------------------------------------------------------------

_PoolCache = tuple[list[MatchedTrajectory], dict[str, CleanTrajectory], dict[str, Any]]
_NetProvider = Callable[[], tuple[RoadNetwork, MapMatcher]]

_MATCHED_SCHEMA = pa.schema(
    [
        ("traj_id", pa.string()),
        ("user_id", pa.string()),
        ("map_id", pa.string()),
        ("edge_seq", pa.list_(pa.int64())),
        ("matched_points", pa.list_(pa.list_(pa.float64()))),  # (x, y, t, offset_m)
        ("match_score", pa.float64()),
        ("frac_matched", pa.float64()),
    ]
)

_CLEAN_SCHEMA = pa.schema(
    [
        ("traj_id", pa.string()),
        ("user_id", pa.string()),
        ("points", pa.list_(pa.list_(pa.float64()))),  # (lat, lon, t)
        ("bbox", pa.list_(pa.float64())),
        ("duration_s", pa.float64()),
        ("length_m", pa.float64()),
        ("mean_speed", pa.float64()),
        ("cleaning_flags", pa.list_(pa.string())),
        ("split", pa.string()),
    ]
)


def _built_map_timestamp(cfg: RunConfig) -> str:
    """OSM snapshot timestamp recorded when the network under ``map_dir`` was built.

    Folded into the pool-cache key so rebuilding a map in place (fresh OSM data, same
    region/bbox) invalidates the stale processed pool instead of silently reusing it.
    Returns "" when the map is not yet built (the pipeline then fails later at load()).
    """
    meta = cfg.map_dir / cfg.map_region / "meta.json"
    if not meta.exists():
        return ""
    try:
        return str(json.loads(meta.read_text()).get("osm_timestamp", ""))
    except (OSError, ValueError):
        return ""


def _version_hash(cfg: RunConfig) -> str:
    """Stable hash of the pre-attack pipeline configuration (design §3)."""
    key = {
        "map": [
            cfg.map_source,
            cfg.map_region,
            cfg.map_crs,
            cfg.map_bbox,
            str(cfg.map_dir),
            _built_map_timestamp(cfg),
        ],
        "dataset": [cfg.dataset_id, str(cfg.dataset_path)],
        "cleaning": asdict(cfg.cleaning),
        "matching": [
            cfg.matcher_id,
            cfg.radius_m,
            cfg.gps_error_m,
            cfg.k_candidates,
            cfg.min_match_score,
        ],
        # Population and split are pinned by split_seed (not the run seed), so
        # repetition runs that vary only the run seed share this pool cache.
        "sample": cfg.max_users,
        "split": [sorted(cfg.fractions.items()), cfg.split_seed],
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def _protected_hash(cfg: RunConfig, spec: MechanismSpec) -> str:
    """Cache key of one protected release: pipeline hash × mechanism params × seed."""
    key = {
        "base": _version_hash(cfg),
        "mechanism": spec.mech_id,
        "params": [[k, v] for k, v in spec.params],
        "seed": cfg.seed,
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def _under_data_raw(path: Path) -> bool:
    """True if ``path`` resolves to, or inside, a ``data/raw`` directory.

    Component-based and cwd-independent: anchoring the forbidden root to ``Path.cwd()``
    would miss an absolute path into the real ``data/raw`` when the process runs from a
    subdirectory. Any ``data/raw`` segment counts, a deliberately conservative default
    for an immutability guard on the project's one immutable input.
    """
    parts = path.resolve().parts
    return any(parts[i : i + 2] == ("data", "raw") for i in range(len(parts) - 1))


def _refuse_raw_write(path: Path, key: str) -> None:
    """Enforce the data/raw immutability rule for configured write locations."""
    if _under_data_raw(path):
        raise ValueError(f"config: {key} {str(path)!r} is under data/raw/, which is immutable")


def _write_pool_cache(
    cache: Path,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
    dropped: int,
    split_counts: dict[str, int],
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """Persist a trajectory pool as Parquet tables plus a small JSON sidecar."""
    cache.mkdir(parents=True, exist_ok=True)
    pq.write_table(  # type: ignore[no-untyped-call]
        pa.table(
            {
                "traj_id": [m.traj_id for m in matched],
                "user_id": [m.user_id for m in matched],
                "map_id": [m.map_id for m in matched],
                "edge_seq": [list(m.edge_seq) for m in matched],
                "matched_points": [[list(p) for p in m.matched_points] for m in matched],
                "match_score": [m.match_score for m in matched],
                "frac_matched": [m.frac_matched for m in matched],
            },
            schema=_MATCHED_SCHEMA,
        ),
        cache / "matched.parquet",
    )
    clean = list(clean_by_id.values())
    pq.write_table(  # type: ignore[no-untyped-call]
        pa.table(
            {
                "traj_id": [t.traj_id for t in clean],
                "user_id": [t.user_id for t in clean],
                "points": [[list(p) for p in t.points] for t in clean],
                "bbox": [list(t.bbox) for t in clean],
                "duration_s": [t.duration_s for t in clean],
                "length_m": [t.length_m for t in clean],
                "mean_speed": [t.mean_speed for t in clean],
                "cleaning_flags": [list(t.cleaning_flags) for t in clean],
                "split": [t.split for t in clean],
            },
            schema=_CLEAN_SCHEMA,
        ),
        cache / "clean.parquet",
    )
    # meta.json marks the entry complete and is swapped in atomically: a crash mid-write
    # leaves only the .tmp file, so a reader never sees a truncated marker (which would
    # otherwise poison the cache with an unrecoverable JSONDecodeError on every rerun).
    meta = {"dropped": dropped, "split_counts": split_counts, **(extra_meta or {})}
    tmp = cache / "meta.json.tmp"
    tmp.write_text(json.dumps(meta))
    os.replace(tmp, cache / "meta.json")


def _read_pool_cache(cache: Path) -> _PoolCache:
    """Rehydrate a trajectory pool written by :func:`_write_pool_cache`."""
    matched = [
        MatchedTrajectory(
            traj_id=r["traj_id"],
            user_id=r["user_id"],
            map_id=r["map_id"],
            edge_seq=tuple(r["edge_seq"]),
            matched_points=tuple(tuple(p) for p in r["matched_points"]),
            match_score=r["match_score"],
            frac_matched=r["frac_matched"],
        )
        for r in pq.read_table(  # type: ignore[no-untyped-call]
            cache / "matched.parquet"
        ).to_pylist()
    ]
    clean_by_id = {
        r["traj_id"]: CleanTrajectory(
            traj_id=r["traj_id"],
            user_id=r["user_id"],
            points=tuple((p[0], p[1], p[2]) for p in r["points"]),
            bbox=(r["bbox"][0], r["bbox"][1], r["bbox"][2], r["bbox"][3]),
            duration_s=r["duration_s"],
            length_m=r["length_m"],
            mean_speed=r["mean_speed"],
            cleaning_flags=tuple(r["cleaning_flags"]),
            split=r["split"],
        )
        for r in pq.read_table(  # type: ignore[no-untyped-call]
            cache / "clean.parquet"
        ).to_pylist()
    }
    meta = json.loads((cache / "meta.json").read_text())
    return matched, clean_by_id, meta


def _net_provider(cfg: RunConfig) -> _NetProvider:
    """Memoized road-network + matcher factory: loads at most once, only on demand.

    Both the raw pipeline and protected re-matching need the network, but on a
    fully warm cache neither does — so nothing is loaded until somebody asks.
    """
    ctx: list[tuple[RoadNetwork, MapMatcher] | None] = [None]

    def provide() -> tuple[RoadNetwork, MapMatcher]:
        current = ctx[0]
        if current is None:
            source_cls = registry.get("map_source", cfg.map_source)
            net = source_cls(cfg.map_region, cfg.map_bbox, cfg.map_crs, cfg.map_dir).load()
            matcher_cls = registry.get("matcher", cfg.matcher_id)
            matcher = matcher_cls(
                radius_m=cfg.radius_m, gps_error_m=cfg.gps_error_m, k_candidates=cfg.k_candidates
            )
            current = (net, matcher)
            ctx[0] = current
        return current

    return provide


def _matched_pool(
    cfg: RunConfig, provide: _NetProvider
) -> tuple[list[MatchedTrajectory], dict[str, CleanTrajectory], int, dict[str, int]]:
    """Load-or-compute the matched trajectory pool, cached by version hash."""
    cache = cfg.cache_dir / _version_hash(cfg)
    if (cache / "meta.json").exists():
        matched, clean_by_id, meta = _read_pool_cache(cache)
        return matched, clean_by_id, meta["dropped"], meta["split_counts"]

    net, matcher = provide()
    loader = registry.get("dataset", cfg.dataset_id)(cfg.dataset_path)
    cleaned: list[CleanTrajectory] = []
    for raw in loader.iter_trajectories():
        c = clean(raw, cfg.cleaning)
        if c is not None:
            cleaned.append(c)
    if cfg.max_users is not None:
        cleaned = _subsample_users(cleaned, cfg.max_users, cfg.split_seed)
    labelled = split_by_user(cleaned, cfg.fractions, cfg.split_seed)
    split_counts: dict[str, int] = {}
    for t in labelled:
        split_counts[t.split or "none"] = split_counts.get(t.split or "none", 0) + 1

    matched, dropped = match_many(matcher, labelled, net, cfg.min_match_score)
    matched_ids = {m.traj_id for m in matched}
    clean_by_id = {t.traj_id: t for t in labelled if t.traj_id in matched_ids}

    _write_pool_cache(cache, matched, clean_by_id, dropped, split_counts)
    return matched, clean_by_id, dropped, split_counts


def _subsample_users(
    trajs: list[CleanTrajectory], max_users: int, seed: int
) -> list[CleanTrajectory]:
    """Keep every trajectory of at most ``max_users`` users (design §6.4 sample sizes).

    Users are drawn by a seeded permutation of the sorted user ids, so the kept
    population is deterministic, independent of trajectory order, and nested:
    a larger ``max_users`` under the same seed keeps a superset of the users.
    """
    users = sorted({t.user_id for t in trajs})
    if len(users) <= max_users:
        return trajs
    rng = np.random.default_rng(seed)
    kept = {users[i] for i in rng.permutation(len(users))[:max_users]}
    return [t for t in trajs if t.user_id in kept]


def _build_metrics(cfg: RunConfig) -> list[SampledMetric]:
    """Instantiate the configured privacy metrics (§8 names → classes)."""
    metrics: list[SampledMetric] = []
    for name in cfg.metric_names:
        if name == "top1_acc":
            metrics.append(TopKAccuracy(k=1))
        elif name == "topk_acc":
            metrics.append(TopKAccuracy(k=cfg.top_k))
        elif name == "linkage_rate":
            metrics.append(LinkageRate())
        else:  # allow direct class names too
            metrics.append(registry.get("metric", name)())
    return metrics


@dataclass(frozen=True)
class _Pool:
    """One attackable arm: its matched pool, its released clean form, and stats."""

    matched: list[MatchedTrajectory]
    clean_by_id: dict[str, CleanTrajectory]
    rematch_dropped: int
    spent_budget: float | None


@dataclass(frozen=True)
class _ArmInfo:
    """Structured identity of one arm for the results table (no ref-string parsing)."""

    scope: str  # raw | protected
    arm_id: str  # mechanism registry id; "" for raw
    epsilon: float | None
    unit_m: float | None


def _opt_float_attr(obj: Any, name: str) -> float | None:
    """float(getattr(obj, name)) when the attribute exists, else None."""
    value = getattr(obj, name, None)
    return None if value is None else float(value)


def _arm_infos(mech_plans: list[tuple[MechanismSpec, PrivacyMechanism]]) -> dict[str, _ArmInfo]:
    """Per-ref arm identity for the raw arm and every mechanism arm.

    epsilon/unit_m come from the instantiated mechanism (so defaults the YAML
    omitted are still recorded), not from re-parsing the arm label.
    """
    infos = {"raw": _ArmInfo("raw", "", None, None)}
    for mspec, mech in mech_plans:
        infos[f"protected:{mspec.ref}"] = _ArmInfo(
            "protected",
            mspec.mech_id,
            _opt_float_attr(mech, "epsilon"),
            _opt_float_attr(mech, "unit_m"),
        )
    return infos


def _noisy_clean(source: CleanTrajectory, payload: Any) -> CleanTrajectory:
    """A CleanTrajectory carrying the released (noisy) points, geometry recomputed."""
    pts = tuple((float(lat), float(lon), float(t)) for lat, lon, t in payload)
    length = sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in itertools.pairwise(pts))
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    return replace(
        source,
        points=pts,
        bbox=(min(lons), min(lats), max(lons), max(lats)),
        length_m=length,
        mean_speed=length / source.duration_s if source.duration_s > 0 else 0.0,
    )


def _protected_pool(
    cfg: RunConfig,
    spec: MechanismSpec,
    mech: PrivacyMechanism,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
    provide: _NetProvider,
) -> _Pool:
    """Apply one mechanism variant and build its attackable pool.

    Identity output reuses the raw matched pool directly. A perturbing mechanism
    yields a noisy release for every source trajectory; the release is re-matched
    (attacker-side snapping back onto the network) and cached under protected_dir
    keyed by pipeline hash × mechanism params × seed. clean.parquet keeps the full
    release — including trajectories that failed re-matching — because the utility
    metrics measure the mechanism, not the attacker-visible survivors.
    """
    cache = cfg.protected_dir / _protected_hash(cfg, spec)
    if (cache / "meta.json").exists():
        pool, noisy_by_id, meta = _read_pool_cache(cache)
        return _Pool(pool, noisy_by_id, meta["dropped"], meta.get("spent_budget"))

    payloads: dict[str, Any] = {}
    identity = True
    for m in matched:
        view = TrajectoryView(clean=clean_by_id[m.traj_id], matched=m)
        protected = mech.apply(view)
        payloads[m.traj_id] = protected.payload
        identity = identity and protected.payload == view.as_gps()
    if identity:
        return _Pool(matched, clean_by_id, 0, mech.spent_budget())

    noisy_by_id = {tid: _noisy_clean(clean_by_id[tid], p) for tid, p in payloads.items()}
    net, matcher = provide()
    pool, dropped = match_many(
        matcher, [noisy_by_id[m.traj_id] for m in matched], net, cfg.min_match_score
    )
    spent = mech.spent_budget()
    _write_pool_cache(
        cache,
        pool,
        noisy_by_id,
        dropped,
        {},
        extra_meta={
            "mechanism": spec.ref,
            "params": dict(spec.params),
            "seed": cfg.seed,
            "spent_budget": spent,
        },
    )
    return _Pool(pool, noisy_by_id, dropped, spent)


def _target_pools(
    cfg: RunConfig,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
    mech_plans: list[tuple[MechanismSpec, PrivacyMechanism]],
    provide: _NetProvider,
) -> dict[str, _Pool]:
    """Build every attackable pool requested by the configured attacks' scopes."""
    scopes = {s for spec in cfg.attacks for s in spec.target_scopes}
    pools: dict[str, _Pool] = {}
    if "raw" in scopes:
        pools["raw"] = _Pool(matched, clean_by_id, 0, None)
    if "protected" in scopes:
        for mspec, mech in mech_plans:
            pools[f"protected:{mspec.ref}"] = _protected_pool(
                cfg, mspec, mech, matched, clean_by_id, provide
            )
    return pools


def _run_measured(
    measure_memory: bool, invoke: Callable[[], AttackResult]
) -> tuple[AttackResult, float | None]:
    """Run one attack, optionally recording its peak traced memory in megabytes.

    tracemalloc counts only allocations made while tracing (numpy buffers
    included), so the peak is the attack's own footprint, not the pipeline's.
    Tracing slows execution — the runtime the attack measures internally then
    carries that overhead, which is why ``metrics.memory`` can turn this off
    for timing-critical sweeps (design §7.6).
    """
    if not measure_memory:
        return invoke(), None
    already_tracing = tracemalloc.is_tracing()  # e.g. an outer profiler; leave it running
    if not already_tracing:
        tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        result = invoke()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not already_tracing:
            tracemalloc.stop()
    return result, round(peak / 1e6, 3)


def _reconstruction_values(
    cfg: RunConfig,
    spec: AttackSpec,
    attack_cls: Callable[..., Attack],
    pools: dict[str, _Pool],
    clean_by_id: dict[str, CleanTrajectory],
    mech_by_ref: dict[str, PrivacyMechanism],
    arm_info: dict[str, _ArmInfo],
) -> list[ResultRow]:
    """Run the MAP reconstruction against every geo_indistinguishability arm.

    Target and aux are the released (noisy) and true GPS points of the full
    release, projected to the map CRS so the attack works in metres. Re-matching
    survival does not matter here: the attacker inverts the release itself, not
    the snapped pool. Arms of other mechanisms (e.g. the identity baseline) are
    skipped — there is no planar-Laplace noise to invert.
    """
    transformer = Transformer.from_crs("EPSG:4326", cfg.map_crs, always_xy=True)

    def project(points: Sequence[tuple[float, float, float]]) -> list[tuple[float, float]]:
        xs, ys = transformer.transform([p[1] for p in points], [p[0] for p in points])
        return list(zip(xs, ys, strict=True))

    rows: list[ResultRow] = []
    for ref, pool in pools.items():
        mech = mech_by_ref.get(ref)
        if not isinstance(mech, GeoIndistinguishability):
            continue
        ids = sorted(set(clean_by_id) & set(pool.clean_by_id))
        target = [project(pool.clean_by_id[i].points) for i in ids]
        aux = [project(clean_by_id[i].points) for i in ids]
        attack = attack_cls(epsilon=mech.epsilon, unit_m=mech.unit_m, motion_m=spec.motion_m)
        result_id = f"reconstruction:{ref}"
        result, peak_mb = _run_measured(cfg.measure_memory, partial(attack.run, target, aux))
        result = replace(
            result,
            exp_id=cfg.exp_id,
            target_data_ref=ref,
            result_id=result_id,
        )
        report = reconstruction_report(
            result, n_bootstrap=cfg.bootstrap_n, ci=cfg.bootstrap_ci, seed=cfg.seed
        )
        info = arm_info[ref]
        rows.extend(
            ResultRow(
                value=MetricValue(
                    metric_id=f"{result_id}:{name}",
                    result_id=result_id,
                    name=name,
                    value=mean,
                    ci_low=lo,
                    ci_high=hi,
                    n_bootstrap=cfg.bootstrap_n,
                ),
                family="reconstruction",
                scope=info.scope,
                arm_id=info.arm_id,
                target_ref=ref,
                epsilon=info.epsilon,
                unit_m=info.unit_m,
                n_pool=len(pool.matched),
                n_gallery_users=len({t.user_id for t in pool.matched}),
                n_rematch_dropped=pool.rematch_dropped,
                spent_budget=pool.spent_budget,
                attack_runtime_s=result.runtime_s,
                peak_memory_mb=peak_mb,
            )
            for name, (mean, lo, hi) in report.items()
        )
    return rows


def _poi_attack(attack_cls: Callable[..., Attack], spec: AttackSpec) -> Attack:
    """Instantiate the POI attack from the spec's stay-point knobs (fail-fast probe)."""
    return attack_cls(**dict(spec.poi_params))


def _poi_inference_values(
    cfg: RunConfig,
    spec: AttackSpec,
    attack_cls: Callable[..., Attack],
    pools: dict[str, _Pool],
    clean_by_id: dict[str, CleanTrajectory],
    arm_info: dict[str, _ArmInfo],
) -> list[ResultRow]:
    """Run home/work POI inference against every protected arm's released GPS pool.

    Target is the arm's full release (``clean_by_id`` keeps every released
    trajectory, so an arm whose noise empties the re-matched pool is still
    attackable); truth is the raw clean pool, matched per ``user_id``. The
    identity arm releases the raw points unchanged, so its rows are a
    near-zero-error sanity baseline, not evidence of protection.
    """
    attack = _poi_attack(attack_cls, spec)
    threshold = spec.threshold_m if spec.threshold_m is not None else 200.0
    rows: list[ResultRow] = []
    for ref, pool in pools.items():
        if not ref.startswith("protected:"):
            continue
        result_id = f"poi_inference:{ref}"
        result, peak_mb = _run_measured(
            cfg.measure_memory,
            partial(attack.run, list(pool.clean_by_id.values()), list(clean_by_id.values())),
        )
        result = replace(
            result,
            exp_id=cfg.exp_id,
            target_data_ref=ref,
            result_id=result_id,
        )
        report = attribute_report(
            result,
            threshold_m=threshold,
            n_bootstrap=cfg.bootstrap_n,
            ci=cfg.bootstrap_ci,
            seed=cfg.seed,
        )
        info = arm_info[ref]
        rows.extend(
            ResultRow(
                value=MetricValue(
                    metric_id=f"{result_id}:{name}",
                    result_id=result_id,
                    name=name,
                    value=mean,
                    ci_low=lo,
                    ci_high=hi,
                    n_bootstrap=cfg.bootstrap_n,
                ),
                family="poi_inference",
                scope=info.scope,
                arm_id=info.arm_id,
                target_ref=ref,
                epsilon=info.epsilon,
                unit_m=info.unit_m,
                n_pool=len(pool.matched),
                n_gallery_users=len({t.user_id for t in pool.matched}),
                n_rematch_dropped=pool.rematch_dropped,
                spent_budget=pool.spent_budget,
                attack_runtime_s=result.runtime_s,
                peak_memory_mb=peak_mb,
            )
            for name, (mean, lo, hi) in report.items()
        )
    return rows


def _generator_ctor(
    gen_cls: Callable[..., Any], params: dict[str, Any], cfg: RunConfig, provide: _NetProvider
) -> Callable[[int], Any]:
    """Seed-offset factory for one generator arm; injects network/seed where accepted.

    Generator constructors differ (MarkovGenerator wants neither, RNLDPSynthGenerator
    wants both), so injection is signature-driven: ``network`` comes from the memoized
    provider, ``seed`` is ``cfg.seed + offset``. Offset 0 builds the target generator;
    ``1000 + k`` builds the k-th same-class shadow (the ``rnldp_eval`` convention).
    """
    sig = inspect.signature(gen_cls)

    def make(seed_offset: int) -> Any:
        kwargs = dict(params)
        if "network" in sig.parameters:
            kwargs["network"] = provide()[0]
        if "seed" in sig.parameters:
            kwargs["seed"] = cfg.seed + seed_offset
        return gen_cls(**kwargs)

    return make


def _mia_pool(
    matched: list[MatchedTrajectory], clean_by_id: dict[str, CleanTrajectory]
) -> tuple[list[tuple[int, ...]], list[tuple[int, bool]], list[MatchedTrajectory]]:
    """Strict LiRA inputs from the split pools (fair MIA, design T3).

    The shadow pool is the shadow split — the attacker's own background data — plus
    the candidate sequences themselves (train members, test non-members), which the
    attacker legitimately knows because it queries them. Uniform shadow subsampling
    then lands each candidate inside roughly half the shadows (its IN group) and
    outside the rest (OUT), without the shadows ever seeing non-candidate train data.
    Returns ``(pool, candidates, train_matched)``.
    """

    def of_split(split: str) -> list[MatchedTrajectory]:
        return [m for m in matched if clean_by_id[m.traj_id].split == split]

    train_m, test_m, shadow_m = of_split("train"), of_split("test"), of_split("shadow")
    if not train_m or not test_m:
        raise ValueError(
            f"membership_inference needs matched trajectories in both the train "
            f"(members: {len(train_m)}) and test (non-members: {len(test_m)}) splits"
        )
    base = [tuple(int(e) for e in m.edge_seq) for m in shadow_m]
    members = [tuple(int(e) for e in m.edge_seq) for m in train_m]
    nonmembers = [tuple(int(e) for e in m.edge_seq) for m in test_m]
    n0 = len(base)
    candidates = [(n0 + i, i < len(members)) for i in range(len(members) + len(nonmembers))]
    return base + members + nonmembers, candidates, train_m


def _membership_values(
    cfg: RunConfig,
    spec: AttackSpec,
    attack_cls: Callable[..., Attack],
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
    gen_plans: list[tuple[MechanismSpec, Callable[[int], Any]]],
) -> list[ResultRow]:
    """Run LiRA membership inference against every fitted generator arm (design §6.2).

    Per arm: the target generator fits on the train split (its release contract), and
    the attack scores train members against test non-members using same-class shadow
    generators from the arm's factory. AUC and TPR@FPR are score-based point values,
    so the CI columns stay empty by design — the interval across seeds comes from
    ``trajguard repeat``.
    """
    pool, candidates, train_m = _mia_pool(matched, clean_by_id)
    n_members = sum(1 for _, is_member in candidates if is_member)
    rows: list[ResultRow] = []
    for gspec, make in gen_plans:
        target = make(0)
        target.fit([TrajectoryView(clean=clean_by_id[m.traj_id], matched=m) for m in train_m])
        attack = attack_cls(
            **dict(spec.mia_params),
            shadow_factory=lambda k, _make=make: _make(1000 + k),
        )
        attack.configure(BackgroundKnowledge(known_points=0, distance="dtw", seed=cfg.seed))
        ref = f"synthetic:{gspec.ref}"
        result_id = f"membership_inference:{ref}"
        result, peak_mb = _run_measured(
            cfg.measure_memory, partial(attack.run, target, (pool, candidates))
        )
        result = replace(
            result,
            exp_id=cfg.exp_id,
            target_data_ref=ref,
            result_id=result_id,
        )
        rows.extend(
            ResultRow(
                value=MetricValue(
                    metric_id=f"{result_id}:{name}",
                    result_id=result_id,
                    name=name,
                    value=val,
                    ci_low=None,
                    ci_high=None,
                    n_bootstrap=None,
                ),
                family="membership_inference",
                scope="synthetic",
                arm_id=gspec.mech_id,
                target_ref=ref,
                epsilon=_opt_float_attr(target, "epsilon"),
                n_shadow=int(attack.n_shadow) if hasattr(attack, "n_shadow") else None,
                n_pool=len(candidates),
                n_members=n_members,
                n_nonmembers=len(candidates) - n_members,
                attack_runtime_s=result.runtime_s,
                peak_memory_mb=peak_mb,
            )
            for name, val in membership_report(result, fprs=spec.fprs).items()
        )
    return rows


def run(config_path: str | Path) -> list[MetricValue]:
    """Load a config file, run the experiment, and return all metric values."""
    return run_experiment(load_config(config_path))


def run_experiment(cfg: RunConfig) -> list[MetricValue]:
    """Run one experiment end to end and write results/<exp_id>/; returns all metrics."""
    started = time.perf_counter()
    _refuse_raw_write(cfg.output_dir, "experiment.output_dir")
    _refuse_raw_write(cfg.cache_dir, "experiment.cache_dir")
    _refuse_raw_write(cfg.protected_dir, "experiment.protected_dir")

    # Consistency check (design T1): the authoritative region is the loader's.
    loader_cls = registry.get("dataset", cfg.dataset_id)
    if not issubclass(loader_cls, DatasetLoader):  # pragma: no cover - registry enforces
        raise TypeError(f"dataset {cfg.dataset_id!r} is not a DatasetLoader")
    native = loader_cls.native_region
    if cfg.map_region != native:
        raise ConsistencyError(
            f"map.region {cfg.map_region!r} != dataset {cfg.dataset_id!r} "
            f"native_region {native!r}; refusing to run (design T1)"
        )
    if cfg.dataset_native_region and cfg.dataset_native_region != native:
        raise ConsistencyError(
            f"config dataset.native_region {cfg.dataset_native_region!r} contradicts "
            f"loader {native!r}"
        )

    # Resolve attacks and instantiate every mechanism variant before the
    # expensive pipeline (fail fast on unknown names or rejected params).
    plans: list[tuple[AttackSpec, type[Attack]]] = []
    for spec in cfg.attacks:
        attack_cls = registry.get("attack", spec.attack_type)
        if not issubclass(attack_cls, Attack):  # pragma: no cover - registry enforces
            raise TypeError(f"attack {spec.attack_type!r} is not an Attack")
        unsupported = set(spec.target_scopes) - attack_cls.target_scope
        if unsupported:
            raise ValueError(
                f"config: attack {spec.attack_type!r} does not support "
                f"target_scope {sorted(unsupported)}"
            )
        # Consumes a different input contract than the run loop supplies (e.g.
        # poi_inference wants clean GPS, not the matched pool): fail fast here
        # instead of crashing after the expensive pipeline.
        if spec.attack_type not in _ORCHESTRATOR_ATTACKS:
            raise ValueError(
                f"config: attack {spec.attack_type!r} is not wired into the orchestrator's "
                f"run loop yet; only {sorted(_ORCHESTRATOR_ATTACKS)} runs end-to-end"
            )
        if spec.attack_type == "reconstruction":
            # The MAP inversion targets planar-Laplace noise, so it needs at least
            # one geo_indistinguishability arm to attack; other arms are skipped.
            if not any(m.mech_id == "geo_indistinguishability" for m in cfg.mechanisms):
                raise ValueError(
                    "config: reconstruction requires a geo_indistinguishability mechanism "
                    "arm (the MAP inversion attacks planar-Laplace noise)"
                )
        elif spec.attack_type == "poi_inference":
            # It attacks protected releases, so an empty mechanism section would
            # silently produce no rows; and the constructor validates its knobs
            # (e.g. dwell_s > 0), so probe it before the expensive pipeline.
            if not cfg.mechanisms:
                raise ValueError(
                    "config: poi_inference targets protected releases, but no "
                    "privacy_mechanisms are configured (the 'none' arm gives the "
                    "sanity baseline)"
                )
            _poi_attack(attack_cls, spec)
        elif spec.attack_type == "membership_inference":
            # LiRA needs fitted generator arms plus member (train) and non-member
            # (test) candidates; the constructor validates its own knobs
            # (n_shadow >= 2, subsample in (0, 1)) — probe it before the pipeline.
            if not cfg.generators:
                raise ValueError(
                    "config: membership_inference targets synthetic generators, but "
                    "synthetic_generators is empty"
                )
            if cfg.fractions.get("train", 0.0) <= 0.0 or cfg.fractions.get("test", 0.0) <= 0.0:
                raise ValueError(
                    "config: membership_inference needs non-zero train (members) and "
                    "test (non-members) split fractions"
                )
            attack_cls(**dict(spec.mia_params))
        else:
            # The reid-shaped loop builds attacks with no arguments; an attack whose
            # constructor needs params the orchestrator cannot supply must die here,
            # not after the expensive pipeline.
            try:
                attack_cls()
            except TypeError as err:
                raise ValueError(
                    f"config: attack {spec.attack_type!r} takes constructor params "
                    f"the orchestrator does not supply: {err}"
                ) from err
        plans.append((spec, attack_cls))
    mech_plans: list[tuple[MechanismSpec, PrivacyMechanism]] = []
    for mspec in cfg.mechanisms:
        mech_cls = registry.get("mechanism", mspec.mech_id)
        if not issubclass(mech_cls, PrivacyMechanism):  # pragma: no cover - registry enforces
            raise TypeError(f"mechanism {mspec.mech_id!r} is not a PrivacyMechanism")
        try:
            mech = mech_cls(**dict(mspec.params), seed=cfg.seed)
        except TypeError as err:
            raise ValueError(f"config: mechanism {mspec.ref!r} rejected its params: {err}") from err
        mech_plans.append((mspec, mech))

    provide = _net_provider(cfg)
    gen_plans: list[tuple[MechanismSpec, Callable[[int], Any]]] = []
    for gspec in cfg.generators:
        gen_cls = registry.get("generator", gspec.mech_id)
        if not issubclass(gen_cls, SyntheticGenerator):  # pragma: no cover - registry enforces
            raise TypeError(f"generator {gspec.mech_id!r} is not a SyntheticGenerator")
        # Constructing may need the road network (rn_ldp_synth), so fail fast on
        # misspelled param names via the signature instead of instantiating here.
        try:
            inspect.signature(gen_cls).bind_partial(**dict(gspec.params))
        except TypeError as err:
            raise ValueError(f"config: generator {gspec.ref!r} rejected its params: {err}") from err
        gen_plans.append((gspec, _generator_ctor(gen_cls, dict(gspec.params), cfg, provide)))

    matched, clean_by_id, dropped, split_counts = _matched_pool(cfg, provide)
    metrics = _build_metrics(cfg)
    pools = _target_pools(cfg, matched, clean_by_id, mech_plans, provide)

    mech_by_ref: dict[str, PrivacyMechanism] = {
        f"protected:{mspec.ref}": mech for mspec, mech in mech_plans
    }
    arm_info = _arm_infos(mech_plans)
    all_rows: list[ResultRow] = []
    probe_counts: dict[str, int] = {}
    for spec, attack_cls in plans:
        if spec.attack_type == "reconstruction":
            all_rows.extend(
                _reconstruction_values(
                    cfg, spec, attack_cls, pools, clean_by_id, mech_by_ref, arm_info
                )
            )
            continue
        if spec.attack_type == "poi_inference":
            all_rows.extend(
                _poi_inference_values(cfg, spec, attack_cls, pools, clean_by_id, arm_info)
            )
            continue
        if spec.attack_type == "membership_inference":
            all_rows.extend(
                _membership_values(cfg, spec, attack_cls, matched, clean_by_id, gen_plans)
            )
            continue
        for ref, pool in pools.items():
            if ref.split(":", 1)[0] not in spec.target_scopes:
                continue
            # Probes always come from the raw pool (attacker knowledge, design
            # §6.1); the raw arm is the same population via leave-one-out.
            aux = None if ref == "raw" else matched
            for k in spec.known_points:
                attack = attack_cls()
                attack.configure(
                    BackgroundKnowledge(known_points=k, distance=spec.distance, seed=cfg.seed)
                )
                result, peak_mb = _run_measured(
                    cfg.measure_memory, partial(attack.run, pool.matched, aux)
                )
                result = replace(
                    result,
                    exp_id=cfg.exp_id,
                    target_data_ref=ref,
                    result_id=f"{spec.attack_type}:{ref}:k{k}",
                )
                probe_counts[ref] = len(result.predictions)
                values = evaluate(result, metrics, cfg.bootstrap_n, cfg.bootstrap_ci, cfg.seed)
                info = arm_info[ref]
                all_rows.extend(
                    ResultRow(
                        value=v,
                        family=spec.attack_type,
                        scope=info.scope,
                        arm_id=info.arm_id,
                        target_ref=ref,
                        epsilon=info.epsilon,
                        unit_m=info.unit_m,
                        known_points=k,
                        n_pool=len(pool.matched),
                        n_gallery_users=len({t.user_id for t in pool.matched}),
                        n_probes=len(result.predictions),
                        n_rematch_dropped=pool.rematch_dropped,
                        spent_budget=pool.spent_budget,
                        attack_runtime_s=result.runtime_s,
                        peak_memory_mb=peak_mb,
                    )
                    for v in values
                )

    grid = Grid(bbox=cfg.map_bbox, n_rows=cfg.utility_grid[0], n_cols=cfg.utility_grid[1])
    utility_by_ref: dict[str, dict[str, float]] = {}
    for ref, pool in pools.items():
        if not ref.startswith("protected:") or not cfg.utility_names:
            continue
        ids = sorted(set(clean_by_id) & set(pool.clean_by_id))
        raw_release = [clean_by_id[i] for i in ids]
        noisy_release = [pool.clean_by_id[i] for i in ids]
        rng = np.random.default_rng(cfg.seed)
        for name in cfg.utility_names:
            point, lo, hi = UTILITY_METRICS[name](
                raw_release,
                noisy_release,
                grid=grid,
                n_bootstrap=cfg.bootstrap_n,
                ci=cfg.bootstrap_ci,
                rng=rng,
            )
            info = arm_info[ref]
            all_rows.append(
                ResultRow(
                    value=MetricValue(
                        metric_id=f"utility:{ref}:{name}",
                        result_id=f"utility:{ref}",
                        name=name,
                        value=point,
                        ci_low=lo,
                        ci_high=hi,
                        n_bootstrap=cfg.bootstrap_n,
                    ),
                    family="utility",
                    scope=info.scope,
                    arm_id=info.arm_id,
                    target_ref=ref,
                    epsilon=info.epsilon,
                    unit_m=info.unit_m,
                    n_pool=len(pool.matched),
                    n_gallery_users=len({t.user_id for t in pool.matched}),
                    n_rematch_dropped=pool.rematch_dropped,
                    spent_budget=pool.spent_budget,
                )
            )
            utility_by_ref.setdefault(ref, {})[name] = point

    arms = {
        ref: {
            "n_pool": len(pool.matched),
            "n_gallery_users": len({t.user_id for t in pool.matched}),
            "n_probes": probe_counts.get(ref),
            "n_rematch_dropped": pool.rematch_dropped,
            "spent_budget": _finite_or_none(pool.spent_budget),
        }
        for ref, pool in pools.items()
    }
    matrix = _matrix_table(all_rows)
    over_budget = _over_budget_attacks(all_rows, cfg.attack_time_budget_s)
    _write_results(
        cfg,
        all_rows,
        matched,
        dropped,
        split_counts,
        time.perf_counter() - started,
        arms,
        matrix,
        over_budget,
    )
    if over_budget:
        worst = ", ".join(f"{o['result_id']} ({o['runtime_s']:.1f} s)" for o in over_budget)
        print(
            f"warning: {len(over_budget)} attack invocation(s) exceeded the "
            f"{cfg.attack_time_budget_s:g} s runtime budget: {worst} — apply the "
            "scope-reduction rules in docs/RUNNING.md (computational budget)"
        )
    if "tradeoff" in cfg.plots:
        for family, headline in matrix[0]:
            points = _family_tradeoff_points(all_rows, family, utility_by_ref)
            if not any(math.isfinite(x) and math.isfinite(y) for x, y, _ in points):
                # e.g. membership inference: utility (the x-axis) is only measured
                # over protected releases, so synthetic arms have no tradeoff point.
                continue
            name = "tradeoff.png" if family == "reidentification" else f"tradeoff_{family}.png"
            plot_tradeoff(
                points,
                cfg.output_dir / name,
                y_label=f"{family}: {headline}",
                unit_interval=is_share_metric(headline),
            )
    plotters: dict[str, Callable[[Sequence[ResultRow], Path], list[Path]]] = {
        "by_epsilon": plot_by_epsilon,
        "by_knowledge": plot_by_knowledge,
        "mechanisms": plot_mechanisms,
        "runtime": plot_runtime,
    }
    for plot_name in cfg.plots:
        plotter = plotters.get(plot_name)
        if plotter is not None:
            plotter(all_rows, cfg.output_dir)
    return [r.value for r in all_rows]


_Matrix = tuple[list[tuple[str, str]], list[tuple[str, dict[str, float]]]]


def _matrix_table(rows: Sequence[ResultRow]) -> _Matrix:
    """Pivot every family's headline metric into (family columns, target-arm rows)."""
    families = sorted({r.family for r in rows if r.family != "utility"})
    columns: list[tuple[str, str]] = []
    cells: dict[str, dict[str, float]] = {}
    order: dict[str, tuple[Any, ...]] = {}
    for family in families:
        headline, picked = headline_rows(rows, family)
        columns.append((family, headline))
        for r in picked:
            value = _finite_or_none(r.value.value)
            if value is None:
                continue
            cells.setdefault(r.target_ref, {})[family] = value
            order.setdefault(r.target_ref, target_sort_key(r))
    targets = sorted(cells, key=lambda t: order[t])
    return columns, [(t, cells[t]) for t in targets]


def _family_tradeoff_points(
    rows: Sequence[ResultRow], family: str, utility_by_ref: dict[str, dict[str, float]]
) -> list[TradeoffPoint]:
    """(cell JSD, family headline value, arm label) per target arm of one family."""
    _, picked = headline_rows(rows, family)
    points: list[TradeoffPoint] = []
    for r in picked:
        x = (
            0.0
            if r.scope == "raw"
            else utility_by_ref.get(r.target_ref, {}).get("cell_js_divergence", math.nan)
        )
        points.append((x, r.value.value, r.target_ref))
    return points


def _finite_or_none(x: float | None) -> float | None:
    """NaN/inf → None so run.json stays valid RFC JSON."""
    return None if x is None or not math.isfinite(x) else x


def _over_budget_attacks(rows: Sequence[ResultRow], budget_s: float) -> list[dict[str, Any]]:
    """Attack invocations whose runtime exceeded the budget, worst first (report §6.6).

    Rows of one invocation share a result_id and carry the same runtime, so each
    invocation is counted once. Exceeding the budget never invalidates the run:
    the flag exists so the scope-reduction rules in docs/RUNNING.md can be
    applied when planning the next runs of a sweep — never silently to this one.
    """
    seen: dict[str, float] = {}
    for r in rows:
        if r.family != "utility" and r.attack_runtime_s is not None:
            seen.setdefault(r.value.result_id, r.attack_runtime_s)
    over = sorted(
        ((rid, t) for rid, t in seen.items() if t > budget_s), key=lambda item: -item[1]
    )
    return [{"result_id": rid, "runtime_s": round(t, 3)} for rid, t in over]


def _write_results(
    cfg: RunConfig,
    rows: list[ResultRow],
    matched: list[MatchedTrajectory],
    dropped: int,
    split_counts: dict[str, int],
    runtime_s: float,
    arms: dict[str, dict[str, Any]],
    matrix: _Matrix,
    over_budget: list[dict[str, Any]],
) -> None:
    """Write the exported formats, results.csv, and run.json under the output directory."""
    values = [r.value for r in rows]
    provenance: dict[str, Any] = {
        "exp_id": cfg.exp_id,
        "config_hash": _version_hash(cfg),
        "git_commit": _git_commit(),
        "seed": cfg.seed,
        "split_seed": cfg.split_seed,
        "max_users": cfg.max_users,
        "created_at": datetime.now(UTC).isoformat(),
    }
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if "csv" in cfg.export:
        # The unified results table (docs/REZULTATI_SHEMA.md): metrics.csv rows plus
        # run provenance, structured identity/axis columns, arm stats, and runtimes.
        write_results_csv(cfg.output_dir / "results.csv", provenance, rows, round(runtime_s, 3))
        with (cfg.output_dir / "metrics.csv").open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["result_id", "metric", "value", "ci_low", "ci_high", "n_bootstrap"])
            for v in values:
                # Sanitize non-finite floats to blank, matching run.json, so a NaN from a
                # degenerate arm doesn't land in the CSV as literal "nan".
                writer.writerow(
                    [
                        v.result_id,
                        v.name,
                        _finite_or_none(v.value),
                        _finite_or_none(v.ci_low),
                        _finite_or_none(v.ci_high),
                        v.n_bootstrap,
                    ]
                )
        columns, matrix_rows = matrix
        if matrix_rows:
            # Per-run risk-matrix slice: one column per family's headline metric
            # (reidentification at its largest known_points), one row per target arm.
            with (cfg.output_dir / "matrix.csv").open("w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["target", *[f"{family}:{metric}" for family, metric in columns]])
                for ref, kv in matrix_rows:
                    writer.writerow([ref, *[kv.get(family, "") for family, _ in columns]])

    run_record = {
        **provenance,
        "n_matched": len(matched),
        "n_dropped": dropped,
        "split_counts": split_counts,
        "bootstrap": {"n": cfg.bootstrap_n, "ci": cfg.bootstrap_ci},
        "arms": arms,
        # memory_traced marks runtimes measured under tracemalloc (inflated a bit);
        # budget decisions should come from runs with metrics.memory turned off.
        "over_budget": {
            "budget_s": cfg.attack_time_budget_s,
            "memory_traced": cfg.measure_memory,
            "attacks": over_budget,
        },
        "runtime_s": round(runtime_s, 3),
        "metrics": [
            {
                "result_id": v.result_id,
                "metric": v.name,
                "value": _finite_or_none(v.value),
                "ci_low": _finite_or_none(v.ci_low),
                "ci_high": _finite_or_none(v.ci_high),
            }
            for v in values
        ],
    }
    (cfg.output_dir / "run.json").write_text(json.dumps(run_record, indent=2))


def _git_commit() -> str:
    """Best-effort current git commit for provenance (design T4)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):  # pragma: no cover
        return ""
