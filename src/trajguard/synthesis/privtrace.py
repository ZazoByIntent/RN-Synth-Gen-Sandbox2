"""PrivTrace (Wang et al., USENIX Security 2023): DP trajectory synthesis by adaptive Markov models.

PrivTrace discretises space with the two-layer adaptive grid of
:mod:`trajguard.synthesis.adaptive_grid` and estimates a Markov model over its leaf states:

1. measure how much trajectory mass falls into each of the ``K x K`` level-1 cells, every
   trajectory contributing exactly 1 spread over its own points (length-normalised);
2. add Laplace noise at ``eps1`` and repair the negatives with :func:`normcut`;
3. split the dense level-1 cells adaptively -- the leaves are the ``m`` *states*;
4. count first-order transitions between states, with a virtual START before the first state
   and a virtual END after the last one, again length-normalised (``1 / (L + 1)`` per
   transition, ``L`` = number of states in the trajectory), add Laplace noise at ``eps2``,
   zero the impossible entries and NormCut every row;
5. decide once per state whether its next step needs a *second-order* model: it does when the
   state's outgoing mass reaches ``theta1 = sqrt(2) * m / eps2`` **and** its two busiest
   successors are within a factor ``theta2 = 5`` of each other -- i.e. when the state is
   frequent enough to afford the extra noise and ambiguous enough to need it;
6. for those states estimate a ``[previous, next]`` matrix, noise it at ``eps3``, zero the
   impossible entries and NormCut every row again.

**Synthesis and scoring.** A synthetic trajectory is a walk over the leaf states (the paper's
Algorithm 1): the first state is drawn from the noisy START row, and every further step reads
the ``[previous, next]`` row of the current state when that state has a second-order matrix
whose row for this predecessor carries mass, and its first-order row otherwise. The walk stops
when the virtual END is drawn, when it reaches ``max_len`` states, or when the row it would
sample from has no mass left at all; a walk that reaches ``max_len`` without having drawn END is
discarded and redrawn, at most ``max_redraws`` times (D-4.3). The payload is that state
sequence -- state ids, no coordinates: the benchmark scores states, so the reference's last
step, one random point drawn inside each leaf rectangle, is left out. Scoring an input sequence
(the membership-inference hook) multiplies exactly those factors -- START to the first state,
one per step under the same adaptive rule, the last state to END -- each floored at 1e-12 so an
unseen step costs a finite penalty instead of minus infinity, and adds no length term. When
NormCut has emptied the START row, both paths fall back to the same uniform start over the
``m`` real states (:meth:`PrivTraceGenerator._start_probabilities`), so the start factor of a
walk and of its score always agrees. That agreement is for the start only: a walk that stops at
a dead end or at the ``max_len`` cap is scored with an END factor it never drew (the dead end's
is floored at 1e-12), and a walk kept after the redraws of D-4.3 was conditioned on not hitting
the cap, which the score does not model.

**Trust model.** PrivTrace assumes a TRUSTED CURATOR who sees every raw trajectory; the
guarantee is trajectory-level eps-differential privacy (neighbouring databases differ in one
trajectory, not one user; a user with m trajectories is covered at m*eps). In this benchmark
it is therefore an UPPER BOUND on the utility a curator can reach and a baseline candidate
(decision D5 is open), not a like-for-like competitor of the LDP generators ``ldptrace`` /
``rn_ldp_synth``.

**eps unit: per trajectory, central.** One budget is spent once, by the curator, over the
whole database; it is not a per-device budget like LDPTrace's and not a per-point budget like
geo-indistinguishability's.

**Budget split** (the reference default, ``budget_split=(0.2, 0.4, 0.4)``): ``eps1 = 0.2*eps``
buys the level-1 densities, ``eps2 = 0.4*eps`` the first-order matrix and ``eps3 = 0.4*eps``
the second-order matrices. The three stages touch the data once each, so sequential
composition gives exactly ``eps1 + eps2 + eps3 = eps``.

Two input modes, chosen by the constructor (exactly one of ``network`` / ``bbox``):

- **Network mode** (``network=``, the benchmark's segments representation): the level-1 bbox
  is the bounding box of the network's projected nodes and a matched edge sequence becomes the
  path of its endpoint node coordinates, so the states come from the *public* road network and
  never from the raw GPS points. Consecutive duplicates are collapsed; nothing is interpolated.
- **Bbox mode** (``bbox=(min_lon, min_lat, max_lon, max_lat)``): raw ``(lon, lat)`` coordinates
  straight from the clean trajectory, used by the validation harness only. The orchestrator's
  *cells* representation (a bare sequence of grid-cell indices) is **not** supported -- the
  adaptive grid needs coordinates, not cells someone else has already binned. The box itself
  comes from the caller: in network mode it is the public road network's node box, while the
  validation harness derives it from the raw data's min/max (padded by 1e-5 of the span, as the
  reference does), which is **not** differentially private -- the harness documents that.

Deviations from the paper, all deliberate:

- **D-4.1 (grid, and what the split gate may read).** The subdivision rule is the reference
  code's ``kappa_i = ceil(sqrt(d_i / split_scale))`` behind a five-per-cent gate, because the
  paper states its own ``kappa`` formula twice and the two versions disagree by a factor of
  1000 (see :mod:`trajguard.synthesis.adaptive_grid`). The cap ``max_sub_k`` is ours -- without
  it one dense cell can blow up the state count and the quadratic work that follows.
  ``first_level_k`` is a plain parameter instead of the paper's ``K = sqrt(|D| / c)`` with a
  hand-chosen per-dataset ``c``. The paper is **silent** on where the ``|D|`` in the split gate
  comes from -- the gate itself is the reference code's rule, and the reference reads the true
  ``|D|`` there -- so this port feeds the gate the sum of the noisy post-NormCut level-1 vector
  instead. That sum is pure post-processing of the stage-1 release (NormCut preserves the total
  whenever the positive mass covers the negative), so nothing un-noised is read after stage 1
  and the port still spends exactly ``eps1 + eps2 + eps3``.
- **D-4.2 (no trip solver).** The paper calibrates a start/end trip distribution with a
  least-squares program over all state pairs; this port samples the start from the noisy START
  row instead. The paper itself discards the sampled end ("lambda_end will not be used"), so
  the solver only ever reshapes the start distribution, at a cost of ``m^2`` shortest paths
  and an ``m x m`` convex program. The paper's own reason for the solver (section 4.4) is that
  the ``1 / (L + 1)`` normalisation "over-counts short trajectories and under-counts long
  trajectories", and the trip distribution is its bias correction -- so dropping it costs a
  length bias. Measured on Porto (20 000 trips, ``K = 6``, effectively noise-free
  ``eps = 1e4``): the real trips have 12.0 collapsed states on average, this port's walks 8.6,
  about 30 per cent short. A trip solver or an explicit length model is an open item.
- **D-4.3 (walk cap, with a redraw guard).** A generated walk is capped at ``max_len`` states
  instead of running until the virtual END happens to be drawn. A walk that reaches the cap
  without ever drawing END is discarded and redrawn from the same random stream, at most
  ``max_redraws`` times (default 20); if every redraw is capped as well, the last one is kept,
  and after a :meth:`PrivTraceGenerator.generate` call ``n_capped_walks`` and
  ``n_redrawn_walks`` report how often that happened. The guard reads no data and spends no
  budget -- it is post-processing of the released model -- and it applies with and without the
  D-4.6 mask; what it does change is that the emitted walks are conditioned on not hitting the
  cap, which scoring does not model. The motive is the mask: under D-4.6 at ``eps = 0.5`` on
  Porto (20 000 trips) 1207 of the 20 000 walks on seed 1 ran to the cap of 200 states, because
  a masked row can lose its END mass and keep only a few allowed successors, so the walk
  circles its own neighbourhood. Without the mask no walk on Porto reaches the cap at any
  ``eps``, so the paper-faithful port is left unchanged by the guard.
- **D-4.4 (states from the network).** In network mode the states come from the public road
  network's node coordinates, consecutive duplicates are collapsed and gaps are not bridged.
- **D-4.6 (adjacency mask, off by default).** With ``mask_non_adjacent=True`` a transition
  between two real states whose level-1 cells are neither the same nor 4-adjacent (Manhattan
  distance of their level-1 row/column positions above 1) is treated as impossible and zeroed
  together with the structural zeros -- after the Laplace noise and before NormCut, in the
  first-order matrix and in every second-order matrix. This is the reference code's adjacency
  rule (``large_neighbor_or_same_by_subcell_index``) turned into post-processing over the
  public grid geometry: it adds no random draws of its own and reads no data, so the spent
  budget is unchanged; but because it lands before NormCut and before the selection rule, the
  set of second-order states and with it the number of stage-3 Laplace matrices can differ from
  the unmasked fit (5.4 against 4.2 selected states on Porto 20 000 trips at ``eps = 2``). The
  stage still spends ``eps3`` once whatever that count, because one trajectory contributes
  weight 1 across all second-order matrices together. It is **off** by default because the
  paper's Algorithm 1 has no adjacency constraint; the validation harness measures both
  variants.

Places where the authors' public code (github.com/DpTrace/PrivTrace, **no licence**, not used
here) deviates from the paper and this port does **not** follow it: ``K`` derived from the raw
point count rather than from ``|D|``; three extra OR-conditions in the adaptive rule (very
large out-degree, start weight above two per cent, end weight above two per cent) that force
second order regardless of the paper's test; second-order counts truncated to integers and
stored as ``float16``, which destroys everything below 1; ad-hoc end-probability multipliers
(x1.3, x1.5, x0.8, x0.5, x0.2); rejection sampling that discards long or lingering walks; an
adjacency check at generation time (available here as the opt-in D-4.6 mask); and a cvxpy
least-squares solver for the trip distribution. Its guidepost end rescale also divides by zero
whenever a second-order state carries no END mass (the RuntimeWarnings in its logs), which
casts that END column to ``INT_MIN`` on one or two states per run, 0.7 to 2.5 per cent of the
out-mass: those states can never end a walk and depend on its dead-end jump instead. Several of
those steps are also **not private**: ``K`` comes from the raw point count, the true ``|D|``
enters the subdivision gate and the solver target, and the transition mask is read off the
*noiseless* counts -- so the reference as shipped does not meet the eps
it claims, while this port spends exactly ``eps1 + eps2 + eps3``.
"""

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.base import params_hash
from trajguard.representation import TrajectoryView
from trajguard.synthesis.adaptive_grid import AdaptiveGrid, Bbox, level1_density
from trajguard.synthesis.base import SyntheticGenerator

