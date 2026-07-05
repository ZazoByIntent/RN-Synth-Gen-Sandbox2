"""Privacy metrics with bootstrap confidence intervals (design §6, §13)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import numpy as np

from trajguard.datamodel import AttackResult, MetricValue
from trajguard.evaluation.base import Metric
from trajguard.experiments.registry import register


def bootstrap_ci(
    indicators: np.ndarray, n_bootstrap: int, ci: float, rng: np.random.Generator
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) of the mean via seeded percentile bootstrap."""
    point = float(indicators.mean()) if len(indicators) else float("nan")
    if len(indicators) == 0 or n_bootstrap <= 0:
        return point, point, point
    resamples = rng.integers(0, len(indicators), size=(n_bootstrap, len(indicators)))
    means = indicators[resamples].mean(axis=1)
    alpha = (1.0 - ci) / 2.0
    lo = float(np.quantile(means, alpha))
    hi = float(np.quantile(means, 1.0 - alpha))
    return point, lo, hi


class SampledMetric(Metric, ABC):
    """A metric that is the mean of a per-probe 0/1 indicator (bootstrappable)."""

    name: str

    @abstractmethod
    def indicators(self, result: AttackResult) -> np.ndarray:
        """Per-probe 0/1 outcomes underlying this metric."""

    def compute(self, result: AttackResult, ground_truth: Any = None) -> dict[str, float]:
        """Point estimate; ground truth is embedded in the result (see Ranking)."""
        ind = self.indicators(result)
        return {self.name: float(ind.mean()) if len(ind) else float("nan")}


@register("metric", "top_k_accuracy")
class TopKAccuracy(SampledMetric):
    """Fraction of probes whose true user is among the top-k ranked gallery users."""

    def __init__(self, k: int = 1) -> None:
        self.k = k
        self.name = f"top{k}_acc"

    def indicators(self, result: AttackResult) -> np.ndarray:
        return np.array(
            [float(r.true_user in r.users[: self.k]) for r in result.predictions], dtype=float
        )


@register("metric", "linkage_rate")
class LinkageRate(SampledMetric):
    """Fraction of probes whose nearest gallery user is the true user (rank-1 link)."""

    name = "linkage_rate"

    def indicators(self, result: AttackResult) -> np.ndarray:
        return np.array(
            [float(bool(r.users) and r.users[0] == r.true_user) for r in result.predictions],
            dtype=float,
        )


def evaluate(
    result: AttackResult,
    metrics: Sequence[SampledMetric],
    n_bootstrap: int,
    ci: float,
    seed: int,
) -> list[MetricValue]:
    """Compute each metric's point estimate and bootstrap CI for one attack result."""
    rng = np.random.default_rng(seed)
    out: list[MetricValue] = []
    for metric in metrics:
        point, lo, hi = bootstrap_ci(metric.indicators(result), n_bootstrap, ci, rng)
        out.append(
            MetricValue(
                metric_id=f"{result.result_id}:{metric.name}",
                result_id=result.result_id,
                name=metric.name,
                value=point,
                ci_low=lo,
                ci_high=hi,
                n_bootstrap=n_bootstrap,
            )
        )
    return out
