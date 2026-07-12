"""Fixture-scale privacy/utility evidence for RN-LDP-Synth (design doc §12).

Runs, per epsilon: an honest LiRA membership-inference attack against
``RNLDPSynthGenerator`` (same-class shadows via the shadow factory) plus
unpaired population utility (cell JSD, length W1) of its synthetic output
against the member population — alongside the non-private ``MarkovGenerator``
ceiling under the identical protocol.

CLI: ``python -m trajguard.experiments.rnldp_eval [--out results.json]``.
Defaults target the committed ``beijing_fixture`` network; pass ``--region``/
``--map-dir``/``--bbox``/``--crs`` for other prebuilt networks (e.g. Ljubljana
once built). Small-n caveat: with a ~20-trajectory pool the interesting FPR
floor is 1/n_nonmembers, so TPR is reported at FPR in {0.01, 0.1}, not 0.001.
"""

import argparse
import itertools
import json
from collections.abc import Callable, Sequence
from typing import Any

import networkx as nx
import numpy as np

from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.membership import (
    MembershipInferenceAttack,
    ShadowGenerator,
    membership_report,
)
from trajguard.datamodel import MatchedTrajectory
from trajguard.evaluation.utility import unpaired_cell_js_divergence, unpaired_length_w1
from trajguard.maps.base import RoadNetwork
from trajguard.maps.osm import OSMMapSource
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator
from trajguard.synthesis.rn_ldp_synth import RNLDPSynthGenerator

_FPRS = (0.01, 0.1)
_GRID_SHAPE = (10, 10)
_N_BOOTSTRAP = 200


def seed_population(
    network: RoadNetwork, n: int, min_edges: int, seed: int
) -> list[TrajectoryView]:
    """Public seed population: shortest-path routes between largest-SCC node pairs.

    The same recipe as the generator's fixture tests; reusable for a Ljubljana
    demo population later (routes derive from the public map + seed only).
    """
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
    scc = max(nx.strongly_connected_components(network.graph), key=len)
    nodes = sorted(int(x) for x in scc)
    rng = np.random.default_rng(seed)
    views: list[TrajectoryView] = []
    while len(views) < n:
        a = nodes[int(rng.integers(len(nodes)))]
        b = nodes[int(rng.integers(len(nodes)))]
        if a == b:
            continue
        path = nx.shortest_path(network.graph, a, b, weight="length")
        edges = tuple(pair[(x, y)] for x, y in itertools.pairwise(path))
        if len(edges) < min_edges:
            continue
        matched = MatchedTrajectory(
            traj_id=f"seed{len(views)}",
            user_id=f"u{len(views)}",
            map_id=network.region,
            edge_seq=edges,
            matched_points=(),
            match_score=1.0,
            frac_matched=1.0,
        )
        views.append(TrajectoryView(matched=matched))
    return views


def _featurize(
    network: RoadNetwork, grid: Grid, edge_seqs: Sequence[Sequence[int]]
) -> tuple[np.ndarray, np.ndarray]:
    """Per-trajectory (cell-count row, length) from edge sequences — same on both sides."""
    node_ll: dict[int, tuple[float, float]] = {}
    for row in network.nodes.itertuples(index=False):
        node_ll[int(row.node_id)] = (float(row.lat), float(row.lon))
    ends: dict[int, tuple[int, int]] = {}
    lengths: dict[int, float] = {}
    for row in network.edges.itertuples(index=False):
        ends[int(row.edge_id)] = (int(row.u), int(row.v))
        lengths[int(row.edge_id)] = float(row.length_m)
    counts = np.zeros((len(edge_seqs), grid.n_cells))
    total_len = np.zeros(len(edge_seqs))
    for i, seq in enumerate(edge_seqs):
        for eid in seq:
            u, v = ends[int(eid)]
            lat = (node_ll[u][0] + node_ll[v][0]) / 2.0
            lon = (node_ll[u][1] + node_ll[v][1]) / 2.0
            counts[i, grid.cell_of(lat, lon)] += 1.0
            total_len[i] += lengths[int(eid)]
    return counts, total_len


def _grid_over(network: RoadNetwork) -> Grid:
    """Lon/lat grid spanning the network's nodes (utility featurization support)."""
    lats = [float(r.lat) for r in network.nodes.itertuples(index=False)]
    lons = [float(r.lon) for r in network.nodes.itertuples(index=False)]
    return Grid(
        bbox=(min(lons), min(lats), max(lons), max(lats)),
        n_rows=_GRID_SHAPE[0],
        n_cols=_GRID_SHAPE[1],
    )


def _run_mia(
    target: ShadowGenerator,
    factory: Callable[[int], ShadowGenerator],
    pool: list[tuple[int, ...]],
    member_ids: set[int],
    n_shadow: int,
    seed: int,
) -> dict[str, float]:
    """LiRA against ``target`` with ``factory``-built shadows; AUC + TPR at small-n FPRs."""
    candidates = [(i, i in member_ids) for i in range(len(pool))]
    attack = MembershipInferenceAttack(n_shadow=n_shadow, shadow_factory=factory)
    attack.configure(BackgroundKnowledge(known_points=0, seed=seed))
    result = attack.run(target, (pool, candidates))
    return membership_report(result, fprs=_FPRS)


