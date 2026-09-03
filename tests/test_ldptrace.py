"""LDPTraceGenerator: cell chains, two-round OUE fit, Algorithm 1 walk, MIA hook, determinism."""

import itertools
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.datasets.ldptrace_dat import LDPTraceDatLoader
from trajguard.experiments import registry
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.ldptrace import LDPTraceGenerator, _quantile_length

MAP_ID = "osm_beijing_fixture"
_HUGE_EPS = 600.0  # per-report budget ≈ 30 after the L_k + 1 split: OUE noise vanishes
TINY_DAT = Path(__file__).parent / "fixtures" / "ldptrace_dat" / "tiny.dat"
TINY_GRID = Grid(bbox=(0.0, 0.0, 6.0, 6.0), n_rows=6, n_cols=6)
# Expected chains of tiny.dat on TINY_GRID (fixtures/ldptrace_dat/README.md).
TINY_CHAINS = [[0, 1, 8], [0, 7, 8, 9], [14], [28, 35], [5, 10, 15, 20]]


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


def _pair_edges(network: RoadNetwork) -> dict[tuple[int, int], int]:
    """(u, v) -> shortest parallel edge_id."""
    pair: dict[tuple[int, int], int] = {}
    lengths: dict[int, float] = {}
    for row in network.edges.itertuples(index=False):
        eid, u, v = int(row.edge_id), int(row.u), int(row.v)
        lengths[eid] = float(row.length_m)
        if (u, v) not in pair or lengths[eid] < lengths[pair[(u, v)]]:
            pair[(u, v)] = eid
    return pair


def _adjacent(a: int, b: int, n_cols: int) -> bool:
    ra, ca = divmod(a, n_cols)
    rb, cb = divmod(b, n_cols)
    return a != b and max(abs(ra - rb), abs(ca - cb)) == 1


@pytest.fixture(scope="module")
def train_views(fixture_network: RoadNetwork) -> list[TrajectoryView]:
    """~20 realistic on-road routes: shortest paths between SCC node pairs."""
    pair = _pair_edges(fixture_network)
    scc = max(nx.strongly_connected_components(fixture_network.graph), key=len)
    nodes = sorted(int(n) for n in scc)
    rng = np.random.default_rng(20260902)
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
def gen(fixture_network: RoadNetwork, train_views: list[TrajectoryView]) -> LDPTraceGenerator:
    g = LDPTraceGenerator(fixture_network, epsilon=2.0, n_rows=10, n_cols=10, seed=11)
    g.fit(train_views)
    return g


def test_registered_name() -> None:
    assert registry.get("generator", "ldptrace") is LDPTraceGenerator


def test_cell_sequences_are_8_connected_without_duplicates(
    gen: LDPTraceGenerator, train_views: list[TrajectoryView]
) -> None:
    for view in train_views:
        chain = gen.cell_sequence(view.as_segments())
        assert chain
        assert all(0 <= c < gen.n_cells for c in chain)
        for a, b in itertools.pairwise(chain):
            assert _adjacent(a, b, gen.n_cols)


def test_king_walk_interpolates_non_adjacent_cells(gen: LDPTraceGenerator) -> None:
    """Diagonal first, then straight: (0,0) -> (3,1) passes (1,1), (2,1); adjacent -> nothing.

    The walk lives in ``Grid.chain`` (shared with the cells representation); the
    generator's grid spans the projected node bbox of the network.
    """
    n = gen.n_cols
    chain = gen.grid.chain
    assert chain([0, 3 * n + 1]) == [0, 1 * n + 1, 2 * n + 1, 3 * n + 1]
    assert chain([0, 1 * n + 1]) == [0, 1 * n + 1]
    assert chain([2 * n + 2, 0]) == [2 * n + 2, 1 * n + 1, 0]
    # Same cell twice: no intermediate cells.
    assert chain([5, 5]) == [5]
    assert gen.bbox is None  # network mode
    assert gen.grid.bbox == (gen._x0, gen._y0, gen._x1, gen._y1)


def test_generate_end_to_end(gen: LDPTraceGenerator) -> None:
    out = gen.generate(12, seed=42)
    assert len(out) == 12
    for syn in out:
        assert syn.generator_id == "ldptrace"
        assert syn.trained_on_split == "train"
        assert syn.map_id == MAP_ID
        assert isinstance(syn.payload, tuple)
        assert len(syn.payload) >= 1
        assert all(isinstance(c, int) and 0 <= c < gen.n_cells for c in syn.payload)


