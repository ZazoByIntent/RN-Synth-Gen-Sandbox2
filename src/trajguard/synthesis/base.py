"""SyntheticGenerator interface (design §2.3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

from trajguard.datamodel import SyntheticTrajectory
from trajguard.representation import TrajectoryView


class SyntheticGenerator(ABC):
    """Fits a generative model on the train split and samples synthetic trajectories."""

    #: Opt-in for user-level mechanisms (P11, docs/NACRT_ULDP_RANGI.md §10 F3). When
    #: True, the orchestrator calls :meth:`set_user_roster` with every training user of
    #: the split before ``fit``, so a user whose trips all failed map matching is still
    #: enrolled (and later sends a public default report). Off by default: every other
    #: generator receives exactly the matched train views it always did.
    needs_user_roster: ClassVar[bool] = False

    #: The training users handed over by :meth:`set_user_roster`; None until then.
    #: Its length is the user count n for epsilon accounting, never a count of trips.
    user_roster: tuple[str, ...] | None = None

    def set_user_roster(self, users: Sequence[str]) -> None:
        """Receive every training user_id of the split, matched trips or not, before fit."""
        roster = tuple(users)
        if len(set(roster)) != len(roster):
            raise ValueError("user roster lists a user more than once")
        self.user_roster = roster

    @abstractmethod
    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Fit the generator on training trajectories only (never test/shadow/attack)."""

    @abstractmethod
    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n synthetic trajectories, deterministic in the given seed."""


def views_by_user(
    train: Sequence[TrajectoryView], roster: Sequence[str]
) -> dict[str, list[TrajectoryView]]:
    """Group train views by user over the full roster; a user with no view maps to []."""
    grouped: dict[str, list[TrajectoryView]] = {u: [] for u in roster}
    if len(grouped) != len(roster):
        raise ValueError("user roster lists a user more than once")
    for view in train:
        if view.user_id not in grouped:
            raise ValueError(f"train view of user {view.user_id!r} is not in the user roster")
        grouped[view.user_id].append(view)
    return grouped
