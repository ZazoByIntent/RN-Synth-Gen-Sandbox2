"""PrivTrace port: NormCut, the two-layer adaptive grid, and the generator's DP fit."""

import inspect
import itertools
import math

import networkx as nx
import numpy as np
import pytest

from trajguard.attacks.membership import ShadowGenerator
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.experiments import registry
from trajguard.maps.base import RoadNetwork
from trajguard.representation import TrajectoryView
from trajguard.synthesis.adaptive_grid import AdaptiveGrid, level1_cells, level1_density
from trajguard.synthesis.privtrace import (
    PrivTraceGenerator,
    _first_order_counts,
    _position_arrays,
    normcut,
    select_second_order_states,
)

# bbox with deliberately different spans per axis, so a row/column mix-up shows up.
BBOX = (0.0, 0.0, 10.0, 20.0)


def _grid() -> AdaptiveGrid:
    """2x2 level-1 grid with kappa = (1, 3, 5, 1): one cell per split state of the rule."""
    density = np.array([0.5, 1000.0, 5000.0, -3.0])
    return AdaptiveGrid.build(BBOX, 2, density, n_trajectories=100)


# --- NormCut ---------------------------------------------------------------------------


def test_normcut_hand_example() -> None:
    assert normcut(np.array([3.0, -2.0, 1.0, 4.0])).tolist() == [2.0, 0.0, 0.0, 4.0]


def test_normcut_output_is_non_negative_on_noisy_counts() -> None:
    rng = np.random.default_rng(20260920)
    noisy = rng.poisson(5.0, size=60) + rng.laplace(0.0, 4.0, size=60)
    assert (noisy < 0).any()  # the branch under test is actually exercised
    assert np.all(normcut(noisy) >= 0.0)


def test_normcut_preserves_the_total_when_positives_cover_negatives() -> None:
    rng = np.random.default_rng(11)
    noisy = rng.poisson(5.0, size=60) + rng.laplace(0.0, 4.0, size=60)
    assert noisy.sum() > 0
    assert float(normcut(noisy).sum()) == pytest.approx(float(noisy.sum()))


def test_normcut_is_identity_on_non_negative_input() -> None:
    values = np.array([0.0, 2.5, 7.0, 0.0, 1.0])
    once = normcut(values)
    assert once.tolist() == values.tolist()
    assert normcut(once).tolist() == values.tolist()  # idempotent


def test_normcut_is_idempotent_after_one_pass() -> None:
    rng = np.random.default_rng(3)
    noisy = rng.poisson(5.0, size=40) + rng.laplace(0.0, 4.0, size=40)
    once = normcut(noisy)
    assert normcut(once).tolist() == once.tolist()


def test_normcut_zeroes_everything_when_negatives_dominate() -> None:
    assert normcut(np.array([-5.0, 1.0, 1.0])).tolist() == [0.0, 0.0, 0.0]


def test_normcut_zeroes_everything_without_positive_entries() -> None:
    assert normcut(np.array([-5.0, 0.0, -1.0])).tolist() == [0.0, 0.0, 0.0]


def test_normcut_does_not_mutate_its_input() -> None:
    values = np.array([3.0, -2.0, 1.0, 4.0])
    result = normcut(values)
    assert values.tolist() == [3.0, -2.0, 1.0, 4.0]
    assert result is not values


def test_normcut_returns_float64_of_the_same_shape() -> None:
    result = normcut(np.array([3, -2, 1, 4]))
    assert result.dtype == np.float64
    assert result.shape == (4,)


def test_normcut_rejects_a_2d_input() -> None:
    with pytest.raises(ValueError):
        normcut(np.zeros((2, 3)))


# --- AdaptiveGrid ----------------------------------------------------------------------


def test_level1_cells_are_row_major_with_the_row_along_y() -> None:
    points = np.array([[0.0, 0.0], [9.9, 0.1], [0.1, 19.0], [2.6, 5.1]])
    assert level1_cells(points, BBOX, 4).tolist() == [0, 3, 12, 5]


def test_level1_cells_put_the_upper_corner_in_the_last_cell() -> None:
    assert level1_cells(np.array([[10.0, 20.0]]), BBOX, 4).tolist() == [15]


