"""LDPTrace paper metrics: hand-computed reference values, quirks, determinism, fixture sanity."""

import itertools
import math

import networkx as nx
import numpy as np
import pytest

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.evaluation import ldptrace_metrics as lm
from trajguard.evaluation.ldptrace_metrics import (
    METRIC_NAMES,
    coverage_kendall_tau,
    density_error,
    diameter_error,
    evaluate,
    hotspot_query_error,
    length_error,
    pattern_f1,
    pattern_support_error,
    point_query_avre,
    sample_points,
    trip_error,
)
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.ldptrace import LDPTraceGenerator

GRID4 = Grid(bbox=(0.0, 0.0, 4.0, 4.0), n_rows=4, n_cols=4)
GRID5 = Grid(bbox=(0.0, 0.0, 5.0, 5.0), n_rows=5, n_cols=5)
LN2 = math.log(2.0)
_DIRECTIONS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _line(length: float) -> np.ndarray:
    """A two-point trajectory of the given travel length along x."""
    return np.array([[0.0, 0.0], [length, 0.0]])


def _random_walks(
    n_rows: int, n_cols: int, lengths: list[int], rng: np.random.Generator
) -> list[list[int]]:
    """8-connected random walks of the given lengths — an intentionally bad synthesizer."""
    out: list[list[int]] = []
    for length in lengths:
        r, c = int(rng.integers(n_rows)), int(rng.integers(n_cols))
        chain = [r * n_cols + c]
        while len(chain) < length:
            dr, dc = _DIRECTIONS[int(rng.integers(len(_DIRECTIONS)))]
            rr, cc = r + dr, c + dc
            if 0 <= rr < n_rows and 0 <= cc < n_cols:
                r, c = rr, cc
                chain.append(r * n_cols + c)
        out.append(chain)
    return out


# --- shared divergence and hand-computed values -----------------------------------------


def test_density_error_reference_jsd_natural_log() -> None:
    """Real all in cell 0, synthetic half/half: ½·ln(4/3) + ½·(½·ln(2/3) + ½·ln 2) = 0.2157615.

    The base-2 value would be 0.311278, so this pins the natural logarithm; the 1e-8
    smoothing moves the value by ~1e-9.
    """
    value = density_error([[0], [0]], [[0], [1]], GRID4)
    assert value == pytest.approx(0.2157615, abs=1e-6)
    assert density_error([[0], [1]], [[0], [1]], GRID4) == pytest.approx(0.0, abs=1e-7)


def test_density_counts_every_visit_including_revisits() -> None:
    # Chain 0 -> 1 -> 0 visits cell 0 twice: same histogram as two one-cell chains + one.
    assert density_error([[0, 1, 0]], [[0], [0], [1]], GRID4) == pytest.approx(0.0, abs=1e-7)


def test_trip_error_pairs_start_and_end() -> None:
    """Real pairs {(0,1), (0,1)}, synthetic {(0,1), (1,0)}: the density hand value again."""
    assert trip_error([[0, 1], [0, 1]], [[0, 1], [1, 0]], GRID4) == pytest.approx(
        0.2157615, abs=1e-6
    )
    # Only the end points matter, not the interior of the chain.
    assert trip_error([[0, 1, 2, 3]], [[0, 5, 6, 3]], GRID4) == pytest.approx(0.0, abs=1e-7)


def test_hotspot_query_error_hand_value() -> None:
    """Real ranking 0>1>2>3>4, synthetic swaps the first two: 1 − DCG/IDCG = 0.1106876.

    DCG = ½·1 + 1·(1/log2 3) + ⅓·½ + ¼·(1/log2 5) + ⅕·(1/log2 6) = 1.482641,
    IDCG = 1 + ½·(1/log2 3) + ⅓·½ + ¼·(1/log2 5) + ⅕·(1/log2 6) = 1.667176.
    """
    grid = Grid(bbox=(0.0, 0.0, 3.0, 2.0), n_rows=2, n_cols=3)
    real = [[0]] * 5 + [[1]] * 4 + [[2]] * 3 + [[3]] * 2 + [[4]]
    syn = [[0]] * 4 + [[1]] * 5 + [[2]] * 3 + [[3]] * 2 + [[4]]
    assert hotspot_query_error(real, syn, grid) == pytest.approx(0.1106876, abs=1e-6)
    assert hotspot_query_error(real, real, grid) == pytest.approx(0.0, abs=1e-12)
    # No synthetic hotspot among the real ones: maximal error 1.
    assert hotspot_query_error(real, [[5]] * 3, grid, k=1) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="k must be"):
        hotspot_query_error(real, syn, grid, k=7)


