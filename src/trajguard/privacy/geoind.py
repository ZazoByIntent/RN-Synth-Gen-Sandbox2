"""Geo-indistinguishability via the planar Laplace mechanism (Andrés 2013, design §7)."""

import math
from typing import Any

import numpy as np

from trajguard.datamodel import ProtectedTrajectory
from trajguard.experiments.registry import register
from trajguard.privacy.base import PrivacyMechanism, params_hash
from trajguard.representation import TrajectoryView

_METERS_PER_DEG_LAT = 111_320.0


@register("mechanism", "geo_indistinguishability")
class GeoIndistinguishability(PrivacyMechanism):
    """Perturbs every GPS point independently with planar Laplace noise.

    ``epsilon`` is the geo-indistinguishability level per ``unit_m`` meters
    (Andrés 2013: level l at radius r gives epsilon = l/r), so the effective
    per-meter parameter is ``epsilon / unit_m`` and the mean radial displacement
    is ``2 * unit_m / epsilon``. The planar Laplace radius follows the exact
    Gamma(shape=2, scale=unit_m/epsilon) law with a uniform angle; meter offsets
    become degrees via a local equirectangular approximation. Timestamps are
    left unchanged.
    """

    guarantee = "geo-ind"

    def __init__(self, epsilon: float, unit_m: float = 100.0, seed: int = 0) -> None:
        """One Generator is built from ``seed`` and consumed across apply() calls."""
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if unit_m <= 0:
            raise ValueError(f"unit_m must be > 0, got {unit_m}")
        super().__init__(seed)
        self.epsilon = float(epsilon)
        self.unit_m = float(unit_m)
        self._params = {"epsilon": self.epsilon, "unit_m": self.unit_m, "seed": seed}
        self._rng = np.random.default_rng(seed)
        self._spent = 0.0

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the trajectory's GPS view with independently perturbed points."""
        points = traj.as_gps()
        radii = self._rng.gamma(shape=2.0, scale=self.unit_m / self.epsilon, size=len(points))
        angles = self._rng.uniform(0.0, 2.0 * math.pi, size=len(points))
        noisy = tuple(
            (
                lat + r * math.sin(theta) / _METERS_PER_DEG_LAT,
                lon + r * math.cos(theta) / (_METERS_PER_DEG_LAT * math.cos(math.radians(lat))),
                t,
            )
            for (lat, lon, t), r, theta in zip(points, radii, angles, strict=True)
        )
        self._spent += self.epsilon * len(points)
        return ProtectedTrajectory(
            traj_id=f"geoind/{traj.traj_id}",
            source_traj_id=traj.traj_id,
            mechanism_id="geo_indistinguishability",
            params_hash=params_hash(self._params),
            guarantee=self.guarantee,
            epsilon=self.epsilon,
            payload=noisy,
            map_id=traj.map_id,
        )

    def spent_budget(self) -> float | None:
        """Naive sequential-composition upper bound: epsilon per perturbed point."""
        return self._spent
