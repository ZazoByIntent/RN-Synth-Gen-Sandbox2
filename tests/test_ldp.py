"""GRR/OUE primitives: analytic constants, empirical exp(ε) ratio bound, debias accuracy."""

import math

import numpy as np
import pytest

from trajguard.privacy.ldp import grr_estimate, grr_perturb, oue_estimate, oue_perturb

EPS = 0.8
RATIO_TOL = 1.20  # generous band: the extreme output pair sits exactly at the e^eps bound


def _grr_freqs(value: int, k: int, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    counts = np.zeros(k)
    for _ in range(n):
        counts[grr_perturb(value, k, EPS, rng)] += 1
    return counts / n


def test_grr_reports_true_value_with_analytic_probability() -> None:
    k, n = 4, 30_000
    freqs = _grr_freqs(2, k, n, seed=1)
    p_true = math.exp(EPS) / (math.exp(EPS) + k - 1)
    assert freqs[2] == pytest.approx(p_true, rel=0.05)
    q = 1.0 / (math.exp(EPS) + k - 1)
    for other in (0, 1, 3):
        assert freqs[other] == pytest.approx(q, rel=0.10)


def test_grr_empirical_frequency_ratio_bounded_by_exp_eps() -> None:
    """The stated ε-LDP guarantee, checked empirically: max_y freq(y|a)/freq(y|b) <= e^ε·tol."""
    k, n = 4, 30_000
    freqs_a = _grr_freqs(0, k, n, seed=2)
    freqs_b = _grr_freqs(1, k, n, seed=3)
    assert freqs_a.min() > 0 and freqs_b.min() > 0
    max_ratio = max((freqs_a / freqs_b).max(), (freqs_b / freqs_a).max())
    assert max_ratio <= math.exp(EPS) * RATIO_TOL


def test_oue_bit_probabilities_and_ratio_bound() -> None:
    """OUE bit-level frequencies match p=1/2, q=1/(e^ε+1); worst joint ratio <= e^ε·tol."""
    size, n = 6, 30_000
    rng = np.random.default_rng(4)
    sums = np.zeros(size)
    for _ in range(n):
        sums += oue_perturb(2, size, EPS, rng)
    freqs = sums / n
    q = 1.0 / (math.exp(EPS) + 1.0)
    assert freqs[2] == pytest.approx(0.5, rel=0.05)
    for other in (0, 1, 3, 4, 5):
        assert freqs[other] == pytest.approx(q, rel=0.10)
    # Bits are independent, so the worst-case joint likelihood ratio between two
    # one-hot inputs factorizes into (p/q)·((1-q)/(1-p)) — empirically bounded by e^ε.
    p_hat, q_hat = float(freqs[2]), float(freqs[[0, 1, 3, 4, 5]].mean())
    worst = (p_hat / q_hat) * ((1.0 - q_hat) / (1.0 - p_hat))
    assert worst <= math.exp(EPS) * RATIO_TOL


def test_grr_estimate_recovers_true_distribution() -> None:
    k, n = 5, 40_000
    true = np.array([0.5, 0.2, 0.15, 0.1, 0.05])
    rng = np.random.default_rng(5)
    values = rng.choice(k, size=n, p=true)
    counts = np.zeros(k)
    for v in values:
        counts[grr_perturb(int(v), k, EPS, rng)] += 1
    est = grr_estimate(counts, n, EPS)
    # GRR L1 at these params runs ~0.03-0.07 across seeds; a wrong estimator is off by ~0.4+.
    assert np.abs(est / n - true).sum() < 0.12


def test_oue_estimate_recovers_true_distribution() -> None:
    size, n = 6, 40_000
    true = np.array([0.4, 0.25, 0.15, 0.1, 0.06, 0.04])
    rng = np.random.default_rng(6)
    values = rng.choice(size, size=n, p=true)
    sums = np.zeros(size)
    for v in values:
        sums += oue_perturb(int(v), size, EPS, rng)
    est = oue_estimate(sums, n, EPS)
    # OUE variance at eps=0.8 makes L1 ~0.05-0.12 at this n; a wrong estimator is off by ~0.5+.
    assert np.abs(est / n - true).sum() < 0.15


def test_perturbation_is_deterministic_in_seed() -> None:
    a = [grr_perturb(1, 4, EPS, np.random.default_rng(7)) for _ in range(20)]
    b = [grr_perturb(1, 4, EPS, np.random.default_rng(7)) for _ in range(20)]
    assert a == b
    va = oue_perturb(3, 8, EPS, np.random.default_rng(8))
    vb = oue_perturb(3, 8, EPS, np.random.default_rng(8))
    assert np.array_equal(va, vb)


@pytest.mark.parametrize("bad_eps", [0.0, -1.0])
def test_epsilon_must_be_positive(bad_eps: float) -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="epsilon"):
        grr_perturb(0, 3, bad_eps, rng)
    with pytest.raises(ValueError, match="epsilon"):
        oue_perturb(0, 3, bad_eps, rng)


def test_domain_validation() -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="k must be"):
        grr_perturb(0, 1, EPS, rng)
    with pytest.raises(ValueError, match="value must be"):
        grr_perturb(3, 3, EPS, rng)
    with pytest.raises(ValueError, match="value must be"):
        oue_perturb(5, 5, EPS, rng)
