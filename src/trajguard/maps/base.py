"""MapSource interface (design §2.3)."""

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

RoadNetwork: TypeAlias = Any
"""Road-network container; the concrete type lands with the OSM map source (P1)."""


class MapSource(ABC):
    """Builds or loads a road network for one geographic region."""

    @abstractmethod
    def load(self) -> RoadNetwork:
        """Return the road network, building it or reading it from disk as needed."""

    @property
    @abstractmethod
    def crs(self) -> str:
        """Target coordinate reference system, e.g. ``EPSG:32650``."""
