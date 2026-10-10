"""Trajectory cleaning: speed filter, thinning, minimum-size checks (design §5, step 3).

Optionally (``cleaning.split_sessions``, off by default) one recorded session is cut
into trips at stops and recording gaps, so trip durations do not contain dwell time
(docs/NACRT_ULDP_RANGI.md §8 point 4, prerequisite P10).
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from trajguard.datamodel import CleanTrajectory, RawTrajectory

_EARTH_RADIUS_M = 6_371_000.0

# Session-split rule, fixed by docs/NACRT_ULDP_RANGI.md §8 point 4 (P10): a stop is at
# least 3 minutes spent within 150 m, or a recording gap of at least 3 minutes with a
# displacement under 300 m. The plan takes these values from its evaluator's worked
# example and cites no further source; they are never tuned on Geolife. The stop part
# has the shape of classic stay-point detection (Li et al., "Mining user similarity
# based on location history", ACM SIGSPATIAL GIS 2008: an anchor point and every later
# point within a distance threshold, kept if the span lasts at least a time threshold).
STOP_RADIUS_M = 150.0
STOP_MIN_DURATION_S = 180.0
GAP_MIN_DURATION_S = 180.0
GAP_MAX_DISPLACEMENT_M = 300.0
# Version of the split rule as a whole, folded into the pool-cache key with the option
# on. Version 2: a session that passes cleaning but whose every piece fails the minimum
# checks is kept whole, so a user's participation never hinges on their stop structure.
SESSION_SPLIT_RULE_VERSION = 2

_Point = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class CleaningConfig:
    """Cleaning thresholds; field names mirror the design §8 ``cleaning:`` block."""

    max_speed_kmh: float = 200.0
    min_points: int = 20
    min_length_m: float = 500.0
    resample_s: float = 5.0
    split_sessions: bool = False


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def session_split_rule() -> dict[str, float]:
    """The fixed session-split thresholds, as folded into the pool-cache key."""
    return {
        "rule_version": float(SESSION_SPLIT_RULE_VERSION),
        "stop_radius_m": STOP_RADIUS_M,
        "stop_min_duration_s": STOP_MIN_DURATION_S,
        "gap_min_duration_s": GAP_MIN_DURATION_S,
        "gap_max_displacement_m": GAP_MAX_DISPLACEMENT_M,
    }


def _trajectory(
    traj_id: str,
    user_id: str,
    points: tuple[_Point, ...],
    flags: tuple[str, ...],
    cfg: CleaningConfig,
) -> CleanTrajectory | None:
    """Apply the minimum checks to a cleaned point sequence and build the trajectory."""
    if len(points) < cfg.min_points:
        return None
    length_m = sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in pairwise(points))
    if length_m < cfg.min_length_m:
        return None

    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    duration_s = points[-1][2] - points[0][2]
    return CleanTrajectory(
        traj_id=traj_id,
        user_id=user_id,
        points=points,
        bbox=(min(lons), min(lats), max(lons), max(lats)),
        duration_s=duration_s,
        length_m=length_m,
        mean_speed=length_m / duration_s if duration_s > 0 else 0.0,
        cleaning_flags=flags,
        split=None,
    )


def clean(raw: RawTrajectory, cfg: CleaningConfig) -> CleanTrajectory | None:
    """Clean one raw trajectory; returns None when it fails the minimum checks.

    Steps: (1) drop points implying speed > ``max_speed_kmh`` from the last kept
    point (also drops non-monotonic timestamps); (2) thin so consecutive points
    are >= ``resample_s`` apart (no interpolation — no fabricated positions before
    map matching); (3) reject if < ``min_points`` points or < ``min_length_m`` long.
    Ignores ``split_sessions``; :func:`clean_trips` applies it.
    """
    kept: list[_Point] = []
    outliers = 0
    for p in raw.points:
        lat, lon, t = p[0], p[1], p[2]
        if not kept:
            kept.append((lat, lon, t))
            continue
        last = kept[-1]
        dt = t - last[2]
        if dt <= 0:
            outliers += 1
            continue
        speed_kmh = haversine_m(last[0], last[1], lat, lon) / dt * 3.6
        if speed_kmh > cfg.max_speed_kmh:
            outliers += 1
            continue
        kept.append((lat, lon, t))

    thinned: list[_Point] = []
    for point in kept:
        if not thinned or point[2] - thinned[-1][2] >= cfg.resample_s:
            thinned.append(point)

    flags = (f"speed_outliers_dropped:{outliers}", f"resampled:{cfg.resample_s:g}s")
    return _trajectory(raw.traj_id, raw.user_id, tuple(thinned), flags, cfg)


def find_cuts(points: tuple[_Point, ...]) -> list[tuple[int, int]]:
    """Cut points of a session as ``(end, start)`` index pairs, in order.

    A trip ends at index ``end`` (inclusive) and the next one starts at ``start``; the
    points strictly between them are dwell. A gap cut (consecutive points at least
    ``GAP_MIN_DURATION_S`` apart, less than ``GAP_MAX_DISPLACEMENT_M`` apart in space)
    has ``start == end + 1``. A stop cut spans the anchor point ``end`` and the last
    following point ``start`` such that every point in between lies within
    ``STOP_RADIUS_M`` of the anchor and the span lasts at least ``STOP_MIN_DURATION_S``.
    """
    cuts: list[tuple[int, int]] = []
    n = len(points)
    i = 0
    while i < n - 1:
        a, b = points[i], points[i + 1]
        if (
            b[2] - a[2] >= GAP_MIN_DURATION_S
            and haversine_m(a[0], a[1], b[0], b[1]) < GAP_MAX_DISPLACEMENT_M
        ):
            cuts.append((i, i + 1))
            i += 1
            continue
        j = i
        while j + 1 < n and haversine_m(a[0], a[1], points[j + 1][0], points[j + 1][1]) <= (
            STOP_RADIUS_M
        ):
            j += 1
        if points[j][2] - a[2] >= STOP_MIN_DURATION_S:
            cuts.append((i, j))
            i = j
            continue
        i += 1
    return cuts


def split_at_stops(points: tuple[_Point, ...]) -> list[tuple[_Point, ...]]:
    """Split a session's points into trips at the cuts of :func:`find_cuts`."""
    pieces: list[tuple[_Point, ...]] = []
    start = 0
    for end, nxt in find_cuts(points):
        pieces.append(points[start : end + 1])
        start = nxt
    pieces.append(points[start:])
    return pieces