def _utility(
    network: RoadNetwork,
    grid: Grid,
    real_seqs: Sequence[Sequence[int]],
    syn_seqs: Sequence[Sequence[int]],
    seed: int,
) -> dict[str, float]:
    real_counts, real_len = _featurize(network, grid, real_seqs)
    syn_counts, syn_len = _featurize(network, grid, syn_seqs)
    rng = np.random.default_rng(seed)
    jsd, jsd_lo, jsd_hi = unpaired_cell_js_divergence(
        real_counts, syn_counts, n_bootstrap=_N_BOOTSTRAP, ci=0.95, rng=rng
    )
    w1, w1_lo, w1_hi = unpaired_length_w1(
        real_len, syn_len, n_bootstrap=_N_BOOTSTRAP, ci=0.95, rng=rng
    )
    return {
        "cell_jsd": jsd,
        "cell_jsd_lo": jsd_lo,
        "cell_jsd_hi": jsd_hi,
        "length_w1_m": w1,
        "length_w1_lo": w1_lo,
        "length_w1_hi": w1_hi,
    }


def run_eval(
    network: RoadNetwork,
    epsilons: Sequence[float],
    n_shadow: int = 16,
    n_pop: int = 20,
    seed: int = 20260706,
) -> dict[str, Any]:
    """Per-epsilon MIA + utility for rn_ldp_synth, plus the Markov non-private ceiling."""
    population = seed_population(network, n_pop, min_edges=3, seed=seed)
    pool = [tuple(int(e) for e in v.as_segments()) for v in population]
    member_ids = set(range(len(pool) // 2))
    member_views = [population[i] for i in sorted(member_ids)]
    member_seqs = [pool[i] for i in sorted(member_ids)]
    grid = _grid_over(network)

    arms: dict[str, Any] = {}
    for eps in epsilons:
        target = RNLDPSynthGenerator(
            network, epsilon=eps, n_rows=10, n_cols=10, l_max=12, seed=seed
        )
        target.fit(member_views)

        def factory(k: int, _eps: float = eps) -> RNLDPSynthGenerator:
            return RNLDPSynthGenerator(
                network, epsilon=_eps, n_rows=10, n_cols=10, l_max=12, seed=seed + 1000 + k
            )

        mia = _run_mia(target, factory, pool, member_ids, n_shadow, seed)
        syn = target.generate(len(member_seqs), seed=seed + 7)
        utility = _utility(network, grid, member_seqs, [s.payload for s in syn], seed)
        arms[f"rn_ldp_synth@eps={eps:g}"] = {"mia": mia, "utility": utility}

    markov = MarkovGenerator(order=1)
    markov.fit(member_views)
    mia = _run_mia(markov, lambda _k: MarkovGenerator(order=1), pool, member_ids, n_shadow, seed)
    syn = markov.generate(len(member_seqs), seed=seed + 7)
    utility = _utility(network, grid, member_seqs, [tuple(s.payload) for s in syn], seed)
    arms["markov (non-private ceiling)"] = {"mia": mia, "utility": utility}

    return {
        "n_pop": n_pop,
        "n_members": len(member_ids),
        "n_shadow": n_shadow,
        "seed": seed,
        "region": network.region,
        "arms": arms,
    }


def _table(results: dict[str, Any]) -> str:
    """Markdown table of the arms (for the design doc)."""
    arms: dict[str, Any] = results["arms"]
    lines = [
        "| Arm | MIA AUC | TPR@FPR=0.01 | TPR@FPR=0.1 | Cell JSD (bits) | Length W1 (m) |",
        "|---|---|---|---|---|---|",
    ]
    for name, arm in arms.items():
        mia, utility = arm["mia"], arm["utility"]
        lines.append(
            f"| {name} | {mia['auc']:.3f} | {mia['tpr@fpr=0.01']:.2f} "
            f"| {mia['tpr@fpr=0.1']:.2f} | {utility['cell_jsd']:.3f} "
            f"[{utility['cell_jsd_lo']:.3f}, {utility['cell_jsd_hi']:.3f}] "
            f"| {utility['length_w1_m']:.0f} "
            f"[{utility['length_w1_lo']:.0f}, {utility['length_w1_hi']:.0f}] |"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the evidence sweep against a prebuilt network and print the table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epsilons", type=float, nargs="+", default=[0.5, 2.0, 8.0, 80.0])
    parser.add_argument("--n-shadow", type=int, default=16)
    parser.add_argument("--n-pop", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260706)
    parser.add_argument("--region", default="beijing_fixture")
    parser.add_argument("--map-dir", default="tests/fixtures/maps")
    parser.add_argument("--bbox", type=float, nargs=4, default=[116.30, 39.98, 116.32, 39.995])
    parser.add_argument("--crs", default="EPSG:32650")
    parser.add_argument("--out", default=None, help="optional JSON output path")
    args = parser.parse_args(argv)

    bbox = (args.bbox[0], args.bbox[1], args.bbox[2], args.bbox[3])
    network = OSMMapSource(args.region, bbox, args.crs, args.map_dir).load()
    results = run_eval(network, args.epsilons, args.n_shadow, args.n_pop, args.seed)
    print(_table(results))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