# The two virtual states are appended to the m real ones, so their indices are only known
# after a fit: START = n_states + _START_OFFSET and END = n_states + _END_OFFSET.
_START_OFFSET = 0
_END_OFFSET = 1
_N_VIRTUAL = 2
# Largest number of second-order matrix entries this port will allocate (~2.4 GB in float64).
_MAX_SECOND_ORDER_CELLS = 3e8
# Smallest factor sequence_log_prob takes the logarithm of, as in ldptrace.
_PROB_FLOOR = 1e-12


def normcut(values: np.ndarray) -> np.ndarray:
    """NormCut (PrivTrace Algorithm 2) on a 1-D vector, in the reference code's vectorised form.

    Laplace noise pushes some counts below zero. NormCut removes that negative mass by
    paying for it out of the smallest positive entries, which keeps the total unchanged and
    leaves the large, informative entries alone. Write ``N`` for the sum of the entries
    below zero (so ``N <= 0``) and ``P`` for the entries above zero sorted ascending; exact
    zeros count as neither. Three branches:

    1. no negative entry: the vector comes back unchanged, so the function is idempotent
       and a second pass never moves anything;
    2. negatives that the positive mass cannot cover (``sum(P) <= -N``): an all-zero
       vector, which is Algorithm 2's ``P = 0`` exit;
    3. otherwise let ``k`` be the smallest number of the smallest positives whose sum
       reaches ``-N``. Those ``k - 1`` smallest positives become 0, the ``k``-th becomes
       ``sum of the k smallest positives + N`` (which is ``>= 0``), every negative becomes
       0, and the larger positives are left untouched. The total is preserved.

    Hand example: ``[3, -2, 1, 4] -> [2, 0, 0, 4]``. The negative mass is ``-2``; the
    smallest positive (1) does not cover it, the two smallest (``1 + 3 = 4``) do, so 1
    becomes 0 and 3 becomes ``4 - 2 = 2``.

    The result is a new float64 array of the same shape; the input is never mutated.
    """
    out = np.array(values, dtype=np.float64)
    if out.ndim != 1:
        raise ValueError(f"normcut needs a 1-D vector, got shape {out.shape}")
    negatives = np.flatnonzero(out < 0)
    if negatives.size == 0:
        return out
    positives = np.flatnonzero(out > 0)
    negative_sum = float(out[negatives].sum())
    if float(out[positives].sum()) <= -negative_sum:
        return np.zeros_like(out)
    ascending = positives[np.argsort(out[positives], kind="stable")]
    covered = np.cumsum(out[ascending])
    k = int(np.searchsorted(covered, -negative_sum, side="left")) + 1
    out[ascending[: k - 1]] = 0.0
    out[ascending[k - 1]] = float(covered[k - 1]) + negative_sum
    out[negatives] = 0.0
    return out


