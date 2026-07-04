"""Attack interface (design §2.3)."""

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from trajguard.datamodel import AttackResult

BackgroundKnowledge: TypeAlias = Any
"""Attacker prior knowledge (known target points, mechanism params, ...); real type lands in P4."""


class Attack(ABC):
    """A privacy attack with configurable attacker background knowledge."""

    target_scope: set[str]  # subset of {"raw", "protected", "synthetic"}

    @abstractmethod
    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """Set the attacker's background knowledge before running."""

    @abstractmethod
    def run(self, target: Any, aux: Any) -> AttackResult:
        """Execute the attack against target data and return predictions with scores."""
