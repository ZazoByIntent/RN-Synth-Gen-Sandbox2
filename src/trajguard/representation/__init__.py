"""Trajectory representation layer (design §2.2, module 4)."""

from typing import Any, TypeAlias

TrajectoryView: TypeAlias = Any
"""Adapter exposing one trajectory as GPS / segments / cells / ...; real class lands in P3."""
