"""Tests for the point-level ε-LDP mechanism (randomized response over grid cells)."""

import math

import numpy as np
import pytest

from trajguard.datamodel import CleanTrajectory
from trajguard.experiments import registry
from trajguard.privacy.point_ldp import PointLDP
from trajguard.representation import Grid, TrajectoryView

BBOX = (116.20, 39.75, 116.55, 40.05)  # the Beijing map bbox of the Geolife configs
GRID = Grid(bbox=BBOX, n_rows=20, n_cols=20)


def make_view(n_points: int = 50, seed: int = 0, spill: float = 0.0) -> TrajectoryView:
    """A trajectory of ``n_points`` random points over the bbox, widened by ``spill`` degrees."""
    rng = np.random.default_rng(seed)
    lats = rng.uniform(BBOX[1] - spill, BBOX[3] + spill, n_points)
    lons = rng.uniform(BBOX[0] - spill, BBOX[2] + spill, n_points)
    points = tuple(
        (float(lat), float(lon), float(i * 5))
        for i, (lat, lon) in enumerate(zip(lats, lons, strict=True))
    )
    clean = CleanTrajectory(
        traj_id="t1",
        user_id="u1",
        points=points,
        bbox=(float(lons.min()), float(lats.min()), float(lons.max()), float(lats.max())),
        duration_s=points[-1][2],
        length_m=1000.0,
        mean_speed=2.0,
        cleaning_flags=(),
    )
    return TrajectoryView(clean=clean)


def true_cell_fraction(view: TrajectoryView, mech: PointLDP) -> float:
    """Share of released points that fall in the cell of their original point."""
    original = view.as_gps()
    released = mech.apply(view).payload
    same = sum(
        GRID.cell_of(a[0], a[1]) == GRID.cell_of(b[0], b[1])
        for a, b in zip(original, released, strict=True)
    )
    return same / len(original)


def test_same_seed_is_deterministic() -> None:
    view = make_view()
    first = PointLDP(epsilon=6.0, bbox=BBOX, seed=7).apply(view)
    second = PointLDP(epsilon=6.0, bbox=BBOX, seed=7).apply(view)
    assert first.payload == second.payload


def test_different_seed_differs() -> None:
    view = make_view()
    first = PointLDP(epsilon=6.0, bbox=BBOX, seed=7).apply(view)
    second = PointLDP(epsilon=6.0, bbox=BBOX, seed=8).apply(view)
    assert first.payload != second.payload


def test_true_cell_fraction_matches_randomized_response() -> None:
    """At ε = 6 over k = 400 cells the true cell survives w.p. e^6/(e^6 + 399) ≈ 0.50."""
    view = make_view(n_points=2000)
    expected = math.exp(6.0) / (math.exp(6.0) + 399)
    assert expected == pytest.approx(0.5027, abs=1e-3)
    fraction = true_cell_fraction(view, PointLDP(epsilon=6.0, bbox=BBOX, seed=42))
    assert abs(fraction - expected) < 0.05  # binomial sd at n=2000 is ~0.011


def test_higher_epsilon_keeps_more_points() -> None:
    view = make_view(n_points=500)
    weak = true_cell_fraction(view, PointLDP(epsilon=2.0, bbox=BBOX, seed=1))
    strong = true_cell_fraction(view, PointLDP(epsilon=8.0, bbox=BBOX, seed=1))
    assert weak < 0.2 < 0.8 < strong  # expected 0.018 and 0.88


def test_timestamps_metadata_and_guarantee_preserved() -> None:
    view = make_view()
    mech = PointLDP(epsilon=4.0, bbox=BBOX, seed=0)
    protected = mech.apply(view)
    assert [p[2] for p in protected.payload] == [p[2] for p in view.as_gps()]
    assert len(protected.payload) == len(view.as_gps())
    assert protected.traj_id == "point_ldp/t1"
    assert protected.source_traj_id == "t1"
    assert protected.mechanism_id == "point_ldp"
    assert protected.guarantee == "ldp"
    assert protected.epsilon == 4.0
    assert mech.epsilon == 4.0
    assert not hasattr(mech, "unit_m")  # the results table must not record a unit for LDP