def test_kendall_tau_reference_pair_rules() -> None:
    grid = Grid(bbox=(0.0, 0.0, 3.0, 1.0), n_rows=1, n_cols=3)
    # Real counts (2, 1, 0), synthetic (1, 1, 0): pair (0,1) reversed by the synthetic
    # tie, (0,2) and (1,2) concordant -> (2 − 1) / 3.
    assert coverage_kendall_tau([[0], [0, 1]], [[0, 1]], grid) == pytest.approx(1 / 3)
    # Real counts (2, 1, 1): the tie (1,2) is skipped but stays in the denominator;
    # synthetic (1, 2, 0) reverses (0,1) and keeps (0,2) -> (1 − 1) / 3.
    assert coverage_kendall_tau([[0], [0, 1], [2]], [[0], [1], [1]], grid) == pytest.approx(0.0)
    # A chain revisiting a cell counts once per cell (pass-through, not visits).
    np.testing.assert_array_equal(lm._pass_counts([[0, 1, 0]], 3), [1.0, 1.0, 0.0])
    # Identical populations: 1 only without real ties; with ties the skipped pairs
    # still count in the denominator (reference definition).
    assert coverage_kendall_tau([[0], [0, 1], [0, 1, 2]], [[0], [0, 1], [0, 1, 2]], grid) == 1.0
    tied = [[0], [0, 1], [2]]  # counts (2, 1, 1): two ordered pairs out of three
    assert coverage_kendall_tau(tied, tied, grid) == pytest.approx(2 / 3)


# --- length / diameter binning (reference quirks) ---------------------------------------


def test_bucket_counts_reproduce_reference_quirks() -> None:
    """Width (20 − 5)/20 = 0.75, edges from 0: 20 and 30 are dropped, 7.5 lands in two buckets."""
    real, syn = lm._bucket_counts(np.array([5.0, 10.0, 20.0]), np.array([7.5, 5.0, 30.0]), 20)
    assert np.flatnonzero(real).tolist() == [6, 13]  # 5 in [4.5, 5.25], 10 in [9.75, 10.5]
    assert real.sum() == 2.0  # 20 > max − min = 15: dropped
    assert np.flatnonzero(syn).tolist() == [6, 9, 10]  # 7.5 = edge between buckets 9 and 10
    assert syn.sum() == 3.0  # 30 dropped, 7.5 counted twice


def test_length_error_values() -> None:
    real = [_line(5.0), _line(10.0), _line(20.0)]
    # Disjoint bucket supports: the divergence saturates at ln 2.
    assert length_error(real, [_line(7.5), _line(30.0)]) == pytest.approx(LN2, abs=1e-6)
    # Hand value with the double-counted edge: p = (½, ½) on buckets {6, 13},
    # q = (⅓, ⅓, ⅓) on {6, 9, 10} -> ½·[½ln(6/5) + ½ln 2] + ½·[⅓ln(4/5) + ⅔ln 2].
    expected = 0.5 * (0.5 * math.log(1.2) + 0.5 * LN2) + 0.5 * (math.log(0.8) / 3 + 2 * LN2 / 3)
    assert length_error(real, [_line(7.5), _line(5.0), _line(30.0)]) == pytest.approx(
        expected, abs=1e-6
    )
    assert length_error(real, real) == pytest.approx(0.0, abs=1e-7)
    # Every synthetic value dropped: no mass, nan instead of a numpy warning.
    assert math.isnan(length_error(real, [_line(30.0)]))


