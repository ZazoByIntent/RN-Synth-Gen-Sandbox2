"""MapSource interface and the RoadNetwork container (design §2.3)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import geopandas as gpd
import networkx as nx


@dataclass(frozen=True)
class RoadNetwork:
    """A projected road graph with its normalized node and edge tables."""

    graph: nx.MultiDiGraph
    nodes: gpd.GeoDataFrame  # node_id, x, y, lon, lat, street_count, geometry
    edges: gpd.GeoDataFrame  # edge_id, u, v, key, length_m, highway, oneway, maxspeed, geometry
    region: str
    crs: str


class MapSource(ABC):
    """Builds or loads a road network for one geographic region."""

    @abstractmethod
    def load(self) -> RoadNetwork:
        """Read a previously built road network from disk (never touches the network)."""

    @property
    @abstractmethod
    def crs(self) -> str:
        """Target coordinate reference system, e.g. ``EPSG:32650``."""
