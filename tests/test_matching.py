"""Tests for LeuvenMapMatcher on the committed fixture network (no network IO)."""

from itertools import pairwise
from pathlib import Path

import pytest

from trajguard.datamodel import CleanTrajectory
from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.experiments import registry
from trajguard.maps.base import RoadNetwork
from trajguard.matching.base import match_many
from trajguard.matching.leuven import LeuvenMapMatcher

# DoD anchor: route documented in tests/fixtures/geolife_onroad/README.md
# (nodes 1767362150 -> 1293134700); sequence pinned at fixture generation time.
KNOWN_ID = "geolife/005/20081201080000"
KNOWN_EDGE_SEQ = (233, 234, 227, 13, 15, 7, 9, 225, 33)

CFG = CleaningConfig()


@pytest.fixture()
def onroad_cleaned(onroad_root: Path) -> list[CleanTrajectory]:
    cleaned = [clean(r, CFG) for r in GeolifeLoader(onroad_root).iter_trajectories()]
    assert all(c is not None for c in cleaned)
    return [c for c in cleaned if c is not None]


@pytest.fixture()
def matcher() -> LeuvenMapMatcher:
    return LeuvenMapMatcher()


def test_matcher_is_registered() -> None:
    assert registry.get("matcher", "leuven") is LeuvenMapMatcher


def test_known_trajectory_expected_edge_sequence(
    matcher: LeuvenMapMatcher, onroad_cleaned: list[CleanTrajectory], fixture_network: RoadNetwork
) -> None:
    traj = next(c for c in onroad_cleaned if c.traj_id == KNOWN_ID)
    matched = matcher.match(traj, fixture_network)
    assert matched.edge_seq == KNOWN_EDGE_SEQ
    # sequence must be contiguous in the graph: v of edge i == u of edge i+1
    edges = fixture_network.edges.set_index("edge_id")
    for a, b in pairwise(matched.edge_seq):
        assert edges.loc[a, "v"] == edges.loc[b, "u"]


def test_all_onroad_fully_matched(
    matcher: LeuvenMapMatcher, onroad_cleaned: list[CleanTrajectory], fixture_network: RoadNetwork
) -> None:
    for traj in onroad_cleaned:
        matched = matcher.match(traj, fixture_network)
        q = matcher.quality(matched)
        assert matched.frac_matched == 1.0, traj.traj_id
        assert q["mean_offset_m"] < 10.0, traj.traj_id
        assert matched.match_score > 0.8, traj.traj_id
        assert len(matched.matched_points) == len(traj.points)
        assert matched.map_id == "osm_beijing_fixture"
        # timestamps carried over unchanged
        assert [p[2] for p in matched.matched_points] == [p[2] for p in traj.points]


def test_offroad_walk_scores_low_and_is_dropped(
    matcher: LeuvenMapMatcher,
    onroad_cleaned: list[CleanTrajectory],
    geolife_root: Path,
    fixture_network: RoadNetwork,
) -> None:
    walk_raw = next(
        r
        for r in GeolifeLoader(geolife_root).iter_trajectories()
        if r.traj_id == "geolife/001/20081026103000"
    )
    walk = clean(walk_raw, CFG)
    assert walk is not None
    matched = matcher.match(walk, fixture_network)
    assert matched.match_score < 0.6

    kept, dropped = match_many(matcher, [*onroad_cleaned, walk], fixture_network, 0.6)
    assert len(kept) == len(onroad_cleaned)
    assert dropped == 1
