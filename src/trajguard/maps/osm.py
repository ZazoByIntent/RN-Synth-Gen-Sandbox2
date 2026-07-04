"""OSM-backed MapSource built on OSMnx (design §2.2, module 1)."""

import json
from dataclasses import asdict
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox

from trajguard.datamodel import Map
from trajguard.experiments.registry import register
from trajguard.maps.base import MapSource, RoadNetwork

_GRAPH_FILE = "graph.graphml"
_NODES_FILE = "nodes.parquet"
_EDGES_FILE = "edges.parquet"
_META_FILE = "meta.json"

# OSM edge attributes that may be scalar or list after simplification; pyarrow
# rejects mixed columns, so they are stringified before the Parquet write.
_LISTY_EDGE_COLS = ("osmid", "highway", "maxspeed")

_NODE_COLS = ["node_id", "x", "y", "lon", "lat", "street_count", "geometry"]
_EDGE_COLS = ["edge_id", "u", "v", "key", "length_m", "highway", "oneway", "maxspeed", "geometry"]


@register("map_source", "osm")
class OSMMapSource(MapSource):
    """Downloads, projects, and persists an OSM road network for one bbox."""

    def __init__(
        self,
        region: str,
        bbox: tuple[float, float, float, float],
        crs: str,
        out_dir: str | Path,
        network_type: str = "drive",
    ) -> None:
        self.region = region
        self.bbox = bbox
        self._crs = crs
        self.out_dir = Path(out_dir) / region
        self.network_type = network_type

    @property
    def crs(self) -> str:
        """Target CRS from configuration."""
        return self._crs

    def build(self) -> RoadNetwork:
        """Download the bbox from OSM, project to the target CRS, persist, and return."""
        graph = ox.graph_from_bbox(self.bbox, network_type=self.network_type)
        # Projection overwrites node x/y in place and OSMnx keeps no geographic
        # copy, so preserve lon/lat before projecting.
        for _, data in graph.nodes(data=True):
            data["lon"] = data["x"]
            data["lat"] = data["y"]
        graph = ox.project_graph(graph, to_crs=self._crs)
        nodes, edges = _to_tables(graph)
        self._save(graph, nodes, edges)
        return RoadNetwork(graph=graph, nodes=nodes, edges=edges, region=self.region, crs=self._crs)

    def load(self) -> RoadNetwork:
        """Read a previously built network from disk (never touches the network)."""
        meta_path = self.out_dir / _META_FILE
        if not meta_path.exists():
            raise FileNotFoundError(
                f"no built map at {self.out_dir}; "
                f"run: python -m trajguard.maps.build config/maps.yaml --region {self.region}"
            )
        meta = json.loads(meta_path.read_text())
        graph = ox.load_graphml(self.out_dir / _GRAPH_FILE)
        nodes = gpd.read_parquet(self.out_dir / _NODES_FILE)
        edges = gpd.read_parquet(self.out_dir / _EDGES_FILE)
        return RoadNetwork(
            graph=graph, nodes=nodes, edges=edges, region=meta["region"], crs=meta["crs"]
        )

    def _save(
        self, graph: nx.MultiDiGraph, nodes: gpd.GeoDataFrame, edges: gpd.GeoDataFrame
    ) -> None:
        """Write graph.graphml, node/edge Parquet tables, and the Map metadata JSON."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(graph, self.out_dir / _GRAPH_FILE)
        nodes.to_parquet(self.out_dir / _NODES_FILE)
        edges.to_parquet(self.out_dir / _EDGES_FILE)
        meta = Map(
            map_id=f"osm_{self.region}",
            source="osm",
            region=self.region,
            bbox=self.bbox,
            crs=self._crs,
            osm_timestamp=str(graph.graph.get("created_date")),
            path_graph=str(self.out_dir / _GRAPH_FILE),
            path_edges=str(self.out_dir / _EDGES_FILE),
            path_nodes=str(self.out_dir / _NODES_FILE),
        )
        (self.out_dir / _META_FILE).write_text(json.dumps(asdict(meta), indent=2))


def _to_tables(graph: nx.MultiDiGraph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Normalize OSMnx node/edge GeoDataFrames to the design §4 RoadGraph schema."""
    nodes, edges = ox.graph_to_gdfs(graph)

    nodes = nodes.reset_index(names="node_id")
    nodes = nodes[[c for c in _NODE_COLS if c in nodes.columns]]

    edges = edges.reset_index()  # u, v, key become columns
    edges["edge_id"] = range(len(edges))
    edges = edges.rename(columns={"length": "length_m"})
    for col in _LISTY_EDGE_COLS:
        edges[col] = edges[col].astype(str) if col in edges.columns else None
    return nodes, edges[_EDGE_COLS]
