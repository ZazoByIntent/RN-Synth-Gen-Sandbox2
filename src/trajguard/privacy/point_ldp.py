"""Point-level ε-LDP: k-ary randomized response over grid cells (NACRT_MEHANIZMI §3, ZM-2).

The local-differential-privacy counterpart of geo-indistinguishability: every GPS
point is mapped to a cell of a regular grid over the map's bbox, the cell index goes
through k-ary generalized randomized response (``grr_perturb`` in ``privacy/ldp.py``:
the true cell is reported with probability e^ε/(e^ε + k − 1), any other cell with
probability 1/(e^ε + k − 1)), and the released point is a uniformly random point
inside the *reported* cell (``jitter=True``, the default) or its centre
(``jitter=False``). Timestamps are unchanged.

ε unit: ε is spent **per point**, and ``spent_budget`` is the naive sequential
composition ε · (number of points released) — the same accounting as geo-ind, but a
different unit from LDPTrace / RN-LDP-Synth (ε per trajectory). The values are not
comparable across those mechanisms. Jitter is post-processing of the report with
independent randomness, so the per-point guarantee stays ε-LDP.

The grid's bbox is the map's bbox, injected by the orchestrator (``bbox=`` is
signature-driven there, like ``network=`` for generators), because a list-valued YAML
param would expand into one arm per coordinate. ``n_rows``/``n_cols`` default to the
20 × 20 utility grid of the S4 configs (k = 400): over Beijing a cell is ~1.5 × 1.7 km.
Baseline candidate — the baseline set for the paper (decision D5) is still open.
"""

from typing import Any

import numpy as np

from trajguard.datamodel import ProtectedTrajectory
from trajguard.experiments.registry import register
from trajguard.privacy.base import PrivacyMechanism, params_hash
from trajguard.privacy.ldp import grr_perturb
from trajguard.representation import Grid, TrajectoryView


@register("mechanism", "point_ldp")
class PointLDP(PrivacyMechanism):
    """Per-point ε-LDP over a grid: GRR on the cell index, release a point in the reported cell.

    ``epsilon`` is the LDP level per point over ``n_rows × n_cols`` cells spanning
    ``bbox`` (``(min_lon, min_lat, max_lon, max_lat)``, the map's bbox). Points outside
    the bbox clamp to the border cell (``Grid.cell_of``), so every released point lies
    inside the bbox. One Generator is built from ``seed`` and consumed across
    ``apply()`` calls; the GRR draws of a trajectory come before its jitter draws, so
    the reported cells are the same for ``jitter=True`` and ``jitter=False``.
    """

    guarantee = "ldp"

    def __init__(
        self,
        epsilon: float,
        bbox: tuple[float, float, float, float],
        n_rows: int = 20,
        n_cols: int = 20,
        jitter: bool = True,
        seed: int = 0,
    ) -> None:
        """Validate the grid and level; ``bbox`` is the map's bbox (injected, not from YAML)."""
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if n_rows < 1 or n_cols < 1:
            raise ValueError(f"n_rows and n_cols must be >= 1, got {n_rows}x{n_cols}")
        if n_rows * n_cols < 2:
            raise ValueError("the grid needs at least 2 cells (randomized response over k >= 2)")
        values = tuple(float(x) for x in bbox)
        if len(values) != 4:
            raise ValueError(f"bbox must be (min_lon, min_lat, max_lon, max_lat), got {bbox!r}")
        if values[0] >= values[2] or values[1] >= values[3]:
            raise ValueError(f"bbox must have min < max, got {list(values)}")
        super().__init__(seed)
        self.epsilon = float(epsilon)
        self.n_rows = int(n_rows)
        self.n_cols = int(n_cols)
        self.jitter = bool(jitter)
        self.grid = Grid(
            bbox=(values[0], values[1], values[2], values[3]),
            n_rows=self.n_rows,
            n_cols=self.n_cols,
        )
        self._params = {
            "epsilon": self.epsilon,
            "bbox": list(self.grid.bbox),
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "jitter": self.jitter,
            "seed": seed,
        }
        self._rng = np.random.default_rng(seed)
        self._spent = 0.0

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the GPS view with every point replaced by a point of its GRR-reported cell."""
        points = traj.as_gps()
        k = self.grid.n_cells
        reported = [
            grr_perturb(self.grid.cell_of(lat, lon), k, self.epsilon, self._rng)
            for lat, lon, _ in points
        ]
        n = len(points)
        offsets = self._rng.random((n, 2)) if self.jitter else np.full((n, 2), 0.5)
        min_lon, min_lat, max_lon, max_lat = self.grid.bbox
        released: list[tuple[float, float, float]] = []
        for (_, _, t), cell, (u, v) in zip(points, reported, offsets, strict=True):
            c_min_lon, c_min_lat, c_max_lon, c_max_lat = self.grid.cell_bounds(cell)
            lat = c_min_lat + float(u) * (c_max_lat - c_min_lat)
            lon = c_min_lon + float(v) * (c_max_lon - c_min_lon)
            # the outer cell edges are computed, not stored: clamp away rounding overshoot
            lat = min(max(lat, min_lat), max_lat)
            lon = min(max(lon, min_lon), max_lon)
            released.append((lat, lon, t))
        self._spent += self.epsilon * n
        return ProtectedTrajectory(
            traj_id=f"point_ldp/{traj.traj_id}",
            source_traj_id=traj.traj_id,
            mechanism_id="point_ldp",
            params_hash=params_hash(self._params),
            guarantee=self.guarantee,
            epsilon=self.epsilon,
            payload=tuple(released),
            map_id=traj.map_id,
        )

    def spent_budget(self) -> float | None:
        """Naive sequential-composition upper bound: epsilon per released point."""
        return self._spent