def test_level1_cells_clamp_points_outside_the_bbox() -> None:
    outside = np.array([[-5.0, -5.0], [100.0, 100.0], [-1.0, 100.0], [100.0, -1.0]])
    assert level1_cells(outside, BBOX, 4).tolist() == [0, 15, 12, 3]


def test_level1_density_sums_to_the_trajectory_count_and_one_per_trajectory() -> None:
    first = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])  # 4 points, cell 0
    second = np.array([[1.0, 1.0], [2.0, 2.0], [9.0, 19.0], [8.0, 18.0]])  # 2 + 2 cells
    density = level1_density([first, second], BBOX, 2)
    assert float(density.sum()) == pytest.approx(2.0)
    assert float(level1_density([second], BBOX, 2).sum()) == pytest.approx(1.0)
    assert density.tolist() == pytest.approx([1.5, 0.0, 0.0, 0.5])


def test_build_splits_dense_cells_and_leaves_sparse_ones_alone() -> None:
    grid = _grid()
    assert grid.kappa == (1, 3, 5, 1)  # ceil(sqrt(1000/200)) = 3, ceil(sqrt(5000/200)) = 5


def test_build_gate_blocks_cells_below_five_percent_of_the_uniform_share() -> None:
    density = np.array([0.5, 1000.0, 5000.0, -3.0])
    # threshold = 0.05 * 100000 / 4 = 1250, so the 1000-density cell no longer splits.
    grid = AdaptiveGrid.build(BBOX, 2, density, n_trajectories=100_000)
    assert grid.kappa == (1, 1, 5, 1)


def test_build_treats_nan_density_as_not_split() -> None:
    density = np.array([np.nan, 1000.0, 5000.0, -3.0])
    assert AdaptiveGrid.build(BBOX, 2, density, n_trajectories=100).kappa == (1, 3, 5, 1)


def test_build_clamps_kappa_to_max_sub_k() -> None:
    density = np.array([0.5, 1000.0, 5000.0, -3.0])
    grid = AdaptiveGrid.build(BBOX, 2, density, n_trajectories=100, max_sub_k=2)
    assert grid.kappa == (1, 2, 2, 1)


def test_build_offsets_are_prefix_sums_and_n_states_their_total() -> None:
    grid = _grid()
    assert grid.offsets == (0, 1, 10, 35)
    assert grid.n_states == sum(kappa**2 for kappa in grid.kappa) == 36


def test_build_twice_on_the_same_density_gives_the_same_leaf_ids() -> None:
    """Leaf ids must not wander: the Markov states of a fit are these integers."""
    first, second = _grid(), _grid()
    assert first == second  # frozen dataclass, so this compares bbox, k, kappa and offsets
    assert first.kappa == second.kappa
    assert first.offsets == second.offsets
    assert first.n_states == second.n_states
    points = np.array([[1.0, 1.0], [7.0, 3.0], [2.0, 15.0], [9.5, 19.5]])
    assert first.states_of(points).tolist() == second.states_of(points).tolist()


def test_states_of_numbers_sub_cells_row_major_inside_the_level1_cell() -> None:
    grid = _grid()  # cell 1 spans x in [5, 10], y in [0, 10] with kappa = 3, offset 1
    points = np.array([[5.1, 0.1], [9.9, 9.9], [5.1, 9.9], [9.9, 0.1]])
    assert grid.states_of(points).tolist() == [1, 9, 7, 3]


def test_states_of_lands_inside_state_bounds_for_random_points() -> None:
    grid = _grid()
    rng = np.random.default_rng(20260920)
    points = rng.uniform([0.0, 0.0], [10.0, 20.0], size=(500, 2))
    states = grid.states_of(points)
    assert states.min() >= 0 and states.max() < grid.n_states
    for (x, y), state in zip(points, states.tolist(), strict=True):
        x0, y0, x1, y1 = grid.state_bounds(state)
        assert x0 - 1e-9 <= x <= x1 + 1e-9
        assert y0 - 1e-9 <= y <= y1 + 1e-9


