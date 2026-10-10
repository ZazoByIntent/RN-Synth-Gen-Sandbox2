"""Tests for the timed synthetic utility metrics and the gain helper (ULDP P2 + P12)."""

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import pytest

from test_orchestrator import FIXTURES, base_config, beijing_maps_dir, write_config
from trajguard.datamodel import (
    BEIJING_UTC_OFFSET_S,
    CleanTrajectory,
    LinkVisit,
    SyntheticTrajectory,
    TimedRoute,
)
from trajguard.evaluation.timed_utility import (
    PERIOD_METRICS,
    TIMED_UTILITY_METRICS,
    TripFeatures,
    circular_w1,
    gain,
    od_zones,
    reference_trips,
    synthetic_trips,
    timed_utility,
    utility_gain,
    weighted_w1,
)
from trajguard.evaluation.utility import unpaired_cell_js_divergence, unpaired_length_w1
from trajguard.experiments.orchestrator import load_config, run
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here
BBOX = (116.30, 39.98, 116.32, 39.995)
MIDNIGHT_UTC = 1_222_819_200.0  # 2008-10-01 00:00:00 UTC, 08:00 in Beijing
GRID = Grid(bbox=BBOX, n_rows=4, n_cols=4)


def _trip(
    user: str,
    duration: float,
    hour: float = 10.0,
    od: tuple[int, int] = (0, 8),
    cells: tuple[int, ...] = (0, 5),
) -> Any:
    return TripFeatures(
        user_id=user,
        duration_s=duration,
        length_m=duration * 5.0,
        departure_hour=hour,
        origin_zone=od[0],
        dest_zone=od[1],
        cells=cells,
    )


def _ones(n: int) -> np.ndarray:
    return np.ones(n)


def test_weighted_w1_matches_the_sorted_difference_for_equal_samples() -> None:
    a, b = np.array([1.0, 2.0, 7.0]), np.array([3.0, 3.0, 4.0])
    expected = float(np.abs(np.sort(a) - np.sort(b)).mean())
    assert weighted_w1(a, _ones(3), b, _ones(3)) == pytest.approx(expected)
    assert math.isnan(weighted_w1(a, _ones(3), np.array([]), np.array([])))


def test_circular_w1_wraps_around_midnight() -> None:
    """23:00 vs 01:00 is two hours apart on the clock, not 22."""
    x, y = np.array([23.0]), np.array([1.0])
    assert circular_w1(x, _ones(1), y, _ones(1)) == pytest.approx(2.0)
    assert weighted_w1(x, _ones(1), y, _ones(1)) == pytest.approx(22.0)
    assert circular_w1(np.array([6.0]), _ones(1), np.array([18.0]), _ones(1)) == pytest.approx(12.0)


def test_reference_is_weighted_per_user_not_per_trip() -> None:
    """One user with one short trip and one with nine long trips weigh 50/50."""
    reference = [_trip("a", 100.0)] + [_trip("b", 1000.0) for _ in range(9)]
    synthetic = [_trip("", 100.0), _trip("", 1000.0)]
    out = timed_utility(reference, synthetic, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0))
    assert out["duration_w1_s"][0] == pytest.approx(0.0)
    assert out["od3x3_jsd"][0] == pytest.approx(0.0)
    assert out["length_w1_m"][0] == pytest.approx(0.0)
    assert set(out) == set(TIMED_UTILITY_METRICS)


def test_reference_weighting_reaches_the_cell_metric() -> None:
    """A user's many trips in one cell weigh no more than another user's single trip."""
    reference = [_trip("a", 100.0, cells=(1,))] + [_trip("b", 100.0, cells=(2,)) for _ in range(9)]
    synthetic = [_trip("", 100.0, cells=(1,)), _trip("", 100.0, cells=(2,))]
    out = timed_utility(reference, synthetic, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0))
    assert out["cell_js_divergence"][0] == pytest.approx(0.0)


