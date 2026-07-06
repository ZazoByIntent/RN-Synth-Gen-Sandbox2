"""RN-LDP-Synth: road-network-constrained trajectory synthesis under per-trajectory ε-LDP.

Mechanism (full design + proof sketch: docs/RN_LDP_SYNTH_DESIGN.md): public,
map-derived structures — a road-masked zone grid in projected metres, the zone
digraph of road-feasible zone transitions, the largest strongly-connected
component for decoding — are built from the ``RoadNetwork`` and config alone.
``fit`` simulates the devices: each training trajectory is reduced to (start
zone, end zone, clipped transition count, ONE uniformly sampled zone
transition) and randomized on the spot with GRR/GRR/GRR/OUE under the split
budget ε = ε_s+ε_e+ε_ℓ+ε_t; only the aggregated noisy reports are retained.
``generate`` walks the zone digraph from the debiased estimates (reachability-
guided toward a sampled end zone) and decodes each zone path into a connected
edge sequence by stitching SCC-restricted representative edges with shortest
paths on the real graph — feasibility is structural, not statistical.
"""

import itertools
import math
from collections import deque
from collections.abc import Sequence

import networkx as nx
import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.base import params_hash
from trajguard.privacy.ldp import grr_estimate, grr_perturb, oue_estimate, oue_perturb
from trajguard.representation import TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator

_PROB_FLOOR = 1e-12  # keeps sequence_log_prob finite after clipped-to-zero estimates
_ENTRY_CHOICES = 3  # nearest zone-entry nodes sampled from during decoding
_UNREACHABLE = 10**9


