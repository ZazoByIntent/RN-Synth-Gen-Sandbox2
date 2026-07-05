"""Experiment orchestrator: YAML → validated run graph → results (design §2.2 module 9)."""

import csv
import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory, MetricValue
from trajguard.datasets.base import DatasetLoader
from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.split import split_by_user
from trajguard.evaluation.metrics import LinkageRate, SampledMetric, TopKAccuracy, evaluate
from trajguard.experiments import builtins as _builtins  # registers first-party implementations
from trajguard.experiments import registry
from trajguard.matching.base import MapMatcher, match_many
from trajguard.privacy.base import PrivacyMechanism
from trajguard.representation import TrajectoryView

_ = _builtins  # imported for its registration side effects


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
class RunConfig:
    """A fully validated experiment configuration."""

    exp_id: str
    seed: int
    output_dir: Path
    cache_dir: Path
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
    mechanisms: tuple[str, ...]
    attacks: tuple[AttackSpec, ...]
    metric_names: tuple[str, ...]
    top_k: int
    bootstrap_n: int
    bootstrap_ci: float
    export: tuple[str, ...]


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

    export = tuple(str(f) for f in raw.get("reporting", {}).get("export", ["csv"]))
    unknown_formats = set(export) - {"csv"}
    if unknown_formats:
        raise ValueError(
            f"config: reporting.export {sorted(unknown_formats)} unsupported; only 'csv' exists"
        )

    mechanisms = tuple(
        str(_req(m, "id", "privacy_mechanisms[]")) for m in raw.get("privacy_mechanisms", [])
    )
    attacks = _req(raw, "attacks", "")
    if not attacks:
        raise ValueError("config: at least one attack is required")

    return RunConfig(
        exp_id=str(_req(exp, "id", "experiment")),
        seed=int(_req(exp, "seed", "experiment")),
        output_dir=Path(exp.get("output_dir", f"results/{exp['id']}")),
        cache_dir=Path(exp.get("cache_dir", "data/processed")),
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
        mechanisms=mechanisms,
        attacks=_attack_specs(attacks),
        metric_names=tuple(str(m) for m in _req(metrics, "privacy", "metrics")),
        top_k=int(metrics.get("top_k", 5)),
        bootstrap_n=int(_req(metrics, "bootstrap", "metrics").get("n", 1000)),
        bootstrap_ci=float(_req(metrics, "bootstrap", "metrics").get("ci", 0.95)),
        export=export,
    )


# --- pipeline -------------------------------------------------------------------

_PoolCache = tuple[list[MatchedTrajectory], dict[str, CleanTrajectory], int, dict[str, int]]

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


