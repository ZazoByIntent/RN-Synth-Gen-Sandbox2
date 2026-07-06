"""Round-trip test for OSMMapSource.load() on the committed fixture network (no network IO)."""

from pathlib import Path

import pytest

from trajguard.experiments import registry
from trajguard.maps.osm import OSMMapSource

FIXTURE_BBOX = (116.30, 39.98, 116.32, 39.995)


def test_source_is_registered() -> None:
    assert registry.get("map_source", "osm") is OSMMapSource


def test_load_missing_map_raises_with_hint(tmp_path: Path) -> None:
    source = OSMMapSource(region="nowhere", bbox=FIXTURE_BBOX, crs="EPSG:32650", out_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="trajguard.maps.build"):
        source.load()


def test_fixture_map_roundtrip(fixture_maps_dir: Path) -> None:
    source = OSMMapSource(
        region="beijing_fixture", bbox=FIXTURE_BBOX, crs="EPSG:32650", out_dir=fixture_maps_dir
    )
    net = source.load()
    assert net.region == "beijing_fixture"
    assert net.crs == "EPSG:32650"
    assert source.crs == "EPSG:32650"
    # tables match the graph
    assert len(net.nodes) == net.graph.number_of_nodes() > 0
    assert len(net.edges) == net.graph.number_of_edges() > 0
    # design §4 RoadGraph schema
    assert {"node_id", "x", "y", "lon", "lat"} <= set(net.nodes.columns)
    assert {"edge_id", "u", "v", "key", "length_m", "highway", "oneway"} <= set(net.edges.columns)
    assert list(net.edges["edge_id"]) == list(range(len(net.edges)))
    assert net.edges["geometry"].notna().all()
    assert (net.edges["length_m"] > 0).all()
    # projected coordinates are meters (UTM 50N), geographic copies stay degrees
    assert net.nodes["x"].between(100_000, 900_000).all()
    assert net.nodes["lon"].between(116.29, 116.33).all()
    assert net.nodes["lat"].between(39.97, 40.00).all()
    # graph node dict lon/lat come back as floats (build() leaves them float; load_graphml
    # would otherwise round-trip these custom attrs as strings)
    _, data = next(iter(net.graph.nodes(data=True)))
    assert isinstance(data["lon"], float) and isinstance(data["lat"], float)
