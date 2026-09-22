"""Differential validation of the ``privtrace`` port against the PrivTrace reference code.

The reference implementation (github.com/DpTrace/PrivTrace, run from ``external/PrivTrace``)
reads a database of raw-coordinate trajectories, builds its own two-layer adaptive grid over
them, estimates the adaptive-order Markov model and writes one synthetic trajectory per input
trajectory. Unlike LDPTrace it prints **no** utility numbers, so this harness scores both
sides itself with the paper-faithful metrics of ``evaluation/ldptrace_metrics.py``
(``docs/NACRT_MEHANIZMI.md`` §5, step ZM-4) and the comparison table has only two columns:

1. **port** — :class:`~trajguard.synthesis.privtrace.PrivTraceGenerator` in bbox mode, fitted
   on the raw points of the ``.dat`` file, ``len(db)`` synthetic state walks, one uniform
   point per leaf state;
2. **reference** — the reference's saved synthesis, read back from its output file
   (``external/PrivTrace/generated_eps_<ε>_seed_<s>.txt``) and scored here
   (``--score-synthesis``).

Both sides read and write the same two-line text format as our ``.dat`` files (``#<i>:`` then
``>0:x,y;…;``, longitude first, six decimals, no space after ``>0:``); ``--write-subset``
produces the exact input file the reference is run on, so the two sides see the same trips.

**Grid.** The reference's level-1 bounding box (``discretization/grid.py``) is the data
min/max per axis extended by ``1e-5 × (raw span)`` on *each* side; :func:`reference_bbox`
reproduces it, and the port is constructed with that box so both adaptive grids cover exactly
the same area. That box is read straight off the raw data and is therefore **not**
differentially private — on either side, and in the reference just as much as here. It is
treated as part of the shared, public-by-assumption experimental setup (the region the data
live in, fixed before any budget is spent and identical for both columns), not as part of the
mechanism; a deployment would have to fix the region from public knowledge or pay for it.
Its level-1 bins are uniform ``np.arange`` edges and a point exactly on an interior edge falls
into the **lower** bin, whereas our :class:`AdaptiveGrid` floors and takes the upper one; with
the 1e-5 extension the edges are not round coordinates, so exact hits do not occur in practice
and the rule is deliberately not replicated.

**Points.** The reference draws exactly one uniform point inside the leaf rectangle of every
state of a walk, and a one-state walk is first duplicated into two states, i.e. it yields two
*independently drawn* points from the same leaf (``generator/to_real_translator.py``,
``translate_given_state_sequence``). :func:`sample_leaf_points` does the same, which also
matches ``ldptrace_metrics.sample_points``.

**Scoring.** Both sides are mapped onto one uniform ``n × n`` evaluation grid (default
20 × 20) over :func:`reference_bbox`, which is independent of either adaptive grid, and scored
with the same nine metrics: cell chains for the cell metrics, the raw GPS points of the real
side against the sampled synthetic points for the length and diameter errors, and, for the
point query, one uniform point per cell of the *real* chains against those same synthetic
points.

Every run is scored **twice**, because the two passes disagree about what a walk that jumps
between far-apart cells is worth:

1. *bridged* (the nine metrics under their plain names) — the LDPTrace convention, where
   :meth:`Grid.chain` fills every pair of non-adjacent consecutive cells with a straight
   king's walk, so a jump is charged as the whole line of cells it flies over;
2. *unbridged* (the same nine values under ``nobridge_<name>``) — :func:`points_to_cell_sequences`
   keeps only the cells the trajectory's own points fall in, so a jump is charged as one step.

Seven of the nine values move between the two passes: the six metrics that read cell chains,
plus the point query, whose real side is one uniform point drawn per cell of the *real* chains
(``ldptrace_metrics.evaluate``), so a real side with fewer cells gives a different real sample
(and, because the same ``rng`` draws that sample before the 200 query centres, a shifted set of
centres as well -- within one pass every column still sees the same real sample and centres).
Only the length and diameter errors are identical in both passes, because they read the raw
real points and the synthetic points and never see a chain; all nine unbridged values are
stored, but only the seven that can move (:data:`NOBRIDGE_METRICS`) are summarized and
tabulated, and those two are not repeated.

The port's Algorithm 1 has no adjacency constraint, so its walks jump often and bridging turns
those jumps into long straight runs of cells that no point ever visited: on Porto 20 000 trips
two thirds of the port's chain cells at ε = 0.5 are interpolated, against 8 % for the real
trips. Those runs flatter the cell metrics (they thicken the density map and lengthen trips),
so the bridged numbers alone would overstate the port. ``interpolated_share`` per run and
``source["real_interpolated_share"]`` report the size of the effect directly: the fraction of
chain cells that bridging inserted. ``--mask-non-adjacent`` measures the third variant, the
port with its optional adjacency mask (D-4.6) switched on, which removes the jumps at the
source rather than at scoring time.

**Seeds.** For run seed ``s`` the port's noise uses ``s``, synthesis uses
``s + 7``, the leaf → point sampling ``s + 11`` and the metric randomness ``s``; the same
``s`` in ``--score-synthesis`` reproduces the metric randomness, so scoring the port's own
saved synthesis (``--save-synthesis``) returns the run's values (up to the six decimals of the
text format). The reference's ``--seed`` (added by ``scripts/privtrace_reference.patch``) has
no comparable contract — it is matched in distribution across seeds, not draw by draw.

Output: one JSON per side (``runs[epsilon][seed]``) and a console table with mean and range
over seeds; ``--compare A.json B.json`` prints the two-column Markdown table for the handoff.
Every port run also records ``max_redraws``, ``n_capped_walks`` and ``n_redrawn_walks``, which
measure how often the D-4.3 walk-length cap bound (it matters for the masked port at
ε = 0.5); they stay in the JSON and are deliberately not table rows.
Nothing here is registered or wired into the orchestrator.

CLI::

    python -m trajguard.experiments.privtrace_eval --dat data/interim/porto/porto.dat \\
        --max-trajectories 20000 --write-subset external/PrivTrace/datasets/porto_20k.dat
    python -m trajguard.experiments.privtrace_eval --dat data/interim/porto/porto.dat \\
        --max-trajectories 20000 --first-level-k 6 --eval-grid 20 \\
        --epsilons 0.5 1.0 2.0 --seeds 1 2 3 4 5 \\
        --out results/privtrace_validation/port.json
    python -m trajguard.experiments.privtrace_eval --dat … --mask-non-adjacent \\
        --label port_masked --out results/privtrace_validation/port_masked.json
    python -m trajguard.experiments.privtrace_eval --dat … --max-trajectories 20000 \\
        --score-synthesis "external/PrivTrace/generated_eps_{eps}_seed_{seed}.txt" \\
        --label reference --out results/privtrace_validation/reference.json
    python -m trajguard.experiments.privtrace_eval --compare port.json reference.json
"""

