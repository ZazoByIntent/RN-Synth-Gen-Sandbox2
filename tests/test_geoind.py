"""Tests for the planar-Laplace geo-indistinguishability mechanism."""

import pytest

from trajguard.datamodel import CleanTrajectory
from trajguard.datasets.cleaning import haversine_m
from trajguard.experiments import registry
from trajguard.privacy.geoind import GeoIndistinguishability
from trajguard.representation import TrajectoryView


def make_view(n_points: int = 50) -> TrajectoryView:
    """A straight-line trajectory near the Beijing fixture area."""
    points = tuple((39.98 + i * 1e-4, 116.31 + i * 1e-4, float(i * 5)) for i in range(n_points))
    clean = CleanTrajectory(
        traj_id="t1",
        user_id="u1",
        points=points,
        bbox=(116.31, 39.98, points[-1][1], points[-1][0]),
        duration_s=points[-1][2],
        length_m=1000.0,
        mean_speed=2.0,
        cleaning_flags=(),
    )
    return TrajectoryView(clean=clean)


def mean_displacement_m(view: TrajectoryView, mech: GeoIndistinguishability) -> float:
    original = view.as_gps()
    noisy = mech.apply(view).payload
    dists = [
        haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(original, noisy, strict=True)
    ]
    return sum(dists) / len(dists)


def test_same_seed_is_deterministic() -> None:
    view = make_view()
    first = GeoIndistinguishability(epsilon=1.0, seed=7).apply(view)
    second = GeoIndistinguishability(epsilon=1.0, seed=7).apply(view)
    assert first.payload == second.payload


def test_different_seed_differs() -> None:
    view = make_view()
    first = GeoIndistinguishability(epsilon=1.0, seed=7).apply(view)
    second = GeoIndistinguishability(epsilon=1.0, seed=8).apply(view)
    assert first.payload != second.payload


def test_noise_scale_matches_planar_laplace_mean() -> None:
    """Mean radial displacement of planar Laplace is 2 * unit_m / epsilon."""
    view = make_view(n_points=2000)
    mean = mean_displacement_m(view, GeoIndistinguishability(epsilon=1.0, unit_m=100.0, seed=42))
    assert 180.0 < mean < 220.0  # expected 200 m, sem ~3 m at n=2000


def test_higher_epsilon_means_less_noise() -> None:
    view = make_view(n_points=500)
    strong = mean_displacement_m(view, GeoIndistinguishability(epsilon=0.1, seed=1))
    weak = mean_displacement_m(view, GeoIndistinguishability(epsilon=10.0, seed=1))
    assert weak < strong


def test_timestamps_metadata_and_guarantee_preserved() -> None:
    view = make_view()
    protected = GeoIndistinguishability(epsilon=2.0, seed=0).apply(view)
    assert [p[2] for p in protected.payload] == [p[2] for p in view.as_gps()]
    assert protected.source_traj_id == "t1"
    assert protected.mechanism_id == "geo_indistinguishability"
    assert protected.guarantee == "geo-ind"
    assert protected.epsilon == 2.0


def test_spent_budget_accumulates_per_point() -> None:
    view = make_view(n_points=50)
    mech = GeoIndistinguishability(epsilon=2.0, seed=0)
    assert mech.spent_budget() == 0.0
    mech.apply(view)
    mech.apply(view)
    assert mech.spent_budget() == pytest.approx(2.0 * 50 * 2)


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        GeoIndistinguishability(epsilon=0.0)
    with pytest.raises(ValueError, match="epsilon"):
        GeoIndistinguishability(epsilon=-1.0)
    with pytest.raises(ValueError, match="unit_m"):
        GeoIndistinguishability(epsilon=1.0, unit_m=0.0)


def test_registered_under_expected_name() -> None:
    assert registry.get("mechanism", "geo_indistinguishability") is GeoIndistinguishability