def test_spent_budget_accumulates_per_point() -> None:
    view = make_view(n_points=50)
    mech = PointLDP(epsilon=4.0, bbox=BBOX, seed=0)
    assert mech.spent_budget() == 0.0
    mech.apply(view)
    mech.apply(view)
    assert mech.spent_budget() == pytest.approx(4.0 * 50 * 2)


def test_released_points_stay_inside_bbox_even_for_outside_points() -> None:
    view = make_view(n_points=400, spill=0.1)  # a quarter of the points lie outside the bbox
    outside = [
        p for p in view.as_gps() if not (BBOX[1] <= p[0] <= BBOX[3] and BBOX[0] <= p[1] <= BBOX[2])
    ]
    assert outside, "the fixture must spill outside the bbox for this test to mean anything"
    for jitter in (True, False):
        payload = PointLDP(epsilon=4.0, bbox=BBOX, jitter=jitter, seed=3).apply(view).payload
        assert all(
            BBOX[1] <= lat <= BBOX[3] and BBOX[0] <= lon <= BBOX[2] for lat, lon, _ in payload
        )


def test_jittered_point_lies_inside_the_reported_cell() -> None:
    """Same seed, jitter on/off: identical reported cells, the jittered point inside that cell."""
    view = make_view(n_points=300)
    centres = PointLDP(epsilon=6.0, bbox=BBOX, jitter=False, seed=5).apply(view).payload
    jittered = PointLDP(epsilon=6.0, bbox=BBOX, jitter=True, seed=5).apply(view).payload
    assert jittered != centres
    for (c_lat, c_lon, _), (j_lat, j_lon, _) in zip(centres, jittered, strict=True):
        min_lon, min_lat, max_lon, max_lat = GRID.cell_bounds(GRID.cell_of(c_lat, c_lon))
        assert min_lat <= j_lat <= max_lat and min_lon <= j_lon <= max_lon
    # the jitter is not degenerate: released points spread over the cell, not one corner
    lat_offsets = [
        (j[0] - GRID.cell_bounds(GRID.cell_of(c[0], c[1]))[1]) / ((BBOX[3] - BBOX[1]) / 20)
        for c, j in zip(centres, jittered, strict=True)
    ]
    assert 0.4 < float(np.mean(lat_offsets)) < 0.6


def test_centre_release_is_the_exact_cell_centre() -> None:
    view = make_view(n_points=100)
    payload = PointLDP(epsilon=6.0, bbox=BBOX, jitter=False, seed=9).apply(view).payload
    for lat, lon, _ in payload:
        min_lon, min_lat, max_lon, max_lat = GRID.cell_bounds(GRID.cell_of(lat, lon))
        assert lat == pytest.approx((min_lat + max_lat) / 2)
        assert lon == pytest.approx((min_lon + max_lon) / 2)


def test_grid_dimensions_are_configurable() -> None:
    view = make_view(n_points=100)
    mech = PointLDP(epsilon=6.0, bbox=BBOX, n_rows=2, n_cols=3, jitter=False, seed=0)
    assert mech.grid.n_cells == 6
    centres = {(round(lat, 6), round(lon, 6)) for lat, lon, _ in mech.apply(view).payload}
    assert len(centres) <= 6


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        PointLDP(epsilon=0.0, bbox=BBOX)
    with pytest.raises(ValueError, match="epsilon"):
        PointLDP(epsilon=-1.0, bbox=BBOX)
    with pytest.raises(ValueError, match="n_rows and n_cols"):
        PointLDP(epsilon=1.0, bbox=BBOX, n_rows=0)
    with pytest.raises(ValueError, match="n_rows and n_cols"):
        PointLDP(epsilon=1.0, bbox=BBOX, n_cols=0)
    with pytest.raises(ValueError, match="at least 2 cells"):
        PointLDP(epsilon=1.0, bbox=BBOX, n_rows=1, n_cols=1)
    with pytest.raises(ValueError, match="min < max"):
        PointLDP(epsilon=1.0, bbox=(116.55, 39.75, 116.20, 40.05))
    with pytest.raises(ValueError, match="min < max"):
        PointLDP(epsilon=1.0, bbox=(116.20, 40.05, 116.55, 40.05))
    with pytest.raises(ValueError, match="bbox must be"):
        PointLDP(epsilon=1.0, bbox=(116.20, 39.75, 116.55))  # type: ignore[arg-type]


def test_registered_under_expected_name() -> None:
    assert registry.get("mechanism", "point_ldp") is PointLDP
