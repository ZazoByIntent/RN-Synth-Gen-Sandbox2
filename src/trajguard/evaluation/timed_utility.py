"""Unpaired utility metrics for timed synthetic releases (ULDP prerequisites P2 and P12).

A user-level generator releases trips with times (``TimedRoute`` payloads) and no
bijection to real trips, so its output is compared, as a population, with the trips of
the held-out **test** users (docs/NACRT_ULDP_SINTEZA.md §5.3). Each reference user
weighs equally: a user's trips share that user's weight (docs/NACRT_ULDP_RANGI.md §8,
point 8). Synthetic trips carry no user, so each one weighs equally. A user with trips
in a departure period keeps its full weight in that period's metric.

Both sides are featurised from edge sequences on the same road network (the matched
``edge_seq`` of a reference trip, the route of a synthetic trip): length is the sum of
network edge lengths, cells and origin-destination zones come from node coordinates.
Duration and departure of a reference trip are read off its own points.

The pre-registered metrics (lower is better for all of them):

- ``duration_w1_s``: Wasserstein-1 (W1) between trip durations, seconds;
- ``speed_w1_mps``: W1 between mean trip speeds (length / duration), m/s;
- ``departure_hour_circ_w1_h``: W1 on the 24-hour circle between local departure
  hours, hours (0 to 12);
- ``od3x3_jsd``: Jensen-Shannon divergence, bits, between the 3 x 3 origin-destination
  zone matrices (zones: a 3 x 3 grid over the public map bbox);
- ``cell_js_divergence``: JSD, bits, between the summed cell-visit distributions (each
  edge's midpoint counts once in its utility-grid cell), as ``rnldp_eval`` computes it;
- ``length_w1_m``: W1 between network trip lengths, metres;
- ``duration_w1_s@<period>``: W1 of trip duration within each departure period (P12).

Intervals come from a two-sided bootstrap: reference **users** are resampled with
replacement (each drawn user brings all of its trips), synthetic trips independently.
With ``n_bootstrap <= 0`` the interval is NaN.
These functions do not fit the attack-shaped ``Metric`` ABC (there is no attack result),
so, like ``evaluation.utility``, they are plain functions the orchestrator calls.

:func:`utility_gain` turns three arms into the share of the prior-to-oracle gap an arm
closes, ``(prior - arm) / (prior - oracle)``, with a bootstrap interval over reference
users. A metric on which the oracle does not beat the prior is still reported, but
flagged as not counting as evidence (§5.3). No success threshold is applied anywhere.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from trajguard.datamodel import (
    BEIJING_UTC_OFFSET_S,
    CleanTrajectory,
    SyntheticTrajectory,
    TimedRoute,
)
from trajguard.evaluation.utility import jsd_bits
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid

#: Local-time offset of each map region whose real trips can serve as a reference.
#: Beijing is UTC+8 without daylight saving (the datamodel constant); a region missing
#: here has no timed reference, and the orchestrator refuses the run at config time.
REGION_UTC_OFFSET_S: dict[str, int] = {"beijing": BEIJING_UTC_OFFSET_S}

#: Origin-destination zones: a 3 x 3 grid over the public map bbox
#: (docs/NACRT_ULDP_SINTEZA.md §4.4, "9 = 3 x 3 at n ~ 91").
OD_ZONES_PER_SIDE = 3

#: Departure periods of the day, local time, as [start_h, end_h). The plan fixes five
#: periods (docs/NACRT_ULDP_SINTEZA.md §4.4) without boundaries. The two peaks follow
#: the Beijing peak-hour convention of the Beijing Transport Institute's annual
#: transport report (北京交通发展年报: morning peak 07:00-09:00, evening peak
#: 17:00-19:00); the other three periods are what lies between them and midnight.
DEPARTURE_PERIODS: tuple[tuple[str, float, float], ...] = (
    ("night", 0.0, 7.0),
    ("am_peak", 7.0, 9.0),
    ("midday", 9.0, 17.0),
    ("pm_peak", 17.0, 19.0),
    ("evening", 19.0, 24.0),
)

PRIMARY_METRICS: tuple[str, ...] = (
    "duration_w1_s",
    "speed_w1_mps",
    "departure_hour_circ_w1_h",
    "od3x3_jsd",
    "cell_js_divergence",
    "length_w1_m",
)
PERIOD_METRICS: tuple[str, ...] = tuple(f"duration_w1_s@{name}" for name, _, _ in DEPARTURE_PERIODS)
TIMED_UTILITY_METRICS: tuple[str, ...] = PRIMARY_METRICS + PERIOD_METRICS
"""Every metric name :func:`timed_utility` returns, in reporting order."""


@dataclass(frozen=True, slots=True)
class TripFeatures:
    """The per-trip quantities the timed utility metrics compare."""

    user_id: str  # "" for a synthetic trip (each one counts as its own unit)
    duration_s: float
    length_m: float
    departure_hour: float  # local hour of day in [0, 24)
    origin_zone: int  # row-major index into the 3 x 3 zone grid
    dest_zone: int
    cells: tuple[int, ...] = ()  # utility-grid cell of each edge's midpoint, in order

    @property
    def speed_mps(self) -> float:
        """Mean trip speed (m/s); 0.0 when the duration is not positive."""
        return self.length_m / self.duration_s if self.duration_s > 0 else 0.0


def od_zones(bbox: tuple[float, float, float, float]) -> Grid:
    """The 3 x 3 origin-destination zone grid over a public map bbox."""
    return Grid(bbox=bbox, n_rows=OD_ZONES_PER_SIDE, n_cols=OD_ZONES_PER_SIDE)


def _local_hour(t: float, utc_offset_s: int) -> float:
    """Local hour of day in [0, 24) of a Unix-seconds UTC instant."""
    return ((t + utc_offset_s) % 86400.0) / 3600.0


class _Geometry:
    """Edge lengths, edge end nodes and node coordinates of one road network."""

    def __init__(self, network: RoadNetwork) -> None:
        edges = network.edges.set_index("edge_id")
        nodes = network.nodes.set_index("node_id")
        self.length: dict[int, float] = edges["length_m"].astype(float).to_dict()
        self.tail: dict[int, int] = edges["u"].to_dict()
        self.head: dict[int, int] = edges["v"].to_dict()
        self.lat: dict[int, float] = nodes["lat"].astype(float).to_dict()
        self.lon: dict[int, float] = nodes["lon"].astype(float).to_dict()

    def route(
        self, edge_seq: Sequence[int], zones: Grid, grid: Grid
    ) -> tuple[float, int, int, tuple[int, ...]]:
        """(network length, origin zone, destination zone, edge-midpoint cells) of a route."""
        o, d = self.tail[edge_seq[0]], self.head[edge_seq[-1]]
        cells = tuple(
            grid.cell_of(
                (self.lat[self.tail[e]] + self.lat[self.head[e]]) / 2.0,
                (self.lon[self.tail[e]] + self.lon[self.head[e]]) / 2.0,
            )
            for e in edge_seq
        )
        return (
            float(sum(self.length[e] for e in edge_seq)),
            zones.cell_of(self.lat[o], self.lon[o]),
            zones.cell_of(self.lat[d], self.lon[d]),
            cells,
        )


def reference_trips(
    trips: Sequence[tuple[CleanTrajectory, Sequence[int]]],
    network: RoadNetwork,
    zones: Grid,
    grid: Grid,
    utc_offset_s: int,
) -> list[TripFeatures]:
    """Features of real trips: times from their own points, the rest from ``edge_seq``.

    Each item is a clean trip with its map-matched edge sequence, so length, zones and
    cells are featurised exactly as for a synthetic route on the same network (GPS
    length would differ from network length even for a perfect generator).
    """
    geo = _Geometry(network)
    out: list[TripFeatures] = []
    for t, edge_seq in trips:
        if len(t.points) < 2 or not edge_seq:
            continue
        t0, t1 = t.points[0][2], t.points[-1][2]
        length, o, d, cells = geo.route(edge_seq, zones, grid)
        out.append(
            TripFeatures(
                user_id=t.user_id,
                duration_s=float(t1 - t0),
                length_m=length,
                departure_hour=_local_hour(t0, utc_offset_s),
                origin_zone=o,
                dest_zone=d,
                cells=cells,
            )
        )
    return out


def carries_times(trips: Sequence[SyntheticTrajectory]) -> bool:
    """True when every synthetic trip (and at least one) carries a ``TimedRoute``."""
    return bool(trips) and all(isinstance(t.payload, TimedRoute) for t in trips)


def synthetic_trips(
    trips: Sequence[SyntheticTrajectory], network: RoadNetwork, zones: Grid, grid: Grid
) -> list[TripFeatures]:
    """Features of timed synthetic trips; length, zones and cells from the road network."""
    geo = _Geometry(network)
    out: list[TripFeatures] = []
    for t in trips:
        route = t.payload
        if not isinstance(route, TimedRoute):
            raise TypeError(f"synthetic_trips: {t.syn_id} payload is not a TimedRoute")
        length, o, d, cells = geo.route(route.edge_seq, zones, grid)
        out.append(
            TripFeatures(
                user_id="",
                duration_s=route.arrival_t - route.departure_t,
                length_m=length,
                departure_hour=_local_hour(route.departure_t, route.utc_offset_s),
                origin_zone=o,
                dest_zone=d,
                cells=cells,
            )
        )
    return out


# --- weighted distances -------------------------------------------------------------


def _cdf_at(values: np.ndarray, weights: np.ndarray, at: np.ndarray) -> np.ndarray:
    """Right-continuous weighted empirical CDF of ``values`` evaluated at ``at``."""
    order = np.argsort(values)
    cum = np.concatenate(([0.0], np.cumsum(weights[order])))
    cum /= cum[-1]
    return cum[np.searchsorted(values[order], at, side="right")]


def weighted_w1(x: np.ndarray, wx: np.ndarray, y: np.ndarray, wy: np.ndarray) -> float:
    """Exact W1 between two weighted samples: the integral of |F_x - F_y|."""
    if x.size == 0 or y.size == 0 or wx.sum() <= 0 or wy.sum() <= 0:
        return math.nan
    knots = np.sort(np.concatenate([x, y]))
    diff = _cdf_at(x, wx, knots[:-1]) - _cdf_at(y, wy, knots[:-1])
    return float(np.sum(np.abs(diff) * np.diff(knots)))


def circular_w1(
    x: np.ndarray, wx: np.ndarray, y: np.ndarray, wy: np.ndarray, period: float = 24.0
) -> float:
    """Exact W1 on a circle of the given circumference between two weighted samples.

    Uses min over a of the integral of |F_x - F_y - a| (Rabin, Delon & Gousseau,
    "Transportation distances on the circle", J. Math. Imaging Vis. 41, 2011); the
    minimising shift is the length-weighted median of the CDF difference.
    """
    if x.size == 0 or y.size == 0 or wx.sum() <= 0 or wy.sum() <= 0:
        return math.nan
    x, y = np.mod(x, period), np.mod(y, period)
    knots = np.unique(np.concatenate([[0.0], x, y, [period]]))
    diff = _cdf_at(x, wx, knots[:-1]) - _cdf_at(y, wy, knots[:-1])
    widths = np.diff(knots)
    order = np.argsort(diff)
    cum = np.cumsum(widths[order])
    shift = diff[order][np.searchsorted(cum, 0.5 * cum[-1])]
    return float(np.sum(np.abs(diff - shift) * widths))


# --- metric computation -----------------------------------------------------------


@dataclass(frozen=True)
class _Trips:
    """Column arrays of a trip population plus the unit (user) index of each trip."""

    unit: np.ndarray  # int: user index (reference) or trip index (synthetic)
    n_units: int
    duration: np.ndarray
    length: np.ndarray
    speed: np.ndarray
    hour: np.ndarray
    od: np.ndarray  # origin_zone * n_zones + dest_zone
    cell: np.ndarray  # utility-grid cell of every edge visit, all trips concatenated
    cell_trip: np.ndarray  # the trip index of each entry of ``cell``

    @classmethod
    def of(cls, trips: Sequence[TripFeatures]) -> "_Trips":
        """Arrays of a population; trips with an empty user_id are their own unit."""
        index: dict[str, int] = {}
        units = []
        for i, t in enumerate(trips):
            key = t.user_id if t.user_id else f"\0{i}"
            units.append(index.setdefault(key, len(index)))
        n_zones = OD_ZONES_PER_SIDE * OD_ZONES_PER_SIDE
        return cls(
            unit=np.asarray(units, dtype=int),
            n_units=len(index),
            duration=np.asarray([t.duration_s for t in trips], dtype=float),
            length=np.asarray([t.length_m for t in trips], dtype=float),
            speed=np.asarray([t.speed_mps for t in trips], dtype=float),
            hour=np.asarray([t.departure_hour for t in trips], dtype=float),
            od=np.asarray([t.origin_zone * n_zones + t.dest_zone for t in trips], dtype=int),
            cell=np.asarray([c for t in trips for c in t.cells], dtype=int),
            cell_trip=np.asarray([i for i, t in enumerate(trips) for _ in t.cells], dtype=int),
        )

    def weights(self, unit_draws: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        """Per-trip weights: each drawn unit splits its draw count over its (masked) trips."""
        keep = np.ones(self.unit.size, dtype=bool) if mask is None else mask
        per_unit = np.bincount(self.unit[keep], minlength=self.n_units).astype(float)
        w = np.zeros(self.unit.size)
        share = np.divide(unit_draws, per_unit, out=np.zeros(self.n_units), where=per_unit > 0)
        w[keep] = share[self.unit[keep]]
        return w


def _period_mask(hour: np.ndarray, start: float, end: float) -> np.ndarray:
    """Trips departing in [start, end) local hours."""
    return (hour >= start) & (hour < end)


def _jsd_or_nan(p: np.ndarray, q: np.ndarray) -> float:
    """JSD (bits) of two count vectors; NaN when either side is empty."""
    return jsd_bits(p, q) if p.sum() > 0 and q.sum() > 0 else math.nan


def _values(ref: _Trips, rd: np.ndarray, syn: _Trips, sd: np.ndarray) -> dict[str, float]:
    """Every timed metric for given unit draw counts on both sides."""
    wr, ws = ref.weights(rd), syn.weights(sd)
    n_cells = (OD_ZONES_PER_SIDE * OD_ZONES_PER_SIDE) ** 2
    od_r = np.bincount(ref.od, weights=wr, minlength=n_cells)
    od_s = np.bincount(syn.od, weights=ws, minlength=n_cells)
    # Cell-visit counts summed over trips, each trip's edge visits scaled by its weight
    # (the statistic of unpaired_cell_js_divergence in evaluation.utility, per user).
    n_grid = int(max(ref.cell.max(initial=-1), syn.cell.max(initial=-1))) + 1
    cell_r = np.bincount(ref.cell, weights=wr[ref.cell_trip], minlength=n_grid)
    cell_s = np.bincount(syn.cell, weights=ws[syn.cell_trip], minlength=n_grid)
    out = {
        "duration_w1_s": weighted_w1(ref.duration, wr, syn.duration, ws),
        "speed_w1_mps": weighted_w1(ref.speed, wr, syn.speed, ws),
        "departure_hour_circ_w1_h": circular_w1(ref.hour, wr, syn.hour, ws),
        "od3x3_jsd": _jsd_or_nan(od_r, od_s),
        "cell_js_divergence": _jsd_or_nan(cell_r, cell_s),
        "length_w1_m": weighted_w1(ref.length, wr, syn.length, ws),
    }
    for (_, start, end), name in zip(DEPARTURE_PERIODS, PERIOD_METRICS, strict=True):
        mr, ms = _period_mask(ref.hour, start, end), _period_mask(syn.hour, start, end)
        out[name] = weighted_w1(
            ref.duration[mr], ref.weights(rd, mr)[mr], syn.duration[ms], syn.weights(sd, ms)[ms]
        )
    return out


def _draw_counts(n: int, rng: np.random.Generator) -> np.ndarray:
    """How often each of n units is drawn in one bootstrap resample."""
    return np.bincount(rng.integers(0, n, size=n), minlength=n).astype(float)


def _interval(samples: np.ndarray, ci: float) -> tuple[float, float]:
    """Percentile interval of the finite bootstrap replicates (NaN when none is finite)."""
    finite = samples[np.isfinite(samples)]
    if finite.size == 0:
        return math.nan, math.nan
    alpha = (1.0 - ci) / 2.0
    return float(np.quantile(finite, alpha)), float(np.quantile(finite, 1.0 - alpha))


def timed_utility(
    reference: Sequence[TripFeatures],
    synthetic: Sequence[TripFeatures],
    *,
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> dict[str, tuple[float, float, float]]:
    """(point, ci_low, ci_high) of every timed metric, reference weighted per user."""
    if not reference or not synthetic:
        return {name: (math.nan, math.nan, math.nan) for name in TIMED_UTILITY_METRICS}
    ref, syn = _Trips.of(reference), _Trips.of(synthetic)
    point = _values(ref, np.ones(ref.n_units), syn, np.ones(syn.n_units))
    if n_bootstrap <= 0:
        return {name: (point[name], math.nan, math.nan) for name in TIMED_UTILITY_METRICS}
    reps = {name: np.empty(n_bootstrap) for name in TIMED_UTILITY_METRICS}
    for b in range(n_bootstrap):
        rd, sd = _draw_counts(ref.n_units, rng), _draw_counts(syn.n_units, rng)
        for name, value in _values(ref, rd, syn, sd).items():
            reps[name][b] = value
    return {name: (point[name], *_interval(reps[name], ci)) for name in TIMED_UTILITY_METRICS}


# --- gain over the prior ------------------------------------------------------------


def gain(prior: float, arm: float, oracle: float) -> float:
    """Share of the prior-to-oracle gap an arm closes: (prior - arm) / (prior - oracle)."""
    gap = prior - oracle
    if not (math.isfinite(gap) and math.isfinite(arm)) or gap == 0.0:
        return math.nan
    return (prior - arm) / gap


@dataclass(frozen=True, slots=True)
class UtilityGain:
    """Gain of one arm over the prior on one metric, with a user-bootstrap interval."""

    metric: str
    prior: float
    arm: float
    oracle: float
    gain: float
    ci_low: float
    ci_high: float
    n_bootstrap: int
    oracle_beats_prior: bool

    @property
    def counts_as_evidence(self) -> bool:
        """False when even the oracle does not beat the prior: reported, never counted."""
        return self.oracle_beats_prior


def utility_gain(
    reference: Sequence[TripFeatures],
    prior: Sequence[TripFeatures],
    arm: Sequence[TripFeatures],
    oracle: Sequence[TripFeatures],
    *,
    metric: str,
    n_bootstrap: int,
    ci: float = 0.95,
    rng: np.random.Generator,
) -> UtilityGain:
    """Gain of ``arm`` over ``prior`` toward ``oracle`` on one metric (lower is better).

    The interval resamples reference users with replacement and evaluates all three
    arms on the same resample (paired), so it reflects which test users happen to be
    held out; the synthetic samples stay fixed, and variation across seeds is the job
    of ``trajguard repeat``. The oracle beats the prior when its point value is lower.
    """
    if metric not in TIMED_UTILITY_METRICS:
        raise ValueError(f"unknown timed utility metric {metric!r}")
    ref = _Trips.of(reference)
    arms = [_Trips.of(a) for a in (prior, arm, oracle)]
    fixed = [np.ones(a.n_units) for a in arms]

    def triple(rd: np.ndarray) -> tuple[float, float, float]:
        p, a, o = (_values(ref, rd, s, sd)[metric] for s, sd in zip(arms, fixed, strict=True))
        return p, a, o

    p, a, o = triple(np.ones(ref.n_units))
    reps = np.array(
        [gain(*triple(_draw_counts(ref.n_units, rng))) for _ in range(max(n_bootstrap, 0))]
    )
    lo, hi = _interval(reps, ci) if reps.size else (math.nan, math.nan)
    return UtilityGain(
        metric=metric,
        prior=p,
        arm=a,
        oracle=o,
        gain=gain(p, a, o),
        ci_low=lo,
        ci_high=hi,
        n_bootstrap=n_bootstrap,
        oracle_beats_prior=bool(math.isfinite(p) and math.isfinite(o) and o < p),
    )
