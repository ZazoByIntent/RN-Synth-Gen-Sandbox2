"""Shared pytest fixtures over the committed fixture data (synthetic Geolife + map fragment)."""

from pathlib import Path

import pytest

from trajguard.maps.base import RoadNetwork
from trajguard.maps.osm import OSMMapSource

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def geolife_root() -> Path:
    """Root of the synthetic Geolife fixture tree (see fixtures/geolife/README.md)."""
    return FIXTURES_DIR / "geolife"


@pytest.fixture()
def fixture_maps_dir() -> Path:
    """Directory containing the committed beijing_fixture road network."""
    return FIXTURES_DIR / "maps"


@pytest.fixture()
def onroad_root() -> Path:
    """Root of the road-following fixture tree (see fixtures/geolife_onroad/README.md)."""
    return FIXTURES_DIR / "geolife_onroad"


@pytest.fixture(scope="session")
def fixture_network() -> RoadNetwork:
    """The committed beijing_fixture RoadNetwork, loaded once per test session."""
    return OSMMapSource(
        region="beijing_fixture",
        bbox=(116.30, 39.98, 116.32, 39.995),
        crs="EPSG:32650",
        out_dir=FIXTURES_DIR / "maps",
    ).load()
