"""Trajectory-distance primitives over (x, y) point sequences in projected metres.

Layer-neutral geometry shared by the linkage attack (DTW nearest-neighbour) and the
reconstruction metrics (Hausdorff, DTW, mean spatial error); kept here so the attacks
and evaluation layers reuse one implementation instead of duplicating it.

``DISTANCES`` is the single registry of the trajectory distances an attacker may be
configured with: ``dtw`` (the unnormalised warping cost, the distance of the measured
S4 record) and ``dtw_norm`` (that cost divided by the length of the optimal alignment).
``DEFAULT_DISTANCE`` names the first of the two and lives here, the one module of the
package that imports nothing from ``trajguard``, so the attack and reporting layers
share one literal instead of each keeping a copy that can drift.
"""

from collections.abc import Callable

import numpy as np


def _dtw_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cumulative DTW cost matrix of two non-empty (x, y) sequences, with an inf border.

    Shared by ``dtw`` and ``dtw_norm`` so the two cannot drift apart; ``cost[i, j]``
    is the best warping cost of the first ``i`` points of ``a`` against the first
    ``j`` points of ``b``, and row/column 0 is the border (only ``cost[0, 0]`` is 0).
    """
    n, m = len(a), len(b)
    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0.0
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            d = float(np.hypot(ai[0] - b[j - 1, 0], ai[1] - b[j - 1, 1]))
            cost[i, j] = d + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
    return cost


def _alignment_length(cost: np.ndarray) -> int:
    """Cells on the optimal warping path of a cost matrix, from the last cell back to (1, 1).

    Ties prefer the diagonal step, then the vertical one (``i-1, j``), then the
    horizontal one. The result is at least ``max(n, m)``: every step lowers ``i``
    or ``j`` (or both) by one.
    """
    i, j = cost.shape[0] - 1, cost.shape[1] - 1
    length = 1
    while i > 1 or j > 1:
        diagonal, vertical, horizontal = cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1]
        best = min(diagonal, vertical, horizontal)
        if diagonal == best:
            i, j = i - 1, j - 1
        elif vertical == best:
            i -= 1
        else:
            j -= 1
        length += 1
    return length


def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Dynamic time warping distance between two (x, y) point sequences (metres)."""
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    return float(_dtw_matrix(a, b)[n, m])


def dtw_norm(a: np.ndarray, b: np.ndarray) -> float:
    """Length-normalised DTW: the warping cost divided by its alignment length (metres).

    The unnormalised sum grows with the number of gallery points, so a short trace
    beats a long one whatever its geometry; dividing by ``L``, the number of cells
    on the optimal path, turns the cost into a per-matched-pair mean.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    cost = _dtw_matrix(a, b)
    return float(cost[n, m]) / _alignment_length(cost)


# The trajectory distances an attack may be configured with, by config name.
DISTANCES: dict[str, Callable[[np.ndarray, np.ndarray], float]] = {
    "dtw": dtw,
    "dtw_norm": dtw_norm,
}

# The distance an attacker uses unless the config names another one. It is the one
# every measured S4 number was produced with, so result ids and display labels leave
# it implicit and only spell out a non-default distance.
DEFAULT_DISTANCE = "dtw"


def _directed_hausdorff(a: np.ndarray, b: np.ndarray) -> float:
    """Max over points of ``a`` of the nearest-point distance to ``b`` (metres)."""
    worst = 0.0
    for p in a:
        nearest = float(np.min(np.hypot(b[:, 0] - p[0], b[:, 1] - p[1])))
        worst = max(worst, nearest)
    return worst


def hausdorff(a: np.ndarray, b: np.ndarray) -> float:
    """Symmetric Hausdorff distance between two (x, y) point sets (metres)."""
    if len(a) == 0 or len(b) == 0:
        return float("inf")
    return max(_directed_hausdorff(a, b), _directed_hausdorff(b, a))


def mean_spatial_error(a: np.ndarray, b: np.ndarray) -> float:
    """Mean pointwise Euclidean distance between two aligned equal-length sequences (metres)."""
    if len(a) != len(b):
        raise ValueError(
            f"mean_spatial_error needs equal-length sequences, got {len(a)} and {len(b)}"
        )
    if len(a) == 0:
        return float("nan")
    return float(np.hypot(a[:, 0] - b[:, 0], a[:, 1] - b[:, 1]).mean())
