"""Tests for the paired-bootstrap utility metrics."""

import numpy as np

from trajguard.datamodel import CleanTrajectory
from trajguard.evaluation.utility import UTILITY_METRICS, cell_js_divergence, length_dist_error
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
    assert set(UTILITY_METRICS) == {"cell_js_divergence", "length_dist_error"}
