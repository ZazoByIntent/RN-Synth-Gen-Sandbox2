"""Trajectory-distance primitives over (x, y) point sequences in projected metres.

Layer-neutral geometry shared by the linkage attack (DTW nearest-neighbour) and the
reconstruction metrics (Hausdorff, DTW, mean spatial error); kept here so the attacks
and evaluation layers reuse one implementation instead of duplicating it.
"""

import numpy as np


def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Dynamic time warping distance between two (x, y) point sequences (metres)."""
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0.0
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            d = float(np.hypot(ai[0] - b[j - 1, 0], ai[1] - b[j - 1, 1]))
            cost[i, j] = d + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
    return float(cost[n, m])


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