def test_cell_and_length_match_the_unpaired_rnldp_metrics_for_one_trip_per_user() -> None:
    """With one trip per user, the weighted points equal unpaired_cell_js / unpaired_length_w1."""
    rng = np.random.default_rng(5)
    reference = [
        _trip(f"u{i}", float(rng.integers(60, 900)), cells=tuple(rng.integers(0, 16, size=3)))
        for i in range(12)
    ]
    synthetic = [
        _trip("", float(rng.integers(60, 900)), cells=tuple(rng.integers(0, 16, size=4)))
        for _ in range(9)
    ]
    out = timed_utility(reference, synthetic, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0))

    def counts(trips: list[Any]) -> np.ndarray:
        return np.stack([np.bincount(t.cells, minlength=16) for t in trips]).astype(float)

    gen = np.random.default_rng(0)
    jsd = unpaired_cell_js_divergence(
        counts(reference), counts(synthetic), n_bootstrap=0, ci=0.95, rng=gen
    )[0]
    w1 = unpaired_length_w1(
        np.array([t.length_m for t in reference]),
        np.array([t.length_m for t in synthetic]),
        n_bootstrap=0,
        ci=0.95,
        rng=gen,
    )[0]
    assert out["cell_js_divergence"][0] == pytest.approx(jsd)
    assert out["length_w1_m"][0] == pytest.approx(w1)


def test_period_metrics_split_by_departure_hour_and_nan_when_empty() -> None:
    reference = [_trip("a", 100.0, hour=8.0), _trip("b", 500.0, hour=12.0)]
    synthetic = [_trip("", 300.0, hour=8.5), _trip("", 500.0, hour=13.0)]
    out = timed_utility(reference, synthetic, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0))
    assert out["duration_w1_s@am_peak"][0] == pytest.approx(200.0)
    assert out["duration_w1_s@midday"][0] == pytest.approx(0.0)
    for empty in ("night", "pm_peak", "evening"):
        assert math.isnan(out[f"duration_w1_s@{empty}"][0])
    assert len(PERIOD_METRICS) == 5


def test_bootstrap_is_seeded_and_brackets_the_point() -> None:
    rng = np.random.default_rng(1)
    reference = [_trip(f"u{i % 7}", float(rng.integers(60, 3600))) for i in range(40)]
    synthetic = [_trip("", float(rng.integers(60, 3600))) for _ in range(30)]
    first = timed_utility(
        reference, synthetic, n_bootstrap=200, ci=0.95, rng=np.random.default_rng(3)
    )
    again = timed_utility(
        reference, synthetic, n_bootstrap=200, ci=0.95, rng=np.random.default_rng(3)
    )
    assert first == again
    point, lo, hi = first["speed_w1_mps"]
    assert lo <= point <= hi or math.isclose(lo, point) or math.isclose(hi, point)
    empty = timed_utility([], synthetic, n_bootstrap=10, ci=0.95, rng=np.random.default_rng(3))
    assert all(math.isnan(v[0]) for v in empty.values())
    # Without bootstrap there is no interval (NaN), not a zero-width one at the point.
    bare = timed_utility(reference, synthetic, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(3))
    assert all(
        math.isfinite(v[0]) and math.isnan(v[1]) and math.isnan(v[2])
        for k, v in bare.items()
        if not k.startswith("duration_w1_s@")
    )


