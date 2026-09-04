"""Tests for the three naive baselines: spatial rounding, temporal downsampling, Gaussian noise."""

import csv
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from test_orchestrator import base_config, beijing_maps_dir, write_config
from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.reidentification import ReidentificationAttack, _evenly_spaced
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.datasets.cleaning import CleaningConfig, clean, haversine_m
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.experiments import registry
from trajguard.experiments.orchestrator import _read_clean_table, run
from trajguard.maps.base import RoadNetwork
from trajguard.matching.base import match_many
from trajguard.matching.leuven import LeuvenMapMatcher
from trajguard.privacy.naive import (
    _METERS_PER_DEG_LAT,
    GaussianNoise,
    SpatialRounding,
    TemporalDownsampling,
)
from trajguard.representation import TrajectoryView

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here

Point = tuple[float, float, float]


def make_view(n_points: int = 50, step_s: float = 5.0) -> TrajectoryView:
    """A straight-line trajectory near the Beijing fixture area, one point per ``step_s``."""
    points = tuple(
        (39.98 + i * 1e-4, 116.31 + i * 1e-4, float(i) * step_s) for i in range(n_points)
    )
    clean_traj = CleanTrajectory(
        traj_id="t1",
        user_id="u1",
        points=points,
        bbox=(116.31, 39.98, points[-1][1], points[-1][0]),
        duration_s=points[-1][2],
        length_m=1000.0,
        mean_speed=2.0,
        cleaning_flags=(),
    )
    return TrajectoryView(clean=clean_traj)


def displacements_m(view: TrajectoryView, payload: tuple[Point, ...]) -> list[float]:
    """Pointwise haversine distance between the input and an equal-length release."""
    return [
        haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(view.as_gps(), payload, strict=True)
    ]


@pytest.fixture()
def onroad_cleaned(onroad_root: Path) -> list[CleanTrajectory]:
    """The eight road-following fixture trajectories, cleaned with the default config."""
    cleaned = [clean(r, CleaningConfig()) for r in GeolifeLoader(onroad_root).iter_trajectories()]
    assert all(c is not None for c in cleaned)
    return [c for c in cleaned if c is not None]


def released(clean_traj: CleanTrajectory, payload: tuple[Point, ...]) -> CleanTrajectory:
    """The released points as a CleanTrajectory (what the orchestrator re-matches)."""
    return replace(clean_traj, points=payload)


# --- spatial rounding -----------------------------------------------------------------


