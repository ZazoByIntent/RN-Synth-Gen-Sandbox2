"""Tests for the Geolife .plt loader against the synthetic fixture tree."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trajguard.datamodel import RawTrajectory
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.experiments import registry

KNOWN_ID = "geolife/000/20081023025304"
KNOWN_START = datetime(2008, 10, 23, 2, 53, 4, tzinfo=UTC).timestamp()


@pytest.fixture()
def raws(geolife_root: Path) -> list[RawTrajectory]:
    return list(GeolifeLoader(geolife_root).iter_trajectories())


def test_loader_is_registered() -> None:
    assert registry.get("dataset", "geolife") is GeolifeLoader


def test_dataset_metadata(geolife_root: Path) -> None:
    loader = GeolifeLoader(geolife_root)
    assert loader.dataset_id == "geolife"
    assert loader.native_region == "beijing"


def test_yields_all_fixture_trajectories(raws: list[RawTrajectory]) -> None:
    assert len(raws) == 20
    assert len({r.traj_id for r in raws}) == 20
    assert {r.user_id for r in raws} == {"000", "001", "002", "003", "004"}


def test_known_file_parses_exactly(raws: list[RawTrajectory]) -> None:
    raw = next(r for r in raws if r.traj_id == KNOWN_ID)
    assert raw.n_points == 100
    assert raw.points[0] == (39.983, 116.305, KNOWN_START)
    assert raw.start_t == KNOWN_START
    assert raw.end_t == KNOWN_START + 99 * 2  # 100 points, 2 s interval
    assert raw.source_file.endswith("20081023025304.plt")


def test_headers_skipped_and_points_consistent(raws: list[RawTrajectory]) -> None:
    for raw in raws:
        assert raw.n_points == len(raw.points)
        assert raw.start_t == raw.points[0][2]
        assert raw.end_t == raw.points[-1][2]
        # header lines would parse as NaN/garbage; all points must be numeric coords
        for lat, lon, t in raw.points:
            assert 39.9 < lat < 40.1
            assert 116.2 < lon < 116.4
            assert t > 0


def test_timestamps_strictly_increasing(raws: list[RawTrajectory]) -> None:
    for raw in raws:
        ts = [p[2] for p in raw.points]
        assert all(b > a for a, b in zip(ts, ts[1:], strict=False))
