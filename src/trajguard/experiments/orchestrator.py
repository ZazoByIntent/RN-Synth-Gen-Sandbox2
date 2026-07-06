"""Experiment orchestrator: YAML → validated run graph → results (design §2.2 module 9)."""

import csv
import hashlib
import itertools
import json
import math
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory, MetricValue
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
from trajguard.reporting.tradeoff import TradeoffPoint, plot_tradeoff
from trajguard.representation import Grid, TrajectoryView

_ = _builtins  # imported for its registration side effects

_HEADLINE = "top1_acc"  # metric pivoted into matrix.csv and the tradeoff y-axis

# Attacks the run loop can actually drive: it configures with no constructor args and
# calls run(matched_pool, aux), the reidentification contract (the P4 vertical slice).
# Other families (membership: synthetic + shadows; reconstruction: point sequences +
# epsilon; poi: clean GPS + timestamps) have standalone harnesses and tests, but the
# run loop would feed them the wrong inputs — so a config naming them is rejected up
# front rather than crashing mid-pipeline. They join here as they are wired in.
_ORCHESTRATOR_ATTACKS = frozenset({"reidentification"})


class ConsistencyError(ValueError):
    """Raised when a config pairs a map with a dataset from a different region (design T1)."""


# --- resolved config (manual validation, no pydantic/Hydra) ---------------------


