"""Metric interface (design §2.3)."""

from abc import ABC, abstractmethod
from typing import Any

from trajguard.datamodel import AttackResult


class Metric(ABC):
    """Computes named metric values from an attack result and its ground truth."""

    @abstractmethod
    def compute(self, result: AttackResult, ground_truth: Any) -> dict[str, float]:
        """Return metric name → value pairs for one attack result."""