def select_second_order_states(
    order1: np.ndarray, n_states: int, eps2: float, theta2: float
) -> list[int]:
    """States whose next step uses the second-order model (paper rule, decided once per state).

    Reads the *noisy, post-NormCut* first-order matrix, whose last two rows and columns are the
    virtual START and END states and are excluded from every quantity below. A real state gets
    a second-order matrix when both halves of the paper's test hold:

    * **enough traffic** -- the mass leaving the state towards real states reaches
      ``theta1 = sqrt(2) * n_states / eps2``, the point at which the Laplace noise is small
      compared with the counts, and
    * **an ambiguous choice** -- the two busiest successors ``n1 >= n2 > 0`` satisfy
      ``n1 / n2 < theta2``, so the first-order row does not already decide the next step.

    Returns the selected state ids in ascending order. The reference code ORs three further
    conditions onto this test; they are not in the paper and are not reproduced here.
    """
    matrix = np.asarray(order1, dtype=np.float64)
    if n_states < 2:
        raise ValueError(f"the selection rule needs at least 2 real states, got {n_states}")
    size = n_states + _N_VIRTUAL
    if matrix.shape != (size, size):
        raise ValueError(
            f"order1 must have shape ({size}, {size}) for {n_states} real states, "
            f"got shape {matrix.shape}"
        )
    if eps2 <= 0:
        raise ValueError(f"eps2 must be > 0, got {eps2}")
    if theta2 <= 0:
        raise ValueError(f"theta2 must be > 0, got {theta2}")
    real = matrix[:n_states, :n_states]
    outgoing = real.sum(axis=1)
    theta1 = math.sqrt(2.0) * n_states / eps2
    two_largest = np.partition(real, -2, axis=1)[:, -2:]
    n1 = two_largest.max(axis=1)
    n2 = two_largest.min(axis=1)
    ratio = np.full(n_states, np.inf)
    np.divide(n1, n2, out=ratio, where=n2 > 0)
    selected = (outgoing >= theta1) & (n2 > 0) & (ratio < theta2)
    return [int(state) for state in np.flatnonzero(selected)]