def test_state_level1_agrees_with_level1_cells() -> None:
    grid = _grid()
    rng = np.random.default_rng(7)
    points = rng.uniform([0.0, 0.0], [10.0, 20.0], size=(200, 2))
    cells = level1_cells(points, BBOX, grid.k).tolist()
    assert [grid.state_level1(s) for s in grid.states_of(points).tolist()] == cells


def test_state_bounds_of_an_unsplit_cell_is_the_whole_cell() -> None:
    grid = _grid()
    assert grid.state_bounds(0) == pytest.approx((0.0, 0.0, 5.0, 10.0))
    assert grid.state_bounds(35) == pytest.approx((5.0, 10.0, 10.0, 20.0))


def test_sequence_of_collapses_only_consecutive_duplicates() -> None:
    grid = _grid()
    points = np.array([[1.0, 1.0], [2.0, 2.0], [7.0, 15.0], [8.0, 16.0], [1.0, 3.0]])
    assert grid.sequence_of(points) == [0, 35, 0]


def test_sequence_of_a_single_point_is_one_state() -> None:
    grid = _grid()
    assert grid.sequence_of(np.array([[1.0, 1.0]])) == [0]


def test_level1_cells_reject_bad_input() -> None:
    points = np.array([[1.0, 1.0]])
    with pytest.raises(ValueError):
        level1_cells(np.zeros((0, 2)), BBOX, 2)  # empty
    with pytest.raises(ValueError):
        level1_cells(np.zeros(4), BBOX, 2)  # not (n, 2)
    with pytest.raises(ValueError):
        level1_cells(np.zeros((3, 3)), BBOX, 2)  # not (n, 2)
    with pytest.raises(ValueError):
        level1_cells(points, BBOX, 0)  # k < 1
    with pytest.raises(ValueError):
        level1_cells(points, (0.0, 0.0, 0.0, 20.0), 2)  # degenerate bbox


def test_build_rejects_bad_arguments() -> None:
    density = np.zeros(4)
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 1, np.zeros(1), 100)  # k < 2
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 2, np.zeros(5), 100)  # wrong density length
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 2, density, 0)  # no trajectories
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 2, density, 100, split_scale=0.0)
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 2, density, 100, split_gate=-0.1)
    with pytest.raises(ValueError):
        AdaptiveGrid.build(BBOX, 2, density, 100, max_sub_k=0)
    with pytest.raises(ValueError):
        AdaptiveGrid.build((0.0, 0.0, 10.0, 0.0), 2, density, 100)  # degenerate bbox


def test_state_bounds_rejects_states_outside_the_grid() -> None:
    grid = _grid()
    with pytest.raises(ValueError):
        grid.state_bounds(-1)
    with pytest.raises(ValueError):
        grid.state_bounds(grid.n_states)


# --- PrivTraceGenerator: fit -----------------------------------------------------------

MAP_ID = "osm_beijing_fixture"
# Large eps so the Laplace noise does not swamp 20 fixture routes and the adaptive rule
# actually selects a few second-order states; the estimation code paths are the same.
_BIG_EPS = 200.0


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


def _rule_matrix() -> np.ndarray:
    """First-order matrix over 4 real states, one row per branch of the selection rule.

    With ``eps2 = 100`` the mass threshold is ``theta1 = sqrt(2) * 4 / 100 = 0.057``:
    row 0 is busy and flat, row 1 is below the threshold (its END mass must not count),
    row 2 is busy but dominated by one successor, row 3 has a single successor.
    """
    matrix = np.zeros((6, 6))
    matrix[0, :4] = [5.0, 5.0, 5.0, 5.0]
    matrix[1, :4] = [0.02, 0.02, 0.0, 0.0]
    matrix[1, 5] = 100.0  # END column: excluded from the rule's row sum
    matrix[2, :4] = [10.0, 1.0, 0.0, 0.0]
    matrix[3, :4] = [7.0, 0.0, 0.0, 0.0]
    return matrix


def _bbox_points() -> list[np.ndarray]:
    """Four raw (x, y) trajectories inside BBOX for the bbox-mode tests."""
    return [
        np.array([[1.0, 1.0], [2.0, 3.0], [7.0, 15.0]]),
        np.array([[6.0, 12.0], [7.0, 16.0], [8.0, 18.0], [9.0, 19.0]]),
        np.array([[1.0, 2.0], [4.0, 11.0], [6.0, 14.0]]),
        np.array([[9.0, 19.0]]),  # a single point collapses to one state
    ]


