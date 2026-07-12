"""Frozen dataclass schemas for the benchmark entities (design §4)."""

from dataclasses import dataclass
from typing import Any, Literal

Split = Literal["train", "test", "shadow", "attack"]
"""Dataset split, assigned once at CleanTrajectory level and propagated (design §3)."""


@dataclass(frozen=True, slots=True)
class Map:
    """A built road-network artefact and where it is stored on disk."""

    map_id: str
    source: str  # "osm" | "synthetic"
    region: str
    bbox: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    crs: str
    osm_timestamp: str | None
    path_graph: str
    path_edges: str
    path_nodes: str


@dataclass(frozen=True, slots=True)
class RawTrajectory:
    """One trajectory as parsed from the source files, before any cleaning."""

    traj_id: str
    user_id: str
    dataset_id: str
    points: tuple[tuple[float, ...], ...]  # (lat, lon, t) or (lat, lon, t, alt)
    start_t: float
    end_t: float
    n_points: int
    source_file: str


@dataclass(frozen=True, slots=True)
class CleanTrajectory:
    """A cleaned, filtered, resampled trajectory ready for map matching."""

    traj_id: str
    user_id: str
    points: tuple[tuple[float, float, float], ...]  # (lat, lon, t)
    bbox: tuple[float, float, float, float]
    duration_s: float
    length_m: float
    mean_speed: float
    cleaning_flags: tuple[str, ...]
    split: Split | None = None  # assigned once by the splitter (P3)


@dataclass(frozen=True, slots=True)
class MatchedTrajectory:
    """A trajectory snapped onto road-network edges."""

    traj_id: str
    user_id: str
    map_id: str
    edge_seq: tuple[int, ...]
    matched_points: tuple[tuple[float, float, float, float], ...]  # (x, y, t, offset_m)
    match_score: float
    frac_matched: float


@dataclass(frozen=True, slots=True)
class ProtectedTrajectory:
    """The output of one privacy mechanism applied to one source trajectory."""

    traj_id: str
    source_traj_id: str
    mechanism_id: str
    params_hash: str
    guarantee: str
    epsilon: float | None
    payload: Any  # view-dependent (GPS points, edge sequence, cells, ...)
    map_id: str


@dataclass(frozen=True, slots=True)
class SyntheticTrajectory:
    """One trajectory sampled from a fitted generator."""

    syn_id: str
    generator_id: str
    params_hash: str
    payload: Any  # view-dependent, as for ProtectedTrajectory
    trained_on_split: str
    map_id: str


@dataclass(frozen=True, slots=True)
class AttackResult:
    """Predictions and scores produced by one attack run."""

    result_id: str
    attack_id: str
    exp_id: str
    target_data_ref: str
    predictions: Any
    scores: Any
    ground_truth_ref: str
    runtime_s: float


@dataclass(frozen=True, slots=True)
class MetricValue:
    """One named metric computed from an attack result, with optional bootstrap CI."""

    metric_id: str
    result_id: str
    name: str
    value: float
    ci_low: float | None
    ci_high: float | None
    n_bootstrap: int | None


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Identifying metadata of one experiment run (design §4, Experiment)."""

    exp_id: str
    config_hash: str
    map_id: str
    dataset_id: str
    git_commit: str
    seed: int
    created_at: str  # ISO-8601
    mlflow_run_id: str | None  # unused in the MVP (tracking deferred, plan §"NI v tem načrtu")