@register("generator", "privtrace")
class PrivTraceGenerator(SyntheticGenerator):
    """Central-DP trajectory synthesis from an adaptive grid and adaptive-order Markov models.

    The constructor only fixes the geometry and the parameters; :meth:`fit` (or
    :meth:`fit_points`) spends the budget. Every noise draw comes from the seeded
    ``np.random.Generator`` built from the constructor seed, so a fit is reproducible. See the
    module docstring for the mechanism, the trust model, the eps unit, the two input modes and
    the deviations from the paper and from the authors' code.
    """

    grid: AdaptiveGrid
    """The two-layer adaptive grid; only defined after a successful fit."""

    def __init__(
        self,
        network: RoadNetwork | None = None,
        bbox: Bbox | None = None,
        epsilon: float = 1.0,
        first_level_k: int = 6,
        split_scale: float = 200.0,
        split_gate: float = 0.05,
        max_sub_k: int = 8,
        budget_split: tuple[float, float, float] = (0.2, 0.4, 0.4),
        theta2: float = 5.0,
        max_len: int = 200,
        max_redraws: int = 20,
        mask_non_adjacent: bool = False,
        seed: int = 0,
    ) -> None:
        """Validate the parameters and fix the level-1 bounding box; no data is touched."""
        if (network is None) == (bbox is None):
            raise ValueError("PrivTraceGenerator needs exactly one of network= or bbox=")
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if first_level_k < 2:
            raise ValueError(f"first_level_k must be >= 2, got {first_level_k}")
        if split_scale <= 0:
            raise ValueError(f"split_scale must be > 0, got {split_scale}")
        if split_gate < 0:
            raise ValueError(f"split_gate must be >= 0, got {split_gate}")
        if max_sub_k < 1:
            raise ValueError(f"max_sub_k must be >= 1, got {max_sub_k}")
        if len(budget_split) != 3 or any(share <= 0 for share in budget_split):
            raise ValueError(f"budget_split needs 3 positive weights, got {budget_split}")
        if theta2 <= 0:
            raise ValueError(f"theta2 must be > 0, got {theta2}")
        if max_len < 1:
            raise ValueError(f"max_len must be >= 1, got {max_len}")
        if max_redraws < 0:
            raise ValueError(f"max_redraws must be >= 0, got {max_redraws}")

        self.epsilon = float(epsilon)
        self.first_level_k = int(first_level_k)
        self.split_scale = float(split_scale)
        self.split_gate = float(split_gate)
        self.max_sub_k = int(max_sub_k)
        self.theta2 = float(theta2)
        self.max_len = int(max_len)
        self.max_redraws = int(max_redraws)
        self.mask_non_adjacent = bool(mask_non_adjacent)
        self.seed = seed
        w1, w2, w3 = (float(share) for share in budget_split)
        total = w1 + w2 + w3
        # Stage shares, normalised to sum to 1, and the eps each stage may spend.
        self.budget_split: tuple[float, float, float] = (w1 / total, w2 / total, w3 / total)
        self.stage_epsilons: tuple[float, float, float] = (
            self.epsilon * self.budget_split[0],
            self.epsilon * self.budget_split[1],
            self.epsilon * self.budget_split[2],
        )
        self._params: dict[str, Any] = {
            "epsilon": self.epsilon,
            "first_level_k": self.first_level_k,
            "split_scale": self.split_scale,
            "split_gate": self.split_gate,
            "max_sub_k": self.max_sub_k,
            "budget_split": list(self.budget_split),
            "theta2": self.theta2,
            "max_len": self.max_len,
            "max_redraws": self.max_redraws,
            "mask_non_adjacent": self.mask_non_adjacent,
            "seed": seed,
        }
        self._network_mode = network is not None
        self._node_xy: dict[int, tuple[float, float]] = {}
        self._edge_nodes: dict[int, tuple[int, int]] = {}
        if network is not None:
            self.bbox: Bbox = self._build_network_index(network)
        else:
            assert bbox is not None
            self.bbox = _validated_bbox(bbox)
            self._params["bbox"] = list(self.bbox)  # network-mode params stay as before
        self._rng = np.random.default_rng(seed)
        self._fitted = False
        self._map_id = ""
        self.n_states = 0
        self.second_order_states: tuple[int, ...] = ()
        self._order1 = np.zeros((0, 0))
        self._order2: dict[int, np.ndarray] = {}
        # D-4.3 bookkeeping of the last generate() call; both are reset there.
        self.n_capped_walks = 0
        self.n_redrawn_walks = 0

    # -- public geometry ----------------------------------------------------------------

    def _build_network_index(self, network: RoadNetwork) -> Bbox:
        """Network mode: node coordinates, edge endpoints, and the projected nodes' bbox."""
        for row in network.nodes.itertuples(index=False):
            self._node_xy[int(row.node_id)] = (float(row.x), float(row.y))
        if not self._node_xy:
            raise ValueError("the road network has no nodes to span a bounding box")
        for row in network.edges.itertuples(index=False):
            self._edge_nodes[int(row.edge_id)] = (int(row.u), int(row.v))
        xs = [xy[0] for xy in self._node_xy.values()]
        ys = [xy[1] for xy in self._node_xy.values()]
        return _validated_bbox((min(xs), min(ys), max(xs), max(ys)))

    def points_of(self, seq: Sequence[int]) -> np.ndarray:
        """``(n, 2)`` node path of an edge-id sequence (network mode only).

        Every edge contributes its two endpoint nodes, and a node is not repeated when the
        previous edge already ended there, so a connected route yields one point per node.
        """
        if not self._network_mode:
            raise ValueError("points_of needs network mode; in bbox mode PrivTrace reads GPS")
        if len(seq) == 0:
            raise ValueError("cannot map an empty edge sequence to points")
        nodes: list[int] = []
        for edge_id in seq:
            pair = self._edge_nodes.get(int(edge_id))
            if pair is None:
                raise ValueError(f"edge {edge_id} is not part of this generator's road network")
            u, v = pair
            if not nodes or nodes[-1] != u:
                nodes.append(u)
            nodes.append(v)
        return np.array([self._node_xy[node] for node in nodes], dtype=np.float64)

    # -- estimation ---------------------------------------------------------------------

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Estimate the grid and the Markov models on the train split under central eps-DP."""
        splits = {v.split for v in train if v.split is not None}
        if splits - {"train"}:
            raise ValueError(
                f"PrivTraceGenerator fits on the train split only, got splits {sorted(splits)}"
            )
        map_ids: set[str] = set()
        points: list[np.ndarray] = []
        for view in train:
            map_ids.add(view.map_id)
            points.append(self._points_of_view(view))
        self.fit_points(points)
        self._map_id = next(iter(map_ids)) if len(map_ids) == 1 else ""

    def _points_of_view(self, view: TrajectoryView) -> np.ndarray:
        """``(n, 2)`` coordinates of one view: the node path, or ``(lon, lat)`` in bbox mode."""
        if self._network_mode:
            return self.points_of(view.as_sequence())
        if view.clean is None:
            raise ValueError(
                "PrivTraceGenerator in bbox mode needs raw coordinates, so the cells "
                "representation (a bare sequence of grid-cell indices) is not supported"
            )
        gps = view.as_gps()
        if not gps:
            raise ValueError("cannot fit on an empty trajectory")
        points = np.empty((len(gps), 2), dtype=np.float64)
        for i, (lat, lon, _) in enumerate(gps):
            points[i] = (lon, lat)
        return points

    def fit_points(self, points: Sequence[np.ndarray]) -> None:
        """Run the three budget stages on one ``(n, 2)`` coordinate array per trajectory.

        This is the entry point of the estimation pipeline: :meth:`fit` maps trajectory views
        onto it, and the validation harness calls it directly on raw coordinates.
        """
        n = len(points)
        if n == 0:
            raise ValueError("cannot fit PrivTraceGenerator on an empty trajectory set")
        eps1, eps2, eps3 = self.stage_epsilons
        k = self.first_level_k

        # Stage 1 (eps1): length-normalised level-1 densities, noised, repaired, subdivided.
        # The split gate is measured against the sum of the noisy vector, not against the true
        # trajectory count: post-processing of the stage-1 release only (D-4.1).
        density = level1_density(points, self.bbox, k)
        noisy_density = normcut(density + self._rng.laplace(0.0, 1.0 / eps1, k * k))
        self.grid = AdaptiveGrid.build(
            self.bbox,
            k,
            noisy_density,
            float(noisy_density.sum()),
            self.split_scale,
            self.split_gate,
            self.max_sub_k,
        )
        m = self.grid.n_states
        start, end = m + _START_OFFSET, m + _END_OFFSET
        seqs = [self.grid.sequence_of(trajectory) for trajectory in points]
        # D-4.6: the optional adjacency mask, read off the public grid geometry (no data, no
        # random draws), applied together with the structural zeros below.
        allowed = _adjacency_allowed(self.grid, m) if self.mask_non_adjacent else None

        # Stage 2 (eps2): the first-order matrix. Nothing can enter START or leave END, and
        # every trajectory has at least one state, so START -> END is impossible as well.
        order1 = _first_order_counts(seqs, m)
        order1 = order1 + self._rng.laplace(0.0, 1.0 / eps2, order1.shape)
        order1[:, start] = 0.0
        order1[end, :] = 0.0
        order1[start, end] = 0.0
        if allowed is not None:
            order1[~allowed] = 0.0
        order1 = _normcut_rows(order1)

        # Stage 3 (eps3): one [previous, next] matrix per adaptively selected state.
        selected = select_second_order_states(order1, m, eps2, self.theta2)
        entries = len(selected) * (m + _N_VIRTUAL) ** 2
        if entries > _MAX_SECOND_ORDER_CELLS:
            raise ValueError(
                f"the second-order model would need {entries:.3g} matrix entries "
                f"({len(selected)} selected states x ({m} + {_N_VIRTUAL})^2), above the "
                f"{_MAX_SECOND_ORDER_CELLS:.3g} cap; lower first_level_k "
                f"(now {self.first_level_k}) or max_sub_k (now {self.max_sub_k})"
            )
        self._order2 = self._fit_second_order(seqs, m, selected, eps3, allowed)

        self._order1 = order1
        self.n_states = m
        self.second_order_states = tuple(selected)
        self._fitted = True

    def _fit_second_order(
        self,
        seqs: Sequence[Sequence[int]],
        m: int,
        selected: Sequence[int],
        eps3: float,
        allowed: np.ndarray | None = None,
    ) -> dict[int, np.ndarray]:
        """Noisy ``[previous, next]`` matrix per selected state, built in ascending state order.

        The counts are gathered once over every position of every sequence and then sliced per
        state, and the Laplace draws follow the ascending state order, so the whole stage is
        deterministic in the constructor seed. The counts stay float64: the reference casts
        them to integers, which destroys every count below 1 and is not in the paper.

        ``allowed`` is the D-4.6 adjacency mask or None: when given, the matrix of state
        ``s`` keeps entry ``[p, n]`` only if ``p`` is START or a neighbour of ``s`` and ``n``
        is END or a neighbour of ``s``.
        """
        order2: dict[int, np.ndarray] = {}
        if not selected:
            return order2
        start, end = m + _START_OFFSET, m + _END_OFFSET
        size = m + _N_VIRTUAL
        current, previous, following, weight = _position_arrays(seqs, m)
        keep = np.isin(current, np.asarray(selected, dtype=np.int64))
        by_state = np.argsort(current[keep], kind="stable")
        current_s = current[keep][by_state]
        previous_s = previous[keep][by_state]
        following_s = following[keep][by_state]
        weight_s = weight[keep][by_state]
        for state in selected:
            lo = int(np.searchsorted(current_s, state, side="left"))
            hi = int(np.searchsorted(current_s, state, side="right"))
            matrix = np.zeros((size, size), dtype=np.float64)
            np.add.at(matrix, (previous_s[lo:hi], following_s[lo:hi]), weight_s[lo:hi])
            matrix = matrix + self._rng.laplace(0.0, 1.0 / eps3, matrix.shape)
            matrix[:, start] = 0.0
            matrix[end, :] = 0.0
            if allowed is not None:
                near = allowed[:m, :m]
                previous_ok = np.zeros(size, dtype=bool)
                previous_ok[:m] = near[:, state]
                previous_ok[start] = True  # a walk may always enter the state from START
                next_ok = np.zeros(size, dtype=bool)
                next_ok[:m] = near[state]
                next_ok[end] = True  # and may always end in it
                matrix[~(previous_ok[:, None] & next_ok[None, :])] = 0.0
            order2[state] = _normcut_rows(matrix)
        return order2

    def spent_budget(self) -> float | None:
        """Total eps spent by the three stages; None before fit.

        Per-trajectory central differential privacy with a trusted curator: neighbouring
        databases differ in one trajectory, so a user who contributed m trajectories is
        covered at m*eps by group privacy.
        """
        return self.epsilon if self._fitted else None

    # -- synthesis ----------------------------------------------------------------------

    def _start_probabilities(self) -> np.ndarray:
        """Start distribution over the ``m`` real states: the normalised noisy START row.

        NormCut can empty that row -- every entry of it may be paid out to cover the negative
        noise -- and then there is nothing left to sample a first state from, so the fallback
        is the uniform distribution over the ``m`` states. Synthesis and scoring both go
        through this method, so a walk that was generated under the fallback is scored under
        the same fallback. The result is a fresh array; no caller reaches into the fitted
        matrix.
        """
        weights = np.array(
            self._order1[self.n_states + _START_OFFSET, : self.n_states], dtype=np.float64
        )
        mass = float(weights.sum())
        if mass <= 0.0:
            return np.full(self.n_states, 1.0 / self.n_states)
        probabilities: np.ndarray = weights / mass
        return probabilities

    def _context_row(self, previous: int, current: int) -> np.ndarray:
        """Next-state weights of ``current``: its second-order row when usable, else first order.

        The second-order model of a selected state is used only when its row for this
        ``previous`` state still carries mass: the paper's rule selects a state once for all of
        its predecessors, and NormCut can empty an individual row, so the first-order row is
        the fallback. The result is a view into the fitted matrix and must not be modified.
        """
        second = self._order2.get(current)
        if second is not None:
            second_row: np.ndarray = second[previous]
            if float(second_row.sum()) > 0.0:
                return second_row
        first_row: np.ndarray = self._order1[current]
        return first_row

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n state-sequence trajectories (Algorithm 1), deterministic in ``seed``.

        The payload is the leaf-state sequence itself; states are not decoded back to
        coordinates (see the module docstring, "Synthesis and scoring").

        D-4.3's redraw guard: a walk that runs into the ``max_len`` cap without ever drawing END
        is discarded and drawn again from the same stream, at most ``max_redraws`` times; the
        last attempt is kept even when it is capped too. The call resets
        :attr:`n_redrawn_walks`, the number of walks it discarded, and :attr:`n_capped_walks`,
        the number of returned walks that are still capped.
        """
        if not self._fitted:
            raise RuntimeError("PrivTraceGenerator.generate called before fit()")
        rng = np.random.default_rng(seed)
        ph = params_hash({**self._params, "generate_seed": seed})
        self.n_capped_walks = 0
        self.n_redrawn_walks = 0
        return [
            SyntheticTrajectory(
                syn_id=f"privtrace/{seed}/{i}",
                generator_id="privtrace",
                params_hash=ph,
                payload=tuple(self._sample_walk_with_redraws(rng)),
                trained_on_split="train",
                map_id=self._map_id,
            )
            for i in range(n)
        ]

    def _sample_walk_with_redraws(self, rng: np.random.Generator) -> list[int]:
        """One walk under D-4.3: redraw while it hits the cap, at most ``max_redraws`` times.

        Every attempt draws from the same ``rng`` in turn, so with ``max_redraws = 0`` -- and
        whenever no attempt hits the cap -- the sequence of random draws is exactly the one
        :meth:`_sample_walk` produces on its own. The two counters are updated in place.
        """
        walk = self._sample_walk(rng)
        for _ in range(self.max_redraws):
            if len(walk) < self.max_len:
                return walk
            self.n_redrawn_walks += 1
            walk = self._sample_walk(rng)
        if len(walk) >= self.max_len:
            self.n_capped_walks += 1
        return walk

    def _sample_walk(self, rng: np.random.Generator) -> list[int]:
        """Start ~ the noisy START row, then adaptive steps until END, ``max_len`` or a dead end.

        START is never drawn again because its column is zero everywhere; an emptied START row
        falls back to the uniform start of :meth:`_start_probabilities`, exactly as scoring does.
        """
        start, end = self.n_states + _START_OFFSET, self.n_states + _END_OFFSET
        current = int(rng.choice(self.n_states, p=self._start_probabilities()))
        previous = start
        states = [current]
        while len(states) < self.max_len:
            row = self._context_row(previous, current)
            row_mass = float(row.sum())
            if row_mass <= 0.0:
                break  # dead end: the walk simply stops here
            pick = int(rng.choice(row.size, p=row / row_mass))
            if pick == end:
                break
            states.append(pick)
            previous, current = current, pick
        return states

    # -- likelihood hook for membership inference ---------------------------------------

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """log P(START -> s0) + sum log P(step) + log P(END | last state) under the fitted model.

        ``edge_seq`` is an input sequence in the generator's mode: matched edge ids in network
        mode, which become the node path and then leaf states, or a leaf-state sequence in bbox
        mode. The steps follow the same adaptive rule as synthesis and every factor is floored
        at 1e-12; there is no length term, so a caller that compares sequences of different
        lengths should divide by the number of states.
        """
        if not self._fitted:
            raise RuntimeError("PrivTraceGenerator.sequence_log_prob called before fit()")
        states = self._states_to_score(edge_seq)
        start, end = self.n_states + _START_OFFSET, self.n_states + _END_OFFSET
        first = float(self._start_probabilities()[states[0]])
        log_prob = math.log(max(first, _PROB_FLOOR))
        for i in range(1, len(states)):
            row = self._context_row(states[i - 2] if i >= 2 else start, states[i - 1])
            log_prob += math.log(max(_row_probability(row, states[i]), _PROB_FLOOR))
        last = self._context_row(states[-2] if len(states) >= 2 else start, states[-1])
        log_prob += math.log(max(_row_probability(last, end), _PROB_FLOOR))
        return log_prob

    def _states_to_score(self, seq: Sequence[int]) -> list[int]:
        """Leaf states of an input sequence: the node path in network mode, states in bbox mode."""
        if self._network_mode:
            return self.grid.sequence_of(self.points_of(seq))
        if len(seq) == 0:
            raise ValueError("cannot score an empty state sequence")
        states = [int(state) for state in seq]
        for state in states:
            if not 0 <= state < self.n_states:
                raise ValueError(
                    f"state {state} lies outside the {self.n_states} leaf states of this fit"
                )
        return states


