"""Tests for TrajectoryView/Grid adapters and the NoProtection baseline."""

from pathlib import Path

import pytest

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.experiments import registry
from trajguard.privacy.none import NoProtection
from trajguard.representation import Grid, TrajectoryView

GRID = Grid(bbox=(116.30, 39.98, 116.32, 39.995), n_rows=3, n_cols=4)


@pytest.fixture()
def fixture_clean(onroad_root: Path) -> CleanTrajectory:
    raw = next(GeolifeLoader(onroad_root).iter_trajectories())
    cleaned = clean(raw, CleaningConfig())
    assert cleaned is not None
    return cleaned


def make_matched(traj_id: str = "geolife/005/x") -> MatchedTrajectory:
    return MatchedTrajectory(
        traj_id=traj_id,
        user_id="005",
        map_id="osm_beijing_fixture",
        edge_seq=(3, 1, 4),
        matched_points=((1.0, 2.0, 0.0, 0.5),),
        match_score=0.9,
        frac_matched=1.0,
    )


def test_as_gps_returns_clean_points(fixture_clean: CleanTrajectory) -> None:
    view = TrajectoryView(clean=fixture_clean)
    assert view.as_gps() == fixture_clean.points
    assert view.traj_id == fixture_clean.traj_id
    assert view.user_id == fixture_clean.user_id
    assert view.map_id == ""  # unmatched


def test_as_segments_returns_edge_seq(fixture_clean: CleanTrajectory) -> None:
    matched = make_matched(fixture_clean.traj_id)
    view = TrajectoryView(clean=fixture_clean, matched=matched)
    assert view.as_segments() == (3, 1, 4)
    assert view.map_id == "osm_beijing_fixture"


def test_grid_cell_indices() -> None:
    # 3x4 grid over bbox: cell width 0.005 lon, height 0.005 lat
    assert GRID.n_cells == 12
    assert GRID.cell_of(39.98, 116.30) == 0  # bottom-left corner
    assert GRID.cell_of(39.981, 116.311) == 2  # row 0, col 2
    assert GRID.cell_of(39.9949, 116.3199) == 11  # top-right interior
    # boundary max lat/lon and out-of-bbox points clamp to border cells
    assert GRID.cell_of(39.995, 116.32) == 11
    assert GRID.cell_of(50.0, 200.0) == 11
    assert GRID.cell_of(0.0, 0.0) == 0


def test_as_cells_one_per_point(fixture_clean: CleanTrajectory) -> None:
    cells = TrajectoryView(clean=fixture_clean).as_cells(GRID)
    assert len(cells) == len(fixture_clean.points)
    assert all(0 <= c < GRID.n_cells for c in cells)


def test_missing_forms_raise(fixture_clean: CleanTrajectory) -> None:
    with pytest.raises(ValueError, match="clean and/or matched"):
        TrajectoryView()
    with pytest.raises(ValueError, match="requires a matched"):
        TrajectoryView(clean=fixture_clean).as_segments()
    with pytest.raises(ValueError, match="requires a clean"):
        TrajectoryView(matched=make_matched()).as_gps()


def test_matched_only_view_properties() -> None:
    view = TrajectoryView(matched=make_matched())
    assert view.traj_id == "geolife/005/x"
    assert view.user_id == "005"
    assert view.split is None


def test_horizon_b_views_not_implemented(fixture_clean: CleanTrajectory) -> None:
    view = TrajectoryView(clean=fixture_clean)
    with pytest.raises(NotImplementedError):
        view.as_graph_path()
    with pytest.raises(NotImplementedError):
        view.as_poi_visits(None)


def test_no_protection_is_registered() -> None:
    assert registry.get("mechanism", "none") is NoProtection


def test_no_protection_identity(fixture_clean: CleanTrajectory) -> None:
    view = TrajectoryView(clean=fixture_clean)
    mech = NoProtection()
    protected = mech.apply(view)
    assert protected.payload == view.as_gps()
    assert protected.guarantee == "none"
    assert protected.epsilon is None
    assert protected.mechanism_id == "none"
    assert protected.source_traj_id == fixture_clean.traj_id
    assert protected.traj_id == f"none/{fixture_clean.traj_id}"
    assert mech.spent_budget() is None
    # params_hash is deterministic and parameter-sensitive
    assert protected.params_hash == mech.apply(view).params_hash
    assert mech.apply(view, foo=1).params_hash != protected.params_hash