@pytest.mark.parametrize("cell_m", [100.0, 500.0, 2000.0])
def test_rounded_points_lie_on_the_grid(cell_m: float) -> None:
    view = make_view()
    payload = SpatialRounding(cell_m=cell_m).apply(view).payload
    d_lat = cell_m / _METERS_PER_DEG_LAT
    for lat, lon, _t in payload:
        assert (lat / d_lat) % 1.0 == pytest.approx(0.5, abs=1e-6)
        d_lon = cell_m / (_METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
        assert (lon / d_lon) % 1.0 == pytest.approx(0.5, abs=1e-6)


def test_rounding_is_idempotent() -> None:
    view = make_view()
    assert view.clean is not None
    mech = SpatialRounding(cell_m=500.0)
    once = mech.apply(view).payload
    twice = mech.apply(TrajectoryView(clean=released(view.clean, once))).payload
    assert twice == once


@pytest.mark.parametrize("cell_m", [100.0, 500.0, 2000.0])
def test_rounding_displacement_is_at_most_half_the_cell_diagonal(cell_m: float) -> None:
    view = make_view(n_points=400)
    dists = displacements_m(view, SpatialRounding(cell_m=cell_m).apply(view).payload)
    assert max(dists) <= cell_m * math.sqrt(2) / 2 * (1 + 1e-3)
    assert max(dists) > cell_m * 0.25  # some point sits far from its centre


def test_rounding_keeps_duplicates_and_the_matcher_accepts_them(
    onroad_cleaned: list[CleanTrajectory], fixture_network: RoadNetwork
) -> None:
    """D-3.3: consecutive identical released points are kept; match_many does not choke."""
    fine = [
        released(c, SpatialRounding(cell_m=25.0).apply(TrajectoryView(clean=c)).payload)
        for c in onroad_cleaned
    ]
    duplicates = sum(
        sum(1 for a, b in zip(r.points, r.points[1:], strict=False) if a[:2] == b[:2]) for r in fine
    )
    assert duplicates > 0, "the fixture must produce duplicate released points"
    kept, dropped = match_many(LeuvenMapMatcher(), fine, fixture_network, 0.6)
    assert len(kept) == 8 and dropped == 0
    # a coarse grid displaces every point beyond the 50 m matching radius: dropped, no error
    coarse = [
        released(c, SpatialRounding(cell_m=500.0).apply(TrajectoryView(clean=c)).payload)
        for c in onroad_cleaned
    ]
    kept, dropped = match_many(LeuvenMapMatcher(), coarse, fixture_network, 0.6)
    assert len(kept) + dropped == 8


# --- temporal downsampling ------------------------------------------------------------


def test_downsampling_keeps_first_and_last_and_spaces_points() -> None:
    view = make_view(n_points=50, step_s=5.0)  # 0..245 s
    payload = TemporalDownsampling(interval_s=30.0).apply(view).payload
    points = view.as_gps()
    assert payload[0] == points[0] and payload[-1] == points[-1]
    assert 1 < len(payload) < len(points)
    gaps = [b[2] - a[2] for a, b in zip(payload, payload[1:], strict=False)]
    assert all(g >= 30.0 for g in gaps[:-1])
    assert gaps[-1] > 0.0  # the last point is appended even when its gap is shorter
    assert set(payload) <= set(points)  # a subsequence: nothing is moved or invented


def test_downsampling_at_or_below_the_cleaning_step_is_the_identity() -> None:
    view = make_view(step_s=5.0)
    assert TemporalDownsampling(interval_s=5.0).apply(view).payload == view.as_gps()
    assert TemporalDownsampling(interval_s=1.0).apply(view).payload == view.as_gps()


@pytest.mark.parametrize("n_points", [1, 2, 3])
def test_downsampling_short_trajectories_do_not_break(n_points: int) -> None:
    view = make_view(n_points=n_points)
    payload = TemporalDownsampling(interval_s=600.0).apply(view).payload
    expected = view.as_gps() if n_points <= 2 else (view.as_gps()[0], view.as_gps()[-1])
    assert payload == expected


def test_short_releases_pass_through_matching(
    onroad_cleaned: list[CleanTrajectory], fixture_network: RoadNetwork
) -> None:
    """D-3.2: a first-and-last-only release re-matches or drops, never raises."""
    two_point = [
        released(c, TemporalDownsampling(interval_s=1e9).apply(TrajectoryView(clean=c)).payload)
        for c in onroad_cleaned
    ]
    assert all(len(r.points) == 2 for r in two_point)
    kept, dropped = match_many(LeuvenMapMatcher(), two_point, fixture_network, 0.6)
    assert len(kept) + dropped == 8
    for m in kept:
        assert 1 <= len(m.matched_points) <= 2


def test_evenly_spaced_returns_everything_for_short_sequences() -> None:
    for n in (1, 2):
        seq = np.arange(n * 2, dtype=float).reshape(n, 2)
        for k in (3, 5, 10):
            assert _evenly_spaced(seq, k).shape == (n, 2)


def mt(traj_id: str, user: str, pts: list[tuple[float, float]]) -> MatchedTrajectory:
    return MatchedTrajectory(
        traj_id=traj_id,
        user_id=user,
        map_id="osm_test",
        edge_seq=(1,),
        matched_points=tuple((x, y, float(i), 0.0) for i, (x, y) in enumerate(pts)),
        match_score=0.9,
        frac_matched=1.0,
    )


def test_reidentification_ranks_short_gallery_trajectories() -> None:
    """D-3.2: gallery entries of one or two points still get a DTW distance and a rank."""
    raw = [
        mt("A1", "A", [(0, 0), (1, 0), (2, 0), (3, 0)]),
        mt("A2", "A", [(0, 0.1), (1, 0.1), (2, 0.1), (3, 0.1)]),
        mt("B1", "B", [(0, 10), (0, 11), (0, 12), (0, 13)]),
        mt("B2", "B", [(0.1, 10), (0.1, 11), (0.1, 12), (0.1, 13)]),
    ]
    thinned = [  # the released gallery after heavy downsampling: 1-2 points each
        mt("A1", "A", [(0, 0), (3, 0)]),
        mt("A2", "A", [(0, 0.1)]),
        mt("B1", "B", [(0, 10), (0, 13)]),
        mt("B2", "B", [(0.1, 10)]),
    ]
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=10))  # more than any release holds
    result = attack.run(thinned, aux=raw)
    assert len(result.predictions) == 4
    for ranking in result.predictions:
        assert ranking.users[0] == ranking.true_user  # the thinned own-user trace is nearest
        assert all(math.isfinite(d) for d in ranking.distances)


