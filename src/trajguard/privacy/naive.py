"""Three protection baselines without a formal guarantee (NACRT_MEHANIZMI §4, ZM-3).

What practice most often does instead of a differentially private mechanism: spatial
rounding (snap every coordinate to the centre of a square cell), temporal downsampling
(keep one point per time interval) and Gaussian location noise. None of them carries a
privacy guarantee — ``guarantee = "none"``, ``spent_budget()`` is ``None`` and there is
no ``epsilon`` attribute — so the results table lists their arms by parameter
(``cell_m=500.0`` etc.) and the ``by_epsilon`` plot skips them. Their purpose is breadth
in the risk matrix next to geo-indistinguishability and point LDP: the same attacks
(reidentification after re-matching, home/work inference, utility) run over their
releases. All three are baseline candidates — the baseline set for the paper (decision
D5) is still open.

Meter offsets become degrees via the local equirectangular approximation of
``geoind.py``: one degree of latitude is 111,320 m, one degree of longitude is
111,320 · cos φ m. Timestamps are never changed; temporal downsampling drops points,
the other two keep the point count.
"""

import math
from typing import Any

import numpy as np

from trajguard.datamodel import ProtectedTrajectory
from trajguard.experiments.registry import register
from trajguard.privacy.base import PrivacyMechanism, params_hash
from trajguard.representation import TrajectoryView

_METERS_PER_DEG_LAT = 111_320.0  # the equirectangular constant of geoind.py

Point = tuple[float, float, float]


def _positive_finite(name: str, value: float) -> float:
    """Validate a strictly positive, finite mechanism parameter; returns it as float."""
    out = float(value)
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value!r}")
    return out


def _release(
    traj: TrajectoryView, name: str, params: dict[str, Any], payload: tuple[Point, ...]
) -> ProtectedTrajectory:
    """The ProtectedTrajectory shared by the three mechanisms: no guarantee, no epsilon."""
    return ProtectedTrajectory(
        traj_id=f"{name}/{traj.traj_id}",
        source_traj_id=traj.traj_id,
        mechanism_id=name,
        params_hash=params_hash(params),
        guarantee="none",
        epsilon=None,
        payload=payload,
        map_id=traj.map_id,
    )


