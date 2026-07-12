"""Trajectory cleaning: speed filter, thinning, minimum-size checks (design §5, step 3)."""

import math
from dataclasses import dataclass
from itertools import pairwise

from trajguard.datamodel import CleanTrajectory, RawTrajectory

_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True, slots=True)
class CleaningConfig:
    """Cleaning thresholds; field names mirror the design §8 ``cleaning:`` block."""

    max_speed_kmh: float = 200.0
    min_points: int = 20
    min_length_m: float = 500.0
    resample_s: float = 5.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def clean(raw: RawTrajectory, cfg: CleaningConfig) -> CleanTrajectory | None:
    """Clean one raw trajectory; returns None when it fails the minimum checks.

    Steps: (1) drop points implying speed > ``max_speed_kmh`` from the last kept
    point (also drops non-monotonic timestamps); (2) thin so consecutive points
    are >= ``resample_s`` apart (no interpolation — no fabricated positions before
    map matching); (3) reject if < ``min_points`` points or < ``min_length_m`` long.
    """
    kept: list[tuple[float, float, float]] = []
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

    thinned: list[tuple[float, float, float]] = []
    for point in kept:
        if not thinned or point[2] - thinned[-1][2] >= cfg.resample_s:
            thinned.append(point)

    if len(thinned) < cfg.min_points:
        return None
    length_m = sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in pairwise(thinned))
    if length_m < cfg.min_length_m:
        return None

    lats = [p[0] for p in thinned]
    lons = [p[1] for p in thinned]
    duration_s = thinned[-1][2] - thinned[0][2]
    return CleanTrajectory(
        traj_id=raw.traj_id,
        user_id=raw.user_id,
        points=tuple(thinned),
        bbox=(min(lons), min(lats), max(lons), max(lats)),
        duration_s=duration_s,
        length_m=length_m,
        mean_speed=length_m / duration_s if duration_s > 0 else 0.0,
        cleaning_flags=(
            f"speed_outliers_dropped:{outliers}",
            f"resampled:{cfg.resample_s:g}s",
        ),
        split=None,
    )