def _validated_bbox(bbox: Sequence[float]) -> Bbox:
    """``(x0, y0, x1, y1)`` as floats; the span must be positive on both axes."""
    if len(bbox) != 4:
        raise ValueError(f"bbox needs 4 numbers (x0, y0, x1, y1), got {bbox}")
    x0, y0, x1, y1 = (float(v) for v in bbox)
    if not (x0 < x1 and y0 < y1):
        raise ValueError(f"bbox must satisfy min < max on both axes, got {bbox}")
    return (x0, y0, x1, y1)


def _adjacency_allowed(grid: AdaptiveGrid, n_states: int) -> np.ndarray:
    """D-4.6 mask: ``(m + 2, m + 2)`` booleans, True where a transition may keep its mass.

    Two real states may be connected when their level-1 cells are the same or 4-adjacent,
    i.e. when the Manhattan distance between the cells' ``(row, col)`` positions is at most 1;
    the diagonal (a state to itself) is always allowed. Everything that touches START or END
    stays True here, so the structural zeros applied next remain the only rule for the virtual
    states. The mask is built from the public grid geometry alone -- no data, no random draws.
    """
    cells = np.array([grid.state_level1(state) for state in range(n_states)], dtype=np.int64)
    rows, cols = cells // grid.k, cells % grid.k
    distance = np.abs(rows[:, None] - rows[None, :]) + np.abs(cols[:, None] - cols[None, :])
    allowed = np.ones((n_states + _N_VIRTUAL, n_states + _N_VIRTUAL), dtype=bool)
    allowed[:n_states, :n_states] = distance <= 1
    return allowed