@pytest.fixture(scope="module")
def train_views(fixture_network: RoadNetwork) -> list[TrajectoryView]:
    """~20 realistic on-road routes: shortest paths between SCC node pairs."""
    pair = _pair_edges(fixture_network)
    scc = max(nx.strongly_connected_components(fixture_network.graph), key=len)
    nodes = sorted(int(n) for n in scc)
    rng = np.random.default_rng(20260920)
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
def fitted(fixture_network: RoadNetwork, train_views: list[TrajectoryView]) -> PrivTraceGenerator:
    gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=11)
    gen.fit(train_views)
    return gen


def test_privtrace_registered_name() -> None:
    assert registry.get("generator", "privtrace") is PrivTraceGenerator


def test_rule_selects_a_busy_state_with_a_flat_row() -> None:
    assert 0 in select_second_order_states(_rule_matrix(), 4, eps2=100.0, theta2=5.0)


def test_rule_skips_a_state_below_the_mass_threshold() -> None:
    assert 1 not in select_second_order_states(_rule_matrix(), 4, eps2=100.0, theta2=5.0)


def test_rule_skips_a_state_with_one_dominant_successor() -> None:
    assert 2 not in select_second_order_states(_rule_matrix(), 4, eps2=100.0, theta2=5.0)


def test_rule_skips_a_state_with_a_single_successor() -> None:
    assert 3 not in select_second_order_states(_rule_matrix(), 4, eps2=100.0, theta2=5.0)


def test_rule_returns_only_the_flat_busy_state() -> None:
    assert select_second_order_states(_rule_matrix(), 4, eps2=100.0, theta2=5.0) == [0]


def test_rule_mass_threshold_grows_as_epsilon_shrinks() -> None:
    # theta1 = sqrt(2) * 4 / 0.001 = 5657, which even the busiest row (20) misses.
    assert select_second_order_states(_rule_matrix(), 4, eps2=0.001, theta2=5.0) == []


def test_rule_rejects_bad_arguments() -> None:
    matrix = _rule_matrix()
    with pytest.raises(ValueError):
        select_second_order_states(matrix, 1, eps2=100.0, theta2=5.0)  # fewer than 2 real states
    with pytest.raises(ValueError):
        select_second_order_states(matrix, 5, eps2=100.0, theta2=5.0)  # shape does not match
    with pytest.raises(ValueError):
        select_second_order_states(matrix, 4, eps2=0.0, theta2=5.0)
    with pytest.raises(ValueError):
        select_second_order_states(matrix, 4, eps2=100.0, theta2=0.0)


def test_constructor_rejects_bad_arguments(fixture_network: RoadNetwork) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        PrivTraceGenerator()
    with pytest.raises(ValueError, match="exactly one"):
        PrivTraceGenerator(fixture_network, bbox=BBOX)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, epsilon=0.0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, first_level_k=1)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, split_scale=0.0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, split_gate=-0.1)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, max_sub_k=0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, budget_split=(0.5, 0.5))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, budget_split=(0.5, 0.5, 0.0))
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, theta2=0.0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, max_len=0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=(0.0, 0.0, 10.0))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=(0.0, 0.0, 0.0, 20.0))  # degenerate span


def test_stage_epsilons_are_normalised_shares_of_epsilon() -> None:
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=3.0, budget_split=(1.0, 2.0, 2.0))
    assert sum(gen.stage_epsilons) == pytest.approx(3.0)
    assert gen.budget_split == pytest.approx((0.2, 0.4, 0.4))
    assert gen.stage_epsilons == pytest.approx((0.6, 1.2, 1.2))


def test_stage_epsilons_follow_a_non_default_budget_split() -> None:
    """Sequential composition: whatever the weights, the three stages spend epsilon together."""
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=4.0, budget_split=(1.0, 1.0, 2.0))
    assert gen.budget_split == pytest.approx((0.25, 0.25, 0.5))
    assert gen.stage_epsilons == pytest.approx((1.0, 1.0, 2.0))
    assert sum(gen.stage_epsilons) == pytest.approx(4.0)