def test_gain_formula_and_evidence_flag() -> None:
    assert gain(10.0, 5.0, 0.0) == pytest.approx(0.5)
    assert gain(10.0, 10.0, 0.0) == pytest.approx(0.0)
    assert math.isnan(gain(3.0, 1.0, 3.0))

    reference = [_trip(f"u{i}", 100.0 * (i + 1)) for i in range(10)]
    oracle = [_trip("", t.duration_s) for t in reference]
    prior = [_trip("", 5000.0) for _ in range(10)]
    arm = [_trip("", 0.5 * (t.duration_s + 5000.0)) for t in reference]
    g = utility_gain(
        reference,
        prior,
        arm,
        oracle,
        metric="duration_w1_s",
        n_bootstrap=200,
        rng=np.random.default_rng(0),
    )
    assert g.oracle_beats_prior and g.counts_as_evidence
    assert g.gain == pytest.approx(0.5)
    assert g.ci_low <= g.gain <= g.ci_high

    # The oracle does not beat the prior: the gain is still reported, but flagged.
    flagged = utility_gain(
        reference,
        oracle,
        arm,
        prior,
        metric="duration_w1_s",
        n_bootstrap=20,
        rng=np.random.default_rng(0),
    )
    assert not flagged.counts_as_evidence and math.isfinite(flagged.gain)
    with pytest.raises(ValueError, match="unknown"):
        utility_gain(
            reference,
            prior,
            arm,
            oracle,
            metric="nope",
            n_bootstrap=1,
            rng=np.random.default_rng(0),
        )


def _fixture_network() -> RoadNetwork:
    d = FIXTURES / "maps" / "beijing_fixture"
    return RoadNetwork(
        graph=nx.MultiDiGraph(),
        nodes=gpd.read_parquet(d / "nodes.parquet"),
        edges=gpd.read_parquet(d / "edges.parquet"),
        region="beijing",
        crs="EPSG:32650",
    )


def _route(edges: Sequence[int], start: float) -> TimedRoute:
    visits = tuple(
        LinkVisit(edge_id=e, t_enter=start + 30.0 * i, t_exit=start + 30.0 * (i + 1))
        for i, e in enumerate(edges)
    )
    return TimedRoute(visits=visits, utc_offset_s=BEIJING_UTC_OFFSET_S)


def test_reference_trips_read_times_from_points_and_the_rest_from_edges() -> None:
    """A real trip and a synthetic route over the same edges get identical geometry.

    The clean trip's GPS length (3000 m here) is ignored: both sides use the network
    edge-length sum, so a perfect generator can reach zero length and speed distance.
    """
    net = _fixture_network()
    pts = ((39.981, 116.301, MIDNIGHT_UTC), (39.994, 116.319, MIDNIGHT_UTC + 60.0))
    clean = CleanTrajectory(
        traj_id="t",
        user_id="u",
        points=pts,
        bbox=BBOX,
        duration_s=60.0,
        length_m=3000.0,
        mean_speed=50.0,
        cleaning_flags=(),
        split="test",
    )
    (real,) = reference_trips([(clean, (0, 1))], net, od_zones(BBOX), GRID, BEIJING_UTC_OFFSET_S)
    syn = SyntheticTrajectory("s0", "g", "h", _route([0, 1], MIDNIGHT_UTC), "train", "m")
    (fake,) = synthetic_trips([syn], net, od_zones(BBOX), GRID)
    assert real.departure_hour == pytest.approx(8.0) and real.duration_s == pytest.approx(60.0)
    lengths = net.edges.set_index("edge_id")["length_m"]
    assert real.length_m == pytest.approx(float(lengths[0] + lengths[1]))
    assert (real.length_m, real.origin_zone, real.dest_zone, real.cells) == (
        fake.length_m,
        fake.origin_zone,
        fake.dest_zone,
        fake.cells,
    )
    assert len(real.cells) == 2
    out = timed_utility([real], [fake], n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0))
    for name in ("speed_w1_mps", "length_w1_m", "cell_js_divergence", "od3x3_jsd"):
        assert out[name][0] == pytest.approx(0.0)
    assert reference_trips([(clean, ())], net, od_zones(BBOX), GRID, BEIJING_UTC_OFFSET_S) == []


