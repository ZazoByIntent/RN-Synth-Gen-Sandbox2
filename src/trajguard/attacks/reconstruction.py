"""Reconstruction attack: MAP inversion of the planar-Laplace mechanism (design §6.3)."""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import AttackResult
from trajguard.evaluation.metrics import bootstrap_ci
from trajguard.experiments.registry import register
from trajguard.geometry import dtw, hausdorff, mean_spatial_error

_MOTION_FLOOR_M = 1.0  # smallest motion std (m) so the random-walk prior stays proper


@dataclass(frozen=True, slots=True)
class Reconstruction:
    """One trajectory's MAP estimate and its ground-truth positions (projected metres)."""

    estimate: tuple[tuple[float, float], ...]
    truth: tuple[tuple[float, float], ...]


@register("attack", "reconstruction")
class ReconstructionAttack(Attack):
    """MAP inversion of planar-Laplace noise under a low-curvature smoothness prior.

    The attacker knows the mechanism and its parameters (design §6.3): the planar-Laplace
    radius is ``r ~ Gamma(2, unit_m/epsilon)``, so the per-coordinate observation variance
    is ``3*(unit_m/epsilon)^2``. Under a second-difference (near-constant-velocity) prior
    on the true path, the MAP estimate is a Whittaker smoother that trades the known noise
    variance against the trajectory's curvature, recovering positions closer to the truth
    than the raw noisy release when the path is smoother than the noise. Reports Hausdorff,
    DTW, and mean spatial error.
    """

    target_scope = {"protected"}

    def __init__(
        self, epsilon: float, unit_m: float = 100.0, motion_m: float | None = None
    ) -> None:
        """Attacker who knows epsilon/unit_m; ``motion_m`` is the curvature (acceleration)
        scale in metres for the prior — estimated from the release when None."""
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if unit_m <= 0:
            raise ValueError(f"unit_m must be > 0, got {unit_m}")
        if motion_m is not None and motion_m <= 0:
            raise ValueError(f"motion_m must be > 0, got {motion_m}")
        self.epsilon = float(epsilon)
        self.unit_m = float(unit_m)
        self.motion_m = motion_m
        self._obs_var = 3.0 * (self.unit_m / self.epsilon) ** 2  # per-coordinate noise variance

    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """No stochastic knowledge: the MAP estimate is deterministic."""

    def run(self, target: Any, aux: Any) -> AttackResult:
        """Reconstruct each noisy trajectory in ``target``; ``aux`` holds the true paths.

        ``target`` and ``aux`` are aligned sequences of point sequences; each point's
        first two entries are (x, y) in projected metres. The orchestrator stamps
        ``exp_id``/``target_data_ref`` onto the result.
        """
        started = time.perf_counter()
        preds: list[Reconstruction] = []
        for noisy_pts, true_pts in zip(target, aux, strict=True):
            estimate = self._smooth(_xy(noisy_pts))
            preds.append(
                Reconstruction(
                    estimate=tuple((float(x), float(y)) for x, y in estimate),
                    truth=tuple((float(p[0]), float(p[1])) for p in true_pts),
                )
            )
        return AttackResult(
            result_id="reconstruction",
            attack_id="reconstruction",
            exp_id="",  # stamped by the orchestrator
            target_data_ref="protected",  # stamped by the orchestrator
            predictions=tuple(preds),
            scores=tuple(mean_spatial_error(_arr(p.estimate), _arr(p.truth)) for p in preds),
            ground_truth_ref="matched_points",
            runtime_s=time.perf_counter() - started,
        )

    def _smooth(self, noisy: np.ndarray) -> np.ndarray:
        """Whittaker MAP smoother: penalise curvature (D2) against the known noise."""
        n = len(noisy)
        if n < 3:
            return noisy  # no curvature to penalise
        lam = self._obs_var / self._curvature_var(noisy)
        d2 = np.zeros((n - 2, n))  # second-difference operator, rows [1, -2, 1]
        for i in range(n - 2):
            d2[i, i : i + 3] = (1.0, -2.0, 1.0)
        a = np.eye(n) + lam * (d2.T @ d2)
        solved: np.ndarray = np.linalg.solve(a, noisy)  # solves the x and y columns together
        return solved

    def _curvature_var(self, noisy: np.ndarray) -> float:
        """Per-coordinate acceleration variance: fixed, or noise-corrected from data.

        A second difference of independent noise has variance ``6 * obs_var``, so we
        subtract that from the observed curvature to recover the true motion scale.
        """
        if self.motion_m is not None:
            return self.motion_m**2
        accel = noisy[2:] - 2.0 * noisy[1:-1] + noisy[:-2]
        observed = float((accel**2).mean())
        return max(observed - 6.0 * self._obs_var, _MOTION_FLOOR_M**2)


def reconstruction_report(
    result: AttackResult, n_bootstrap: int = 1000, ci: float = 0.95, seed: int = 0
) -> dict[str, tuple[float, float, float]]:
    """Per-metric (mean, ci_low, ci_high) over the reconstructed trajectories (metres)."""
    per: dict[str, list[float]] = {"hausdorff_m": [], "dtw_m": [], "mean_spatial_error_m": []}
    for p in result.predictions:
        est, tru = _arr(p.estimate), _arr(p.truth)
        per["hausdorff_m"].append(hausdorff(est, tru))
        per["dtw_m"].append(dtw(est, tru))
        per["mean_spatial_error_m"].append(mean_spatial_error(est, tru))
    rng = np.random.default_rng(seed)
    return {name: bootstrap_ci(np.array(vals), n_bootstrap, ci, rng) for name, vals in per.items()}


def _xy(points: Sequence[Any]) -> np.ndarray:
    """First two coordinates (x, y) of each point as an (n, 2) array."""
    return np.array([(float(p[0]), float(p[1])) for p in points], dtype=float)


def _arr(points: Sequence[tuple[float, float]]) -> np.ndarray:
    return np.array(points, dtype=float)
