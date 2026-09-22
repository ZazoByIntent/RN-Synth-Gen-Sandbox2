"""Attack interface (design §2.3)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from trajguard.datamodel import AttackResult
from trajguard.geometry import DEFAULT_DISTANCE

# Which form of the released data the attacker holds as gallery and probes:
# "rematched" = the map-matched (snapped) points that survived re-matching,
# "release" = the full released points as published. See the reidentification
# module docstring; "rematched" is the default so measured result ids keep their meaning.
GALLERIES: tuple[str, ...] = ("rematched", "release")
DEFAULT_GALLERY = "rematched"


@dataclass(frozen=True, slots=True)
class BackgroundKnowledge:
    """What the attacker knows about the target before the attack runs."""

    known_points: int  # number of spatio-temporal points known about each target
    # trajectory distance used for nearest-neighbour linkage, one of geometry.DISTANCES
    distance: str = DEFAULT_DISTANCE
    seed: int = 0  # for any stochastic knowledge selection (evenly-spaced is deterministic)
    gallery: str = DEFAULT_GALLERY  # which released form the attacker sees, one of GALLERIES


class Attack(ABC):
    """A privacy attack with configurable attacker background knowledge."""

    target_scope: set[str]  # subset of {"raw", "protected", "synthetic"}

    @abstractmethod
    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """Set the attacker's background knowledge before running."""

    @abstractmethod
    def run(self, target: Any, aux: Any) -> AttackResult:
        """Execute the attack against target data and return predictions with scores."""