def _version_hash(cfg: RunConfig) -> str:
    """Stable hash of the pre-attack pipeline configuration (design §3)."""
    key = {
        "map": [cfg.map_source, cfg.map_region, cfg.map_crs, cfg.map_bbox],
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


def _refuse_raw_write(path: Path, key: str) -> None:
    """Enforce the data/raw immutability rule for configured write locations."""
    raw_root = (Path.cwd() / "data" / "raw").resolve()
    resolved = path.resolve()
    if resolved == raw_root or raw_root in resolved.parents:
        raise ValueError(f"config: {key} {str(path)!r} is under data/raw/, which is immutable")


def _write_pool_cache(
    cache: Path,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
    dropped: int,
    split_counts: dict[str, int],
) -> None:
    """Persist the matched pool as Parquet tables plus a small JSON sidecar."""
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
    # meta.json is written last: its presence marks the cache entry as complete.
    meta = {"dropped": dropped, "split_counts": split_counts}
    (cache / "meta.json").write_text(json.dumps(meta))


def _read_pool_cache(cache: Path) -> _PoolCache:
    """Rehydrate the matched pool written by :func:`_write_pool_cache`."""
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
    return matched, clean_by_id, meta["dropped"], meta["split_counts"]


def _matched_pool(cfg: RunConfig) -> _PoolCache:
    """Load-or-compute the matched trajectory pool, cached by version hash."""
    cache = cfg.cache_dir / _version_hash(cfg)
    if (cache / "meta.json").exists():
        return _read_pool_cache(cache)

    source_cls = registry.get("map_source", cfg.map_source)
    net = source_cls(cfg.map_region, cfg.map_bbox, cfg.map_crs, cfg.map_dir).load()
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

    matcher_cls = registry.get("matcher", cfg.matcher_id)
    matcher: MapMatcher = matcher_cls(
        radius_m=cfg.radius_m, gps_error_m=cfg.gps_error_m, k_candidates=cfg.k_candidates
    )
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


def _protected_pool(
    mech: PrivacyMechanism,
    mech_id: str,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
) -> list[MatchedTrajectory]:
    """Apply the mechanism to every trajectory and return the attackable pool.

    An output identical to its input leaves map matching unchanged, so the
    existing matched trajectory is reused; anything else needs re-matching (P5).
    """
    pool: list[MatchedTrajectory] = []
    for m in matched:
        view = TrajectoryView(clean=clean_by_id[m.traj_id], matched=m)
        protected = mech.apply(view)
        if protected.payload != view.as_gps():
            raise NotImplementedError(
                f"mechanism {mech_id!r} perturbs its input; "
                "re-matching protected trajectories lands in P5"
            )
        pool.append(m)
    return pool


def _target_pools(
    cfg: RunConfig,
    matched: list[MatchedTrajectory],
    clean_by_id: dict[str, CleanTrajectory],
) -> dict[str, list[MatchedTrajectory]]:
    """Build every attackable pool requested by the configured attacks' scopes."""
    scopes = {s for spec in cfg.attacks for s in spec.target_scopes}
    pools: dict[str, list[MatchedTrajectory]] = {}
    if "raw" in scopes:
        pools["raw"] = matched
    if "protected" in scopes:
        for mech_id in cfg.mechanisms:
            mech_cls = registry.get("mechanism", mech_id)
            if not issubclass(mech_cls, PrivacyMechanism):  # pragma: no cover - registry enforces
                raise TypeError(f"mechanism {mech_id!r} is not a PrivacyMechanism")
            pools[f"protected:{mech_id}"] = _protected_pool(
                mech_cls(), mech_id, matched, clean_by_id
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

    # Resolve every configured attack before the expensive pipeline (fail fast).
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
        plans.append((spec, attack_cls))

    matched, clean_by_id, dropped, split_counts = _matched_pool(cfg)
    metrics = _build_metrics(cfg)
    pools = _target_pools(cfg, matched, clean_by_id)

    all_values: list[MetricValue] = []
    for spec, attack_cls in plans:
        for ref, pool in pools.items():
            if ref.split(":", 1)[0] not in spec.target_scopes:
                continue
            for k in spec.known_points:
                attack = attack_cls()
                attack.configure(
                    BackgroundKnowledge(known_points=k, distance=spec.distance, seed=cfg.seed)
                )
                result = attack.run(pool, None)
                result = replace(
                    result,
                    exp_id=cfg.exp_id,
                    target_data_ref=ref,
                    result_id=f"{spec.attack_type}:{ref}:k{k}",
                )
                all_values.extend(
                    evaluate(result, metrics, cfg.bootstrap_n, cfg.bootstrap_ci, cfg.seed)
                )

    _write_results(cfg, all_values, matched, dropped, split_counts, time.perf_counter() - started)
    return all_values


def _write_results(
    cfg: RunConfig,
    values: list[MetricValue],
    matched: list[MatchedTrajectory],
    dropped: int,
    split_counts: dict[str, int],
    runtime_s: float,
) -> None:
    """Write the exported formats and run.json under the experiment output directory."""
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if "csv" in cfg.export:
        with (cfg.output_dir / "metrics.csv").open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["result_id", "metric", "value", "ci_low", "ci_high", "n_bootstrap"])
            for v in values:
                writer.writerow([v.result_id, v.name, v.value, v.ci_low, v.ci_high, v.n_bootstrap])

    run_record = {
        "exp_id": cfg.exp_id,
        "config_hash": _version_hash(cfg),
        "git_commit": _git_commit(),
        "seed": cfg.seed,
        "created_at": datetime.now(UTC).isoformat(),
        "n_matched": len(matched),
        "n_dropped": dropped,
        "split_counts": split_counts,
        "runtime_s": round(runtime_s, 3),
        "metrics": [
            {
                "result_id": v.result_id,
                "metric": v.name,
                "value": v.value,
                "ci_low": v.ci_low,
                "ci_high": v.ci_high,
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
