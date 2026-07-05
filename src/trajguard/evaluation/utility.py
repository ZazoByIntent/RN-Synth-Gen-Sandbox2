"""Utility metrics: how much a protected release distorts the raw data (design §6).

These compare two aligned trajectory populations (raw vs released), so they do not
fit the attack-shaped ``Metric`` ABC; the orchestrator dispatches them by name via
``UTILITY_METRICS``. Confidence intervals come from a paired bootstrap: raw/noisy
per-trajectory contributions are resampled jointly (same indices), which preserves
the coupling between a trajectory and its protected version.
"""

import math
from collections.abc import Callable, Sequence
from typing import Protocol

import numpy as np

from trajguard.datamodel import CleanTrajectory
from trajguard.representation import Grid


class UtilityMetric(Protocol):
    """A utility metric returning (point, ci_low, ci_high) for raw vs released data."""

    def __call__(
        self,
        raw: Sequence[CleanTrajectory],
        noisy: Sequence[CleanTrajectory],
        *,
        grid: Grid,
        n_bootstrap: int,
        ci: float,
        rng: np.random.Generator,
    ) -> tuple[float, float, float]: ...


def _paired_bootstrap(
    raw_contrib: np.ndarray,
    noisy_contrib: np.ndarray,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """(point, ci_low, ci_high) of a statistic over jointly resampled pairs."""
    point = statistic(raw_contrib, noisy_contrib)
    n = len(raw_contrib)
    if n == 0 or n_bootstrap <= 0:
        return point, point, point
    stats = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        stats[b] = statistic(raw_contrib[idx], noisy_contrib[idx])
    alpha = (1.0 - ci) / 2.0
    return point, float(np.quantile(stats, alpha)), float(np.quantile(stats, 1.0 - alpha))


def _jsd_bits(p_counts: np.ndarray, q_counts: np.ndarray) -> float:
    """Jensen-Shannon divergence, base 2 (in [0, 1]), between two count vectors."""
    p = p_counts / p_counts.sum()
    q = q_counts / q_counts.sum()
    m = 0.5 * (p + q)

    def kl_to_m(a: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / m[mask])))

    return 0.5 * kl_to_m(p) + 0.5 * kl_to_m(q)


def _cell_counts(traj: CleanTrajectory, grid: Grid) -> np.ndarray:
    """Visit count per grid cell for one trajectory's points."""
    cells = [grid.cell_of(lat, lon) for lat, lon, _ in traj.points]
    return np.bincount(cells, minlength=grid.n_cells).astype(float)


def cell_js_divergence(
    raw: Sequence[CleanTrajectory],
    noisy: Sequence[CleanTrajectory],
    *,
    grid: Grid,
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """JS divergence (bits) between raw and released cell-visit distributions."""
    if not raw:
        return math.nan, math.nan, math.nan
    raw_counts = np.stack([_cell_counts(t, grid) for t in raw])
    noisy_counts = np.stack([_cell_counts(t, grid) for t in noisy])

    def stat(a: np.ndarray, b: np.ndarray) -> float:
        return _jsd_bits(a.sum(axis=0), b.sum(axis=0))

    return _paired_bootstrap(raw_counts, noisy_counts, stat, n_bootstrap, ci, rng)


def length_dist_error(
    raw: Sequence[CleanTrajectory],
    noisy: Sequence[CleanTrajectory],
    *,
    grid: Grid,
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """Wasserstein-1 (meters) between raw and released length distributions."""
    if not raw:
        return math.nan, math.nan, math.nan
    raw_len = np.array([t.length_m for t in raw], dtype=float)
    noisy_len = np.array([t.length_m for t in noisy], dtype=float)

    def stat(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.abs(np.sort(a) - np.sort(b)).mean())

    return _paired_bootstrap(raw_len, noisy_len, stat, n_bootstrap, ci, rng)


UTILITY_METRICS: dict[str, UtilityMetric] = {
    "cell_js_divergence": cell_js_divergence,
    "length_dist_error": length_dist_error,
}
