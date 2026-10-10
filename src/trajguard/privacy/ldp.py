"""Pure local-DP frequency-oracle primitives: k-ary GRR and OUE (RN-LDP-Synth design §T1).

Device-side perturbation of one categorical report plus collector-side unbiased
frequency estimation. These are deliberately *not* ``PrivacyMechanism``
implementations — they are building blocks a generator (or a future
LDPTrace-style baseline) composes, with budget accounting done by the caller.

Guarantees (standard results, checked empirically in ``tests/test_ldp.py``):
- ``grr_perturb`` is ε-LDP on a k-ary domain: the true category is reported with
  probability e^ε/(e^ε+k−1), any other with probability 1/(e^ε+k−1) each, so the
  worst-case likelihood ratio is exactly e^ε.
- ``grr_probabilities`` gives those two probabilities exactly, and
  ``grr_output_prob`` the exact probability of one output given one input, so an
  audit can compare an empirical log-ratio against the analytic e^ε bound.
- ``UserBudget`` books the ε each user spends under basic sequential composition and
  refuses a spend that would push a user past the user-level budget (ULDP P4).
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


def grr_probabilities(k: int, epsilon: float) -> tuple[float, float]:
    """Exact GRR probabilities ``(p, q)``: keep the true category w.p. p, any other w.p. q."""
    _check_epsilon(epsilon)
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")
    e = math.exp(epsilon)
    return e / (e + k - 1), 1.0 / (e + k - 1)


def grr_output_prob(output: int, value: int, k: int, epsilon: float) -> float:
    """Exact probability that GRR on input ``value`` reports ``output`` (k-ary, ε-LDP)."""
    p, q = grr_probabilities(k, epsilon)
    for name, x in (("output", output), ("value", value)):
        if not 0 <= x < k:
            raise ValueError(f"{name} must be in [0, {k}), got {x}")
    return p if output == value else q


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


def oue_estimate(bit_sums: np.ndarray, n: int, epsilon: float, *, clip: bool = True) -> np.ndarray:
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


class UserBudget:
    """User-level pure-ε bookkeeping under basic sequential composition (ULDP P4).

    Every randomiser call a user's device makes is charged here; the sum per user may
    not exceed ``epsilon``. A spend that would exceed it raises before it is booked, so a
    module that answers two questions at full ε fails loudly instead of silently
    releasing 2ε.
    """

    #: Slack for floating-point sums of budget shares (e.g. three shares of ε/3).
    TOLERANCE = 1e-9

    def __init__(self, epsilon: float) -> None:
        """Start an empty ledger with the user-level budget ``epsilon``."""
        _check_epsilon(epsilon)
        self.epsilon = float(epsilon)
        self._spent: dict[str, float] = {}

    def spend(self, user_id: str, epsilon: float) -> None:
        """Charge ``epsilon`` to ``user_id``; raise ValueError past the user-level budget."""
        if not epsilon >= 0 or not math.isfinite(epsilon):
            raise ValueError(f"a spend must be a finite epsilon >= 0, got {epsilon}")
        total = self._spent.get(user_id, 0.0) + epsilon
        if total > self.epsilon + self.TOLERANCE:
            raise ValueError(
                f"user {user_id!r} would spend {total:g} > user-level budget {self.epsilon:g}"
            )
        self._spent[user_id] = total

    def spent(self, user_id: str) -> float:
        """Budget charged to ``user_id`` so far (0 for a user never charged)."""
        return self._spent.get(user_id, 0.0)

    def max_spent(self) -> float:
        """Largest budget any single user has spent (the realised user-level ε)."""
        return max(self._spent.values(), default=0.0)