def test_generated_paths_are_8_connected_and_bounded(gen: LDPTraceGenerator) -> None:
    for syn in gen.generate(30, seed=7):
        assert len(syn.payload) <= gen.n_cells
        for a, b in itertools.pairwise(syn.payload):
            assert _adjacent(a, b, gen.n_cols)


def test_generate_deterministic_in_seed(gen: LDPTraceGenerator) -> None:
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
        g = LDPTraceGenerator(fixture_network, epsilon=1.0, seed=5)
        g.fit(train_views)
        outs.append(([s.payload for s in g.generate(6, seed=3)], g.l_k))
    assert outs[0] == outs[1]


def test_fit_rejects_non_train_splits(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    g = LDPTraceGenerator(fixture_network, seed=0)
    bad = [*train_views[:2], _view(train_views[0].as_segments(), split="test", tid="x")]
    with pytest.raises(ValueError, match="train split"):
        g.fit(bad)


def test_fit_rejects_empty_trajectory(fixture_network: RoadNetwork) -> None:
    g = LDPTraceGenerator(fixture_network, seed=0)
    with pytest.raises(ValueError, match="empty"):
        g.fit([_view(())])


def test_generate_and_score_before_fit_raise(fixture_network: RoadNetwork) -> None:
    g = LDPTraceGenerator(fixture_network, seed=0)
    with pytest.raises(RuntimeError, match="fit"):
        g.generate(1, seed=0)
    with pytest.raises(RuntimeError, match="fit"):
        g.sequence_log_prob((1,))


def test_budget_accounting(fixture_network: RoadNetwork, gen: LDPTraceGenerator) -> None:
    """Length round + (L_k + 1) Markov reports sum exactly to epsilon per trajectory."""
    fresh = LDPTraceGenerator(fixture_network, epsilon=1.5, length_share=0.25)
    assert fresh.spent_budget() is None
    assert fresh.report_epsilon is None
    assert gen.spent_budget() == pytest.approx(2.0)
    assert gen.report_epsilon is not None
    assert 1 <= gen.l_k <= gen.n_cells
    assert gen.report_epsilon * (gen.l_k + 1) + gen.epsilon * gen.length_share == pytest.approx(
        gen.epsilon
    )


def test_quantile_length_reproduces_reference_rule() -> None:
    """Negatives stay in the total and the running sum; the first hit gives index + 1."""
    raw = np.array([4.0, -2.0, 5.0, 1.0, -1.0, 3.0])  # total 10, 0.9·total = 9
    # running: 4, 2, 7, 8, 7, 10 -> first >= 9 at index 5 -> L_k = 6
    assert _quantile_length(raw, 0.9) == 6
    assert _quantile_length(raw, 0.7) == 3  # running 7 >= 7 at index 2
    assert _quantile_length(raw, 0.1) == 1
    # Negative total: the threshold (-7.2) is never reached (running -10, -9, -8) -> d.
    assert _quantile_length(np.array([-10.0, 1.0, 1.0]), 0.9) == 3
    # Pure-noise histogram with a negative total collapses to the first index.
    assert _quantile_length(np.array([-1.0, -1.0, -1.0]), 0.9) == 1


def test_high_epsilon_preserves_start_cells_and_lengths(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """Utility smoke test: with negligible noise the synthetic population tracks the train one.

    ε is split over L_k + 1 ≈ 12–20 reports, so ε = 80 still leaves ~5 per report and
    visible OUE noise over 100–800 positions; ε = 600 (per report ≈ 30) silences the
    false bits while staying below the exp() overflow (~709).
    """
    g = LDPTraceGenerator(fixture_network, epsilon=_HUGE_EPS, n_rows=10, n_cols=10, seed=2)
    g.fit(train_views)
    chains = [g.cell_sequence(v.as_segments()) for v in train_views]
    train_starts = {c[0] for c in chains}
    train_mean = float(np.mean([len(c) for c in chains]))
    syn = g.generate(60, seed=9)
    starts = [s.payload[0] for s in syn]
    assert sum(s in train_starts for s in starts) / len(starts) >= 0.8
    # The estimated length histogram tracks the train lengths (measured ratio 0.90).
    lam_mean = float(np.sum((np.arange(g.n_cells) + 1) * g._lam))
    assert train_mean * 0.7 <= lam_mean <= train_mean * 1.3
    # Generated walks are shorter than their sampled length because the virtual end
    # state can stop them early (reference rule); measured ratio 0.47–0.61 over seeds 2–5.
    syn_mean = float(np.mean([len(s.payload) for s in syn]))
    assert train_mean * 0.4 <= syn_mean <= train_mean * 1.2 + 1


def test_sequence_log_prob_finite(
    gen: LDPTraceGenerator, train_views: list[TrajectoryView]
) -> None:
    for view in train_views[:5]:
        assert math.isfinite(gen.sequence_log_prob(view.as_segments()))
    for view in train_views[:3]:
        # Also finite on a route the model has no evidence for (floors, not -inf).
        assert math.isfinite(gen.sequence_log_prob(tuple(reversed(view.as_segments()))))


def test_sequence_log_prob_ranks_coherent_above_incoherent(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """The MIA hook must penalize unseen cell transitions, not just return a number."""
    g = LDPTraceGenerator(fixture_network, epsilon=_HUGE_EPS, n_rows=10, n_cols=10, seed=2)
    g.fit(train_views)
    rng = np.random.default_rng(3)
    all_edges = sorted(g._edge_cells)
    incoherent = tuple(int(all_edges[i]) for i in rng.choice(len(all_edges), size=6, replace=False))
    # A scattered edge pick is king-walk-interpolated into a long chain of transitions
    # the reports never contained, so most of its factors sit at the probability floor.
    assert len(g.cell_sequence(incoherent)) > 10

    # Total log-prob is length-dependent, so compare per cell. Even with sharp estimates
    # the OUE coin (p = 1/2) drops some once-seen transitions of a train route, so the
    # measured per-cell scores are: train min -14.96, incoherent -25.79 (floor -27.6).
    def per_step(seq: tuple[int, ...]) -> float:
        return g.sequence_log_prob(seq) / max(len(g.cell_sequence(seq)), 1)

    train_scores = [per_step(tuple(v.as_segments())) for v in train_views[:5]]
    assert min(train_scores) > per_step(incoherent)


def test_sequence_log_prob_rejects_unknown_edge(gen: LDPTraceGenerator) -> None:
    with pytest.raises(ValueError, match="road network"):
        gen.sequence_log_prob((99_999_999,))


def test_tiny_epsilon_small_n_does_not_crash(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """Near-uniform OUE estimates (ε = 0.05, n ≈ 20) still yield a usable model."""
    g = LDPTraceGenerator(fixture_network, epsilon=0.05, n_rows=6, n_cols=6, seed=1)
    g.fit(train_views)
    assert 1 <= g.l_k <= g.n_cells
    out = g.generate(10, seed=0)
    assert len(out) == 10
    assert all(1 <= len(s.payload) <= g.n_cells for s in out)
    assert math.isfinite(g.sequence_log_prob(train_views[0].as_segments()))


def test_constructor_validation(fixture_network: RoadNetwork) -> None:
    with pytest.raises(ValueError, match="epsilon"):
        LDPTraceGenerator(fixture_network, epsilon=0.0)
    with pytest.raises(ValueError, match="grid"):
        LDPTraceGenerator(fixture_network, n_rows=1)
    with pytest.raises(ValueError, match="quantile"):
        LDPTraceGenerator(fixture_network, quantile=0.0)
    with pytest.raises(ValueError, match="quantile"):
        LDPTraceGenerator(fixture_network, quantile=1.5)
    with pytest.raises(ValueError, match="length_share"):
        LDPTraceGenerator(fixture_network, length_share=1.0)
    with pytest.raises(ValueError, match="alpha"):
        LDPTraceGenerator(fixture_network, beta=-0.1)
    # Exactly one of network / bbox.
    with pytest.raises(ValueError, match="exactly one"):
        LDPTraceGenerator()
    with pytest.raises(ValueError, match="exactly one"):
        LDPTraceGenerator(fixture_network, bbox=(0.0, 0.0, 6.0, 6.0))
    with pytest.raises(ValueError, match="bbox"):
        LDPTraceGenerator(bbox=(6.0, 0.0, 0.0, 6.0))
    with pytest.raises(ValueError, match="bbox"):
        LDPTraceGenerator(bbox=(0.0, 0.0, 6.0))  # type: ignore[arg-type]


# -- bbox mode (cells representation) -----------------------------------------------------


def _cell_views() -> list[TrajectoryView]:
    """tiny.dat in the cells representation: one cell per point, wrapped as bare sequences."""
    views: list[TrajectoryView] = []
    for raw in LDPTraceDatLoader(TINY_DAT).iter_trajectories():
        cells = tuple(TINY_GRID.cell_of(lat, lon) for lat, lon, _ in raw.points)
        views.append(TrajectoryView(sequence=cells))
    return views


def test_bbox_mode_chains_match_fixture_readme() -> None:
    g = LDPTraceGenerator(bbox=TINY_GRID.bbox, n_rows=6, n_cols=6)
    assert g.grid == TINY_GRID
    assert g.bbox == (0.0, 0.0, 6.0, 6.0)
    assert g._params["bbox"] == [0.0, 0.0, 6.0, 6.0]
    assert [g.cell_sequence(v.as_sequence()) for v in _cell_views()] == TINY_CHAINS
    with pytest.raises(ValueError, match="outside"):
        g.cell_sequence((0, 36))


def test_bbox_mode_fit_generate_score() -> None:
    """fit + generate + sequence_log_prob over the five tiny.dat chains, ε = 600."""
    views = _cell_views()
    g = LDPTraceGenerator(bbox=(0.0, 0.0, 6.0, 6.0), epsilon=_HUGE_EPS, n_rows=6, n_cols=6, seed=3)
    assert g.spent_budget() is None
    g.fit(views)
    assert g.spent_budget() == pytest.approx(_HUGE_EPS)
    assert 1 <= g.l_k <= g.n_cells
    syn = g.generate(15, seed=4)
    assert len(syn) == 15
    for s in syn:
        assert s.generator_id == "ldptrace"
        assert s.map_id == ""  # no map in bbox mode
        assert 1 <= len(s.payload) <= g.n_cells
        for a, b in itertools.pairwise(s.payload):
            assert _adjacent(a, b, g.n_cols)
    for v in views:
        assert math.isfinite(g.sequence_log_prob(v.as_sequence()))
    # Seen start cells dominate the synthetic starts once the OUE noise is negligible.
    train_starts = {c[0] for c in TINY_CHAINS}
    assert sum(s.payload[0] in train_starts for s in syn) / len(syn) >= 0.8
    # Scoring a chain with a transition the reports never contained scores lower per cell.
    seen = g.sequence_log_prob((5, 10, 15, 20)) / 4
    unseen = g.sequence_log_prob((35, 34, 33, 32)) / 4
    assert seen > unseen


def test_bbox_mode_deterministic_in_seeds() -> None:
    views = _cell_views()
    outs = []
    for _ in range(2):
        g = LDPTraceGenerator(bbox=(0.0, 0.0, 6.0, 6.0), epsilon=1.0, n_rows=6, n_cols=6, seed=7)
        g.fit(views)
        outs.append(
            (
                [s.payload for s in g.generate(6, seed=1)],
                g.l_k,
                [g.sequence_log_prob(v.as_sequence()) for v in views],
            )
        )
    assert outs[0] == outs[1]


def test_network_and_bbox_modes_agree_on_the_same_route(
    gen: LDPTraceGenerator, train_views: list[TrajectoryView]
) -> None:
    """Endpoint cells of a route, fed to a bbox generator on the same grid, chain identically."""
    twin = LDPTraceGenerator(bbox=gen.grid.bbox, n_rows=gen.n_rows, n_cols=gen.n_cols)
    for view in train_views:
        edges = view.as_segments()
        endpoint_cells = [c for eid in edges for c in gen._edge_cells[int(eid)]]
        assert twin.cell_sequence(endpoint_cells) == gen.cell_sequence(edges)


def test_network_mode_fits_on_bare_sequence_views(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """Shadow models of the membership attack train on TrajectoryView(sequence=...) views."""
    bare = [TrajectoryView(sequence=v.as_segments()) for v in train_views]
    g_bare = LDPTraceGenerator(fixture_network, epsilon=2.0, n_rows=10, n_cols=10, seed=11)
    g_bare.fit(bare)
    g_full = LDPTraceGenerator(fixture_network, epsilon=2.0, n_rows=10, n_cols=10, seed=11)
    g_full.fit(train_views)
    assert [s.payload for s in g_bare.generate(5, seed=1)] == [
        s.payload for s in g_full.generate(5, seed=1)
    ]
    assert g_bare.generate(1, seed=1)[0].map_id == ""  # bare views carry no map
    assert g_full.generate(1, seed=1)[0].map_id == MAP_ID
