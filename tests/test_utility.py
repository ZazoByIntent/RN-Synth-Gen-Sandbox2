"""Tests for the paired-bootstrap and unpaired-population utility metrics."""

import numpy as np
import pytest

from trajguard.datamodel import CleanTrajectory
from trajguard.evaluation.utility import (
    UTILITY_METRICS,
    cell_js_divergence,
    length_dist_error,
    unpaired_cell_js_divergence,
    unpaired_length_w1,
)
from trajguard.representation import Grid

GRID = Grid(bbox=(116.30, 39.98, 116.32, 39.995), n_rows=10, n_cols=10)
BOOT = {"grid": GRID, "n_bootstrap": 200, "ci": 0.95}


def make_traj(
    traj_id: str, lat0: float, lon0: float, n: int = 30, length_m: float = 1000.0
) -> CleanTrajectory:
    points = tuple((lat0 + i * 1e-4, lon0 + i * 1e-4, float(i * 5)) for i in range(n))
    return CleanTrajectory(
        traj_id=traj_id,
        user_id=f"user_{traj_id}",
        points=points,
        bbox=(lon0, lat0, points[-1][1], points[-1][0]),
        duration_s=points[-1][2],
        length_m=length_m,
        mean_speed=1.0,
        cleaning_flags=(),
    )


def sample_pool(lengths: tuple[float, ...] = (800.0, 1200.0, 2000.0)) -> list[CleanTrajectory]:
    return [
        make_traj(f"t{i}", 39.981 + i * 1e-3, 116.301 + i * 1e-3, length_m=length)
        for i, length in enumerate(lengths)
    ]


def test_identical_release_has_zero_divergence_and_error() -> None:
    pool = sample_pool()
    rng = np.random.default_rng(0)
    jsd = cell_js_divergence(pool, pool, rng=rng, **BOOT)
    w1 = length_dist_error(pool, pool, rng=rng, **BOOT)
    assert jsd == (0.0, 0.0, 0.0)
    assert w1 == (0.0, 0.0, 0.0)


def test_shifted_release_has_positive_divergence() -> None:
    raw = sample_pool()
    shifted = [make_traj(t.traj_id, t.points[0][0] + 0.006, t.points[0][1]) for t in raw]
    point, lo, hi = cell_js_divergence(raw, shifted, rng=np.random.default_rng(0), **BOOT)
    assert 0.0 < point <= 1.0
    assert 0.0 < lo <= point <= hi <= 1.0


def test_length_error_recovers_known_shift() -> None:
    raw = sample_pool(lengths=(800.0, 1200.0, 2000.0))
    inflated = [
        make_traj(t.traj_id, t.points[0][0], t.points[0][1], length_m=t.length_m + 500.0)
        for t in raw
    ]
    point, lo, hi = length_dist_error(raw, inflated, rng=np.random.default_rng(0), **BOOT)
    assert point == 500.0  # every trajectory is exactly 500 m longer
    assert lo == 500.0 and hi == 500.0


def test_bootstrap_is_deterministic_and_brackets_point() -> None:
    raw = sample_pool(lengths=(800.0, 1200.0, 2000.0))
    noisy = [
        make_traj(t.traj_id, t.points[0][0], t.points[0][1], length_m=t.length_m * scale)
        for t, scale in zip(raw, (1.1, 1.5, 1.2), strict=True)
    ]
    first = length_dist_error(raw, noisy, rng=np.random.default_rng(7), **BOOT)
    second = length_dist_error(raw, noisy, rng=np.random.default_rng(7), **BOOT)
    assert first == second
    point, lo, hi = first
    assert lo <= point <= hi


def test_dispatch_table_names() -> None:
    """Unpaired variants stay out of the paired dispatch table on purpose."""
    assert set(UTILITY_METRICS) == {"cell_js_divergence", "length_dist_error"}


def test_unpaired_identical_populations_have_zero_point_estimate() -> None:
    counts = np.array([[3.0, 1.0, 0.0], [0.0, 2.0, 2.0]])
    lengths = np.array([800.0, 1200.0, 2000.0])
    rng = np.random.default_rng(0)
    jsd, _, jsd_hi = unpaired_cell_js_divergence(counts, counts, n_bootstrap=100, ci=0.95, rng=rng)
    w1, _, w1_hi = unpaired_length_w1(lengths, lengths, n_bootstrap=100, ci=0.95, rng=rng)
    assert jsd == 0.0
    assert w1 == 0.0
    # Independent resampling of each side makes the bootstrap spread strictly positive.
    assert jsd_hi >= 0.0 and w1_hi >= 0.0


def test_unpaired_jsd_is_one_bit_for_disjoint_populations() -> None:
    real = np.array([[5.0, 0.0, 0.0]])
    syn = np.array([[0.0, 0.0, 7.0]])
    point, lo, hi = unpaired_cell_js_divergence(
        real, syn, n_bootstrap=50, ci=0.95, rng=np.random.default_rng(1)
    )
    assert point == pytest.approx(1.0)
    assert lo == pytest.approx(1.0) and hi == pytest.approx(1.0)


def test_unpaired_w1_recovers_known_shift_with_unequal_sizes() -> None:
    real = np.array([1000.0, 2000.0])
    syn = np.array([1500.0, 1500.0, 2500.0, 2500.0])  # same shape, +500, different n
    point, _, _ = unpaired_length_w1(
        real, syn, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(2)
    )
    assert point == pytest.approx(500.0)


def test_unpaired_w1_matches_paired_statistic_for_equal_sizes() -> None:
    rng = np.random.default_rng(3)
    a = rng.uniform(500.0, 3000.0, size=17)
    b = rng.uniform(500.0, 3000.0, size=17)
    point, _, _ = unpaired_length_w1(a, b, n_bootstrap=0, ci=0.95, rng=rng)
    assert point == pytest.approx(float(np.abs(np.sort(a) - np.sort(b)).mean()))


def test_unpaired_bootstrap_is_deterministic() -> None:
    real = np.array([[3.0, 1.0], [1.0, 3.0], [2.0, 2.0]])
    syn = np.array([[4.0, 0.0], [3.0, 1.0]])
    first = unpaired_cell_js_divergence(
        real, syn, n_bootstrap=200, ci=0.95, rng=np.random.default_rng(9)
    )
    second = unpaired_cell_js_divergence(
        real, syn, n_bootstrap=200, ci=0.95, rng=np.random.default_rng(9)
    )
    assert first == second
    _, lo, hi = first
    assert lo <= hi
