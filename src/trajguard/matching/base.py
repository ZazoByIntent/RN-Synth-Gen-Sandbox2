"""MapMatcher interface and matcher-agnostic quality filtering (design §2.3)."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.maps.base import RoadNetwork


class MapMatcher(ABC):
    """Snaps cleaned GPS trajectories onto road-network edges."""

    @abstractmethod
    def match(self, traj: CleanTrajectory, net: RoadNetwork) -> MatchedTrajectory:
        """Return the trajectory mapped to an edge sequence with a match score."""


def match_many(
    matcher: MapMatcher,
    trajs: Iterable[CleanTrajectory],
    net: RoadNetwork,
    min_match_score: float,
) -> tuple[list[MatchedTrajectory], int]:
    """Match all trajectories and drop those under min_match_score; returns (kept, n_dropped)."""
    kept: list[MatchedTrajectory] = []
    dropped = 0
    for traj in trajs:
        matched = matcher.match(traj, net)
        if matched.match_score >= min_match_score:
            kept.append(matched)
        else:
            dropped += 1
    return kept, dropped
