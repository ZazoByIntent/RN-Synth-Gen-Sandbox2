"""DatasetLoader interface (design §2.3)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from trajguard.datamodel import RawTrajectory


class DatasetLoader(ABC):
    """Imports one raw trajectory collection into the common datamodel."""

    dataset_id: str
    native_region: str  # e.g. "beijing" — orchestrator checks it against map.region

    @abstractmethod
    def iter_trajectories(self) -> Iterator[RawTrajectory]:
        """Yield raw trajectories parsed from the source files."""
