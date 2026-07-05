"""NoProtection baseline mechanism (design §7): the unprotected upper risk bound."""

from typing import Any

from trajguard.datamodel import ProtectedTrajectory
from trajguard.experiments.registry import register
from trajguard.privacy.base import PrivacyMechanism, params_hash
from trajguard.representation import TrajectoryView


@register("mechanism", "none")
class NoProtection(PrivacyMechanism):
    """Identity mechanism: passes the GPS view through unchanged."""

    guarantee = "none"

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        """Return the trajectory's GPS view as an unmodified ProtectedTrajectory."""
        return ProtectedTrajectory(
            traj_id=f"none/{traj.traj_id}",
            source_traj_id=traj.traj_id,
            mechanism_id="none",
            params_hash=params_hash(params),
            guarantee=self.guarantee,
            epsilon=None,
            payload=traj.as_gps(),
            map_id=traj.map_id,
        )

    def spent_budget(self) -> float | None:
        """No formal guarantee — no budget is spent."""
        return None
