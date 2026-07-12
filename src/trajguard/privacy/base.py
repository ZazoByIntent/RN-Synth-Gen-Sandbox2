"""PrivacyMechanism interface (design §2.3)."""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any

from trajguard.datamodel import ProtectedTrajectory
from trajguard.representation import TrajectoryView


def params_hash(params: dict[str, Any]) -> str:
    """Stable short hash of a mechanism/generator parameter dict (versioning key)."""
    payload = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class PrivacyMechanism(ABC):
    """Applies a protective transformation and accounts for its privacy budget."""

    guarantee: str  # "none" | "geo-ind" | "ldp" | "central-dp" | "k-anon"

    def __init__(self, seed: int = 0) -> None:
        """Store the config seed; stochastic mechanisms build their Generator from it."""
        self.seed = seed

    @abstractmethod
    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the protected version of one trajectory view."""

    @abstractmethod
    def spent_budget(self) -> float | None:
        """Privacy budget spent so far, or None when no formal guarantee applies."""
