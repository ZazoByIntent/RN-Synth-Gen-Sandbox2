"""MapMatcher interface (design §2.3)."""

from abc import ABC, abstractmethod

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.maps.base import RoadNetwork


class MapMatcher(ABC):
    """Snaps cleaned GPS trajectories onto road-network edges."""

    @abstractmethod
    def match(self, traj: CleanTrajectory, net: RoadNetwork) -> MatchedTrajectory:
        """Return the trajectory mapped to an edge sequence with a match score."""
