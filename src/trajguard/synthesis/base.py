"""SyntheticGenerator interface (design §2.3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from trajguard.datamodel import SyntheticTrajectory
from trajguard.representation import TrajectoryView


class SyntheticGenerator(ABC):
    """Fits a generative model on the train split and samples synthetic trajectories."""

    @abstractmethod
    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Fit the generator on training trajectories only (never test/shadow/attack)."""

    @abstractmethod
    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n synthetic trajectories, deterministic in the given seed."""
