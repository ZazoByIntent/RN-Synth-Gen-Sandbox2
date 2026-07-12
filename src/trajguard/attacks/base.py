"""Attack interface (design §2.3)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from trajguard.datamodel import AttackResult


@dataclass(frozen=True, slots=True)
class BackgroundKnowledge:
    """What the attacker knows about the target before the attack runs."""

    known_points: int  # number of spatio-temporal points known about each target
    distance: str = "dtw"  # trajectory distance used for nearest-neighbour linkage
    seed: int = 0  # for any stochastic knowledge selection (evenly-spaced is deterministic)


class Attack(ABC):
    """A privacy attack with configurable attacker background knowledge."""

    target_scope: set[str]  # subset of {"raw", "protected", "synthetic"}

    @abstractmethod
    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """Set the attacker's background knowledge before running."""

    @abstractmethod
    def run(self, target: Any, aux: Any) -> AttackResult:
        """Execute the attack against target data and return predictions with scores."""