def test_synthetic_trips_take_length_and_zones_from_the_network() -> None:
    net = _fixture_network()
    syn = SyntheticTrajectory("s0", "g", "h", _route([0, 1], MIDNIGHT_UTC), "train", "m")
    (trip,) = synthetic_trips([syn], net, od_zones(BBOX), GRID)
    lengths = net.edges.set_index("edge_id")["length_m"]
    assert trip.length_m == pytest.approx(float(lengths[0] + lengths[1]))
    assert trip.duration_s == pytest.approx(60.0)
    assert trip.departure_hour == pytest.approx(8.0)
    untimed = SyntheticTrajectory("s1", "g", "h", (0, 1), "train", "m")
    with pytest.raises(TypeError, match="TimedRoute"):
        synthetic_trips([untimed], net, od_zones(BBOX), GRID)


@register("generator", "_test_timed_replay")
class _TimedReplay(SyntheticGenerator):
    """Test-only generator: replays the training edge sequences as timed routes."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._train: list[tuple[tuple[int, ...], float]] = []

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        self._train = [(v.as_segments(), v.as_gps()[0][2]) for v in train]

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        out = []
        for i in range(n):
            edges, start = self._train[i % len(self._train)]
            out.append(
                SyntheticTrajectory(
                    f"s{i}", "_test_timed_replay", "h", _route(edges, start), "train", "m"
                )
            )
        return out


def _rows(out_dir: Path) -> list[dict[str, str]]:
    return list(csv.DictReader((out_dir / "results.csv").open()))


def test_orchestrator_writes_timed_rows_only_for_timed_generators(
    tmp_path: Path, beijing_maps_dir: Path
) -> None:
    """Timed rows appear for the timed arm only; every other row is as without the flag."""
    off = base_config(tmp_path / "off", beijing_maps_dir)
    off["synthetic_generators"] = [
        {"id": "markov", "params": {"order": 1}},
        {"id": "_test_timed_replay"},
    ]
    off["split"]["fractions"] = {"train": 0.5, "test": 0.5}
    on = json.loads(json.dumps(off))
    on["experiment"]["output_dir"] = str(tmp_path / "on" / "out")
    on["metrics"]["timed_utility"] = True
    (tmp_path / "off").mkdir()
    (tmp_path / "on").mkdir()
    run(write_config(tmp_path / "off", off))
    run(write_config(tmp_path / "on", on))

    rows_off, rows_on = _rows(tmp_path / "off" / "out"), _rows(tmp_path / "on" / "out")
    timed = [r for r in rows_on if r["family"] == "utility" and r["scope"] == "synthetic"]
    assert not [r for r in rows_off if r["scope"] == "synthetic"]
    assert {r["arm_id"] for r in timed} == {"_test_timed_replay"}
    assert [r["metric"] for r in timed] == list(TIMED_UTILITY_METRICS)
    assert all(r["n_bootstrap"] == "200" for r in timed)

    def keyed(rows: list[dict[str, str]]) -> dict[tuple[str, str], tuple[str, ...]]:
        skip = {"created_at", "run_runtime_s", "attack_runtime_s", "peak_memory_mb"}
        return {
            (r["result_id"], r["metric"]): tuple(v for k, v in r.items() if k not in skip)
            for r in rows
        }

    others_on = keyed([r for r in rows_on if r not in timed])
    assert others_on == keyed(rows_off)

    arms = json.loads((tmp_path / "on" / "out" / "run.json").read_text())["arms"]
    assert arms["synthetic:markov:order=1"]["timed_utility"].startswith("skipped")
    assert arms["synthetic:_test_timed_replay"]["timed_utility"]["n_reference_users"] >= 1


def test_timed_utility_config_is_validated(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["metrics"]["timed_utility"] = True
    with pytest.raises(ValueError, match="synthetic_generators"):
        load_config(write_config(tmp_path, cfg))
    cfg["synthetic_generators"] = [{"id": "markov"}]
    cfg["map"]["region"] = "porto"
    with pytest.raises(ValueError, match="local-time offset"):
        load_config(write_config(tmp_path, cfg))
    cfg["metrics"]["timed_utility"] = "yes"
    with pytest.raises(ValueError, match="true or false"):
        load_config(write_config(tmp_path, cfg))
