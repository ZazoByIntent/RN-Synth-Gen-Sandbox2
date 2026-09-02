"""LDPTrace (Du et al., PVLDB 2023): grid-cell trajectory synthesis under per-trajectory ε-LDP.

Baseline candidate for the benchmark — the paper's baseline set (decision D5 in the
sibling project "Izbirni predmeti") is still open, so nothing here is a fixed choice.
Reference implementation: github.com/zealscott/LDPTrace (Apache-2.0).

Mechanism. Space is a uniform ``n_rows × n_cols`` grid; a trajectory is a chain of
8-connected cells. Every (simulated) device sends only Optimized Unary Encoding
(OUE, ``privacy/ldp.py``) reports, in two collection rounds:

1. **Length round** — the trajectory length in cells, one OUE report over the domain
   ``N = n_rows·n_cols`` (index ``len − 1``, longer trajectories capped at ``N``),
   budget ``ε·length_share``. The collector turns the noisy length histogram into the
   length cap ``L_k``: the ``quantile`` point of the *unclipped* debiased estimate,
   exactly the reference code's rule (negatives kept in the total and the cumulative
   sum; fallback ``N`` when the threshold is never reached).
2. **Markov round** — the start cell (domain ``N``), every transition among the first
   ``L_k`` cells (domain ``8·N``, index ``cell·8 + direction slot``) and the end cell
   (domain ``N``), each report at ``ε·(1 − length_share)/(L_k + 1)``. A trajectory
   sends at most ``L_k + 1`` such reports, so sequential composition bounds its total
   spend by ``ε``.

**ε unit: per trajectory, i.e. per device release** (one trajectory per user in the
paper's model). It is not comparable with geo-indistinguishability's per-point ε.

The collector debiases the bit sums, drops estimates ≤ 0, and normalises each cell's
row over its eight neighbours plus a virtual *end* state (``row / (Σrow + 1e-8)``).
Synthesis follows the paper's Algorithm 1: start ~ start estimate, length ``L`` ~ the
clipped noisy length histogram, then a walk whose end weight is scaled by
``min(1, alpha + beta·(l − 1))`` (``l`` = cells generated so far); it stops at the
virtual end, at ``L`` cells, or at a dead end (candidate mass below 1e-5).

Deviations from the public code, all deliberate:

- Cells come from the **public road network**: each matched edge maps to the cells of
  its endpoint nodes (grid over the bounding box of the network's nodes, not of the
  raw GPS points), so ``fit`` and ``sequence_log_prob`` score the same domain as
  ``rn_ldp_synth`` and the membership attack compares like with like.
- The end report carries the **true last cell** of the trajectory (as in the paper),
  even when the transition reports stop at ``L_k``; the public code reports the cell
  at the cut. The budget is identical either way.
- OUE debiasing divides by the number of reports actually summed per domain (one per
  trajectory for start/end/length, the total transition count for transitions).
- The payload is the cell sequence itself (no decoding to coordinates or edges).
- All-zero start or length estimates fall back to uniform instead of failing.
"""

import itertools
import math
from collections.abc import Sequence

import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.base import params_hash
from trajguard.privacy.ldp import oue_estimate, oue_perturb
from trajguard.representation import TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator

_PROB_FLOOR = 1e-12  # keeps sequence_log_prob finite after clipped-to-zero estimates
_ROW_SMOOTHING = 1e-8  # reference code: row / (row.sum() + 1e-8)
_DEAD_END_MASS = 1e-5  # reference code: stop the walk when candidate weights sum below this
# Direction slots in the reference order; report index = cell * 8 + slot.
_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)
_SLOT_OF: dict[tuple[int, int], int] = {d: i for i, d in enumerate(_DIRECTIONS)}
_N_SLOTS = len(_DIRECTIONS)
_END = _N_SLOTS  # column of the virtual end state in a row vector