def test_spent_budget_is_none_before_fit_and_epsilon_after(
    fitted: PrivTraceGenerator, fixture_network: RoadNetwork
) -> None:
    assert PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS).spent_budget() is None
    assert fitted.spent_budget() == pytest.approx(_BIG_EPS)


@pytest.mark.parametrize("split", [(0.2, 0.4, 0.4), (1.0, 1.0, 2.0), (7.0, 1.0, 2.0)])
def test_spent_budget_is_epsilon_whatever_the_split(split: tuple[float, float, float]) -> None:
    """The reported eps is the sum of the three stages, not the largest stage."""
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=6.0, first_level_k=2, budget_split=split, seed=3)
    assert sum(gen.stage_epsilons) == pytest.approx(6.0)
    gen.fit_points(_bbox_points())
    assert gen.spent_budget() == pytest.approx(6.0)


def test_fit_rejects_a_non_train_split(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    held_out = _view(train_views[0].as_segments(), split="test", tid="x")
    gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=1)
    with pytest.raises(ValueError, match="train split"):
        gen.fit([*train_views, held_out])


def test_fit_is_deterministic_in_the_seed(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    a = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=7)
    b = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=7)
    a.fit(train_views)
    b.fit(train_views)
    assert a.grid == b.grid
    assert a.second_order_states == b.second_order_states
    assert np.array_equal(a._order1, b._order1)
    assert [np.array_equal(a._order2[s], b._order2[s]) for s in a.second_order_states] == [
        True for _ in a.second_order_states
    ]


def test_fit_with_another_seed_gives_another_model(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    a = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=7)
    b = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=8)
    a.fit(train_views)
    b.fit(train_views)
    assert not np.array_equal(a._order1, b._order1)


def test_first_order_matrix_is_non_negative_and_has_dead_virtual_entries(
    fitted: PrivTraceGenerator,
) -> None:
    start, end = fitted.n_states, fitted.n_states + 1
    assert fitted._order1.shape == (end + 1, end + 1)
    assert np.all(fitted._order1 >= 0.0)
    assert np.all(fitted._order1[:, start] == 0.0)  # nothing ever enters START
    assert np.all(fitted._order1[end, :] == 0.0)  # nothing ever leaves END
    assert fitted._order1[start, end] == 0.0  # no empty trajectory


def test_n_states_matches_the_grid(fitted: PrivTraceGenerator) -> None:
    assert fitted.n_states == fitted.grid.n_states == 16  # 4x4 level-1 cells, none split


def test_second_order_matrices_are_full_sized_and_non_negative(
    fitted: PrivTraceGenerator,
) -> None:
    size = fitted.n_states + 2
    assert fitted.second_order_states  # the rule really did select states at this eps
    assert sorted(fitted._order2) == list(fitted.second_order_states)
    for state in fitted.second_order_states:
        matrix = fitted._order2[state]
        assert matrix.shape == (size, size)
        assert np.all(matrix >= 0.0)
        assert np.all(matrix[:, fitted.n_states] == 0.0)  # START is never a successor
        assert np.all(matrix[fitted.n_states + 1, :] == 0.0)  # END is never a predecessor


def test_first_order_counts_weigh_every_trajectory_exactly_one() -> None:
    """Stage 2's DP argument: one trajectory moves the matrix by 1 in L1, so sensitivity is 1."""
    start, end = 4, 5
    one = _first_order_counts([[0, 1, 2]], 4)  # 3 states -> 4 transitions of weight 1/4
    two = _first_order_counts([[0, 1, 2], [3]], 4)  # + 1 state -> 2 transitions of weight 1/2
    assert float(one.sum()) == 1.0  # exact: the weights are powers of two here
    assert float(two.sum()) == 2.0
    assert float(np.abs(two - one).sum()) == 1.0  # adding one trajectory costs exactly 1 in L1
    assert one[start, 0] == 0.25  # START -> first state
    assert one[2, end] == 0.25  # last state -> END
    assert two[start, 3] == 0.5 and two[3, end] == 0.5  # the one-state trajectory
    assert np.all(one[:, start] == 0.0) and np.all(one[end, :] == 0.0)


