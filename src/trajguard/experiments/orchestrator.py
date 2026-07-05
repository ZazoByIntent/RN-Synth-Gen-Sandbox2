"""Experiment orchestrator: YAML → validated run graph → results (design §2.2 module 9)."""

import csv
import hashlib
import json
import pickle
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.reidentification import ReidentificationAttack
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory, MetricValue
from trajguard.datasets.base import DatasetLoader
from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.split import split_by_user
from trajguard.evaluation.metrics import LinkageRate, SampledMetric, TopKAccuracy, evaluate
from trajguard.experiments import builtins as _builtins  # registers first-party implementations
from trajguard.experiments import registry
from trajguard.maps.osm import OSMMapSource
from trajguard.matching.base import MapMatcher, match_many

_ = _builtins  # imported for its registration side effects


class ConsistencyError(ValueError):
    """Raised when a config pairs a map with a dataset from a different region (design T1)."""


# --- resolved config (manual validation, no pydantic/Hydra) ---------------------


@dataclass(frozen=True)
class RunConfig:
    """A fully validated experiment configuration."""

    exp_id: str
    seed: int
    output_dir: Path
    cache_dir: Path
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
    target_scopes: tuple[str, ...]
    known_points: tuple[int, ...]
    metric_names: tuple[str, ...]
    top_k: int
    bootstrap_n: int
    bootstrap_ci: float


def _req(d: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise ValueError(f"config: missing required key {ctx}.{key!r}")
    return d[key]


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

    mechanisms = tuple(
        str(_req(m, "id", "privacy_mechanisms[]")) for m in raw.get("privacy_mechanisms", [])
    )
    attacks = _req(raw, "attacks", "")
    if not attacks:
        raise ValueError("config: at least one attack is required")
    attack = attacks[0]
    attacker = _req(attack, "attacker", "attacks[0]")

    return RunConfig(
        exp_id=str(_req(exp, "id", "experiment")),
        seed=int(_req(exp, "seed", "experiment")),
        output_dir=Path(exp.get("output_dir", f"results/{exp['id']}")),
        cache_dir=Path(exp.get("cache_dir", "data/processed")),
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
        target_scopes=tuple(str(s) for s in attack.get("target_scope", ["raw"])),
        known_points=tuple(int(k) for k in _req(attacker, "known_points", "attacks[0].attacker")),
        metric_names=tuple(str(m) for m in _req(metrics, "privacy", "metrics")),
        top_k=int(metrics.get("top_k", 5)),
        bootstrap_n=int(_req(metrics, "bootstrap", "metrics").get("n", 1000)),
        bootstrap_ci=float(_req(metrics, "bootstrap", "metrics").get("ci", 0.95)),
    )


# --- pipeline -------------------------------------------------------------------


def _version_hash(cfg: RunConfig) -> str:
    """Stable hash of the pre-attack pipeline configuration (design §3)."""
    key = {
        "map": [cfg.map_region, cfg.map_crs, cfg.map_bbox],
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


def _matched_pool(cfg: RunConfig) -> tuple[list[MatchedTrajectory], int, dict[str, int]]:
    """Load-or-compute the matched trajectory pool, cached by version hash."""
    cache = cfg.cache_dir / f"{_version_hash(cfg)}.pkl"
    if cache.exists():
        loaded: tuple[list[MatchedTrajectory], int, dict[str, int]] = pickle.loads(
            cache.read_bytes()
        )
        return loaded

    net = OSMMapSource(cfg.map_region, cfg.map_bbox, cfg.map_crs, cfg.map_dir).load()
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

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps((matched, dropped, split_counts)))
    return matched, dropped, split_counts


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


def _targets(
    cfg: RunConfig, matched: list[MatchedTrajectory]
) -> list[tuple[str, list[MatchedTrajectory]]]:
    """Map each requested scope/mechanism to an attackable matched pool."""
    targets: list[tuple[str, list[MatchedTrajectory]]] = []
    if "raw" in cfg.target_scopes:
        targets.append(("raw", matched))
    if "protected" in cfg.target_scopes:
        for mech_id in cfg.mechanisms:
            mech = registry.get("mechanism", mech_id)()
            # Identity fast-path: NoProtection does not change matching, so the
            # protected pool equals the raw pool (real re-matching lands in P5).
            if getattr(mech, "guarantee", None) == "none":
                targets.append((f"protected:{mech_id}", matched))
            else:  # pragma: no cover - no perturbing mechanism exists until P5
                raise NotImplementedError(f"re-matching protected data for {mech_id!r} is P5")
    return targets


def run(config_path: str | Path) -> list[MetricValue]:
    """Run one experiment end to end and write results/<exp_id>/; returns all metrics."""
    started = time.perf_counter()
    cfg = load_config(config_path)

    # Consistency check (design T1): the authoritative region is the loader's.
    loader_cls = registry.get("dataset", cfg.dataset_id)
    assert issubclass(loader_cls, DatasetLoader)
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

    matched, dropped, split_counts = _matched_pool(cfg)
    metrics = _build_metrics(cfg)

    all_values: list[MetricValue] = []
    for ref, pool in _targets(cfg, matched):
        for k in cfg.known_points:
            attack = ReidentificationAttack()
            attack.configure(BackgroundKnowledge(known_points=k, seed=cfg.seed))
            result = attack.run(pool)
            result = replace(
                result,
                exp_id=cfg.exp_id,
                target_data_ref=ref,
                result_id=f"reidentification:{ref}:k{k}",
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
    """Write metrics.csv and run.json under the experiment output directory."""
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
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