def test_diameter_and_travel_length_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    tri = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 4.0]])
    assert lm._travel_length(tri) == pytest.approx(8.0)  # 3 + 5
    assert lm._diameter(tri) == pytest.approx(5.0)  # farthest pair (3,0)–(0,4)
    assert lm._diameter(tri[:1]) == 0.0
    monkeypatch.setattr(lm, "_PAIR_BLOCK", 2)  # force the row-blocked path
    assert lm._diameter(tri) == pytest.approx(5.0)
    real = [tri, tri * 2.0, tri * 4.0]
    assert diameter_error(real, real) == pytest.approx(0.0, abs=1e-7)
    assert diameter_error(real, [tri * 2.5]) > 0.0


# --- patterns ----------------------------------------------------------------------------


def test_pattern_metrics_hand_values() -> None:
    """Sizes 2–3, k = 3. Real top-3 by (count desc, pattern asc): (0,1), (0,1,2), (1,2) at 3.

    Synthetic counts (0,1)=2, (1,2)=2, (0,1,2)=2, (4,5)=5 -> top-3 (4,5), (0,1), (0,1,2):
    intersection 2 -> F1 = 2/3; support error = mean(1/3, 1/3, 1/3) = 1/3.
    """
    real = [[0, 1, 2, 3]] * 3 + [[4, 5]]
    syn = [[0, 1, 2]] * 2 + [[4, 5]] * 5
    assert pattern_f1(real, syn, k=3, min_size=2, max_size=3) == pytest.approx(2 / 3)
    assert pattern_support_error(real, syn, k=3, min_size=2, max_size=3) == pytest.approx(1 / 3)
    # A real top pattern absent on the synthetic side contributes a full 1.
    assert pattern_support_error([[0, 1]], [[2, 3]], k=1) == pytest.approx(1.0)
    # Empty intersection: 0 instead of the reference's 0/0.
    assert pattern_f1([[0, 1]], [[2, 3]], k=1) == 0.0
    # Precision uses the nominal k even when fewer patterns exist (reference rule).
    assert pattern_f1([[0, 1]], [[0, 1]], k=4) == pytest.approx(0.25)
    assert pattern_f1(real, real, k=5, min_size=2, max_size=3) == 1.0


def test_pattern_counts_are_ngrams_with_multiplicity() -> None:
    counts = lm._pattern_counts([[0, 1, 2], [0, 1]], 2, 3)
    assert counts == {(0, 1): 2, (1, 2): 1, (0, 1, 2): 1}
    with pytest.raises(ValueError, match="min_size"):
        lm._pattern_counts([[0, 1]], 3, 2)


# --- points: sampling and range queries --------------------------------------------------


def test_sample_points_follow_reference_rule() -> None:
    chains = [[0, 1, 5], [7]]
    pts = sample_points(GRID4, chains, np.random.default_rng(1))
    assert [len(p) for p in pts] == [3, 2]  # one point per cell; single cell -> two points
    for chain, arr in zip(chains, pts, strict=True):
        cells = chain if len(chain) > 1 else chain * 2
        for cell, (x, y) in zip(cells, arr, strict=True):
            assert GRID4.cell_of(lat=y, lon=x) == cell
    again = sample_points(GRID4, chains, np.random.default_rng(1))
    assert all(np.array_equal(a, b) for a, b in zip(pts, again, strict=True))
    with pytest.raises(ValueError, match="non-empty"):
        sample_points(GRID4, [[]], np.random.default_rng(0))


def test_point_query_avre_deterministic_in_rng() -> None:
    real = sample_points(
        GRID5, _random_walks(5, 5, [6] * 30, np.random.default_rng(3)), np.random.default_rng(4)
    )
    syn = sample_points(
        GRID5, _random_walks(5, 5, [6] * 30, np.random.default_rng(5)), np.random.default_rng(6)
    )
    assert point_query_avre(real, real, GRID5, np.random.default_rng(0)) == 0.0
    a = point_query_avre(real, syn, GRID5, np.random.default_rng(0))
    b = point_query_avre(real, syn, GRID5, np.random.default_rng(0))
    c = point_query_avre(real, syn, GRID5, np.random.default_rng(1))
    assert a == b
    assert a != c
    assert a > 0.0


