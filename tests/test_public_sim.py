"""Public road-network simulator (ULDP P3) and its prior and oracle arms, on the fixture map."""

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from test_orchestrator import base_config, beijing_maps_dir, write_config
from trajguard.datamodel import (
    BEIJING_UTC_OFFSET_S,
    CleanTrajectory,
    MatchedTrajectory,
    TimedRoute,
)
from trajguard.evaluation.timed_utility import (
    TIMED_UTILITY_METRICS,
    _Geometry,
    od_zones,
    reference_trips,
    synthetic_trips,
    timed_utility,
)
from trajguard.experiments import registry
from trajguard.experiments.orchestrator import run
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.public_sim import (
    CLASS_SPEED_KMH,
    PERIODS,
    REGIME_CATALOGUE,
    PublicSimulator,
    Regime,
    SimParams,
    network_hash,
    parse_maxspeed_kmh,
    primary_highway_class,
    prior_params,
)
from trajguard.synthesis.uldp_arms import UldpOracleGenerator, UldpPriorGenerator

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here

BBOX = (116.30, 39.98, 116.32, 39.995)
GRID = Grid(bbox=BBOX, n_rows=4, n_cols=4)
LOCAL_MIDNIGHT_UTC = 1_222_790_400.0  # 2008-10-01 00:00 in Beijing (UTC+8)


def _connected(net: RoadNetwork, edge_seq: Sequence[int]) -> bool:
    edges = net.edges.set_index("edge_id")
    return all(
        edges.at[a, "v"] == edges.at[b, "u"] for a, b in zip(edge_seq, edge_seq[1:], strict=False)
    )


