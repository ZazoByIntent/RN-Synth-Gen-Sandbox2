"""Shared pytest fixtures over the committed fixture data (synthetic Geolife + map fragment)."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def geolife_root() -> Path:
    """Root of the synthetic Geolife fixture tree (see fixtures/geolife/README.md)."""
    return FIXTURES_DIR / "geolife"


@pytest.fixture()
def fixture_maps_dir() -> Path:
    """Directory containing the committed beijing_fixture road network."""
    return FIXTURES_DIR / "maps"
