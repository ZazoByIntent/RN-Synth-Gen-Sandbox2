"""Tests for trajectory cleaning against the planted fixture defects."""

from itertools import pairwise
from pathlib import Path

import pytest

from trajguard.datamodel import CleanTrajectory, RawTrajectory
from trajguard.datasets.cleaning import CleaningConfig, clean, haversine_m
from trajguard.datasets.geolife import GeolifeLoader

SPIKED_ID = "geolife/002/20081101020000"
TOO_FEW_POINTS_ID = "geolife/004/20081104010000"
TOO_SHORT_ID = "geolife/004/20081105010000"
KNOWN_ID = "geolife/000/20081023025304"

CFG = CleaningConfig(max_speed_kmh=200.0, min_points=20, min_length_m=500.0, resample_s=5.0)


@pytest.fixture()
def raws_by_id(geolife_root: Path) -> dict[str, RawTrajectory]:
    return {r.traj_id: r for r in GeolifeLoader(geolife_root).iter_trajectories()}


def test_haversine_known_distance() -> None:
    # one degree of latitude is ~111.2 km
    assert haversine_m(39.0, 116.0, 40.0, 116.0) == pytest.approx(111_195, rel=0.01)


def test_planted_speed_outliers_removed(raws_by_id: dict[str, RawTrajectory]) -> None:
    raw = raws_by_id[SPIKED_ID]
    assert max(p[0] for p in raw.points) > 40.0  # spikes present in raw input
    cleaned = clean(raw, CFG)
    assert cleaned is not None
    assert "speed_outliers_dropped:3" in cleaned.cleaning_flags
    assert max(p[0] for p in cleaned.points) < 39.995  # spikes gone


def test_too_few_points_rejected(raws_by_id: dict[str, RawTrajectory]) -> None:
    assert clean(raws_by_id[TOO_FEW_POINTS_ID], CFG) is None


def test_too_short_rejected(raws_by_id: dict[str, RawTrajectory]) -> None:
    assert clean(raws_by_id[TOO_SHORT_ID], CFG) is None


def test_only_planted_defects_rejected(raws_by_id: dict[str, RawTrajectory]) -> None:
    rejected = {tid for tid, raw in raws_by_id.items() if clean(raw, CFG) is None}
    assert rejected == {TOO_FEW_POINTS_ID, TOO_SHORT_ID}


def test_resampling_spacing(raws_by_id: dict[str, RawTrajectory]) -> None:
    for raw in raws_by_id.values():
        cleaned = clean(raw, CFG)
        if cleaned is None:
            continue
        assert all(b[2] - a[2] >= CFG.resample_s for a, b in pairwise(cleaned.points))


def test_known_trajectory_statistics(raws_by_id: dict[str, RawTrajectory]) -> None:
    cleaned = clean(raws_by_id[KNOWN_ID], CFG)
    assert cleaned is not None
    # deterministic L-shape: ~2 km path at 10 m/s, 198 s span, thinned to 6 s spacing
    assert len(cleaned.points) == 34
    assert cleaned.length_m == pytest.approx(1960, rel=0.01)
    assert cleaned.duration_s == pytest.approx(198.0)
    assert cleaned.mean_speed == pytest.approx(9.9, rel=0.01)
    assert cleaned.cleaning_flags == ("speed_outliers_dropped:0", "resampled:5s")
    min_lon, min_lat, max_lon, max_lat = cleaned.bbox
    assert min_lat < max_lat and min_lon < max_lon
    assert cleaned.split is None  # split is assigned in P3, not here


def test_clean_is_deterministic(raws_by_id: dict[str, RawTrajectory]) -> None:
    raw = raws_by_id[SPIKED_ID]
    first: CleanTrajectory | None = clean(raw, CFG)
    second: CleanTrajectory | None = clean(raw, CFG)
    assert first == second