import argparse
import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from trajguard.datasets.ldptrace_dat import read_dat
from trajguard.evaluation.ldptrace_metrics import METRIC_NAMES, evaluate

# The LDPTrace harness is the sibling of this one in the same package and both sides of this
# comparison are scored by its plumbing; importing its private helpers keeps the two tables,
# the seed offsets and the JSON envelope identical instead of forking them.
from trajguard.experiments.ldptrace_eval import (
    _GENERATE_SEED_OFFSET,
    _POINTS_SEED_OFFSET,
    Chains,
    Points,
    Runs,
    _cell,
    _check_pattern,
    _progress,
    _result,
    eps_key,
    expand_pattern,
    points_to_chains,
    reference_cells,
)
from trajguard.experiments.ldptrace_eval import summarize as _metric_summary
from trajguard.representation import Grid
from trajguard.synthesis.adaptive_grid import AdaptiveGrid
from trajguard.synthesis.privtrace import PrivTraceGenerator

EXTEND_RATIO = 1e-5  # reference Grid.extend_ratio: bbox = data min/max ± ratio · raw span
COORD_DECIMALS = 6  # the reference writes and reads six decimals
_EXTRA_ROWS = ("n_states", "n_second_order", "synthetic_mean_length")  # port-only table rows

# The seven metrics that move when the king's-walk bridging is removed: the six that read cell
# chains, plus ``point_query_avre``, whose real side is one uniform point per cell of the real
# chains and therefore changes with them. Only ``length_error`` and ``diameter_error`` are
# identical in both passes, because they read the raw real points and the synthetic points; all
# nine are stored under ``nobridge_*`` but only these seven are summarized and tabulated.
NOBRIDGE_METRICS: tuple[str, ...] = (
    "density_error",
    "hotspot_query_error",
    "point_query_avre",
    "coverage_kendall_tau",
    "trip_error",
    "pattern_f1",
    "pattern_support_error",
)
# The no-bridge block of the comparison table, in row order.
_NOBRIDGE_ROWS: tuple[str, ...] = (
    *(f"nobridge_{name}" for name in NOBRIDGE_METRICS),
    "interpolated_share",
)