# --- gaussian noise -------------------------------------------------------------------


def test_gaussian_same_seed_is_deterministic() -> None:
    view = make_view()
    first = GaussianNoise(sigma_m=200.0, seed=7).apply(view)
    second = GaussianNoise(sigma_m=200.0, seed=7).apply(view)
    assert first.payload == second.payload


def test_gaussian_different_seed_differs() -> None:
    view = make_view()
    first = GaussianNoise(sigma_m=200.0, seed=7).apply(view)
    second = GaussianNoise(sigma_m=200.0, seed=8).apply(view)
    assert first.payload != second.payload


def test_gaussian_rms_displacement_is_sigma_times_sqrt2() -> None:
    view = make_view(n_points=2000)
    dists = displacements_m(view, GaussianNoise(sigma_m=200.0, seed=42).apply(view).payload)
    rms = math.sqrt(sum(d * d for d in dists) / len(dists))
    assert abs(rms - 200.0 * math.sqrt(2)) < 0.1 * 200.0 * math.sqrt(2)


def test_larger_sigma_means_more_noise() -> None:
    view = make_view(n_points=500)
    small = displacements_m(view, GaussianNoise(sigma_m=50.0, seed=1).apply(view).payload)
    large = displacements_m(view, GaussianNoise(sigma_m=1000.0, seed=1).apply(view).payload)
    assert sum(small) < sum(large)


# --- shared contract ------------------------------------------------------------------


MECHANISMS = [
    ("spatial_rounding", SpatialRounding, {"cell_m": 500.0}),
    ("temporal_downsampling", TemporalDownsampling, {"interval_s": 30.0}),
    ("gaussian_noise", GaussianNoise, {"sigma_m": 200.0}),
]


@pytest.mark.parametrize(("name", "cls", "params"), MECHANISMS)
def test_metadata_guarantee_and_budget(name: str, cls: type, params: dict[str, float]) -> None:
    view = make_view()
    mech = cls(**params, seed=0)
    protected = mech.apply(view)
    times = [p[2] for p in view.as_gps()]
    released_times = [p[2] for p in protected.payload]
    if name == "temporal_downsampling":  # an ordered subsequence of the input timestamps
        assert released_times == [t for t in times if t in set(released_times)]
    else:
        assert released_times == times
    assert protected.traj_id == f"{name}/t1"
    assert protected.source_traj_id == "t1"
    assert protected.mechanism_id == name
    assert protected.guarantee == "none"
    assert protected.epsilon is None
    assert mech.spent_budget() is None
    assert not hasattr(mech, "epsilon") and not hasattr(mech, "unit_m")  # D-3.4: no ε column


@pytest.mark.parametrize(("name", "cls", "params"), MECHANISMS)
def test_registered_under_expected_name(name: str, cls: type, params: dict[str, float]) -> None:
    assert registry.get("mechanism", name) is cls


