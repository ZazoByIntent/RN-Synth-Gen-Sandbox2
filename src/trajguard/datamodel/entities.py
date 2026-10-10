"""Frozen dataclass schemas for the benchmark entities (design §4)."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    payload: Any  # view-dependent, as for ProtectedTrajectory; TimedRoute when timed
    trained_on_split: str
    map_id: str


BEIJING_UTC_OFFSET_S = 8 * 3600
"""Local-time offset of Beijing (UTC+8, no daylight saving), for Geolife and T-Drive."""


@dataclass(frozen=True, slots=True)
class LinkVisit:
    """One timed traversal of a road link inside a timed synthetic route.

    Times are Unix seconds (UTC instants, like ``CleanTrajectory`` points); the
    owning ``TimedRoute`` carries the local offset. ``dwell_s`` is the part of
    ``t_exit - t_enter`` spent stopped on the link, so a stop is recorded as such
    and does not read as an absurdly slow link (finding F1).
    """

    edge_id: int
    t_enter: float
    t_exit: float
    dwell_s: float = 0.0

    def __post_init__(self) -> None:
        """Reject non-finite times, exit before entry and dwells outside the visit."""
        if not (math.isfinite(self.t_enter) and math.isfinite(self.t_exit)):
            raise ValueError(f"LinkVisit: non-finite time on edge {self.edge_id}")
        if self.t_exit < self.t_enter:
            raise ValueError(f"LinkVisit: t_exit < t_enter on edge {self.edge_id}")
        if not (0.0 <= self.dwell_s <= self.t_exit - self.t_enter):
            raise ValueError(
                f"LinkVisit: dwell_s must lie in [0, t_exit - t_enter] on edge {self.edge_id}"
            )

    @property
    def moving_s(self) -> float:
        """Seconds spent moving on the link (visit duration minus dwell)."""
        return self.t_exit - self.t_enter - self.dwell_s


@dataclass(frozen=True, slots=True)
class TimedRoute:
    """A timed synthetic payload: time-ordered link visits plus the local UTC offset.

    The departure time is the first visit's ``t_enter``. Consecutive visits may not
    overlap (``t_enter`` of a visit is at least the previous ``t_exit``).
    """

    visits: tuple[LinkVisit, ...]
    utc_offset_s: int  # local time = UTC + utc_offset_s; BEIJING_UTC_OFFSET_S for Beijing

    def __post_init__(self) -> None:
        """Reject empty routes, overlapping visits and impossible UTC offsets."""
        if not self.visits:
            raise ValueError("TimedRoute: at least one link visit is required")
        if abs(self.utc_offset_s) > 14 * 3600:
            raise ValueError(f"TimedRoute: utc_offset_s {self.utc_offset_s} out of range")
        for prev, nxt in zip(self.visits, self.visits[1:], strict=False):
            if nxt.t_enter < prev.t_exit:
                raise ValueError(
                    f"TimedRoute: visit on edge {nxt.edge_id} starts before the previous ends"
                )

    @property
    def edge_seq(self) -> tuple[int, ...]:
        """Link ids in traversal order."""
        return tuple(v.edge_id for v in self.visits)

    @property
    def departure_t(self) -> float:
        """Departure as a Unix-seconds UTC instant."""
        return self.visits[0].t_enter

    @property
    def arrival_t(self) -> float:
        """Arrival as a Unix-seconds UTC instant."""
        return self.visits[-1].t_exit

    def to_local(self, t: float) -> datetime:
        """Convert a Unix-seconds instant to an aware datetime in the route's local time."""
        return datetime.fromtimestamp(t, tz=timezone(timedelta(seconds=self.utc_offset_s)))


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