def test_point_query_hand_value() -> None:
    """One query covering the whole space (size_factor 1 and a centre draw of 0.5)."""

    class _Half:
        def random(self) -> float:
            return 0.5

    real = [np.array([[1.0, 1.0], [2.0, 2.0]])]
    syn = [np.array([[1.5, 1.5]])]
    # Square of side 4 centred at (2, 2) covers the bbox: counts 2 vs 1,
    # denominator max(2, 2·0.01) = 2 -> 0.5.
    value = point_query_avre(real, syn, GRID4, _Half(), n_queries=1, size_factor=1.0)  # type: ignore[arg-type]
    assert value == pytest.approx(0.5)


# --- invariances and validation ----------------------------------------------------------


def test_metrics_independent_of_trajectory_order() -> None:
    rng = np.random.default_rng(11)
    real = _random_walks(5, 5, [int(x) for x in rng.integers(2, 9, size=40)], rng)
    syn = _random_walks(5, 5, [int(x) for x in rng.integers(2, 9, size=40)], rng)
    real_pts = sample_points(GRID5, real, np.random.default_rng(1))
    syn_pts = sample_points(GRID5, syn, np.random.default_rng(2))
    perm = np.random.default_rng(3).permutation(len(real))
    real_perm = [real[i] for i in perm]
    syn_perm = [syn[i] for i in perm]
    real_pts_perm = [real_pts[i] for i in perm]
    syn_pts_perm = [syn_pts[i] for i in perm]
    a = evaluate(
        real, syn, GRID5, np.random.default_rng(0), real_raw_points=real_pts, syn_points=syn_pts
    )
    b = evaluate(
        real_perm,
        syn_perm,
        GRID5,
        np.random.default_rng(0),
        real_raw_points=real_pts_perm,
        syn_points=syn_pts_perm,
    )
    assert set(a) == set(METRIC_NAMES)
    for name in METRIC_NAMES:
        if name == "point_query_avre":
            continue  # evaluate() samples the real query points in chain order (rng use)
        assert a[name] == pytest.approx(b[name], abs=1e-12), name
    # With the points given, the point query is order-independent too.
    rng_a, rng_b = np.random.default_rng(0), np.random.default_rng(0)
    assert point_query_avre(real_pts, syn_pts, GRID5, rng_a) == point_query_avre(
        real_pts_perm, syn_pts_perm, GRID5, rng_b
    )


def test_evaluate_identical_populations() -> None:
    rng = np.random.default_rng(7)
    real = _random_walks(5, 5, [int(x) for x in rng.integers(4, 10, size=40)], rng)
    assert len(lm._pattern_counts(real, 2, 8)) >= 100  # k = 100 can be fully matched
    out = evaluate(real, real, GRID5, np.random.default_rng(0))
    assert out["density_error"] == pytest.approx(0.0, abs=1e-7)
    assert out["hotspot_query_error"] == pytest.approx(0.0, abs=1e-12)
    assert out["trip_error"] == pytest.approx(0.0, abs=1e-7)
    assert out["pattern_f1"] == 1.0
    assert out["pattern_support_error"] == 0.0
    assert 0.0 < out["coverage_kendall_tau"] <= 1.0
    # The three point metrics resample points independently per side, so they are
    # small but not zero here; zero needs identical points (tested above).
    for name in ("point_query_avre", "diameter_error", "length_error"):
        assert math.isfinite(out[name])


def test_validation_errors() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        density_error([], [[0]], GRID4)
    with pytest.raises(ValueError, match="out of range"):
        density_error([[16]], [[0]], GRID4)
    with pytest.raises(ValueError, match="non-empty"):
        trip_error([[0], []], [[0]], GRID4)
    with pytest.raises(ValueError, match="k must be"):
        pattern_f1([[0, 1]], [[0, 1]], k=0)
    with pytest.raises(ValueError, match="n_queries"):
        point_query_avre([_line(1.0)], [_line(1.0)], GRID4, np.random.default_rng(0), n_queries=0)
    with pytest.raises(ValueError, match="n_buckets"):
        length_error([_line(1.0)], [_line(1.0)], n_buckets=0)


# --- fixture: the ldptrace port at negligible noise beats a random-walk synthesizer ------


