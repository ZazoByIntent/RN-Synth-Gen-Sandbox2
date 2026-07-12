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


# --- unpaired population metrics --------------------------------------------------
#
# Population-level synthesis (e.g. rn_ldp_synth) releases a set of trajectories with
# no raw<->released bijection, so the paired metrics above do not apply. These
# variants compare two INDEPENDENT populations and bootstrap each side separately.
# They are plain functions (like evaluation.roc) and deliberately NOT registered in
# UTILITY_METRICS, whose protocol is the paired CleanTrajectory contract the
# orchestrator dispatches.


def _two_sample_bootstrap(
    real: np.ndarray,
    syn: np.ndarray,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """(point, ci_low, ci_high) of a statistic under independent per-population resampling."""
    point = statistic(real, syn)
    if len(real) == 0 or len(syn) == 0 or n_bootstrap <= 0:
        return point, point, point
    stats = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        ri = rng.integers(0, len(real), size=len(real))
        si = rng.integers(0, len(syn), size=len(syn))
        stats[b] = statistic(real[ri], syn[si])
    alpha = (1.0 - ci) / 2.0
    return point, float(np.quantile(stats, alpha)), float(np.quantile(stats, 1.0 - alpha))


def unpaired_cell_js_divergence(
    real_counts: np.ndarray,
    syn_counts: np.ndarray,
    *,
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """JSD (bits) between summed cell-visit distributions of two independent populations.

    Inputs are per-trajectory cell-count matrices (n_traj × n_cells) built with the
    SAME featurization on both sides — comparing different featurizations is
    meaningless and on the caller.
    """
    if len(real_counts) == 0 or len(syn_counts) == 0:
        return math.nan, math.nan, math.nan

    def stat(a: np.ndarray, b: np.ndarray) -> float:
        return _jsd_bits(a.sum(axis=0), b.sum(axis=0))

    return _two_sample_bootstrap(
        np.asarray(real_counts, dtype=float),
        np.asarray(syn_counts, dtype=float),
        stat,
        n_bootstrap,
        ci,
        rng,
    )


def unpaired_length_w1(
    real_lengths: np.ndarray,
    syn_lengths: np.ndarray,
    *,
    n_bootstrap: int,
    ci: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """Wasserstein-1 (metres) between two trip-length samples of possibly different sizes."""
    if len(real_lengths) == 0 or len(syn_lengths) == 0:
        return math.nan, math.nan, math.nan
    return _two_sample_bootstrap(
        np.asarray(real_lengths, dtype=float),
        np.asarray(syn_lengths, dtype=float),
        _w1,
        n_bootstrap,
        ci,
        rng,
    )


def _w1(a: np.ndarray, b: np.ndarray) -> float:
    """Exact W1 between two empirical distributions via their piecewise quantile functions.

    Reduces to ``mean(|sort(a) - sort(b)|)`` when the sample sizes are equal (the
    paired statistic above), but stays exact for unequal sizes.
    """
    a = np.sort(a)
    b = np.sort(b)
    na, nb = len(a), len(b)
    cuts = np.union1d(np.arange(1, na) / na, np.arange(1, nb) / nb)
    edges = np.concatenate(([0.0], cuts, [1.0]))
    mids = (edges[:-1] + edges[1:]) / 2.0
    widths = np.diff(edges)
    a_vals = a[np.minimum((mids * na).astype(int), na - 1)]
    b_vals = b[np.minimum((mids * nb).astype(int), nb - 1)]
    return float(np.sum(widths * np.abs(a_vals - b_vals)))
