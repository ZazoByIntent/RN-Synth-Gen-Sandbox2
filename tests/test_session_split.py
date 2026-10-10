"""Tests for the optional session split at stops (P10, cleaning.split_sessions)."""

from pathlib import Path

import pytest

from test_orchestrator import base_config, write_config
from trajguard.datamodel import RawTrajectory
from trajguard.datasets.cleaning import (
    CleaningConfig,
    clean,
    clean_trips,
    find_cuts,
    haversine_m,
)
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.experiments.orchestrator import _version_hash, load_config

OFF = CleaningConfig()
ON = CleaningConfig(split_sessions=True)
LAT = 39.9
M_PER_DEG_LON = 111_320.0 * 0.76668  # cos(39.9 deg)

# Version hash of the fixed-path config below as computed before P10 existed: the option
# off must leave it, and so every cached pool and config_hash, byte-identical.
PRE_P10_HASH = "abe8b341d8bfb1ca"


def _move(x0_m: float, t0: float, n: int, step_m: float = 50.0) -> list[tuple[float, float, float]]:
    """``n`` points heading east from ``x0_m`` at 10 m/s, 5 s apart."""
    return [(LAT, 116.30 + (x0_m + k * step_m) / M_PER_DEG_LON, t0 + 5.0 * k) for k in range(n)]


def _dwell(x_m: float, t0: float, n: int) -> list[tuple[float, float, float]]:
    """``n`` points 5 s apart jittering by 10 m around ``x_m``."""
    return [
        (LAT + (10.0 if k % 2 else -10.0) / 111_320.0, 116.30 + x_m / M_PER_DEG_LON, t0 + 5.0 * k)
        for k in range(n)
    ]


def _raw(points: list[tuple[float, float, float]]) -> RawTrajectory:
    return RawTrajectory(
        traj_id="geolife/007/20081010101010",
        user_id="007",
        dataset_id="geolife",
        points=tuple(points),
        start_t=points[0][2],
        end_t=points[-1][2],
        n_points=len(points),
        source_file="synthetic",
    )


def _session_with_stop(dwell_points: int) -> RawTrajectory:
    first = _move(0.0, 0.0, 40)  # 1950 m in 195 s
    stop_x = first[-1][1] - 116.30
    dwell = _dwell(stop_x * M_PER_DEG_LON, first[-1][2] + 5.0, dwell_points)
    second = _move(stop_x * M_PER_DEG_LON + 50.0, dwell[-1][2] + 5.0, 40)
    return _raw(first + dwell + second)


def test_stop_splits_session_into_two_trips() -> None:
    raw = _session_with_stop(dwell_points=48)  # 4 minutes within ~20 m
    trips = clean_trips(raw, ON)
    assert [t.traj_id for t in trips] == [f"{raw.traj_id}_trip0", f"{raw.traj_id}_trip1"]
    assert all(t.user_id == "007" for t in trips)
    stop_start, stop_end = raw.points[40][2], raw.points[40 + 47][2]
    assert trips[0].points[-1][2] < stop_start and trips[1].points[0][2] >= stop_end
    assert sum(t.duration_s for t in trips) < raw.end_t - raw.start_t - 200.0
    assert trips[1].cleaning_flags[-1] == "session_trip:1"


def test_short_stop_and_no_stop_keep_session_whole() -> None:
    short = _session_with_stop(dwell_points=24)  # 2 minutes: below the 3-minute rule
    assert clean_trips(short, ON) == [clean(short, OFF)]
    moving = _raw(_move(0.0, 0.0, 80))
    assert find_cuts(clean(moving, OFF).points) == []  # type: ignore[union-attr]
    assert clean_trips(moving, ON) == [clean(moving, OFF)]


def test_gap_rule_cuts_only_short_displacement() -> None:
    first = _move(0.0, 0.0, 30)
    x_end = (first[-1][1] - 116.30) * M_PER_DEG_LON
    near = _move(x_end + 250.0, first[-1][2] + 200.0, 30)  # 200 s gap, 250 m away
    far = _move(x_end + 500.0, first[-1][2] + 200.0, 30)  # 200 s gap, 500 m away
    pts_near = tuple(first + near)
    assert haversine_m(*first[-1][:2], *near[0][:2]) == pytest.approx(250.0, rel=0.01)
    assert find_cuts(pts_near) == [(29, 30)]
    assert find_cuts(tuple(first + far)) == []


def test_split_is_deterministic() -> None:
    raw = _session_with_stop(dwell_points=48)
    assert clean_trips(raw, ON) == clean_trips(raw, ON)


def test_option_off_matches_clean_on_fixture(geolife_root: Path) -> None:
    for raw in GeolifeLoader(geolife_root).iter_trajectories():
        whole = clean(raw, OFF)
        assert clean_trips(raw, OFF) == ([] if whole is None else [whole])


def test_version_hash_unchanged_off_and_changed_on(tmp_path: Path) -> None:
    cfg = base_config(Path("out_fixed"), Path("maps_fixed"))
    cfg["dataset"]["path"] = "geolife_fixed"
    assert _version_hash(load_config(write_config(tmp_path, cfg))) == PRE_P10_HASH
    cfg["cleaning"]["split_sessions"] = False
    assert _version_hash(load_config(write_config(tmp_path, cfg))) == PRE_P10_HASH
    cfg["cleaning"]["split_sessions"] = True
    on = load_config(write_config(tmp_path, cfg))
    assert on.cleaning.split_sessions is True
    assert _version_hash(on) != PRE_P10_HASH


def test_split_sessions_must_be_boolean(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["cleaning"]["split_sessions"] = "yes"
    with pytest.raises(ValueError, match="split_sessions"):
        load_config(write_config(tmp_path, cfg))