def clean_trips(raw: RawTrajectory, cfg: CleaningConfig) -> list[CleanTrajectory]:
    """Clean one raw session; with ``cfg.split_sessions`` also cut it into trips at stops.

    With the option off this is ``[clean(raw, cfg)]`` minus a rejected session, so the
    output is exactly today's. With it on, a session without a cut is returned whole
    under its own id; otherwise each piece is re-checked against ``min_points`` and
    ``min_length_m`` and kept as ``<traj_id>_trip<k>`` (``k`` the piece's position in
    the session) with the same ``user_id``. If no piece survives those checks, the
    cleaned session is returned whole under its own id, so a session that passes
    cleaning always yields at least one trip and the user's presence in the population
    does not depend on their private stop structure. A rejected session yields no trip.
    """
    whole = clean(raw, cfg)
    if whole is None:
        return []
    if not cfg.split_sessions:
        return [whole]
    pieces = split_at_stops(whole.points)
    if len(pieces) == 1:
        return [whole]
    trips: list[CleanTrajectory] = []
    for k, piece in enumerate(pieces):
        flags = (*whole.cleaning_flags, f"session_trip:{k}")
        trip = _trajectory(f"{raw.traj_id}_trip{k}", raw.user_id, piece, flags, cfg)
        if trip is not None:
            trips.append(trip)
    return trips or [whole]
