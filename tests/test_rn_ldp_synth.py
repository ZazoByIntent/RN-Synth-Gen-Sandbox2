"""RNLDPSynthGenerator: fixture end-to-end slice, road-constraint invariant, determinism."""

import itertools
import math

import networkx as nx
import numpy as np
import pytest

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.maps.base import RoadNetwork
from trajguard.representation import TrajectoryView
from trajguard.synthesis.rn_ldp_synth import RNLDPSynthGenerator

MAP_ID = "osm_beijing_fixture"


def _view(edge_seq: tuple[int, ...], split: str = "train", tid: str = "t") -> TrajectoryView:
    matched = MatchedTrajectory(
        traj_id=tid,
        user_id="u",
        map_id=MAP_ID,
        edge_seq=tuple(edge_seq),
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    clean = CleanTrajectory(
        traj_id=tid,
        user_id="u",
        points=((39.99, 116.31, 0.0),),
        bbox=(116.30, 39.98, 116.32, 39.995),
        duration_s=1.0,
        length_m=1.0,
        mean_speed=1.0,
        cleaning_flags=(),
        split=split,  # type: ignore[arg-type]
    )
    return TrajectoryView(clean=clean, matched=matched)


def _edge_tables(
    network: RoadNetwork,
) -> tuple[dict[int, tuple[int, int]], dict[tuple[int, int], int]]:
    """edge_id -> (u, v) endpoints, and (u, v) -> shortest parallel edge_id."""
    ends: dict[int, tuple[int, int]] = {}
    lengths: dict[int, float] = {}
    for row in network.edges.itertuples(index=False):
        eid = int(row.edge_id)
        ends[eid] = (int(row.u), int(row.v))
        lengths[eid] = float(row.length_m)
    pair: dict[tuple[int, int], int] = {}
    for eid, (u, v) in ends.items():
        if (u, v) not in pair or lengths[eid] < lengths[pair[(u, v)]]:
            pair[(u, v)] = eid
    return ends, pair


@pytest.fixture(scope="module")
def train_views(fixture_network: RoadNetwork) -> list[TrajectoryView]:
    """~20 realistic on-road routes: shortest paths between SCC node pairs."""
    _, pair = _edge_tables(fixture_network)
    scc = max(nx.strongly_connected_components(fixture_network.graph), key=len)
    nodes = sorted(int(n) for n in scc)
    rng = np.random.default_rng(20260706)
    views: list[TrajectoryView] = []
    while len(views) < 20:
        a = nodes[int(rng.integers(len(nodes)))]
        b = nodes[int(rng.integers(len(nodes)))]
        if a == b:
            continue
        path = nx.shortest_path(fixture_network.graph, a, b, weight="length")
        edges = tuple(pair[(x, y)] for x, y in itertools.pairwise(path))
        if len(edges) < 3:
            continue
        views.append(_view(edges, tid=f"t{len(views)}"))
    return views


@pytest.fixture(scope="module")
def gen(fixture_network: RoadNetwork, train_views: list[TrajectoryView]) -> RNLDPSynthGenerator:
    g = RNLDPSynthGenerator(fixture_network, epsilon=2.0, n_rows=10, n_cols=10, l_max=12, seed=11)
    g.fit(train_views)
    return g


def test_zone_sequences_follow_zone_arcs(
    gen: RNLDPSynthGenerator, train_views: list[TrajectoryView]
) -> None:
    """Real edge sequences project onto walks of the public zone digraph."""
    arcs = set(gen.zone_arcs)
    for view in train_views:
        zseq = gen.zone_sequence(view.as_segments())
        for a, b in itertools.pairwise(zseq):
            assert (a, b) in arcs


def test_generate_end_to_end(gen: RNLDPSynthGenerator) -> None:
    out = gen.generate(12, seed=42)
    assert len(out) == 12
    for syn in out:
        assert syn.generator_id == "rn_ldp_synth"
        assert syn.trained_on_split == "train"
        assert syn.map_id == MAP_ID
        assert isinstance(syn.payload, tuple)
        assert len(syn.payload) >= 1
        assert all(isinstance(e, int) for e in syn.payload)


def test_generated_paths_are_connected_road_walks(
    gen: RNLDPSynthGenerator, fixture_network: RoadNetwork
) -> None:
    """The road-network constraint: consecutive edges chain head-to-tail in the real graph."""
    ends, _ = _edge_tables(fixture_network)
    for syn in gen.generate(15, seed=7):
        for e1, e2 in itertools.pairwise(syn.payload):
            assert ends[e1][1] == ends[e2][0]


def test_generate_deterministic_in_seed(gen: RNLDPSynthGenerator) -> None:
    a = [s.payload for s in gen.generate(8, seed=1)]
    b = [s.payload for s in gen.generate(8, seed=1)]
    c = [s.payload for s in gen.generate(8, seed=2)]
    assert a == b
    assert a != c


def test_fit_deterministic_in_constructor_seed(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    outs = []
    for _ in range(2):
        g = RNLDPSynthGenerator(fixture_network, epsilon=1.0, seed=5)
        g.fit(train_views)
        outs.append([s.payload for s in g.generate(6, seed=3)])
    assert outs[0] == outs[1]


def test_fit_rejects_non_train_splits(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    g = RNLDPSynthGenerator(fixture_network, seed=0)
    bad = [*train_views[:2], _view(train_views[0].as_segments(), split="test", tid="x")]
    with pytest.raises(ValueError, match="train split"):
        g.fit(bad)


def test_fit_rejects_empty_trajectory(fixture_network: RoadNetwork) -> None:
    g = RNLDPSynthGenerator(fixture_network, seed=0)
    with pytest.raises(ValueError, match="empty"):
        g.fit([_view(())])


def test_generate_before_fit_raises(fixture_network: RoadNetwork) -> None:
    with pytest.raises(RuntimeError, match="fit"):
        RNLDPSynthGenerator(fixture_network, seed=0).generate(1, seed=0)


def test_budget_accounting(fixture_network: RoadNetwork, gen: RNLDPSynthGenerator) -> None:
    """The four stage budgets sum exactly to epsilon; spent_budget reports it after fit."""
    g = RNLDPSynthGenerator(fixture_network, epsilon=1.5, budget_split=(1.0, 1.0, 1.0, 1.0))
    assert sum(g.stage_epsilons) == pytest.approx(1.5)
    assert g.stage_epsilons == pytest.approx((0.375, 0.375, 0.375, 0.375))
    assert g.spent_budget() is None
    # Unequal default split pins the stage ORDER (s, e, l, t) — a transposition fails here.
    assert gen.stage_epsilons == pytest.approx((0.3, 0.3, 0.4, 1.0))
    assert sum(gen.stage_epsilons) == pytest.approx(2.0)
    assert gen.spent_budget() == pytest.approx(2.0)


def test_high_epsilon_preserves_start_zones_and_lengths(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """Utility smoke test: with negligible noise the synthetic population tracks the train one."""
    g = RNLDPSynthGenerator(fixture_network, epsilon=80.0, n_rows=10, n_cols=10, l_max=12, seed=2)
    g.fit(train_views)
    train_starts = {g.zone_sequence(v.as_segments())[0] for v in train_views}
    train_mean = float(np.mean([len(g.zone_sequence(v.as_segments())) - 1 for v in train_views]))
    syn = g.generate(40, seed=9)
    starts = [g.zone_sequence(s.payload)[0] for s in syn]
    assert sum(s in train_starts for s in starts) / len(starts) >= 0.8
    syn_mean = float(np.mean([len(g.zone_sequence(s.payload)) - 1 for s in syn]))
    # Public inflation calibration keeps decoded trips near the sampled walk scale
    # (measured: overlap 1.0, length ratio 1.03 on this fixture at these seeds).
    assert train_mean * 0.6 <= syn_mean <= train_mean * 1.4 + 1


def test_sequence_log_prob_finite(
    gen: RNLDPSynthGenerator, train_views: list[TrajectoryView]
) -> None:
    for view in train_views[:5]:
        assert math.isfinite(gen.sequence_log_prob(view.as_segments()))
    for syn in gen.generate(5, seed=13):
        assert math.isfinite(gen.sequence_log_prob(syn.payload))


def test_sequence_log_prob_ranks_coherent_above_incoherent(
    gen: RNLDPSynthGenerator, fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """The MIA hook must penalize infeasible zone transitions, not just return a number."""
    ends, _ = _edge_tables(fixture_network)
    rng = np.random.default_rng(3)
    all_edges = sorted(ends)
    incoherent = tuple(int(all_edges[i]) for i in rng.choice(len(all_edges), size=6, replace=False))
    # A scattered edge pick crosses non-adjacent zones, so it hits the probability floor.
    assert any(
        (a, b) not in set(gen.zone_arcs)
        for a, b in itertools.pairwise(gen.zone_sequence(incoherent))
    )

    # Total log-prob is length-dependent, so compare per zone step: floor-hit
    # transitions (~log 1e-12 each) must dominate any coherent trajectory's average.
    def per_step(seq: tuple[int, ...]) -> float:
        return gen.sequence_log_prob(seq) / max(len(gen.zone_sequence(seq)), 1)

    train_scores = [per_step(tuple(v.as_segments())) for v in train_views[:5]]
    assert min(train_scores) > per_step(incoherent)


def test_sequence_log_prob_rejects_unknown_edge(gen: RNLDPSynthGenerator) -> None:
    with pytest.raises(ValueError, match="road network"):
        gen.sequence_log_prob((99_999_999,))


def test_fit_handles_single_zone_trajectory(fixture_network: RoadNetwork) -> None:
    """The l=0 dummy-transition branch: a one-edge trajectory encodes and synthesizes."""
    ends, _ = _edge_tables(fixture_network)
    single = _view((sorted(ends)[0],), tid="single")
    g = RNLDPSynthGenerator(fixture_network, epsilon=1.0, seed=4)
    g.fit([single])
    out = g.generate(3, seed=1)
    assert len(out) == 3
    assert all(len(s.payload) >= 1 for s in out)


def test_walk_truncates_gracefully_at_sink_zones_and_dead_ends(
    gen: RNLDPSynthGenerator, fixture_network: RoadNetwork
) -> None:
    """Sink zones stop walks; dead-end nodes make _route_into_zone return None."""
    sinks = set(range(gen.n_zones)) - {i for i, _ in gen.zone_arcs}
    rng = np.random.default_rng(5)
    uniform = np.full(gen.n_zones, 1.0 / gen.n_zones)
    if sinks:
        pi = np.zeros(gen.n_zones)
        pi[next(iter(sinks))] = 1.0
        walk = gen._sample_walk(rng, 5, pi, uniform, gen._row_probs)
        assert walk == [next(iter(sinks))]
    ends, _ = _edge_tables(fixture_network)
    tails = {u for u, _ in ends.values()}
    dead_ends = {v for _, v in ends.values()} - tails
    if dead_ends:
        assert gen._route_into_zone(next(iter(dead_ends)), 0, rng) is None
    assert sinks or dead_ends, "fixture unexpectedly has neither sinks nor dead ends"


def test_zone_rep_weights_are_valid_distributions(gen: RNLDPSynthGenerator) -> None:
    """Representative-edge weights must be finite probability vectors for every zone."""
    for reps, weights in gen._zone_reps.values():
        assert len(reps) == len(weights)
        assert np.all(np.isfinite(weights))
        assert float(weights.sum()) == pytest.approx(1.0)


def test_constructor_validation(fixture_network: RoadNetwork) -> None:
    with pytest.raises(ValueError, match="epsilon"):
        RNLDPSynthGenerator(fixture_network, epsilon=0.0)
    with pytest.raises(ValueError, match="budget_split"):
        RNLDPSynthGenerator(fixture_network, budget_split=(1.0, 1.0, 1.0))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="l_max"):
        RNLDPSynthGenerator(fixture_network, l_max=0)
    with pytest.raises(ValueError, match="grid"):
        RNLDPSynthGenerator(fixture_network, n_rows=0)
