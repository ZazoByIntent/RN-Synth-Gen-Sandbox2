"""Tests for the MAP reconstruction attack against planar-Laplace noise."""

import math

import numpy as np
import pytest

from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.reconstruction import (
    Reconstruction,
    ReconstructionAttack,
    reconstruction_report,
)
from trajguard.experiments import registry
from trajguard.geometry import mean_spatial_error

EPSILON, UNIT_M = 10.0, 100.0  # planar-Laplace scale b = 10 m, mean radius 20 m


def smooth_truth(n: int = 60) -> list[tuple[float, float, float]]:
    """A constant-velocity path with ~5 m steps (much smoother than the 20 m noise)."""
    return [(i * 4.0, i * 3.0, float(i)) for i in range(n)]


def planar_laplace_noise(n: int, seed: int) -> np.ndarray:
    """n planar-Laplace displacements (metres) with the mechanism's Gamma(2, b) radius."""
    rng = np.random.default_rng(seed)
    b = UNIT_M / EPSILON
    r = rng.gamma(2.0, b, size=n)
    theta = rng.uniform(0.0, 2.0 * np.pi, size=n)
    return np.column_stack([r * np.cos(theta), r * np.sin(theta)])


def noisy_release(
    truth: list[tuple[float, float, float]], seed: int
) -> list[tuple[float, float, float]]:
    noise = planar_laplace_noise(len(truth), seed)
    return [(t[0] + noise[i, 0], t[1] + noise[i, 1], t[2]) for i, t in enumerate(truth)]


def attack() -> ReconstructionAttack:
    a = ReconstructionAttack(epsilon=EPSILON, unit_m=UNIT_M)
    a.configure(BackgroundKnowledge(known_points=0))
    return a


def test_registered() -> None:
    assert registry.get("attack", "reconstruction") is ReconstructionAttack


def test_reconstruction_beats_raw_noise() -> None:
    truth = smooth_truth()
    noisy = noisy_release(truth, seed=0)
    result = attack().run([noisy], [truth])
    report = reconstruction_report(result)

    truth_xy = np.array([(t[0], t[1]) for t in truth])
    noisy_xy = np.array([(p[0], p[1]) for p in noisy])
    raw_error = mean_spatial_error(noisy_xy, truth_xy)
    # the MAP estimate is closer to the truth than the raw noisy release
    assert report["mean_spatial_error_m"][0] < raw_error
    assert all(math.isfinite(v) for triple in report.values() for v in triple)


def test_report_has_all_three_metrics() -> None:
    result = attack().run([noisy_release(smooth_truth(), seed=1)], [smooth_truth()])
    report = reconstruction_report(result)
    assert set(report) == {"hausdorff_m", "dtw_m", "mean_spatial_error_m"}
    for point, lo, hi in report.values():
        assert lo <= point <= hi


def test_predictions_carry_estimate_and_truth() -> None:
    truth = smooth_truth(10)
    result = attack().run([noisy_release(truth, seed=2)], [truth])
    assert len(result.predictions) == 1
    pred = result.predictions[0]
    assert isinstance(pred, Reconstruction)
    assert len(pred.estimate) == len(truth)
    assert len(pred.truth) == len(truth)


def test_deterministic() -> None:
    truth = smooth_truth()
    noisy = noisy_release(truth, seed=5)
    first = attack().run([noisy], [truth]).predictions[0].estimate
    second = attack().run([noisy], [truth]).predictions[0].estimate
    assert first == second


def test_stronger_prior_smooths_more() -> None:
    # a tiny fixed curvature scale forces heavy smoothing -> estimate hugs a straight line
    truth = smooth_truth()
    noisy = noisy_release(truth, seed=7)
    loose = ReconstructionAttack(epsilon=EPSILON, unit_m=UNIT_M, motion_m=100.0)
    tight = ReconstructionAttack(epsilon=EPSILON, unit_m=UNIT_M, motion_m=1.0)
    truth_xy = np.array([(t[0], t[1]) for t in truth])

    def error(a: ReconstructionAttack) -> float:
        est = a.run([noisy], [truth]).predictions[0].estimate
        return mean_spatial_error(np.array(est), truth_xy)

    # for this near-straight path, heavier smoothing recovers it better
    assert error(tight) < error(loose)


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        ReconstructionAttack(epsilon=0.0)
    with pytest.raises(ValueError, match="unit_m"):
        ReconstructionAttack(epsilon=1.0, unit_m=-1.0)
    with pytest.raises(ValueError, match="motion_m"):
        ReconstructionAttack(epsilon=1.0, motion_m=0.0)