# --- inputs ----------------------------------------------------------------------------


def reference_bbox(points: Points) -> tuple[float, float, float, float]:
    """The reference's level-1 box: data min/max per axis, ± ``1e-5 × (raw span)`` each side.

    ``discretization/grid.py`` computes the extension from the *raw* span, i.e. before
    widening, and applies it to both ends, so the box is ``(1 + 2e-5)`` times the data span.
    """
    if not points:
        raise ValueError("reference_bbox needs at least one trajectory")
    lo = np.array([np.inf, np.inf])
    hi = np.array([-np.inf, -np.inf])
    for xy in points:
        arr = np.asarray(xy, dtype=float).reshape(-1, 2)
        lo = np.minimum(lo, arr.min(axis=0))
        hi = np.maximum(hi, arr.max(axis=0))
    span = hi - lo
    if not (span > 0).all():
        raise ValueError(f"degenerate data box: min {lo.tolist()}, max {hi.tolist()}")
    lo = lo - EXTEND_RATIO * span
    hi = hi + EXTEND_RATIO * span
    return (float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))


def load_points(path: str | Path, max_trajectories: int | None = None) -> Points:
    """Raw ``(x, y)`` points of the first ``max_trajectories`` ``.dat`` records, in file order.

    Each record becomes an ``(n, 2)`` float array (16 bytes per point); the file is read once
    and reading stops as soon as enough records are in hand.
    """
    if max_trajectories is not None and max_trajectories < 1:
        raise ValueError(f"max_trajectories must be >= 1, got {max_trajectories}")
    points: Points = []
    for _record_id, polyline in read_dat(path):
        points.append(np.asarray(polyline, dtype=float).reshape(-1, 2))
        if max_trajectories is not None and len(points) >= max_trajectories:
            break
    if not points:
        raise ValueError(f"{path}: no trajectories read")
    return points