@dataclass(frozen=True)
class AttackSpec:
    """One configured attack: its registry name, attacker knowledge, and targets."""

    attack_type: str
    known_points: tuple[int, ...]
    distance: str
    target_scopes: tuple[str, ...]


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
    seed: int
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
    cleaning: CleaningConfig
    matcher_id: str
    radius_m: float
    gps_error_m: float
    k_candidates: int
    min_match_score: float
    fractions: dict[str, float]
    mechanisms: tuple[MechanismSpec, ...]
    attacks: tuple[AttackSpec, ...]
    metric_names: tuple[str, ...]
    top_k: int
    utility_names: tuple[str, ...]
    utility_grid: tuple[int, int]  # (n_rows, n_cols)
    bootstrap_n: int
    bootstrap_ci: float
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
        attacker = _req(a, "attacker", ctx)
        known = tuple(int(k) for k in _req(attacker, "known_points", f"{ctx}.attacker"))
        if not known:
            raise ValueError(f"config: {ctx}.attacker.known_points must not be empty")
        scopes = tuple(str(s) for s in a.get("target_scope", ["raw"]))
        unknown_scopes = set(scopes) - {"raw", "protected"}
        if unknown_scopes:
            raise ValueError(
                f"config: {ctx}.target_scope {sorted(unknown_scopes)} unsupported "
                "(synthetic targets land in a later phase)"
            )
        specs.append(
            AttackSpec(
                attack_type=str(_req(a, "type", ctx)),
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


def _mechanism_specs(mechs: list[dict[str, Any]]) -> tuple[MechanismSpec, ...]:
    """Validate ``privacy_mechanisms`` and expand list-valued params into a grid."""
    specs: list[MechanismSpec] = []
    for i, m in enumerate(mechs):
        ctx = f"privacy_mechanisms[{i}]"
        mech_id = str(_req(m, "id", ctx))
        params = m.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"config: {ctx}.params must be a mapping")
        grid: dict[str, list[Any]] = {}
        for key, value in params.items():
            values = value if isinstance(value, list) else [value]
            if not values:
                raise ValueError(f"config: {ctx}.params.{key} must not be empty")
            grid[str(key)] = [_canon_param(v) for v in values]
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
    unknown_plots = set(plots) - {"tradeoff"}
    if unknown_plots:
        raise ValueError(
            f"config: reporting.plots {sorted(unknown_plots)} unsupported; only 'tradeoff' exists"
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
    if "tradeoff" in plots and "top1_acc" not in metric_names:
        raise ValueError("config: the tradeoff plot needs 'top1_acc' in metrics.privacy")
    grid_cfg = metrics.get("utility_grid", {})

    attacks = _req(raw, "attacks", "")
    if not attacks:
        raise ValueError("config: at least one attack is required")

    return RunConfig(
        exp_id=str(_req(exp, "id", "experiment")),
        seed=int(_req(exp, "seed", "experiment")),
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
        mechanisms=_mechanism_specs(raw.get("privacy_mechanisms", [])),
        attacks=_attack_specs(attacks),
        metric_names=metric_names,
        top_k=int(metrics.get("top_k", 5)),
        utility_names=utility_names,
        utility_grid=(int(grid_cfg.get("n_rows", 20)), int(grid_cfg.get("n_cols", 20))),
        bootstrap_n=int(_req(metrics, "bootstrap", "metrics").get("n", 1000)),
        bootstrap_ci=float(_req(metrics, "bootstrap", "metrics").get("ci", 0.95)),
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
        "split": [sorted(cfg.fractions.items()), cfg.seed],
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
    labelled = split_by_user(cleaned, cfg.fractions, cfg.seed)
    split_counts: dict[str, int] = {}
    for t in labelled:
        split_counts[t.split or "none"] = split_counts.get(t.split or "none", 0) + 1

    matched, dropped = match_many(matcher, labelled, net, cfg.min_match_score)
    matched_ids = {m.traj_id for m in matched}
    clean_by_id = {t.traj_id: t for t in labelled if t.traj_id in matched_ids}

    _write_pool_cache(cache, matched, clean_by_id, dropped, split_counts)
    return matched, clean_by_id, dropped, split_counts


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
        # The run loop builds attacks with no arguments; an attack whose constructor
        # needs params the orchestrator cannot supply (e.g. reconstruction's epsilon)
        # must die here, not after the expensive pipeline.
        try:
            attack_cls()
        except TypeError as err:
            raise ValueError(
                f"config: attack {spec.attack_type!r} takes constructor params "
                f"the orchestrator does not supply: {err}"
            ) from err
        # Constructs fine but consumes a different input contract than the run loop
        # supplies (e.g. poi_inference wants clean GPS, not the matched pool): fail
        # fast here instead of crashing after the expensive pipeline.
        if spec.attack_type not in _ORCHESTRATOR_ATTACKS:
            raise ValueError(
                f"config: attack {spec.attack_type!r} is not wired into the orchestrator's "
                f"run loop yet; only {sorted(_ORCHESTRATOR_ATTACKS)} runs end-to-end"
            )
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
    matched, clean_by_id, dropped, split_counts = _matched_pool(cfg, provide)
    metrics = _build_metrics(cfg)
    pools = _target_pools(cfg, matched, clean_by_id, mech_plans, provide)

    all_values: list[MetricValue] = []
    attack_rows: list[tuple[str, int, list[MetricValue]]] = []  # (ref, known_points, values)
    probe_counts: dict[str, int] = {}
    for spec, attack_cls in plans:
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
                result = attack.run(pool.matched, aux)
                result = replace(
                    result,
                    exp_id=cfg.exp_id,
                    target_data_ref=ref,
                    result_id=f"{spec.attack_type}:{ref}:k{k}",
                )
                probe_counts[ref] = len(result.predictions)
                values = evaluate(result, metrics, cfg.bootstrap_n, cfg.bootstrap_ci, cfg.seed)
                all_values.extend(values)
                attack_rows.append((ref, k, values))

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
            all_values.append(
                MetricValue(
                    metric_id=f"utility:{ref}:{name}",
                    result_id=f"utility:{ref}",
                    name=name,
                    value=point,
                    ci_low=lo,
                    ci_high=hi,
                    n_bootstrap=cfg.bootstrap_n,
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
    matrix = _matrix_rows(list(pools), attack_rows)
    _write_results(
        cfg,
        all_values,
        matched,
        dropped,
        split_counts,
        time.perf_counter() - started,
        arms,
        matrix,
    )
    if "tradeoff" in cfg.plots:
        plot_tradeoff(_tradeoff_points(matrix, utility_by_ref), cfg.output_dir / "tradeoff.png")
    return all_values


_Matrix = tuple[list[int], list[tuple[str, dict[int, float]]]]


def _matrix_rows(refs: list[str], attack_rows: list[tuple[str, int, list[MetricValue]]]) -> _Matrix:
    """Pivot the headline metric into (known_points columns, target-ref rows)."""
    cells: dict[tuple[str, int], float] = {}
    for ref, k, values in attack_rows:
        for v in values:
            if v.name == _HEADLINE:
                cells[(ref, k)] = v.value
    ks = sorted({k for _, k in cells})
    rows = [(ref, {k: cells[(ref, k)] for k in ks if (ref, k) in cells}) for ref in refs]
    return ks, [(ref, kv) for ref, kv in rows if kv]


def _tradeoff_points(
    matrix: _Matrix, utility_by_ref: dict[str, dict[str, float]]
) -> list[TradeoffPoint]:
    """(cell JSD, headline accuracy at the largest known_points, arm label) per arm."""
    ks, rows = matrix
    if not ks:
        return []
    k_max = ks[-1]
    points: list[TradeoffPoint] = []
    for ref, kv in rows:
        if k_max not in kv:
            continue
        x = 0.0 if ref == "raw" else utility_by_ref.get(ref, {}).get("cell_js_divergence", math.nan)
        points.append((x, kv[k_max], ref))
    return points


def _finite_or_none(x: float | None) -> float | None:
    """NaN/inf → None so run.json stays valid RFC JSON."""
    return None if x is None or not math.isfinite(x) else x


def _write_results(
    cfg: RunConfig,
    values: list[MetricValue],
    matched: list[MatchedTrajectory],
    dropped: int,
    split_counts: dict[str, int],
    runtime_s: float,
    arms: dict[str, dict[str, Any]],
    matrix: _Matrix,
) -> None:
    """Write the exported formats and run.json under the experiment output directory."""
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if "csv" in cfg.export:
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
        ks, rows = matrix
        if rows:
            with (cfg.output_dir / "matrix.csv").open("w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["target", *[f"k={k}" for k in ks]])
                for ref, kv in rows:
                    writer.writerow([ref, *[kv.get(k, "") for k in ks]])

    run_record = {
        "exp_id": cfg.exp_id,
        "config_hash": _version_hash(cfg),
        "git_commit": _git_commit(),
        "seed": cfg.seed,
        "created_at": datetime.now(UTC).isoformat(),
        "n_matched": len(matched),
        "n_dropped": dropped,
        "split_counts": split_counts,
        "bootstrap": {"n": cfg.bootstrap_n, "ci": cfg.bootstrap_ci},
        "arms": arms,
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