def test_invalid_params_rejected() -> None:
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="cell_m"):
            SpatialRounding(cell_m=bad)
        with pytest.raises(ValueError, match="interval_s"):
            TemporalDownsampling(interval_s=bad)
        with pytest.raises(ValueError, match="sigma_m"):
            GaussianNoise(sigma_m=bad)


# --- orchestrator end to end ----------------------------------------------------------


DOWNSAMPLING_REFS = (
    "temporal_downsampling:interval_s=15.0",
    "temporal_downsampling:interval_s=60.0",
)


def test_temporal_downsampling_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """A release with fewer points goes through re-matching, the cache and the metrics."""
    cfg = base_config(tmp_path, beijing_maps_dir)
    cfg["privacy_mechanisms"] = [
        {"id": "none"},
        {"id": "temporal_downsampling", "params": {"interval_s": [15, 60]}},
    ]
    cfg["metrics"]["utility"] = ["cell_js_divergence", "length_dist_error"]
    cfg["metrics"]["utility_grid"] = {"n_rows": 10, "n_cols": 10}
    cfg["reporting"] = {"export": ["csv"], "plots": ["mechanisms"]}
    config_path = write_config(tmp_path, cfg)
    values = run(config_path)

    arms = json.loads((tmp_path / "out" / "run.json").read_text())["arms"]
    fine, coarse = (arms[f"protected:{ref}"] for ref in DOWNSAMPLING_REFS)
    # 15 s keeps a third of the 5 s points: every fixture trajectory still re-matches
    assert fine["n_pool"] == 8 and fine["n_rematch_dropped"] == 0
    # 60 s leaves 4-11 points: some releases fail re-matching, none is lost silently
    assert coarse["n_rematch_dropped"] > 0
    assert coarse["n_pool"] + coarse["n_rematch_dropped"] == 8
    for arm in (fine, coarse):
        assert arm["spent_budget"] is None
        assert arm["n_probes"] == arms["raw"]["n_probes"]
    for ref in DOWNSAMPLING_REFS:
        prefix = f"reidentification:protected:{ref}"
        assert [v for v in values if v.result_id.startswith(prefix)], f"{ref} not attacked"

    # the cached release holds fewer points per trajectory, with the first and last
    # timestamps of the raw trajectory; a release is never empty
    raw_pool = _read_clean_table(next((tmp_path / "cache").glob("*/clean.parquet")))
    entries = sorted((tmp_path / "protected").iterdir())
    assert len(entries) == 2  # one cache entry per perturbing arm; the identity arm is free
    for entry in entries:
        meta = json.loads((entry / "meta.json").read_text())
        assert meta["mechanism"] in DOWNSAMPLING_REFS and meta["spent_budget"] is None
        release = _read_clean_table(entry / "clean.parquet")
        assert len(release) == 8 and set(release) <= set(raw_pool)
        for tid, traj in release.items():
            source = raw_pool[tid]
            assert 2 <= len(traj.points) < len(source.points)
            assert traj.points[0][2] == source.points[0][2]
            assert traj.points[-1][2] == source.points[-1][2]

    # utility runs over the whole release: thinning shortens the chord length
    utility = {(v.result_id, v.name): v.value for v in values if v.result_id.startswith("utility")}
    assert utility[("utility:protected:none", "length_dist_error")] == 0.0
    for ref in DOWNSAMPLING_REFS:
        assert utility[(f"utility:protected:{ref}", "length_dist_error")] > 0.0
    # no epsilon is recorded for these arms in the results table (D-3.4)
    with (tmp_path / "out" / "results.csv").open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if "temporal_downsampling" in r["target_ref"]]
    assert rows and all(r["epsilon"] == "" for r in rows)

    # a second run hits the protected cache and reproduces the values
    again = run(config_path)
    assert [(v.result_id, v.name, v.value) for v in again] == [
        (v.result_id, v.name, v.value) for v in values
    ]