@register("generator", "ldptrace")
class LDPTraceGenerator(SyntheticGenerator):
    """Grid-cell synthesis from per-trajectory ε-LDP OUE reports (LDPTrace, Du et al. 2023).

    All stochastic steps draw from seeded ``np.random.Generator``s: the constructor
    seed drives the device-side randomizers in :meth:`fit` (reproducibility only —
    deployed devices use local entropy), :meth:`generate` is deterministic in its own
    seed. See the module docstring for the mechanism, the ε unit and the deviations
    from the reference code.
    """

    def __init__(
        self,
        network: RoadNetwork,
        epsilon: float = 1.0,
        n_rows: int = 12,
        n_cols: int = 12,
        quantile: float = 0.9,
        length_share: float = 0.1,
        alpha: float = 0.3,
        beta: float = 0.2,
        seed: int = 0,
    ) -> None:
        """Build the public grid and edge→cell tables from the network; no data is touched."""
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if n_rows < 2 or n_cols < 2:
            raise ValueError(f"grid must be >= 2x2, got {n_rows}x{n_cols}")
        if not 0.0 < quantile <= 1.0:
            raise ValueError(f"quantile must be in (0, 1], got {quantile}")
        if not 0.0 < length_share < 1.0:
            raise ValueError(f"length_share must be in (0, 1), got {length_share}")
        if alpha < 0 or beta < 0:
            raise ValueError(f"alpha and beta must be >= 0, got {alpha}, {beta}")
        self.epsilon = float(epsilon)
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_cells = n_rows * n_cols
        self.quantile = float(quantile)
        self.length_share = float(length_share)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.seed = seed
        self._params = {
            "epsilon": self.epsilon,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "quantile": self.quantile,
            "length_share": self.length_share,
            "alpha": self.alpha,
            "beta": self.beta,
            "seed": seed,
        }
        self._build_public_structures(network)
        self._rng = np.random.default_rng(seed)
        self._fitted = False
        self._map_id = ""
        self._n_encoded = 0
        self.l_k = 0  # length cap after fit
        self.report_epsilon: float | None = None  # per-report budget of the Markov round
        self._len_raw = np.array([])  # unclipped length estimate (quantile rule input)
        self._lam = np.array([])  # length distribution over {1..N} (index = len − 1)
        self._pi = np.array([])  # start-cell distribution
        self._rows = np.zeros((0, _N_SLOTS + 1))  # per cell: 8 neighbour slots + end

    # -- public grid structures ----------------------------------------------------

    def _build_public_structures(self, network: RoadNetwork) -> None:
        """Grid bbox, edge → (cell_u, cell_v) and the 8-neighbour table — from the map only."""
        node_xy: dict[int, tuple[float, float]] = {}
        for row in network.nodes.itertuples(index=False):
            node_xy[int(row.node_id)] = (float(row.x), float(row.y))
        xs = [xy[0] for xy in node_xy.values()]
        ys = [xy[1] for xy in node_xy.values()]
        self._x0, self._x1 = min(xs), max(xs)
        self._y0, self._y1 = min(ys), max(ys)
        self._edge_cells: dict[int, tuple[int, int]] = {}
        for row in network.edges.itertuples(index=False):
            u_xy, v_xy = node_xy[int(row.u)], node_xy[int(row.v)]
            self._edge_cells[int(row.edge_id)] = (self._cell(*u_xy), self._cell(*v_xy))
        # targets[cell, slot] = neighbour cell in that direction, −1 when off the grid.
        targets = np.full((self.n_cells, _N_SLOTS), -1, dtype=np.int64)
        for cell in range(self.n_cells):
            r, c = divmod(cell, self.n_cols)
            for slot, (dr, dc) in enumerate(_DIRECTIONS):
                rr, cc = r + dr, c + dc
                if 0 <= rr < self.n_rows and 0 <= cc < self.n_cols:
                    targets[cell, slot] = rr * self.n_cols + cc
        self._targets = targets

    def _cell(self, x: float, y: float) -> int:
        """Row-major grid cell of a projected point; border points clamp inward."""
        col = min(int((x - self._x0) / (self._x1 - self._x0 + 1e-9) * self.n_cols), self.n_cols - 1)
        row = min(int((y - self._y0) / (self._y1 - self._y0 + 1e-9) * self.n_rows), self.n_rows - 1)
        return row * self.n_cols + col

    def _slot(self, a: int, b: int) -> int:
        """Direction slot of the step a → b; raises for non-adjacent cells."""
        ra, ca = divmod(a, self.n_cols)
        rb, cb = divmod(b, self.n_cols)
        slot = _SLOT_OF.get((rb - ra, cb - ca))
        if slot is None:
            raise ValueError(f"cells {a} and {b} are not 8-adjacent")
        return slot

    def _king_walk(self, a: int, b: int) -> list[int]:
        """Cells strictly between a and b on the reference greedy king's-move walk.

        Each step moves the row toward the target if it differs and the column toward
        the target if it differs (diagonal first, then straight), as in the reference
        ``GridMap.find_shortest_path``.
        """
        r, c = divmod(a, self.n_cols)
        rb, cb = divmod(b, self.n_cols)
        out: list[int] = []
        while True:
            if r != rb:
                r += 1 if rb > r else -1
            if c != cb:
                c += 1 if cb > c else -1
            if (r, c) == (rb, cb):
                return out
            out.append(r * self.n_cols + c)

    def cell_sequence(self, edge_seq: Sequence[int]) -> list[int]:
        """8-connected cell chain of an edge sequence, no consecutive duplicates."""
        cells: list[int] = []
        for eid in edge_seq:
            pair = self._edge_cells.get(int(eid))
            if pair is None:
                raise ValueError(f"edge {eid} is not part of this generator's road network")
            for cell in pair:
                if not cells or cells[-1] != cell:
                    cells.append(cell)
        chain: list[int] = []
        for cell in cells:
            if chain and not self._adjacent(chain[-1], cell):
                chain.extend(self._king_walk(chain[-1], cell))
            chain.append(cell)
        return chain

    def _adjacent(self, a: int, b: int) -> bool:
        """True when b is one of a's eight grid neighbours."""
        ra, ca = divmod(a, self.n_cols)
        rb, cb = divmod(b, self.n_cols)
        return (rb - ra, cb - ca) in _SLOT_OF

    # -- device simulation + aggregation --------------------------------------------

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Two OUE collection rounds over the simulated devices; keep only the aggregates."""
        splits = {v.split for v in train if v.split is not None}
        if splits - {"train"}:
            raise ValueError(
                f"LDPTraceGenerator fits on the train split only, got splits {sorted(splits)}"
            )
        n_cells = self.n_cells
        seqs: list[list[int]] = []
        map_ids: set[str] = set()
        for view in train:
            cells = self.cell_sequence(view.as_segments())
            if not cells:
                raise ValueError("cannot encode an empty trajectory")
            map_ids.add(view.map_id)
            seqs.append(cells)
        n = len(seqs)

        # Round 1: one length report per trajectory, then the public length cap L_k.
        eps_len = self.epsilon * self.length_share
        len_sums = np.zeros(n_cells)
        for cells in seqs:
            len_sums += oue_perturb(min(len(cells), n_cells) - 1, n_cells, eps_len, self._rng)
        self._len_raw = oue_estimate(len_sums, n, eps_len, clip=False)
        self.l_k = _quantile_length(self._len_raw, self.quantile)
        self._lam = _normalized(np.clip(self._len_raw, 0.0, None))

        # Round 2: start, up to L_k − 1 transitions and the true end cell per trajectory.
        eps_r = self.epsilon * (1.0 - self.length_share) / (self.l_k + 1)
        self.report_epsilon = eps_r
        start_sums = np.zeros(n_cells)
        end_sums = np.zeros(n_cells)
        trans_sums = np.zeros(n_cells * _N_SLOTS)
        n_trans = 0
        for cells in seqs:
            start_sums += oue_perturb(cells[0], n_cells, eps_r, self._rng)
            for i in range(min(len(cells), self.l_k) - 1):
                idx = cells[i] * _N_SLOTS + self._slot(cells[i], cells[i + 1])
                trans_sums += oue_perturb(idx, n_cells * _N_SLOTS, eps_r, self._rng)
                n_trans += 1
            end_sums += oue_perturb(cells[-1], n_cells, eps_r, self._rng)

        # Aggregation: clipped estimates (≤ 0 dropped), rows over neighbours + end.
        self._pi = _normalized(oue_estimate(start_sums, n, eps_r))
        end_est = oue_estimate(end_sums, n, eps_r)
        trans_est = oue_estimate(trans_sums, n_trans, eps_r).reshape(n_cells, _N_SLOTS)
        trans_est[self._targets < 0] = 0.0  # off-grid slots carry noise only
        rows = np.concatenate([trans_est, end_est[:, None]], axis=1)
        self._rows = rows / (rows.sum(axis=1, keepdims=True) + _ROW_SMOOTHING)
        self._map_id = next(iter(map_ids)) if len(map_ids) == 1 else ""
        self._n_encoded = n
        self._fitted = True

    def spent_budget(self) -> float | None:
        """Per-trajectory (per-device) ε spent by the on-device reports; None before fit.

        Devices randomize in parallel — budgets do not sum across users. A user
        contributing m trajectories spends m·ε of their own budget.
        """
        return self.epsilon if self._fitted else None

    # -- synthesis --------------------------------------------------------------------

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n cell-sequence trajectories (Algorithm 1), deterministic in ``seed``."""
        if not self._fitted:
            raise RuntimeError("LDPTraceGenerator.generate called before fit()")
        rng = np.random.default_rng(seed)
        ph = params_hash({**self._params, "generate_seed": seed})
        return [
            SyntheticTrajectory(
                syn_id=f"ldptrace/{seed}/{i}",
                generator_id="ldptrace",
                params_hash=ph,
                payload=tuple(self._sample_walk(rng)),
                trained_on_split="train",
                map_id=self._map_id,
            )
            for i in range(n)
        ]

    def _sample_walk(self, rng: np.random.Generator) -> list[int]:
        """Start ~ π, length ~ λ, then neighbour/end steps with the α+β·(l−1) end scaling."""
        current = int(rng.choice(self.n_cells, p=self._pi))
        length = int(rng.choice(self.n_cells, p=self._lam)) + 1
        cells = [current]
        for _ in range(1, length):
            weights = self._rows[current].copy()
            weights[_END] *= min(1.0, self.alpha + self.beta * (len(cells) - 1))
            mass = float(weights.sum())
            if mass < _DEAD_END_MASS:
                break
            pick = int(rng.choice(_N_SLOTS + 1, p=weights / mass))
            if pick == _END:
                break
            current = int(self._targets[current, pick])
            cells.append(current)
        return cells

    # -- likelihood hook for membership inference ------------------------------------

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """log P(start) + Σ log P(transition) + log P(end | last cell) under the aggregates.

        No α/β end scaling (that is a generation rule, not part of the estimated
        model) and no length term; every factor is floored at 1e-12.
        """
        if not self._fitted:
            raise RuntimeError("LDPTraceGenerator.sequence_log_prob called before fit()")
        cells = self.cell_sequence(edge_seq)
        if not cells:
            raise ValueError("cannot score an empty trajectory")
        lp = math.log(max(float(self._pi[cells[0]]), _PROB_FLOOR))
        for a, b in itertools.pairwise(cells):
            lp += math.log(max(float(self._rows[a, self._slot(a, b)]), _PROB_FLOOR))
        lp += math.log(max(float(self._rows[cells[-1], _END]), _PROB_FLOOR))
        return lp


def _quantile_length(raw_estimate: np.ndarray, quantile: float) -> int:
    """Reference length-cap rule on the UNCLIPPED estimate over lengths 1..d.

    ``total`` and the running sum keep negative entries; the first index whose running
    sum reaches ``quantile·total`` gives the cap ``index + 1``; fallback ``d``.
    """
    total = float(raw_estimate.sum())
    running = 0.0
    for i, value in enumerate(raw_estimate):
        running += float(value)
        if running >= quantile * total:
            return i + 1
    return len(raw_estimate)


def _normalized(values: np.ndarray) -> np.ndarray:
    """Values scaled to a probability vector; uniform when the mass is zero."""
    total = float(values.sum())
    if total <= 0:
        return np.full(len(values), 1.0 / len(values))
    result: np.ndarray = values / total
    return result
