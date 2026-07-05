"""Tests for the shared trajectory-distance primitives."""

import numpy as np
import pytest

from trajguard.geometry import dtw, hausdorff, mean_spatial_error


def test_dtw_identity_and_symmetry() -> None:
    a = np.array([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    b = np.array([(0.0, 1.0), (1.0, 1.0), (2.0, 1.0)])
    assert dtw(a, a) == 0.0
    assert dtw(a, b) == dtw(b, a)
    assert dtw(a, b) > 0.0


def test_dtw_empty_is_inf() -> None:
    assert dtw(np.array([(0.0, 0.0)]), np.empty((0, 2))) == float("inf")


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
