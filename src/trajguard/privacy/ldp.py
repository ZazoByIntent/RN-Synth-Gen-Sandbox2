"""Pure local-DP frequency-oracle primitives: k-ary GRR and OUE (RN-LDP-Synth design §T1).

Device-side perturbation of one categorical report plus collector-side unbiased
frequency estimation. These are deliberately *not* ``PrivacyMechanism``
implementations — they are building blocks a generator (or a future
LDPTrace-style baseline) composes, with budget accounting done by the caller.

Guarantees (standard results, checked empirically in ``tests/test_ldp.py``):
- ``grr_perturb`` is ε-LDP on a k-ary domain: the true category is reported with
  probability e^ε/(e^ε+k−1), any other with probability 1/(e^ε+k−1) each, so the
  worst-case likelihood ratio is exactly e^ε.
- ``oue_perturb`` (Optimized Unary Encoding, Wang et al. 2017) is ε-LDP over the
  full bit-vector output space for one-hot inputs: the true bit stays 1 with
  probability 1/2, every other bit turns 1 with probability 1/(e^ε+1); the
  worst-case joint ratio (p/q)·((1−q)/(1−p)) equals e^ε.
"""

import math

import numpy as np


def _check_epsilon(epsilon: float) -> None:
    if not epsilon > 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")


def grr_perturb(value: int, k: int, epsilon: float, rng: np.random.Generator) -> int:
    """ε-LDP k-ary randomized response: report ``value`` w.p. e^ε/(e^ε+k−1), else uniform other."""
    _check_epsilon(epsilon)
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")
    if not 0 <= value < k:
        raise ValueError(f"value must be in [0, {k}), got {value}")
    p_true = math.exp(epsilon) / (math.exp(epsilon) + k - 1)
    if rng.random() < p_true:
        return value
    other = int(rng.integers(k - 1))
    return other if other < value else other + 1


def grr_estimate(counts: np.ndarray, n: int, epsilon: float) -> np.ndarray:
    """Unbiased per-category frequency estimates from ``n`` GRR reports, clipped at 0."""
    _check_epsilon(epsilon)
    k = len(counts)
    e = math.exp(epsilon)
    p = e / (e + k - 1)
    q = 1.0 / (e + k - 1)
    est: np.ndarray = (np.asarray(counts, dtype=float) - n * q) / (p - q)
    clipped: np.ndarray = np.clip(est, 0.0, None)
    return clipped


def oue_perturb(value: int, size: int, epsilon: float, rng: np.random.Generator) -> np.ndarray:
    """ε-LDP optimized unary encoding of a one-hot input; returns the perturbed bool vector."""
    _check_epsilon(epsilon)
    if size < 1:
        raise ValueError(f"size must be >= 1, got {size}")
    if not 0 <= value < size:
        raise ValueError(f"value must be in [0, {size}), got {value}")
    q = 1.0 / (math.exp(epsilon) + 1.0)
    bits: np.ndarray = rng.random(size) < q
    bits[value] = rng.random() < 0.5
    return bits


def oue_estimate(
    bit_sums: np.ndarray, n: int, epsilon: float, *, clip: bool = True
) -> np.ndarray:
    """Unbiased per-position frequency estimates from ``n`` summed OUE vectors.

    Clipped at 0 by default; ``clip=False`` returns the raw unbiased estimate with
    its negative entries (LDPTrace's length-quantile rule needs the unclipped total).
    """
    _check_epsilon(epsilon)
    q = 1.0 / (math.exp(epsilon) + 1.0)
    est: np.ndarray = (np.asarray(bit_sums, dtype=float) - n * q) / (0.5 - q)
    if not clip:
        return est
    clipped: np.ndarray = np.clip(est, 0.0, None)
    return clipped