def _first_order_counts(seqs: Sequence[Sequence[int]], n_states: int) -> np.ndarray:
    """Length-normalised first-order transition counts over the states plus START and END.

    A trajectory of ``L`` states makes ``L + 1`` transitions (START to its first state, the
    ``L - 1`` steps, its last state to END) and each carries ``1 / (L + 1)``, so every
    trajectory contributes exactly 1 and the L1 sensitivity of the matrix is 1.
    """
    start = n_states + _START_OFFSET
    end = n_states + _END_OFFSET
    size = n_states + _N_VIRTUAL
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    for seq in seqs:
        states = np.asarray(seq, dtype=np.int64)
        if states.size == 0:
            raise ValueError("cannot count the transitions of an empty state sequence")
        row = np.empty(states.size + 1, dtype=np.int64)
        row[0] = start
        row[1:] = states
        col = np.empty(states.size + 1, dtype=np.int64)
        col[:-1] = states
        col[-1] = end
        rows.append(row)
        cols.append(col)
        weights.append(np.full(states.size + 1, 1.0 / (states.size + 1)))
    matrix = np.zeros((size, size), dtype=np.float64)
    np.add.at(matrix, (np.concatenate(rows), np.concatenate(cols)), np.concatenate(weights))
    return matrix


def _position_arrays(
    seqs: Sequence[Sequence[int]], n_states: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Flat ``(current, previous, following, weight)`` arrays over every position of every seq.

    ``previous`` is START at the first position and ``following`` is END at the last one; the
    weight is ``1 / L`` for a sequence of ``L`` states, so one trajectory again contributes 1
    in total across all the second-order matrices together.
    """
    start = n_states + _START_OFFSET
    end = n_states + _END_OFFSET
    current: list[np.ndarray] = []
    previous: list[np.ndarray] = []
    following: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    for seq in seqs:
        states = np.asarray(seq, dtype=np.int64)
        if states.size == 0:
            raise ValueError("cannot count the transitions of an empty state sequence")
        before = np.empty(states.size, dtype=np.int64)
        before[0] = start
        before[1:] = states[:-1]
        after = np.empty(states.size, dtype=np.int64)
        after[:-1] = states[1:]
        after[-1] = end
        current.append(states)
        previous.append(before)
        following.append(after)
        weights.append(np.full(states.size, 1.0 / states.size))
    return (
        np.concatenate(current),
        np.concatenate(previous),
        np.concatenate(following),
        np.concatenate(weights),
    )


def _normcut_rows(matrix: np.ndarray) -> np.ndarray:
    """:func:`normcut` applied row by row, as the reference does after every Laplace stage."""
    return np.stack([normcut(row) for row in matrix])


def _row_probability(row: np.ndarray, index: int) -> float:
    """``row[index] / row.sum()``, and 0.0 when the row carries no mass at all."""
    mass = float(row.sum())
    return float(row[index]) / mass if mass > 0.0 else 0.0