def test_position_arrays_weigh_every_trajectory_exactly_one() -> None:
    """Stage 3's DP argument: the second-order matrices together see weight 1 per trajectory."""
    start, end = 4, 5
    current, previous, following, weight = _position_arrays([[0, 1, 2, 1], [3, 0]], 4)
    assert current.tolist() == [0, 1, 2, 1, 3, 0]
    assert previous.tolist() == [start, 0, 1, 2, start, 3]  # START before the first state
    assert following.tolist() == [1, 2, 1, end, 0, end]  # END after the last one
    assert float(weight[:4].sum()) == 1.0  # the 4-state trajectory: 1/4 per position
    assert float(weight[4:].sum()) == 1.0  # the 2-state trajectory: 1/2 per position
    assert float(weight.sum()) == 2.0


def test_fit_rejects_a_second_order_model_above_the_memory_cap(
    fixture_network: RoadNetwork,
    train_views: list[TrajectoryView],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard names the knob that lowers the state count instead of allocating the matrices."""
    monkeypatch.setattr("trajguard.synthesis.privtrace._MAX_SECOND_ORDER_CELLS", 1.0)
    gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=11)
    with pytest.raises(ValueError, match="first_level_k"):
        gen.fit(train_views)  # this eps selects 5 second-order states, so the cap is reached


def test_points_of_rejects_empty_and_unknown_edges(fitted: PrivTraceGenerator) -> None:
    with pytest.raises(ValueError, match="empty"):
        fitted.points_of(())
    with pytest.raises(ValueError, match="road network"):
        fitted.points_of((10**9,))


def test_bare_sequence_views_fit_like_full_views(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """The membership attack trains shadow models on bare TrajectoryView(sequence=...)."""
    bare = [TrajectoryView(sequence=view.as_segments()) for view in train_views]
    full_gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=5)
    bare_gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=5)
    full_gen.fit(train_views)
    bare_gen.fit(bare)
    assert np.array_equal(full_gen._order1, bare_gen._order1)
    assert full_gen.second_order_states == bare_gen.second_order_states


def test_bbox_mode_fits_on_raw_coordinate_arrays() -> None:
    points = _bbox_points()
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=50.0, first_level_k=2, seed=3)
    gen.fit_points(points)
    assert gen.n_states == gen.grid.n_states >= 4
    assert gen.spent_budget() == pytest.approx(50.0)
    assert np.all(gen._order1 >= 0.0)
    with pytest.raises(ValueError):
        PrivTraceGenerator(bbox=BBOX, seed=3).fit_points([])


def test_bbox_mode_rejects_the_cells_representation() -> None:
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=50.0, first_level_k=2, seed=3)
    with pytest.raises(ValueError, match="cells"):
        gen.fit([TrajectoryView(sequence=(1, 2))])


# --- PrivTraceGenerator: synthesis and scoring -----------------------------------------

# Noise so small that the fitted model reproduces the training structure: used only where the
# assertion is about what the model learned, not about what the privacy noise does to it.
_HUGE_EPS = 1e4


def _state_chains(gen: PrivTraceGenerator, views: list[TrajectoryView]) -> list[list[int]]:
    """Leaf-state chain of every view under a fitted network-mode generator."""
    return [gen.grid.sequence_of(gen.points_of(view.as_segments())) for view in views]


def test_generate_returns_well_formed_state_sequences(fitted: PrivTraceGenerator) -> None:
    out = fitted.generate(12, seed=4)
    assert len(out) == 12
    for syn in out:
        assert syn.generator_id == "privtrace"
        assert syn.trained_on_split == "train"
        assert syn.map_id == MAP_ID
        assert isinstance(syn.payload, tuple)
        assert 1 <= len(syn.payload) <= fitted.max_len
        assert all(isinstance(s, int) and 0 <= s < fitted.n_states for s in syn.payload)
    # Staying in the same state is rare but not impossible: the training chains collapse
    # consecutive duplicates, so the true diagonal counts are 0, but neither the paper nor the
    # reference zeroes the diagonal, so the Laplace noise left on it can survive NormCut.
    # Measured on this fit: 1 self-transition in the 822 steps below, and at most 0.14% of the
    # steps over 30 generate seeds. The assertion is therefore a rate and not an absence, so a
    # noise draw that shifts with the numpy version or the seed cannot flake it.
    bulk = [syn.payload for syn in fitted.generate(300, seed=5)]
    steps = [pair for payload in bulk for pair in itertools.pairwise(payload)]
    assert len(steps) >= 100  # the rate below is measured on enough steps to mean something
    assert sum(a == b for a, b in steps) <= 0.01 * len(steps)


def test_generate_is_deterministic_in_the_seed(fitted: PrivTraceGenerator) -> None:
    first = [syn.payload for syn in fitted.generate(8, seed=1)]
    again = [syn.payload for syn in fitted.generate(8, seed=1)]
    other = [syn.payload for syn in fitted.generate(8, seed=2)]
    assert first == again
    assert first != other


def test_generate_ids_and_params_hash_carry_the_generate_seed(fitted: PrivTraceGenerator) -> None:
    one = fitted.generate(2, seed=1)
    two = fitted.generate(2, seed=2)
    assert [syn.syn_id for syn in one] == ["privtrace/1/0", "privtrace/1/1"]
    assert one[0].params_hash == one[1].params_hash
    assert one[0].params_hash != two[0].params_hash


def test_walks_stop_at_max_len(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, max_len=3, seed=11)
    gen.fit(train_views)
    lengths = [len(syn.payload) for syn in gen.generate(20, seed=6)]
    assert min(lengths) >= 1
    assert max(lengths) == 3  # the cap binds: the same fit runs to 10 states uncapped


def test_high_epsilon_walks_follow_the_training_structure(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """Utility smoke test: with negligible noise the walks stay on the training transitions."""
    gen = PrivTraceGenerator(fixture_network, epsilon=_HUGE_EPS, first_level_k=4, seed=2)
    gen.fit(train_views)
    chains = _state_chains(gen, train_views)
    observed = {pair for chain in chains for pair in itertools.pairwise(chain)}
    train_starts = {chain[0] for chain in chains}
    payloads = [syn.payload for syn in gen.generate(100, seed=13)]
    steps = [pair for payload in payloads for pair in itertools.pairwise(payload)]
    # Measured: 0.993 of the 298 steps are training transitions, 1.000 of the starts are
    # training starts; the residue is Laplace noise that NormCut left standing.
    assert sum(pair in observed for pair in steps) / len(steps) >= 0.9
    assert sum(payload[0] in train_starts for payload in payloads) / len(payloads) >= 0.8


def test_sequence_log_prob_is_finite_on_train_and_reversed_routes(
    fitted: PrivTraceGenerator, train_views: list[TrajectoryView]
) -> None:
    for view in train_views:
        assert math.isfinite(fitted.sequence_log_prob(view.as_segments()))
    for view in train_views[:3]:
        # A route the model has no evidence for floors its factors instead of hitting -inf.
        assert math.isfinite(fitted.sequence_log_prob(tuple(reversed(view.as_segments()))))


def test_sequence_log_prob_ranks_coherent_above_incoherent(
    fixture_network: RoadNetwork, train_views: list[TrajectoryView]
) -> None:
    """The membership-inference hook must penalize steps the model never saw."""
    gen = PrivTraceGenerator(fixture_network, epsilon=_HUGE_EPS, first_level_k=4, seed=2)
    gen.fit(train_views)
    rng = np.random.default_rng(3)
    all_edges = sorted(gen._edge_nodes)
    incoherent = tuple(int(all_edges[i]) for i in rng.choice(len(all_edges), size=6, replace=False))
    assert len(gen.grid.sequence_of(gen.points_of(incoherent))) >= 3  # it really does jump

    def per_state(seq: tuple[int, ...]) -> float:
        return gen.sequence_log_prob(seq) / len(gen.grid.sequence_of(gen.points_of(seq)))

    # The total is length-dependent, so compare per state. Measured: train routes between
    # -2.05 and -0.85, the incoherent 7-state chain -24.35.
    train_scores = [per_state(view.as_segments()) for view in train_views[:5]]
    assert min(train_scores) > per_state(incoherent)


def test_generate_and_score_before_fit_raise(fixture_network: RoadNetwork) -> None:
    gen = PrivTraceGenerator(fixture_network, epsilon=_BIG_EPS, first_level_k=4, seed=0)
    with pytest.raises(RuntimeError, match="fit"):
        gen.generate(1, seed=0)
    with pytest.raises(RuntimeError, match="fit"):
        gen.sequence_log_prob((1,))


def test_bbox_mode_scores_a_leaf_state_sequence() -> None:
    gen = PrivTraceGenerator(bbox=BBOX, epsilon=50.0, first_level_k=2, seed=3)
    gen.fit_points(_bbox_points())
    assert math.isfinite(gen.sequence_log_prob([0]))
    assert math.isfinite(gen.sequence_log_prob([0, gen.n_states - 1]))
    with pytest.raises(ValueError, match="leaf states"):
        gen.sequence_log_prob([gen.n_states])
    with pytest.raises(ValueError, match="empty"):
        gen.sequence_log_prob([])


def test_context_row_prefers_the_second_order_row_where_it_has_mass(
    fitted: PrivTraceGenerator,
) -> None:
    state = fitted.second_order_states[0]
    second = fitted._order2[state]
    previous = int(np.argmax(second.sum(axis=1)))
    assert second[previous].sum() > 0.0
    assert np.array_equal(fitted._context_row(previous, state), second[previous])
    # END is zeroed as a predecessor by construction, so that row falls back to first order.
    assert np.array_equal(fitted._context_row(fitted.n_states + 1, state), fitted._order1[state])
    plain = next(s for s in range(fitted.n_states) if s not in fitted._order2)
    assert np.array_equal(fitted._context_row(previous, plain), fitted._order1[plain])


def test_second_order_row_reaches_successors_the_first_order_row_cannot(
    fitted: PrivTraceGenerator,
) -> None:
    """What the second-order model buys: steps to a state whose first-order weight is 0."""
    real = fitted.n_states  # ignore the two virtual states: only real successors count here
    gaps = [
        (previous, state, int(successor))
        for state in fitted.second_order_states
        for previous in range(real + 2)
        if float(fitted._order2[state][previous].sum()) > 0.0
        for successor in np.flatnonzero(
            (fitted._order2[state][previous][:real] > 0.0) & (fitted._order1[state][:real] == 0.0)
        )
    ]
    assert gaps  # measured on this fit: 35 (previous, state) rows carry such a successor
    previous, state, successor = gaps[0]
    row = fitted._context_row(previous, state)
    assert np.array_equal(row, fitted._order2[state][previous])  # the adaptive rule picked it
    assert row[successor] > 0.0
    assert fitted._order1[state][successor] == 0.0  # unreachable under the first-order row


# --- Contracts and robustness ----------------------------------------------------------


def test_generator_satisfies_the_shadow_generator_protocol(fitted: PrivTraceGenerator) -> None:
    """The membership attack drives its shadow models through this protocol only."""
    # ShadowGenerator is a plain Protocol (no @runtime_checkable), so isinstance cannot be
    # used on it; this annotated binding is what mypy checks, the asserts what pytest checks.
    shadow: ShadowGenerator = fitted
    assert callable(shadow.fit)
    assert callable(shadow.sequence_log_prob)
    edge = next(iter(fitted._edge_nodes))
    assert math.isfinite(shadow.sequence_log_prob((edge,)))  # callable through the protocol


def test_constructor_signature_matches_the_orchestrator_injection(
    fixture_network: RoadNetwork,
) -> None:
    """orchestrator._generator_ctor binds the YAML params, then injects network= and seed=."""
    signature = inspect.signature(PrivTraceGenerator)
    assert {"network", "bbox", "seed"} <= set(signature.parameters)
    assert signature.parameters["network"].default is None  # so bbox mode needs no network
    bound = signature.bind_partial(epsilon=2.0)  # the planning-time probe on YAML params
    assert bound.arguments == {"epsilon": 2.0}
    with pytest.raises(TypeError):
        signature.bind_partial(epsilonn=2.0)  # a misspelled YAML param is a config error
    gen = PrivTraceGenerator(network=fixture_network, epsilon=2.0, seed=7)  # the injection
    assert gen.seed == 7 and gen.epsilon == 2.0 and gen.bbox[0] < gen.bbox[2]
