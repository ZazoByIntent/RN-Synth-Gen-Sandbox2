"""Tests for the shared trajectory-distance primitives."""

import numpy as np
import pytest

from trajguard.geometry import (
    DEFAULT_DISTANCE,
    DISTANCES,
    dtw,
    dtw_norm,
    hausdorff,
    mean_spatial_error,
)

# One probe point against a four-point gallery trace: DTW must match the single probe
# point to every gallery point, so the cost is 0 + 1 + 2 + 3 = 6 over an alignment of
# L = 4 cells, and the normalised distance is 1.5.
ONE_POINT = np.array([(0.0, 0.0)])
FOUR_POINTS = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])


def test_dtw_identity_and_symmetry() -> None:
    a = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    b = np.array([(0.0, 1.0), (1.0, 1.0), (2.0, 1.0)])
    assert dtw(a, a) == 0.0
    assert dtw(a, b) == dtw(b, a)
    assert dtw(a, b) > 0.0


def test_dtw_known_value() -> None:
    """Hand-computed: the one probe point pays its distance to each gallery point."""
    assert dtw(ONE_POINT, FOUR_POINTS) == pytest.approx(6.0)
    # the right-angled detour: 0 + 3 + 5
    assert dtw(ONE_POINT, np.array([(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)])) == pytest.approx(8.0)


def test_dtw_empty_is_inf() -> None:
    assert dtw(np.array([(0.0, 0.0)]), np.empty((0, 2))) == float("inf")


def test_dtw_norm_divides_by_the_alignment_length() -> None:
    """dtw / L, with L the number of cells on the optimal path (here 4, then 3)."""
    assert dtw_norm(ONE_POINT, FOUR_POINTS) == pytest.approx(6.0 / 4)
    three = np.array([(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)])
    assert dtw_norm(ONE_POINT, three) == pytest.approx(8.0 / 3)


def test_dtw_norm_counts_a_diagonal_step_on_the_optimal_path() -> None:
    """A case whose optimal path is not all-horizontal: one diagonal step, then one
    horizontal one.

    a's two points sit exactly on b's first two, so the path runs (1,1) -> (2,2)
    diagonally at zero cost; b's extra point (2, 0) is then matched to a's last point
    for a cost of 1 by a horizontal step. That is cost 1 over L = 3 cells, so
    dtw_norm is 1/3. No step of this path is a tie, so the tie rule (diagonal, then
    vertical, then horizontal) does not change the value.
    """
    a = np.array([(0.0, 0.0), (1.0, 0.0)])
    b = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    assert dtw(a, b) == pytest.approx(1.0)
    assert dtw_norm(a, b) == pytest.approx(1.0 / 3)


def test_dtw_norm_is_zero_on_identical_sequences() -> None:
    a = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    assert dtw_norm(a, a) == 0.0  # path length 3, cost 0


def test_dtw_norm_never_exceeds_dtw() -> None:
    a = np.array([(0.0, 0.0), (10.0, 5.0), (20.0, 0.0)])
    b = np.array([(0.0, 2.0), (5.0, 6.0), (12.0, 4.0), (20.0, 1.0), (25.0, 0.0)])
    assert 0.0 < dtw_norm(a, b) <= dtw(a, b)


def test_dtw_norm_empty_is_inf() -> None:
    assert dtw_norm(np.array([(0.0, 0.0)]), np.empty((0, 2))) == float("inf")
    assert dtw_norm(np.empty((0, 2)), np.array([(0.0, 0.0)])) == float("inf")


def test_distances_registry_names_both_attacker_distances() -> None:
    assert DISTANCES == {"dtw": dtw, "dtw_norm": dtw_norm}
    # the one literal the attack and reporting layers share (they import it from here)
    assert DEFAULT_DISTANCE == "dtw" and DEFAULT_DISTANCE in DISTANCES


def test_hausdorff_symmetric_and_zero_on_identity() -> None:
    a = np.array([(0.0, 0.0), (0.0, 3.0), (4.0, 0.0)])
    b = np.array([(0.0, 0.0), (0.0, 3.0), (4.0, 0.0), (2.0, 2.0)])
    assert hausdorff(a, a) == 0.0
    assert hausdorff(a, b) == hausdorff(b, a)
    assert hausdorff(a, b) > 0.0


def test_hausdorff_known_value() -> None:
    # a's points are all in b, so the distance is driven by b's extra point (5, 4),
    # whose nearest a-point is sqrt(5^2 + 4^2) away.
    a = np.array([(0.0, 0.0), (10.0, 0.0)])
    b = np.array([(0.0, 0.0), (10.0, 0.0), (5.0, 4.0)])
    assert hausdorff(a, b) == pytest.approx(float(np.hypot(5.0, 4.0)))


def test_mean_spatial_error() -> None:
    a = np.array([(0.0, 0.0), (0.0, 0.0)])
    b = np.array([(3.0, 4.0), (0.0, 0.0)])
    assert mean_spatial_error(a, b) == pytest.approx(2.5)  # (5 + 0) / 2


def test_mean_spatial_error_length_mismatch() -> None:
    with pytest.raises(ValueError, match="equal-length"):
        mean_spatial_error(np.zeros((2, 2)), np.zeros((3, 2)))