def write_points(path: str | Path, points: Points) -> int:
    """Write point trajectories in the reference's text format; returns the record count.

    ``#<i>:`` / ``>0:x,y;…;`` with x = longitude first, six decimals, no space after ``>0:``
    and LF line endings — what the reference's reader expects and its writer produces.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for i, xy in enumerate(points):
            arr = np.asarray(xy, dtype=float).reshape(-1, 2)
            body = ";".join(f"{x:.{COORD_DECIMALS}f},{y:.{COORD_DECIMALS}f}" for x, y in arr)
            fh.write(f"#{i}:\n>0:{body};\n")
    return len(points)


def write_subset(src: str | Path, dst: str | Path, n: int) -> int:
    """Rewrite the first ``n`` records of a ``.dat`` file as the reference's input file.

    Ids are renumbered ``0 … n-1`` and coordinates are written with six decimals, so both
    sides of the comparison read exactly the same trips.
    """
    return write_points(dst, load_points(src, n))


# --- chains without the king's walk -------------------------------------------------------


def points_to_cell_sequences(grid: Grid, points: Points) -> Chains:
    """The same per-point cells as :func:`points_to_chains`, minus the king's-walk bridging.

    Each trajectory becomes the cells its own points fall in (:func:`reference_cells`), with
    consecutive duplicates collapsed and **nothing** inserted between two non-adjacent cells.
    A jump therefore costs one step here and a whole straight run of cells under
    :meth:`Grid.chain`; bridging the result reproduces the bridged chain exactly
    (``grid.chain(sequence) == grid.chain(cells)``), so this is the same information with the
    interpolation left out, not a different mapping.
    """
    out: Chains = []
    for xy in points:
        sequence: list[int] = []
        for cell in reference_cells(grid, xy):
            if not sequence or sequence[-1] != cell:
                sequence.append(cell)
        out.append(sequence)
    return out


def interpolated_share(chains: Chains, sequences: Chains) -> float:
    """Fraction of all bridged chain cells that the king's walk inserted; 0.0 when empty.

    ``sum(len(chain) − len(sequence)) / sum(len(chain))`` over the pairs of
    :func:`points_to_chains` and :func:`points_to_cell_sequences` output for the same
    trajectories, so 0.0 means every consecutive pair of visited cells was already adjacent
    and 0.66 means two thirds of the cells the metrics see were never visited by a point.
    """
    if len(chains) != len(sequences):
        raise ValueError(f"{len(chains)} chains but {len(sequences)} sequences")
    total = 0
    inserted = 0
    for i, (chain, sequence) in enumerate(zip(chains, sequences, strict=True)):
        if len(chain) < len(sequence):
            raise ValueError(
                f"trajectory {i}: the bridged chain ({len(chain)} cells) is shorter than its "
                f"unbridged sequence ({len(sequence)} cells)"
            )
        total += len(chain)
        inserted += len(chain) - len(sequence)
    return inserted / total if total else 0.0


# --- the port side ---------------------------------------------------------------------


def sample_leaf_points(
    grid: AdaptiveGrid, payloads: Sequence[Sequence[int]], rng: np.random.Generator
) -> Points:
    """One uniform point inside the leaf rectangle of every state; a 1-state walk gives two.

    The reference's ``to_real_translator.translate_given_state_sequence`` first pads a walk of
    fewer than two states — ``start_end_array[0] = state_sequence[0]`` and
    ``start_end_array[1] = state_sequence[0]`` — and then draws a location per index
    (``location = self.sample_from_a_subcell(borders)`` inside the loop), so the two points are
    drawn independently from the same leaf rather than duplicated.
    """
    out: Points = []
    for payload in payloads:
        states = [int(s) for s in payload]
        if not states:
            raise ValueError("a synthetic trajectory has no states")
        if len(states) == 1:
            states = states * 2
        bounds = np.asarray([grid.state_bounds(s) for s in states], dtype=float)
        u = rng.random((len(states), 2))
        x = bounds[:, 0] + u[:, 0] * (bounds[:, 2] - bounds[:, 0])
        y = bounds[:, 1] + u[:, 1] * (bounds[:, 3] - bounds[:, 1])
        out.append(np.column_stack([x, y]))
    return out


def run_synthesis(
    raw_points: Points,
    eval_grid: Grid,
    first_level_k: int,
    epsilons: Sequence[float],
    seeds: Sequence[int],
    save_dir: str | Path | None = None,
    label: str = "port",
    **generator_kwargs: Any,
) -> Runs:
    """Fit, synthesize and score the port for every (epsilon, seed); the port column.

    Per run: ``PrivTraceGenerator(bbox=eval_grid.bbox, epsilon, first_level_k, seed)`` fitted
    on the raw points, ``len(raw_points)`` synthetic walks, one uniform point per leaf state,
    then :func:`evaluate` against the same real points. Scoring runs twice, once on the bridged
    chains (the nine plain keys) and once on the unbridged cell sequences (``nobridge_<name>``,
    all nine stored, seven of them different — the six chain metrics plus the point query, whose
    real side is sampled per cell of the real chains; see the module docstring);
    ``interpolated_share`` records how much of the synthetic side's bridged chains was inserted
    by the king's walk, and ``max_redraws`` / ``n_capped_walks`` / ``n_redrawn_walks`` record how
    often the generator's walk-length cap bound. ``generator_kwargs`` reach the generator
    unchanged (e.g. ``mask_non_adjacent=True``). ``save_dir`` (optional) receives
    ``syn_<label>_eps_<ε>_seed_<s>.txt`` in the reference's text format.
    """
    real_chains: Chains = points_to_chains(eval_grid, raw_points)
    real_sequences: Chains = points_to_cell_sequences(eval_grid, raw_points)
    runs: Runs = {}
    for epsilon in epsilons:
        for seed in seeds:
            t0 = time.perf_counter()
            gen = PrivTraceGenerator(
                bbox=eval_grid.bbox,
                epsilon=epsilon,
                first_level_k=first_level_k,
                seed=seed,
                **generator_kwargs,
            )
            gen.fit_points(raw_points)
            t1 = time.perf_counter()
            payloads = [
                list(t.payload)
                for t in gen.generate(len(raw_points), seed=seed + _GENERATE_SEED_OFFSET)
            ]
            syn_points = sample_leaf_points(
                gen.grid, payloads, np.random.default_rng(seed + _POINTS_SEED_OFFSET)
            )
            syn_chains: Chains = points_to_chains(eval_grid, syn_points)
            t2 = time.perf_counter()
            metrics = evaluate(
                real_chains,
                syn_chains,
                eval_grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            t3 = time.perf_counter()
            syn_sequences: Chains = points_to_cell_sequences(eval_grid, syn_points)
            nobridge = evaluate(
                real_sequences,
                syn_sequences,
                eval_grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            t4 = time.perf_counter()
            record: dict[str, Any] = {
                **metrics,
                **{f"nobridge_{name}": value for name, value in nobridge.items()},
                "interpolated_share": interpolated_share(syn_chains, syn_sequences),
                "mask_non_adjacent": bool(gen.mask_non_adjacent),
                "n_states": int(gen.n_states),
                "n_second_order": len(gen.second_order_states),
                "n_split_cells": sum(1 for kappa in gen.grid.kappa if kappa > 1),
                "max_kappa": max(gen.grid.kappa),
                "stage_epsilons": [float(e) for e in gen.stage_epsilons],
                "n_synthetic": len(payloads),
                "max_redraws": int(gen.max_redraws),
                "n_capped_walks": int(gen.n_capped_walks),
                "n_redrawn_walks": int(gen.n_redrawn_walks),
                "synthetic_mean_length": float(np.mean([len(p) for p in payloads])),
                "synthetic_mean_points": float(np.mean([len(p) for p in syn_points])),
                "fit_s": round(t1 - t0, 3),
                "generate_s": round(t2 - t1, 3),
                "metrics_s": round(t3 - t2, 3),
                "nobridge_metrics_s": round(t4 - t3, 3),
            }
            if save_dir is not None:
                out = Path(save_dir) / f"syn_{label}_eps_{eps_key(epsilon)}_seed_{seed}.txt"
                write_points(out, syn_points)
                record["synthesis_path"] = str(out)
            runs.setdefault(eps_key(epsilon), {})[str(seed)] = record
            _progress(label, epsilon, seed, record)
    return runs


# --- the reference side ------------------------------------------------------------------


def score_synthesis(
    raw_points: Points,
    eval_grid: Grid,
    pattern: str,
    epsilons: Sequence[float],
    seeds: Sequence[int],
    label: str = "reference",
) -> Runs:
    """Score saved synthetic ``.dat``-format files with our metrics; the reference column.

    Each file's points are mapped onto ``eval_grid`` (chains for the cell metrics, the points
    themselves for the point metrics), so a synthesis written by the reference and one written
    by :func:`run_synthesis` are scored the same way — including the second, unbridged pass
    (``nobridge_<name>``) and ``interpolated_share``.
    """
    _check_pattern(pattern, epsilons, seeds)
    real_chains: Chains = points_to_chains(eval_grid, raw_points)
    real_sequences: Chains = points_to_cell_sequences(eval_grid, raw_points)
    runs: Runs = {}
    for epsilon in epsilons:
        for seed in seeds:
            path = expand_pattern(pattern, epsilon, seed)
            t0 = time.perf_counter()
            syn_points = load_points(path)
            syn_chains: Chains = points_to_chains(eval_grid, syn_points)
            metrics = evaluate(
                real_chains,
                syn_chains,
                eval_grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            syn_sequences: Chains = points_to_cell_sequences(eval_grid, syn_points)
            nobridge = evaluate(
                real_sequences,
                syn_sequences,
                eval_grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            record: dict[str, Any] = {
                **metrics,
                **{f"nobridge_{name}": value for name, value in nobridge.items()},
                "interpolated_share": interpolated_share(syn_chains, syn_sequences),
                "n_synthetic": len(syn_points),
                "synthetic_mean_points": float(np.mean([len(p) for p in syn_points])),
                "metrics_s": round(time.perf_counter() - t0, 3),
                "synthesis_path": str(path),
            }
            runs.setdefault(eps_key(epsilon), {})[str(seed)] = record
            _progress(label, epsilon, seed, record)
    return runs


# --- summaries ---------------------------------------------------------------------------


def summarize(
    runs: Runs, extra_rows: Sequence[str] = _EXTRA_ROWS
) -> dict[str, dict[str, dict[str, float]]]:
    """Per epsilon: ``mean``/``min``/``max``/``n`` of the nine metrics plus ``extra_rows``.

    The metric part is ``ldptrace_eval.summarize``; the extra rows (state counts, mean walk
    length) exist on the port side only and are summarized the same way. The unbridged pass is
    summarized too — ``nobridge_<name>`` for the seven metrics of :data:`NOBRIDGE_METRICS` that
    bridging can move (the six chain metrics plus the point query, whose real side is sampled
    per cell of the real chains) and ``interpolated_share`` — for every epsilon whose records
    carry them. The unbridged length and diameter errors are stored but not summarized: they
    read the raw real points and the synthetic points, so they equal the bridged values.
    """
    out = _metric_summary(runs)
    for eps, by_seed in runs.items():
        for name in (*extra_rows, *_NOBRIDGE_ROWS):
            values = [float(r[name]) for r in by_seed.values() if r.get(name) is not None]
            if not values:
                continue
            arr = np.asarray(values)
            out.setdefault(eps, {})[name] = {
                "mean": float(arr.mean()),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "n": float(len(values)),
            }
    return out


def compare_table(
    results: Sequence[dict[str, Any]],
    extra_rows: Sequence[str] = _EXTRA_ROWS,
    digits: int = 4,
) -> str:
    """Markdown table: one row per (epsilon, metric), one column per result (its ``label``).

    Same layout as ``ldptrace_eval.compare_table`` — cells are ``mean [min; max]`` over seeds,
    the bare mean when all seeds agree — with the port-only ``extra_rows`` appended per
    epsilon instead of LDPTrace's ``l_k``, and after them the no-bridge block: the seven
    ``nobridge_<name>`` rows of :data:`NOBRIDGE_METRICS` and ``interpolated_share``. Those are
    the seven metrics bridging can move (the six chain metrics plus the point query, whose real
    side is sampled per cell of the real chains); the unbridged length and diameter errors equal
    their bridged values and are not repeated. A side that has no value for a row shows ``—``;
    a row no side has is left out.
    """
    if not results:
        raise ValueError("compare_table needs at least one result")
    labels = [str(r.get("label", f"side {i + 1}")) for i, r in enumerate(results)]
    summaries = [summarize(r["runs"], extra_rows) for r in results]
    eps_keys = sorted({eps for s in summaries for eps in s}, key=float)
    lines = [
        "| ε | metric | " + " | ".join(labels) + " |",
        "|---|---|" + "---|" * len(labels),
    ]
    for eps in eps_keys:
        for name in (*METRIC_NAMES, *extra_rows, *_NOBRIDGE_ROWS):
            stats = [s.get(eps, {}).get(name) for s in summaries]
            if all(st is None for st in stats):
                continue
            row_digits = 1 if name in extra_rows else digits
            cells = " | ".join(_cell(st, row_digits) for st in stats)
            lines.append(f"| {eps} | {name} | {cells} |")
    return "\n".join(lines)


# --- CLI ---------------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--dat", help="trajectories in the reference .dat format (the real side)")
    p.add_argument("--max-trajectories", type=int, default=None, help="first N records only")
    p.add_argument(
        "--first-level-k", type=int, default=6, help="level-1 grid is K x K cells (default 6)"
    )
    p.add_argument(
        "--eval-grid", type=int, default=20, help="scoring grid is N x N cells (default 20)"
    )
    p.add_argument("--epsilons", type=float, nargs="+", default=[0.5, 1.0, 2.0])
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    p.add_argument(
        "--mask-non-adjacent",
        action="store_true",
        help="port only: zero transitions between non-adjacent level-1 cells (D-4.6 mask)",
    )
    p.add_argument("--label", default=None, help="column label in the JSON and tables")
    p.add_argument("--out", default=None, help="JSON output path")
    p.add_argument(
        "--save-synthesis", default=None, metavar="DIR", help="save the port's synthetic points"
    )
    p.add_argument(
        "--score-synthesis",
        default=None,
        metavar="PATTERN",
        help="score saved synthesis files ({eps}/{seed} placeholders), no synthesis of our own",
    )
    p.add_argument(
        "--compare", nargs="+", default=None, metavar="JSON", help="print the comparison table"
    )
    p.add_argument(
        "--write-subset",
        default=None,
        metavar="PATH",
        help="write the first --max-trajectories records of --dat there and exit",
    )
    return p


def main(argv: Sequence[str] | None = None) -> None:
    """Run one side (or the comparison, or the subset export) and print its table."""
    args = _parser().parse_args(argv)
    modes = [m for m in ("compare", "score_synthesis", "write_subset") if getattr(args, m)]
    if len(modes) > 1:
        raise SystemExit("--compare, --score-synthesis and --write-subset are mutually exclusive")
    if args.mask_non_adjacent and args.score_synthesis:
        raise SystemExit(
            "--mask-non-adjacent changes the port's own synthesis and means nothing when "
            "--score-synthesis only reads saved files"
        )

    if args.compare:
        if args.dat:
            raise SystemExit("--compare reads JSON results only; drop --dat")
        results = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.compare]
        for result in results:
            share = result.get("source", {}).get("real_interpolated_share")
            if share is not None:
                print(f"real interpolated share ({result.get('label', '?')}): {float(share):.4f}")
        print(compare_table(results))
        return

    if not args.dat:
        raise SystemExit("--dat is required unless --compare is given")
    if args.write_subset:
        if args.max_trajectories is None:
            raise SystemExit("--write-subset needs --max-trajectories")
        n = write_subset(args.dat, args.write_subset, args.max_trajectories)
        print(f"written {n} trajectories: {args.write_subset}")
        return
    if args.eval_grid < 2:
        raise SystemExit(f"--eval-grid must be >= 2, got {args.eval_grid}")
    if args.first_level_k < 2:
        raise SystemExit(f"--first-level-k must be >= 2, got {args.first_level_k}")

    t0 = time.perf_counter()
    raw_points = load_points(args.dat, args.max_trajectories)
    eval_grid = Grid(bbox=reference_bbox(raw_points), n_rows=args.eval_grid, n_cols=args.eval_grid)
    real_share = interpolated_share(
        points_to_chains(eval_grid, raw_points), points_to_cell_sequences(eval_grid, raw_points)
    )
    print(
        f"read {len(raw_points)} trajectories, {sum(len(p) for p in raw_points)} points "
        f"in {time.perf_counter() - t0:.1f}s; eval grid "
        f"{eval_grid.n_rows}x{eval_grid.n_cols} over {list(eval_grid.bbox)}; "
        f"real interpolated share {real_share:.4f}",
        flush=True,
    )
    source: dict[str, Any] = {
        "dat": args.dat,
        "n_trajectories": len(raw_points),
        "max_trajectories": args.max_trajectories,
        "first_level_k": args.first_level_k,
        "eval_grid": {
            "bbox": list(eval_grid.bbox),
            "n_rows": eval_grid.n_rows,
            "n_cols": eval_grid.n_cols,
        },
        "bbox": list(eval_grid.bbox),
        "real_interpolated_share": real_share,
    }
    if args.score_synthesis:
        label = args.label or "reference"
        runs = score_synthesis(
            raw_points, eval_grid, args.score_synthesis, args.epsilons, args.seeds, label
        )
        source["synthesis"] = args.score_synthesis
    else:
        label = args.label or "port"
        runs = run_synthesis(
            raw_points,
            eval_grid,
            args.first_level_k,
            args.epsilons,
            args.seeds,
            args.save_synthesis,
            label,
            mask_non_adjacent=args.mask_non_adjacent,
        )
        source["mask_non_adjacent"] = bool(args.mask_non_adjacent)
    result = _result(label, source, runs)

    print()
    print(compare_table([result]))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