def _view(
    user: str, i: int, edge_seq: tuple[int, ...], depart_local_h: float, duration: float
) -> TrajectoryView:
    t0 = LOCAL_MIDNIGHT_UTC + 3600.0 * depart_local_h
    pts = ((39.981, 116.301, t0), (39.994, 116.319, t0 + duration))
    clean = CleanTrajectory(
        traj_id=f"{user}-{i}",
        user_id=user,
        points=pts,
        bbox=BBOX,
        duration_s=duration,
        length_m=1000.0,
        mean_speed=1000.0 / duration,
        cleaning_flags=(),
        split="train",
    )
    matched = MatchedTrajectory(
        traj_id=f"{user}-{i}",
        user_id=user,
        map_id="osm_beijing_fixture",
        edge_seq=edge_seq,
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    return TrajectoryView(clean=clean, matched=matched)


def _training_views(sim: PublicSimulator, b_walks: bool = True) -> list[TrajectoryView]:
    """User a: three trips at 08:00 at 0.9 x free flow (motorised); b: one at 18:00.

    User b walks at half the walking speed, or with ``b_walks=False`` drives at 0.9 x
    free flow too.
    """
    walk, _, motorised = REGIME_CATALOGUE
    b_regime, b_factor = (walk, 0.5) if b_walks else (motorised, 0.9)
    routes = sim.simulate(prior_params(), 4, np.random.default_rng(5))
    views = []
    for i, r in enumerate(routes):
        user, hour, regime, factor = (
            ("a", 8.0, motorised, 0.9) if i < 3 else ("b", 18.0, b_regime, b_factor)
        )
        duration = sim.route_time_s(r.edge_seq, regime) / factor
        views.append(_view(user, i, r.edge_seq, hour, duration))
    return views


def test_free_flow_speed_comes_from_osm_or_the_cited_class_table(
    fixture_network: RoadNetwork,
) -> None:
    assert parse_maxspeed_kmh("60") == 60.0
    assert parse_maxspeed_kmh("['40', '60']") == 40.0
    assert parse_maxspeed_kmh("30 mph") == pytest.approx(48.28032)
    assert parse_maxspeed_kmh("None") is None and parse_maxspeed_kmh(None) is None
    assert primary_highway_class("['unclassified', 'residential']") == "unclassified"
    g = PublicSimulator(fixture_network).graph
    i = g.highway.index("residential")
    assert g.free_flow_mps[i] == pytest.approx(CLASS_SPEED_KMH["residential"] / 3.6)


def test_prepared_graph_is_shared_through_the_content_hash_cache(
    fixture_network: RoadNetwork,
) -> None:
    a, b = PublicSimulator(fixture_network), PublicSimulator(fixture_network)
    assert a.graph is b.graph
    assert network_hash(fixture_network) in a.graph.key
    assert PublicSimulator(fixture_network, zones_per_side=2).graph is not a.graph
    g = a.graph
    assert g.usable.sum() > 0 and g.mass[~g.in_scc].sum() == 0
    assert g.zone_mass.sum() == pytest.approx(g.length[g.usable].sum())


def test_simulator_zones_are_the_metric_zones_on_the_public_map_frame(
    fixture_network: RoadNetwork,
) -> None:
    sim = PublicSimulator(fixture_network)
    g = sim.graph
    assert fixture_network.bbox == BBOX and g.bbox == BBOX  # meta.json frame, not node extent
    metric_zones = od_zones(BBOX)  # what od3x3_jsd cuts on (the config's map.bbox)
    assert g.zones == metric_zones
    nodes = fixture_network.nodes.set_index("node_id")
    for node_id, i in g.node_index.items():
        lat, lon = float(nodes.at[node_id, "lat"]), float(nodes.at[node_id, "lon"])
        assert g.zone[i] == metric_zones.cell_of(lat, lon)
    geometry = _Geometry(fixture_network)
    for route in sim.simulate(prior_params(), 10, np.random.default_rng(3)):
        _, zo, zd, _ = geometry.route(route.edge_seq, metric_zones, GRID)
        assert sim.od_zones(route.edge_seq) == (zo, zd)
    framed = replace(fixture_network, bbox=None)
    with pytest.raises(ValueError, match="map frame"):
        PublicSimulator(framed)


def test_prior_arm_samples_valid_timed_routes_deterministically(
    fixture_network: RoadNetwork,
) -> None:
    gen = UldpPriorGenerator(fixture_network, seed=0)
    gen.fit([])
    first = gen.generate(40, seed=3)
    assert [t.payload for t in first] == [t.payload for t in gen.generate(40, seed=3)]
    assert [t.payload for t in first] != [t.payload for t in gen.generate(40, seed=4)]
    other = UldpPriorGenerator(fixture_network)
    other.fit(_training_views(gen.sim))  # the prior never reads the data
    assert [t.payload for t in other.generate(40, seed=3)] == [t.payload for t in first]
    hours = []
    for t in first:
        route = t.payload
        assert isinstance(route, TimedRoute) and route.utc_offset_s == BEIJING_UTC_OFFSET_S
        assert _connected(fixture_network, route.edge_seq)
        assert route.to_local(route.departure_t).date().isoformat() == "2008-01-01"
        assert route.arrival_t > route.departure_t
        hours.append(route.to_local(route.departure_t).hour)
        assert math.isfinite(gen.sequence_log_prob(route.edge_seq))
    assert len(set(hours)) > 5  # uniform public departure prior
    assert t.generator_id == "uldp_prior" and t.map_id == "osm_beijing_fixture"


@pytest.mark.parametrize(
    "params",
    [
        SimParams(),
        SimParams(regimes=(Regime("decay", distance_decay_per_s=0.01),)),
        SimParams(od_shares=tuple(float(i % 4) for i in range(81))),
    ],
    ids=["gravity", "gravity_decay", "od_table"],
)
def test_origin_destination_probabilities_sum_to_one(
    fixture_network: RoadNetwork, params: SimParams
) -> None:
    sim = PublicSimulator(fixture_network)
    g, router = sim.graph, sim.router(params.regimes[0])
    od = sim._od_table(params)
    nodes = np.flatnonzero(g.mass > 0)
    total = sum(
        math.exp(sim._od_log_prob(router, od, int(o), int(d)))
        for o in nodes
        for d in nodes
        if o != d
    )
    assert total == pytest.approx(1.0, rel=1e-6)  # floored zero-share pairs add ~1e-8


def test_likelihood_is_exact_and_floor_bounded(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    g = sim.graph
    cold = SimParams(regimes=(Regime("cold", detour_scale_s=1e-3),))
    for route in sim.simulate(cold, 5, np.random.default_rng(1)):
        seq = route.edge_seq
        o, d = g.tail[g.edge_index[seq[0]]], g.head[g.edge_index[seq[-1]]]
        # A near-deterministic walk is the shortest path: only the OD term is left.
        od_term = sim._od_log_prob(sim.router(cold.regimes[0]), None, int(o), int(d))
        assert sim.log_prob(cold, seq) == pytest.approx(od_term, abs=1e-6)
    seq = sim.simulate(prior_params(), 1, np.random.default_rng(2))[0].edge_seq
    one = sim.log_prob(SimParams(), seq)
    twin = SimParams(regimes=(Regime("a"), Regime("a")), regime_weights=(0.3, 0.7))
    assert sim.log_prob(twin, seq) == pytest.approx(one)
    gap = sim.log_prob(SimParams(), (*seq, *seq[::-1]))
    assert math.isfinite(gap) and gap < one
    assert math.isfinite(sim.log_prob(prior_params(), seq))  # the three-regime mixture
    assert math.isfinite(sim.log_prob(prior_params(), (10**9,)))


def test_oracle_estimates_user_weighted_parameters(fixture_network: RoadNetwork) -> None:
    gen = UldpOracleGenerator(fixture_network)
    assert gen.needs_user_roster and gen.non_private and gen.epsilon is None
    views = _training_views(gen.sim)
    gen.set_user_roster(["a", "b", "c"])  # c has no trip and stays out of the means
    gen.fit(views)
    p = gen.params
    names = [name for name, _, _ in PERIODS]
    am, pm = names.index("am_peak"), names.index("pm_peak")
    assert p.departure_shares[am] == pytest.approx(0.5)
    assert p.departure_shares[pm] == pytest.approx(0.5)
    assert p.period_speed_factors[am] == pytest.approx(0.9)  # against the motorised time
    assert p.period_speed_factors[pm] == pytest.approx(0.5)  # against the walking time
    assert p.period_speed_factors[names.index("night")] == 1.0  # no trip: prior kept
    assert p.trip_jitter_sigma == pytest.approx(0.0, abs=1e-9)
    assert p.regimes == prior_params().regimes == REGIME_CATALOGUE  # the shared catalogue
    assert p.regime_weights == pytest.approx((0.5, 0.0, 0.5))  # b walks, a drives
    assert p.od_shares is not None and sum(p.od_shares) == pytest.approx(1.0)
    zo, zd = gen.sim.od_zones(views[3].as_segments())
    assert p.od_shares[zo * 9 + zd] >= 0.5  # user b's single trip weighs as much as a's three
    bare = UldpOracleGenerator(fixture_network)
    shadow_style = [TrajectoryView(sequence=v.as_segments(), user_id=v.user_id) for v in views]
    with pytest.raises(RuntimeError, match="roster"):
        bare.fit(shadow_style)  # an opted-in generator never fits without a roster (P5)
    bare.set_user_roster(["a", "b"])
    bare.fit(shadow_style)  # shadow-style views: user ids, no GPS, so no time estimates
    assert bare.params.departure_shares == prior_params().departure_shares
    assert bare.params.od_shares is not None
    assert math.isfinite(gen.sequence_log_prob(views[0].as_segments()))


def test_prior_and_oracle_arms_run_through_the_timed_utility_metrics(
    fixture_network: RoadNetwork,
) -> None:
    prior, oracle = UldpPriorGenerator(fixture_network), UldpOracleGenerator(fixture_network)
    views = _training_views(prior.sim, b_walks=False)  # all driving: the prior's walk/bike miss
    prior.fit(views)
    oracle.set_user_roster(["a", "b"])
    oracle.fit(views)
    zones = od_zones(BBOX)
    reference = reference_trips(
        [(v.clean, v.as_segments()) for v in views if v.clean is not None],
        fixture_network,
        zones,
        GRID,
        BEIJING_UTC_OFFSET_S,
    )
    out = {}
    for arm in (prior, oracle):
        syn = synthetic_trips(arm.generate(60, seed=0), fixture_network, zones, GRID)
        out[arm.generator_id] = timed_utility(
            reference, syn, n_bootstrap=0, ci=0.95, rng=np.random.default_rng(0)
        )
        assert list(out[arm.generator_id]) == list(TIMED_UTILITY_METRICS)
    for metric in ("duration_w1_s", "speed_w1_mps", "departure_hour_circ_w1_h"):
        assert out["uldp_oracle"][metric][0] < out["uldp_prior"][metric][0]


def test_arms_are_registered() -> None:
    from trajguard.experiments import builtins  # noqa: F401  (registration side effect)

    assert registry.get("generator", "uldp_prior") is UldpPriorGenerator
    assert registry.get("generator", "uldp_oracle") is UldpOracleGenerator
    assert not UldpPriorGenerator.needs_user_roster


def test_orchestrator_runs_both_arms_with_timed_utility(
    tmp_path: Path, beijing_maps_dir: Path
) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    cfg["synthetic_generators"] = [{"id": "uldp_prior"}, {"id": "uldp_oracle"}]
    cfg["split"]["fractions"] = {"train": 0.5, "test": 0.5}
    cfg["metrics"]["timed_utility"] = True
    run(write_config(tmp_path, cfg))
    rows = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    timed = [r for r in rows if r["family"] == "utility" and r["scope"] == "synthetic"]
    for arm in ("uldp_prior", "uldp_oracle"):
        assert [r["metric"] for r in timed if r["arm_id"] == arm] == list(TIMED_UTILITY_METRICS)
    arms = json.loads((tmp_path / "out" / "run.json").read_text())["arms"]
    assert arms["synthetic:uldp_oracle"]["timed_utility"]["n_synthetic"] > 0
