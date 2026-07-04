"""PrivacyMechanism interface (design §2.3)."""

from abc import ABC, abstractmethod
from typing import Any

from trajguard.datamodel import ProtectedTrajectory
from trajguard.representation import TrajectoryView


class PrivacyMechanism(ABC):
    """Applies a protective transformation and accounts for its privacy budget."""

    guarantee: str  # "none" | "geo-ind" | "ldp" | "central-dp" | "k-anon"

    @abstractmethod
    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the protected version of one trajectory view."""

    @abstractmethod
    def spent_budget(self) -> float | None:
        """Privacy budget spent so far, or None when no formal guarantee applies."""
