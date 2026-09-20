"""PrivTrace's two-layer adaptive grid (Wang et al., USENIX Security 2023).

PrivTrace discretises space twice. The first layer is a uniform ``k x k`` grid over the
data bounding box. Each level-1 cell is then split again into ``kappa_i x kappa_i`` equal
sub-cells -- finely where the data is dense, not at all (``kappa_i = 1``) where it is
sparse. The leaves of that two-layer split are the *states* of the Markov model PrivTrace
estimates. This module holds the geometry and the deterministic subdivision rule only; it
never adds noise. The caller measures the level-1 densities with :func:`level1_density`,
adds its own Laplace noise under its own budget, and hands the noisy vector to
:meth:`AdaptiveGrid.build`.

**Subdivision rule.** A level-1 cell is split only when its noisy density exceeds
``split_gate * n_trajectories / k**2`` (five per cent of the uniform share), and then
``kappa_i = ceil(sqrt(density_i / split_scale))``, clamped to ``[1, max_sub_k]``. This
follows the authors' code (``discretization/divide.py``, ``discretization/grid.py``)
rather than the paper, because the paper gives the rule twice and the two versions
disagree by a factor of 1000: section 5.1 has ``kappa_i = sqrt(d_i * K * pop / 2e7)``
while the worked example in Appendix E uses ``sqrt(d_i * K * pop / 20000)``. The code's
form -- which carries neither ``K`` nor ``pop``, but does carry the gate, which the paper
never mentions -- is the only unambiguous version available. The upper clamp ``max_sub_k``
is ours: the reference has no cap, and without one a single dense cell can push the state
count (and with it the quadratic work downstream) past what this benchmark can run.

**Numbering.** Cells and sub-cells are numbered *row-major*: the row runs along ``y``
(latitude / northing), the column along ``x`` (longitude / easting), matching
:class:`trajguard.representation.Grid`. The reference numbers x-major instead
(``x_index * y_bin_number + y_index``). That changes only the integer label of a cell --
the geometry, the densities and the state count are identical.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

import numpy as np

Bbox = tuple[float, float, float, float]
"""``(x0, y0, x1, y1)``: x along longitude / easting, y along latitude / northing."""


def level1_cells(xy: np.ndarray, bbox: Bbox, k: int) -> np.ndarray:
    """Row-major level-1 cell index of every ``(x, y)`` point, as an int64 array.

    The row runs along ``y`` and the column along ``x``, so the cell index is
    ``row * k + col`` with ``col = floor((x - x0) / (x1 - x0) * k)`` and the analogous
    expression for the row. Both indices are clamped to ``[0, k - 1]``, so a point on the
    upper border falls into the last cell and a point outside the bbox clamps into the
    nearest border cell instead of raising.
    """
    points = _validated_xy(xy)
    x0, y0, x1, y1 = _validated_bbox(bbox)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    cells: np.ndarray = _bin_index(points[:, 1], y0, y1, k) * k + _bin_index(
        points[:, 0], x0, x1, k
    )
    return cells


def level1_density(points: Sequence[np.ndarray], bbox: Bbox, k: int) -> np.ndarray:
    """Length-normalised visit density of a trajectory set over the ``k * k`` level-1 cells.

    Every trajectory contributes ``1 / n_points`` per point, i.e. exactly 1 in total no
    matter how long it is, so one trajectory can change the vector by at most 1 in L1 norm
    and the L1 sensitivity of the whole histogram is 1 (the reference's
    ``give_regularized_trajectory_cell_density``). ``points`` is one ``(n, 2)`` array of
    ``(x, y)`` coordinates per trajectory; the result sums to the number of trajectories.
    """
    _validated_bbox(bbox)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    density = np.zeros(k * k, dtype=np.float64)
    for trajectory in points:
        cells = level1_cells(trajectory, bbox, k)
        density += np.bincount(cells, minlength=k * k).astype(np.float64) / float(cells.size)
    return density


@dataclass(frozen=True)
class AdaptiveGrid:
    """A built two-layer grid: ``k x k`` level-1 cells, cell ``i`` split ``kappa_i`` ways.

    Immutable and noise-free. Build it with :meth:`build` from a *noisy* level-1 density;
    afterwards :meth:`states_of` maps points to leaf states and :meth:`state_bounds` maps a
    leaf state back to its rectangle.
    """

    bbox: Bbox
    k: int
    kappa: tuple[int, ...]
    """Per level-1 cell (row-major): the cell is split into ``kappa_i x kappa_i``
    sub-cells; ``1`` means it is not split."""
    offsets: tuple[int, ...]
    """Per level-1 cell (row-major): the leaf-state id of its first sub-cell, i.e. the
    exclusive prefix sums of ``kappa_i ** 2``."""

    @property
    def n_states(self) -> int:
        """Total number of leaf states, ``sum(kappa_i ** 2)``."""
        return int(self._sizes.sum())

    @classmethod
    def build(
        cls,
        bbox: Bbox,
        k: int,
        noisy_density: np.ndarray,
        n_trajectories: int,
        split_scale: float = 200.0,
        split_gate: float = 0.05,
        max_sub_k: int = 8,
    ) -> "AdaptiveGrid":
        """Apply the reference subdivision rule to a noisy level-1 density.

        Cell ``i`` is split only when ``noisy_density[i] > split_gate * n_trajectories /
        k**2``; then ``kappa_i = ceil(sqrt(noisy_density[i] / split_scale))`` clamped to
        ``[1, max_sub_k]``, otherwise ``kappa_i = 1``. Negative and NaN densities never
        pass the gate, so they count as "not split".
        """
        checked = _validated_bbox(bbox)
        if k < 2:
            raise ValueError(f"the level-1 grid must be at least 2x2, got k={k}")
        if n_trajectories < 1:
            raise ValueError(f"n_trajectories must be >= 1, got {n_trajectories}")
        density = np.asarray(noisy_density, dtype=np.float64)
        if density.shape != (k * k,):
            raise ValueError(
                f"noisy_density must have {k * k} entries for k={k}, got shape {density.shape}"
            )
        if split_scale <= 0:
            raise ValueError(f"split_scale must be > 0, got {split_scale}")
        if split_gate < 0:
            raise ValueError(f"split_gate must be >= 0, got {split_gate}")
        if max_sub_k < 1:
            raise ValueError(f"max_sub_k must be >= 1, got {max_sub_k}")

        finite = np.where(np.isnan(density), -np.inf, density)
        threshold = split_gate * n_trajectories / float(k * k)
        split = finite > threshold
        kappa = np.ones(k * k, dtype=np.int64)
        sub_k = np.ceil(np.sqrt(finite[split] / split_scale)).astype(np.int64)
        kappa[split] = np.clip(sub_k, 1, max_sub_k)
        offsets = np.concatenate([[0], np.cumsum(kappa * kappa)[:-1]])
        return cls(
            bbox=checked,
            k=k,
            kappa=tuple(int(v) for v in kappa),
            offsets=tuple(int(v) for v in offsets),
        )

    def states_of(self, xy: np.ndarray) -> np.ndarray:
        """Leaf state of every ``(x, y)`` point, as an int64 array.

        The point is first placed in its level-1 cell, then in the row-major sub-cell
        inside that cell's rectangle (sub-row along ``y``, sub-column along ``x``), both
        clamped; the leaf id is ``offsets[cell] + sub_row * kappa + sub_col``.
        """
        points = _validated_xy(xy)
        x0, y0, x1, y1 = self.bbox
        cells = level1_cells(points, self.bbox, self.k)
        kappa = self._kappa_array[cells]
        width = (x1 - x0) / self.k
        height = (y1 - y0) / self.k
        cell_x0 = x0 + (cells % self.k) * width
        cell_y0 = y0 + (cells // self.k) * height
        sub_col = np.floor((points[:, 0] - cell_x0) / width * kappa).astype(np.int64)
        sub_row = np.floor((points[:, 1] - cell_y0) / height * kappa).astype(np.int64)
        states: np.ndarray = (
            self._offset_array[cells]
            + np.clip(sub_row, 0, kappa - 1) * kappa
            + np.clip(sub_col, 0, kappa - 1)
        )
        return states

    def sequence_of(self, xy: np.ndarray) -> list[int]:
        """Leaf states of a trajectory with consecutive duplicates collapsed.

        Nothing is interpolated: two consecutive points may land in states that are far
        apart, exactly as in the reference (``unreapted_int_array``), which never bridges
        the gap on the input side.
        """
        states = self.states_of(xy)
        keep = np.ones(states.size, dtype=bool)
        keep[1:] = states[1:] != states[:-1]
        return [int(state) for state in states[keep]]

    def state_bounds(self, state: int) -> Bbox:
        """``(x0, y0, x1, y1)`` rectangle of a leaf state; the inverse of :meth:`states_of`."""
        cell = self.state_level1(state)
        kappa = self.kappa[cell]
        sub_row, sub_col = divmod(state - self.offsets[cell], kappa)
        x0, y0, x1, y1 = self.bbox
        width = (x1 - x0) / self.k
        height = (y1 - y0) / self.k
        cell_x0 = x0 + (cell % self.k) * width
        cell_y0 = y0 + (cell // self.k) * height
        return (
            cell_x0 + sub_col * width / kappa,
            cell_y0 + sub_row * height / kappa,
            cell_x0 + (sub_col + 1) * width / kappa,
            cell_y0 + (sub_row + 1) * height / kappa,
        )

    def state_level1(self, state: int) -> int:
        """Row-major level-1 cell that contains a leaf state."""
        if not 0 <= state < self.n_states:
            raise ValueError(f"state {state} lies outside the {self.n_states} leaf states")
        return int(np.searchsorted(self._offset_array, state, side="right")) - 1

    # -- cached array views of the tuple fields (hot paths; the grid is immutable) ------

    @cached_property
    def _kappa_array(self) -> np.ndarray:
        """``kappa`` as an int64 array."""
        return np.asarray(self.kappa, dtype=np.int64)

    @cached_property
    def _offset_array(self) -> np.ndarray:
        """``offsets`` as an int64 array."""
        return np.asarray(self.offsets, dtype=np.int64)

    @cached_property
    def _sizes(self) -> np.ndarray:
        """Leaf count ``kappa_i ** 2`` per level-1 cell, as an int64 array."""
        sizes: np.ndarray = self._kappa_array * self._kappa_array
        return sizes


def _validated_bbox(bbox: Bbox) -> Bbox:
    """``(x0, y0, x1, y1)`` as floats; the span must be positive on both axes."""
    if len(bbox) != 4:
        raise ValueError(f"bbox needs 4 numbers (x0, y0, x1, y1), got {bbox}")
    x0, y0, x1, y1 = (float(v) for v in bbox)
    if not (x0 < x1 and y0 < y1):
        raise ValueError(f"bbox must satisfy x0 < x1 and y0 < y1, got {bbox}")
    return (x0, y0, x1, y1)


def _validated_xy(xy: np.ndarray) -> np.ndarray:
    """``(n, 2)`` float64 array of points; empty or wrongly shaped input raises ValueError."""
    points = np.asarray(xy, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f"points must be an (n, 2) array of (x, y), got shape {points.shape}")
    if points.shape[0] == 0:
        raise ValueError("points must not be empty")
    return points


def _bin_index(values: np.ndarray, lo: float, hi: float, n_bins: int) -> np.ndarray:
    """``floor((v - lo) / (hi - lo) * n_bins)`` clamped to ``[0, n_bins - 1]``, as int64."""
    raw = np.floor((values - lo) / (hi - lo) * n_bins).astype(np.int64)
    index: np.ndarray = np.clip(raw, 0, n_bins - 1)
    return index