def _view(edge_seq: tuple[int, ...], tid: str) -> TrajectoryView:
    matched = MatchedTrajectory(
        traj_id=tid,
        user_id="u",
        map_id="osm_beijing_fixture",
        edge_seq=edge_seq,
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
        split="train",
    )
    return TrajectoryView(clean=clean, matched=matched)


@pytest.fixture(scope="module")
def routes(fixture_network: RoadNetwork) -> list[TrajectoryView]:
    """200 shortest-path routes between SCC node pairs (the test_ldptrace.py recipe, larger n)."""
    pair: dict[tuple[int, int], int] = {}
    lengths: dict[int, float] = {}
    for row in fixture_network.edges.itertuples(index=False):
        eid, u, v = int(row.edge_id), int(row.u), int(row.v)
        lengths[eid] = float(row.length_m)
        if (u, v) not in pair or lengths[eid] < lengths[pair[(u, v)]]:
            pair[(u, v)] = eid
    scc = max(nx.strongly_connected_components(fixture_network.graph), key=len)
    nodes = sorted(int(n) for n in scc)
    rng = np.random.default_rng(20260902)
    views: list[TrajectoryView] = []
    while len(views) < 200:
        a = nodes[int(rng.integers(len(nodes)))]
        b = nodes[int(rng.integers(len(nodes)))]
        if a == b:
            continue
        path = nx.shortest_path(fixture_network.graph, a, b, weight="length")
        edges = tuple(pair[(x, y)] for x, y in itertools.pairwise(path))
        if len(edges) < 3:
            continue
        views.append(_view(edges, f"t{len(views)}"))
    return views


def test_fixture_ldptrace_synthesis_scores_well_and_beats_random_walks(
    fixture_network: RoadNetwork, routes: list[TrajectoryView]
) -> None:
    """Population-level metrics need population-scale input: 200 routes on a 6 × 6 grid.

    At ε = 600 (OUE noise negligible) the port's synthesis is compared with 8-connected
    random walks that copy the real chain lengths exactly. Measured (seeds 2, 3):
    density 0.008–0.012 vs 0.14, hotspot 0.18–0.25 vs 0.38–0.51, point query 0.19–0.24
    vs 1.28, Kendall 0.73–0.74 vs 0.31–0.42, pattern F1 0.58–0.61 vs 0.15–0.16, support
    error 0.64–0.65 vs 0.92. Trip error stays high on both sides (0.44–0.48 vs 0.59: 36²
    pairs from 200 chains), and the length-matched walks win length/diameter (the
    port's walks stop early at the virtual end state), so those three are only
    required to be finite.
    """
    n_rows = n_cols = 6
    xs = [float(r.x) for r in fixture_network.nodes.itertuples(index=False)]
    ys = [float(r.y) for r in fixture_network.nodes.itertuples(index=False)]
    grid = Grid(bbox=(min(xs), min(ys), max(xs), max(ys)), n_rows=n_rows, n_cols=n_cols)
    gen = LDPTraceGenerator(fixture_network, epsilon=600.0, n_rows=n_rows, n_cols=n_cols, seed=2)
    gen.fit(routes)
    real = [gen.cell_sequence(v.as_segments()) for v in routes]
    syn = [list(s.payload) for s in gen.generate(len(real), seed=9)]
    walks = _random_walks(n_rows, n_cols, [len(c) for c in real], np.random.default_rng(2))

    good = evaluate(real, syn, grid, np.random.default_rng(0))
    bad = evaluate(real, walks, grid, np.random.default_rng(0))
    assert set(good) == set(METRIC_NAMES)
    assert all(math.isfinite(v) for v in good.values())
    assert good["density_error"] < 0.05
    assert good["hotspot_query_error"] < 0.5
    assert good["point_query_avre"] < 0.6
    assert good["coverage_kendall_tau"] > 0.5
    assert good["pattern_f1"] > 0.4
    for name in (
        "density_error",
        "hotspot_query_error",
        "point_query_avre",
        "pattern_support_error",
    ):
        assert good[name] < bad[name], name
    for name in ("coverage_kendall_tau", "pattern_f1"):
        assert good[name] > bad[name], name