@register("mechanism", "spatial_rounding")
class SpatialRounding(PrivacyMechanism):
    """Snaps every point to the centre of its ``cell_m`` × ``cell_m`` metre cell on a global grid.

    The grid is anchored at (0°, 0°): latitude is rounded to the centre of a
    ``cell_m / 111,320°`` band, longitude to the centre of a ``cell_m / (111,320 · cos φ)°``
    band whose width is computed at the *rounded* latitude, so applying the mechanism
    twice equals applying it once (released points lie on the grid and stay there).
    Cells are square in metres, no bbox is needed and no point is clamped. The maximum
    displacement is ``cell_m · √2 / 2`` (half the cell diagonal), the mean displacement
    of a uniformly placed point ≈ 0.38 · ``cell_m``. Consecutive points inside one cell
    become identical released points and are kept as they are (a faithful release; the
    matcher tolerates duplicates). Deterministic: ``seed`` is accepted because the
    orchestrator passes it to every mechanism, and ignored.
    """

    guarantee = "none"

    def __init__(self, cell_m: float, seed: int = 0) -> None:
        """Validate the cell size (metres, > 0)."""
        super().__init__(seed)
        self.cell_m = _positive_finite("cell_m", cell_m)
        self._params = {"cell_m": self.cell_m}

    def round_point(self, lat: float, lon: float) -> tuple[float, float]:
        """Centre of the grid cell containing (lat, lon)."""
        d_lat = self.cell_m / _METERS_PER_DEG_LAT
        lat_c = (math.floor(lat / d_lat) + 0.5) * d_lat
        d_lon = self.cell_m / (_METERS_PER_DEG_LAT * math.cos(math.radians(lat_c)))
        lon_c = (math.floor(lon / d_lon) + 0.5) * d_lon
        return lat_c, lon_c

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the GPS view with every point moved to its cell centre."""
        rounded: list[Point] = []
        for lat, lon, t in traj.as_gps():
            lat_c, lon_c = self.round_point(lat, lon)
            rounded.append((lat_c, lon_c, t))
        return _release(traj, "spatial_rounding", self._params, tuple(rounded))

    def spent_budget(self) -> float | None:
        """No formal guarantee — no budget is spent."""
        return None


@register("mechanism", "temporal_downsampling")
class TemporalDownsampling(PrivacyMechanism):
    """Keeps the first point, then one point per ``interval_s``, and always the last point.

    The release is a time-subsequence of the input: the first point is always released,
    a later point is released when its timestamp is at least ``interval_s`` after the
    last released one, and the last point is always released (so the final gap may be
    shorter than ``interval_s``). Coordinates and timestamps are unchanged, only their
    number drops; trajectories of one or two points pass unchanged, and ``interval_s``
    at or below the cleaning step (5 s in the Geolife configs) is the identity, which the
    orchestrator recognises and does not re-match. A release can fall below the
    attacker's ``known_points`` and the cleaning ``min_points``: the linkage attack takes
    its known points from the raw pool and DTW handles any non-empty gallery sequence,
    while re-matching of a very short release often fails — a measured effect
    (``n_rematch_dropped``), not an error. Deterministic; ``seed`` is ignored.
    """

    guarantee = "none"

    def __init__(self, interval_s: float, seed: int = 0) -> None:
        """Validate the minimum spacing between released points (seconds, > 0)."""
        super().__init__(seed)
        self.interval_s = _positive_finite("interval_s", interval_s)
        self._params = {"interval_s": self.interval_s}

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the GPS view thinned to one point per ``interval_s``, first and last kept."""
        points = traj.as_gps()
        kept: list[int] = []
        for i, p in enumerate(points):
            if not kept or p[2] - points[kept[-1]][2] >= self.interval_s:
                kept.append(i)
        if points and kept[-1] != len(points) - 1:
            kept.append(len(points) - 1)
        thinned = tuple(points[i] for i in kept)
        return _release(traj, "temporal_downsampling", self._params, thinned)

    def spent_budget(self) -> float | None:
        """No formal guarantee — no budget is spent."""
        return None


@register("mechanism", "gaussian_noise")
class GaussianNoise(PrivacyMechanism):
    """Adds independent N(0, ``sigma_m``²) noise (metres) on the north and east axis of every point.

    Not the differentially private Gaussian mechanism: there is no sensitivity and no δ,
    ``sigma_m`` is simply the noise scale in metres per axis. The radial displacement is
    then Rayleigh-distributed with RMS ``sigma_m · √2`` and mean ``sigma_m · √(π/2)``
    (≈ 1.25 · ``sigma_m``); at ``sigma_m`` = 200 m it lies in the range of geo-ind at
    ε = 1 per 100 m (mean displacement 200 m). One Generator is built from ``seed`` and
    consumed across ``apply()`` calls, as in ``geoind.py``; the same seed reproduces the
    same release.
    """

    guarantee = "none"

    def __init__(self, sigma_m: float, seed: int = 0) -> None:
        """Validate the per-axis noise scale (metres, > 0) and seed the Generator."""
        super().__init__(seed)
        self.sigma_m = _positive_finite("sigma_m", sigma_m)
        self._params = {"sigma_m": self.sigma_m, "seed": seed}
        self._rng = np.random.default_rng(seed)

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the GPS view with independent Gaussian offsets on every point."""
        points = traj.as_gps()
        offsets = self._rng.normal(0.0, self.sigma_m, size=(len(points), 2))
        noisy = tuple(
            (
                lat + float(north) / _METERS_PER_DEG_LAT,
                lon + float(east) / (_METERS_PER_DEG_LAT * math.cos(math.radians(lat))),
                t,
            )
            for (lat, lon, t), (north, east) in zip(points, offsets, strict=True)
        )
        return _release(traj, "gaussian_noise", self._params, noisy)

    def spent_budget(self) -> float | None:
        """No formal guarantee — no budget is spent."""
        return None