@register("generator", "rn_ldp_synth")
class RNLDPSynthGenerator(SyntheticGenerator):
    """Zone-walk synthesis from per-trajectory ε-LDP reports over a public road-zone digraph.

    All stochastic steps draw from seeded ``np.random.Generator``s: the
    constructor seed drives the device-side randomizers in :meth:`fit` (the
    seed is for reproducibility only and confers no privacy — deployed devices
    use local entropy), and :meth:`generate` is deterministic in its own seed.
    """

    def __init__(
        self,
        network: RoadNetwork,
        epsilon: float = 1.0,
        n_rows: int = 12,
        n_cols: int = 12,
        l_max: int = 24,
        budget_split: tuple[float, float, float, float] = (0.15, 0.15, 0.2, 0.5),
        seed: int = 0,
    ) -> None:
        """Build the public zone structures from the network; nothing here touches data."""
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if n_rows < 1 or n_cols < 1:
            raise ValueError(f"grid must be >= 1x1, got {n_rows}x{n_cols}")
        if l_max < 1:
            raise ValueError(f"l_max must be >= 1, got {l_max}")
        if len(budget_split) != 4 or any(w <= 0 for w in budget_split):
            raise ValueError(f"budget_split needs 4 positive weights, got {budget_split}")
        self.epsilon = float(epsilon)
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.l_max = l_max
        total = float(sum(budget_split))
        self.stage_epsilons: tuple[float, float, float, float] = (
            epsilon * budget_split[0] / total,
            epsilon * budget_split[1] / total,
            epsilon * budget_split[2] / total,
            epsilon * budget_split[3] / total,
        )
        self.seed = seed
        self._params = {
            "epsilon": self.epsilon,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "l_max": l_max,
            "budget_split": list(budget_split),
            "seed": seed,
        }
        self._graph = network.graph
        self.last_decode_truncations = 0
        self._build_public_structures(network)
        # Decoding stretches a k-step zone walk into more than k projected zone
        # transitions (entering a zone lands away from the next boundary). The factor
        # is a property of the public structures alone, so it is measured once on
        # public uniform-kernel walks (fixed seed) and costs no privacy budget.
        self._inflation = self._calibrate_inflation()
        self.last_decode_truncations = 0
        self._rng = np.random.default_rng(seed)
        self._fitted = False
        self._map_id = ""
        self._pi = np.array([])  # start-zone distribution
        self._eta = np.array([])  # end-zone distribution
        self._lam = np.array([])  # transition-count distribution over {0..l_max}
        self._trans = np.array([])  # arc-frequency estimates over the arc list
        self._row_probs: dict[int, np.ndarray] = {}
        self._n_encoded = 0

    # -- public map structures ----------------------------------------------------

    def _build_public_structures(self, network: RoadNetwork) -> None:
        """Zones, zone digraph, SCC and lookup tables — from map + config only."""
        node_xy: dict[int, tuple[float, float]] = {}
        for row in network.nodes.itertuples(index=False):
            node_xy[int(row.node_id)] = (float(row.x), float(row.y))
        xs = [xy[0] for xy in node_xy.values()]
        ys = [xy[1] for xy in node_xy.values()]
        self._x0, self._x1 = min(xs), max(xs)
        self._y0, self._y1 = min(ys), max(ys)

        # Edge table: endpoints, length, zone of the projected midpoint.
        self._edge_ends: dict[int, tuple[int, int]] = {}
        edge_len: dict[int, float] = {}
        cell_of_edge: dict[int, int] = {}
        pair_best: dict[tuple[int, int], int] = {}  # (u, v) -> edge_id, parallel-collapsed
        for row in network.edges.itertuples(index=False):
            eid, u, v = int(row.edge_id), int(row.u), int(row.v)
            length = float(row.length_m)
            self._edge_ends[eid] = (u, v)
            edge_len[eid] = length
            mx = (node_xy[u][0] + node_xy[v][0]) / 2.0
            my = (node_xy[u][1] + node_xy[v][1]) / 2.0
            cell_of_edge[eid] = self._cell(mx, my)
            best = pair_best.get((u, v))
            if best is None or length < edge_len[best]:
                pair_best[(u, v)] = eid
        self._pair_edge = pair_best

        # Dense zone ids over occupied cells only.
        occupied = sorted(set(cell_of_edge.values()))
        cell_zone = {cell: z for z, cell in enumerate(occupied)}
        self.n_zones = len(occupied)
        self.edge_zone: dict[int, int] = {e: cell_zone[c] for e, c in cell_of_edge.items()}

        # Zone digraph: arc i->j iff consecutive edge traversal crosses zones i->j.
        edges_by_tail: dict[int, list[int]] = {}
        for eid, (u, _v) in self._edge_ends.items():
            edges_by_tail.setdefault(u, []).append(eid)
        arcs: set[tuple[int, int]] = set()
        for eid, (_u, v) in self._edge_ends.items():
            zi = self.edge_zone[eid]
            for nxt in edges_by_tail.get(v, ()):
                zj = self.edge_zone[nxt]
                if zi != zj:
                    arcs.add((zi, zj))
        self.zone_arcs: tuple[tuple[int, int], ...] = tuple(sorted(arcs))
        if not self.zone_arcs:
            raise ValueError(
                "network collapses into a single zone; increase n_rows/n_cols"
            )
        self._arc_index = {arc: i for i, arc in enumerate(self.zone_arcs)}
        self._out_arcs: dict[int, list[tuple[int, int]]] = {}  # zone -> [(arc_idx, target)]
        for idx, (i, j) in enumerate(self.zone_arcs):
            self._out_arcs.setdefault(i, []).append((idx, j))

        # Hop distances zone -> zone on the zone digraph (for reachability-guided walks).
        fwd: dict[int, list[int]] = {}
        for i, j in self.zone_arcs:
            fwd.setdefault(i, []).append(j)
        self._hops = np.full((self.n_zones, self.n_zones), _UNREACHABLE, dtype=np.int64)
        for src in range(self.n_zones):
            self._hops[src, src] = 0
            queue = deque([src])
            while queue:
                cur = queue.popleft()
                for nxt in fwd.get(cur, ()):
                    if self._hops[src, nxt] == _UNREACHABLE:
                        self._hops[src, nxt] = self._hops[src, cur] + 1
                        queue.append(nxt)

        # Decode support: per zone, the edges a walk can start from (length-weighted, for
        # the first zone) and the entry map tail-node -> best zone edge starting there
        # (for routing into each subsequent zone). Both prefer edges lying in the largest
        # strongly-connected component so a decoded walk keeps outgoing options.
        scc: set[int] = max(nx.strongly_connected_components(self._graph), key=len)
        zone_edges: dict[int, list[int]] = {}
        zone_scc_edges: dict[int, list[int]] = {}
        for eid, (u, v) in self._edge_ends.items():
            z = self.edge_zone[eid]
            zone_edges.setdefault(z, []).append(eid)
            if u in scc and v in scc:
                zone_scc_edges.setdefault(z, []).append(eid)
        self._zone_reps: dict[int, tuple[list[int], np.ndarray]] = {}
        self._zone_tails: dict[int, dict[int, int]] = {}
        for z in range(self.n_zones):
            reps = zone_scc_edges.get(z) or zone_edges[z]
            weights = np.array([edge_len[e] for e in reps], dtype=float)
            # _normalized guards the all-zero-length case (OSM loop/connector artifacts),
            # which would otherwise store NaN probabilities and crash rng.choice later.
            self._zone_reps[z] = (reps, _normalized(weights))
            tails: dict[int, int] = {}
            for eid in reps:
                u = self._edge_ends[eid][0]
                if u not in tails or edge_len[eid] < edge_len[tails[u]]:
                    tails[u] = eid
            self._zone_tails[z] = tails

    def _cell(self, x: float, y: float) -> int:
        """Row-major grid cell of a projected point; border points clamp inward."""
        col = min(int((x - self._x0) / (self._x1 - self._x0 + 1e-9) * self.n_cols), self.n_cols - 1)
        row = min(int((y - self._y0) / (self._y1 - self._y0 + 1e-9) * self.n_rows), self.n_rows - 1)
        return row * self.n_cols + col

    def zone_sequence(self, edge_seq: Sequence[int]) -> list[int]:
        """Zone path of an edge sequence (consecutive duplicates collapsed)."""
        zones: list[int] = []
        for eid in edge_seq:
            z = self.edge_zone.get(int(eid))
            if z is None:
                raise ValueError(f"edge {eid} is not part of this generator's road network")
            if not zones or zones[-1] != z:
                zones.append(z)
        return zones

    # -- device simulation + aggregation --------------------------------------------

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Encode+randomize each training trajectory on the simulated device; keep aggregates."""
        splits = {v.split for v in train if v.split is not None}
        if splits - {"train"}:
            raise ValueError(
                f"RNLDPSynthGenerator fits on the train split only, got splits {sorted(splits)}"
            )
        eps_s, eps_e, eps_l, eps_t = self.stage_epsilons
        n_arcs = len(self.zone_arcs)
        start_counts = np.zeros(self.n_zones)
        end_counts = np.zeros(self.n_zones)
        len_counts = np.zeros(self.l_max + 1)
        bit_sums = np.zeros(n_arcs)
        map_ids: set[str] = set()
        n = 0
        for view in train:
            zseq = self.zone_sequence(view.as_segments())
            if not zseq:
                raise ValueError("cannot encode an empty trajectory")
            map_ids.add(view.map_id)
            # Exactly four fixed-shape reports per trajectory; raw features are dropped.
            transitions = list(itertools.pairwise(zseq))
            if transitions:
                arc = transitions[int(self._rng.integers(len(transitions)))]
                t_idx = self._arc_index[arc]
            else:
                t_idx = int(self._rng.integers(n_arcs))
            start_counts[grr_perturb(zseq[0], self.n_zones, eps_s, self._rng)] += 1
            end_counts[grr_perturb(zseq[-1], self.n_zones, eps_e, self._rng)] += 1
            clipped = min(len(zseq) - 1, self.l_max)
            len_counts[grr_perturb(clipped, self.l_max + 1, eps_l, self._rng)] += 1
            bit_sums += oue_perturb(t_idx, n_arcs, eps_t, self._rng)
            n += 1

        self._pi = _normalized(grr_estimate(start_counts, n, eps_s))
        self._eta = _normalized(grr_estimate(end_counts, n, eps_e))
        self._lam = _normalized(grr_estimate(len_counts, n, eps_l))
        self._trans = oue_estimate(bit_sums, n, eps_t)
        self._row_probs = {
            zone: _normalized(np.array([self._trans[a] for a, _ in outs]))
            for zone, outs in self._out_arcs.items()
        }
        self._map_id = next(iter(map_ids)) if len(map_ids) == 1 else ""
        self._n_encoded = n
        self._fitted = True

    def spent_budget(self) -> float | None:
        """Per-trajectory (per-device) ε spent by the on-device encoder; None before fit.

        Devices randomize in parallel — budgets do not sum across users. A user
        contributing m trajectories spends m·ε of their own budget (see design doc).
        """
        return self.epsilon if self._fitted else None

    # -- synthesis --------------------------------------------------------------------

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n road-constrained synthetic trajectories, deterministic in ``seed``."""
        if not self._fitted:
            raise RuntimeError("RNLDPSynthGenerator.generate called before fit()")
        rng = np.random.default_rng(seed)
        ph = params_hash({**self._params, "generate_seed": seed})
        self.last_decode_truncations = 0
        out: list[SyntheticTrajectory] = []
        for i in range(n):
            target = int(rng.choice(self.l_max + 1, p=self._lam))
            steps = 0 if target == 0 else max(1, round(target / self._inflation))
            walk = self._sample_walk(rng, steps, self._pi, self._eta, self._row_probs)
            edge_path = self._decode(walk, rng)
            out.append(
                SyntheticTrajectory(
                    syn_id=f"rn_ldp_synth/{seed}/{i}",
                    generator_id="rn_ldp_synth",
                    params_hash=ph,
                    payload=tuple(edge_path),
                    trained_on_split="train",
                    map_id=self._map_id,
                )
            )
        return out

    def _sample_walk(
        self,
        rng: np.random.Generator,
        steps: int,
        pi: np.ndarray,
        eta: np.ndarray,
        rows: dict[int, np.ndarray],
    ) -> list[int]:
        """Reachability-guided zone walk: start ~ pi, end ~ eta, transitions ~ rows."""
        z = int(rng.choice(self.n_zones, p=pi))
        z_end = int(rng.choice(self.n_zones, p=eta))
        walk = [z]
        for step in range(steps):
            outs = self._out_arcs.get(z)
            if not outs:
                break
            probs = rows[z]
            remaining = steps - step
            keep = [
                k for k, (_a, j) in enumerate(outs) if self._hops[j, z_end] <= remaining - 1
            ]
            if keep:
                sub = probs[keep]
                idx = keep[int(rng.choice(len(keep), p=_normalized(sub)))]
            else:
                idx = int(rng.choice(len(outs), p=probs))
            z = outs[idx][1]
            walk.append(z)
        return walk

    def _calibrate_inflation(self) -> float:
        """Mean decode stretch, measured on public uniform-kernel walks (no private data)."""
        rng = np.random.default_rng(0)  # fixed public seed: this is part of the public setup
        uniform = np.full(self.n_zones, 1.0 / self.n_zones)
        rows = {z: np.full(len(outs), 1.0 / len(outs)) for z, outs in self._out_arcs.items()}
        ratios: list[float] = []
        for i in range(24):
            steps = 1 + i % self.l_max
            walk = self._sample_walk(rng, steps, uniform, uniform, rows)
            if len(walk) < 2:
                continue
            decoded = self._decode(walk, rng)
            projected = len(self.zone_sequence(decoded)) - 1
            ratios.append(projected / (len(walk) - 1))
        return max(1.0, float(np.mean(ratios))) if ratios else 1.0

    def _decode(self, walk: list[int], rng: np.random.Generator) -> list[int]:
        """Zone path -> connected edge sequence: nearest-entry routing on the real graph."""
        first = self._sample_rep(walk[0], rng)
        edges = [first]
        current = self._edge_ends[first][1]
        for zone in walk[1:]:
            step = self._route_into_zone(current, zone, rng)
            if step is None:
                self.last_decode_truncations += 1
                break
            edges.extend(step)
            current = self._edge_ends[step[-1]][1]
        return edges

    def _route_into_zone(
        self, current: int, zone: int, rng: np.random.Generator
    ) -> list[int] | None:
        """Stitch edges from ``current`` to a near entry of ``zone`` plus one zone edge.

        Reachability is exact (Dijkstra from ``current``); the entry is sampled among
        the nearest reachable zone tails to keep decoded trips close to the sampled
        zone walk while retaining within-zone variety. None when the zone is
        unreachable — the caller truncates the walk (counted).
        """
        dlens = nx.single_source_dijkstra_path_length(self._graph, current, weight="length")
        tails = self._zone_tails[zone]
        reach = sorted((float(dlens[t]), t) for t in tails if t in dlens)
        if not reach:
            return None
        _, tail = reach[int(rng.integers(min(_ENTRY_CHOICES, len(reach))))]
        node_path = nx.shortest_path(self._graph, current, tail, weight="length")
        step = [self._pair_edge[(a, b)] for a, b in itertools.pairwise(node_path)]
        step.append(tails[tail])
        return step

    def _sample_rep(self, zone: int, rng: np.random.Generator) -> int:
        """One representative edge of a zone, weighted by public edge length."""
        reps, weights = self._zone_reps[zone]
        return reps[int(rng.choice(len(reps), p=weights))]

    # -- likelihood hook for membership inference ------------------------------------

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """Zone-projected log-likelihood of an edge sequence under the fitted estimates."""
        if not self._fitted:
            raise RuntimeError("RNLDPSynthGenerator.sequence_log_prob called before fit()")
        zseq = self.zone_sequence(edge_seq)
        if not zseq:
            raise ValueError("cannot score an empty trajectory")
        lp = math.log(max(float(self._pi[zseq[0]]), _PROB_FLOOR))
        lp += math.log(max(float(self._eta[zseq[-1]]), _PROB_FLOOR))
        lp += math.log(max(float(self._lam[min(len(zseq) - 1, self.l_max)]), _PROB_FLOOR))
        for a, b in itertools.pairwise(zseq):
            outs = self._out_arcs.get(a, [])
            probs = self._row_probs.get(a)
            p = _PROB_FLOOR
            if probs is not None:
                for k, (_arc, j) in enumerate(outs):
                    if j == b:
                        p = max(float(probs[k]), _PROB_FLOOR)
                        break
            lp += math.log(p)
        return lp


def _normalized(values: np.ndarray) -> np.ndarray:
    """Values scaled to a probability vector; uniform when the mass is zero."""
    total = float(values.sum())
    if total <= 0:
        return np.full(len(values), 1.0 / len(values))
    result: np.ndarray = values / total
    return result
