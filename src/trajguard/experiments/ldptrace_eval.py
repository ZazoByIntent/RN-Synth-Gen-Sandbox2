"""Differential validation of the ``ldptrace`` port against the LDPTrace reference code.

The reference implementation (github.com/zealscott/LDPTrace, ``LDPTrace/code/main.py``)
reads a whole database of raw-coordinate trajectories, lays a ``n × n`` grid over their
bounding box (widened by 1e-6 on each side), synthesizes one trajectory per input under
per-trajectory ε-LDP and prints nine utility metrics. This harness runs the port over the
same ``.dat`` file (``docs/NACRT_LDPTRACE_VALIDACIJA.md``, decision D-V.8) and scores
both sides with the paper's metrics from ``evaluation/ldptrace_metrics.py``, so the three
columns of the comparison table are computed identically:

1. **reference, own metrics** — parsed from the reference run's console log
   (``--reference-log``);
2. **reference, our metrics** — the reference's saved synthetic points
   (``syn_<dataset>_eps_<ε>_..._seed_<s>.pkl``, a plain pickle of ``list[list[(x, y)]]``)
   mapped onto the same :class:`Grid` and scored here (``--score-synthesis``);
3. **port, our metrics** — ``LDPTraceGenerator(bbox=…)`` fitted on the chains of the
   ``.dat`` file, ``len(db)`` synthetic chains, one uniform point per cell (the default
   mode).

Input split for the point metrics follows the reference (``ldptrace_metrics.evaluate``):
length and diameter compare the raw GPS points of the real side with the synthetic
points; the point query compares one sampled point per cell on both sides. The real side
is the file as it is — no cleaning, no split, no user subsample — exactly what the
reference reads; ``--max-trajectories N`` keeps the first N records for timing runs.

Seeds: for run seed ``s`` the generator's device randomness uses ``s``, synthesis uses
``s + 7``, the synthetic cell → point sampling ``s + 11`` and the metric randomness
(real-side point sampling, query centres) ``s``; the same ``s`` in ``--score-synthesis``
reproduces the metric randomness, so scoring the port's own saved synthesis
(``--save-synthesis``) returns the run's values to the digit. The reference side has no
comparable seed contract — its ``--seed`` is added by ``scripts/ldptrace_reference.patch``
— so it is matched in distribution across seeds, not draw by draw.

Output: one JSON per side (``runs[epsilon][seed]`` = the nine metrics plus ``l_k``,
``report_epsilon`` and timings) and a console table with mean and range over seeds;
``--compare A.json B.json …`` prints the three-column Markdown table for the handoff.
Nothing here is registered or wired into the orchestrator.

CLI::

    python -m trajguard.experiments.ldptrace_eval --dat data/interim/porto/porto.dat \\
        --stats data/interim/porto/porto_stats.json --grid 6 \\
        --epsilons 0.5 1.0 1.5 --seeds 1 2 3 4 5 --out results/ldptrace_validation/port.json
    python -m trajguard.experiments.ldptrace_eval --dat … --stats … --grid 6 --epsilons … \\
        --seeds … --score-synthesis "…/syn_porto_eps_{eps}_max_0.9_grid_6_seed_{seed}.pkl"
    python -m trajguard.experiments.ldptrace_eval --epsilons … --seeds … \\
        --reference-log "results/ldptrace_validation/reference/eps{eps}_seed{seed}.log"
    python -m trajguard.experiments.ldptrace_eval --compare port.json reference_ours.json
"""

import argparse
import json
import math
import pickle
import re
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from trajguard.datasets.ldptrace_dat import read_dat
from trajguard.evaluation.ldptrace_metrics import METRIC_NAMES, evaluate, sample_points
from trajguard.representation import Grid, TrajectoryView
from trajguard.synthesis.ldptrace import LDPTraceGenerator

Chains = list[list[int]]
Points = list[np.ndarray]
Runs = dict[str, dict[str, dict[str, Any]]]  # epsilon key -> seed key -> record

_GENERATE_SEED_OFFSET = 7  # generate(seed) relative to the run seed
_POINTS_SEED_OFFSET = 11  # synthetic cell -> point sampling relative to the run seed
_EXTRA_ROWS = ("l_k",)  # non-metric per-run values the comparison table also shows
# Reference console lines (main.py logger.info calls), our metric names.
_LOG_PATTERNS: dict[str, str] = {
    "l_k": r"Quantile:[ \t]*(\S+)",
    "density_error": r"Density Error:[ \t]*(\S+)",
    "hotspot_query_error": r"Hotspot Query Error:[ \t]*(\S+)",
    "point_query_avre": r"Point Query AvRE:[ \t]*(\S+)",
    "coverage_kendall_tau": r"Kendall_tau:[ \t]*(\S+)",
    "trip_error": r"Trip error:[ \t]*(\S+)",
    "diameter_error": r"Diameter error:[ \t]*(\S+)",
    "length_error": r"Length error:[ \t]*(\S+)",
    "pattern_f1": r"Pattern F1 error:[ \t]*(\S+)",
    "pattern_support_error": r"Pattern support error:[ \t]*(\S+)",
}


# --- inputs ----------------------------------------------------------------------------


def eps_key(epsilon: float) -> str:
    """JSON key and ``{eps}`` placeholder value: Python's float repr (``1.0``, as the reference)."""
    return str(float(epsilon))


def grid_from_stats(path: str | Path, n: int) -> Grid:
    """``n × n`` grid over ``grid_bbox`` of a ``porto_stats.json`` from the Porto conversion."""
    stats = json.loads(Path(path).read_text(encoding="utf-8"))
    bbox = stats.get("grid_bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"{path}: expected a 4-number 'grid_bbox', got {bbox!r}")
    return Grid(
        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])), n_rows=n, n_cols=n
    )


def reference_cells(grid: Grid, xy: np.ndarray) -> list[int]:
    """Row-major cell of every point under the reference's ``GridMap`` / ``Grid.in_cell`` rule.

    The reference lays the edges of cell ``i`` at ``lo = min + step·i`` and ``hi = lo + step``
    (``step = (max − min) / n``, in that floating-point order), tests ``lo <= v <= hi`` on
    each axis and keeps the first cell hit in increasing order — so a point exactly on an
    inner edge belongs to the **lower** cell. ``Grid.cell_of`` uses half-open intervals and
    would give the upper cell. This is not academic: on Porto the column edge
    ``x = −8.620002`` is a six-decimal coordinate that real points do hit (0.5 % of trips
    end up with a different chain), so the harness reproduces the reference arithmetic
    exactly. A point outside every cell raises (the reference drops it silently; on both
    sides of this comparison it cannot occur and would mean a wrong grid).
    """
    xy = np.asarray(xy, dtype=float).reshape(-1, 2)
    min_x, min_y, max_x, max_y = grid.bbox
    cols = _axis_cells(xy[:, 0], min_x, (max_x - min_x) / grid.n_cols, grid.n_cols)
    rows = _axis_cells(xy[:, 1], min_y, (max_y - min_y) / grid.n_rows, grid.n_rows)
    return [int(c) for c in rows * grid.n_cols + cols]


def _axis_cells(values: np.ndarray, start: float, step: float, n: int) -> np.ndarray:
    """First ``i`` with ``start + step·i <= v <= start + step·i + step`` per value; −1 → error."""
    out = np.full(len(values), -1, dtype=np.int64)
    for i in range(n):
        lo = start + step * i
        hi = lo + step
        hit = (out < 0) & (values >= lo) & (values <= hi)
        out[hit] = i
    if (out < 0).any():
        bad = values[out < 0][0]
        raise ValueError(f"coordinate {bad!r} lies outside the grid [{start}, {start + step * n}]")
    return out


def load_dat(
    path: str | Path, grid: Grid, max_trajectories: int | None = None
) -> tuple[Chains, Points]:
    """Cell chains and raw ``(x, y)`` points of the first ``max_trajectories`` ``.dat`` records.

    Each record becomes an ``(n, 2)`` float array (16 bytes per point) and its chain
    ``grid.chain`` of the per-point :func:`reference_cells` — the reference's
    ``trajectory_point2grid`` with interpolation. File order is kept; the file is read once.
    """
    if max_trajectories is not None and max_trajectories < 1:
        raise ValueError(f"max_trajectories must be >= 1, got {max_trajectories}")
    chains: Chains = []
    points: Points = []
    for _record_id, polyline in read_dat(path):
        xy = np.asarray(polyline, dtype=float).reshape(-1, 2)
        points.append(xy)
        chains.append(grid.chain(reference_cells(grid, xy)))
        if max_trajectories is not None and len(chains) >= max_trajectories:
            break
    if not chains:
        raise ValueError(f"{path}: no trajectories read")
    return chains, points


def points_to_chains(grid: Grid, points: Points) -> Chains:
    """Cell chain of every point trajectory (``x`` along longitude, ``y`` along latitude)."""
    return [grid.chain(reference_cells(grid, xy)) for xy in points]


# --- reference synthesis files ---------------------------------------------------------


def load_reference_synthesis(path: str | Path) -> Points:
    """Read a reference ``syn_*.pkl`` (pickle of ``list[list[(x, y)]]``) → one array per trajectory.

    Only load files written by the reference run or by :func:`save_reference_synthesis`;
    a pickle executes code on load.
    """
    with Path(path).open("rb") as fh:
        db = pickle.load(fh)  # trusted local file, see docstring
    if not isinstance(db, list) or not db:
        raise ValueError(f"{path}: expected a non-empty list of trajectories")
    points: Points = []
    for i, traj in enumerate(db):
        xy = np.asarray(traj, dtype=float)
        if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) == 0:
            raise ValueError(f"{path}: trajectory {i} is not a non-empty list of (x, y) pairs")
        points.append(xy)
    return points


def save_reference_synthesis(path: str | Path, points: Points) -> None:
    """Write point trajectories in the reference's output format (plain pickle of tuple lists)."""
    db = [[(float(x), float(y)) for x, y in xy] for xy in points]
    with Path(path).open("wb") as fh:
        pickle.dump(db, fh)


def expand_pattern(pattern: str, epsilon: float, seed: int) -> Path:
    """Fill ``{eps}`` and ``{seed}`` in a path pattern (``{eps}`` as :func:`eps_key`)."""
    return Path(pattern.replace("{eps}", eps_key(epsilon)).replace("{seed}", str(seed)))


def _check_pattern(pattern: str, epsilons: Sequence[float], seeds: Sequence[int]) -> None:
    n_runs = len(epsilons) * len(seeds)
    if n_runs > 1 and not ("{eps}" in pattern or "{seed}" in pattern):
        raise ValueError(
            f"{n_runs} (epsilon, seed) runs but the pattern {pattern!r} has no "
            "{eps}/{seed} placeholder — every run would read the same file"
        )
    if len(epsilons) > 1 and "{eps}" not in pattern:
        raise ValueError(f"several epsilons but no {{eps}} placeholder in {pattern!r}")
    if len(seeds) > 1 and "{seed}" not in pattern:
        raise ValueError(f"several seeds but no {{seed}} placeholder in {pattern!r}")


# --- the three sides -------------------------------------------------------------------


def run_synthesis(
    chains: Chains,
    raw_points: Points,
    grid: Grid,
    epsilons: Sequence[float],
    seeds: Sequence[int],
    quantile: float = 0.9,
    save_dir: str | Path | None = None,
    label: str = "port",
) -> Runs:
    """Fit, synthesize and score the port for every (epsilon, seed); the port column.

    Per run: ``LDPTraceGenerator(bbox=grid.bbox, epsilon, n_rows, n_cols, quantile,
    seed)`` fitted on all chains, ``len(chains)`` synthetic chains, one uniform point per
    synthetic cell, then :func:`evaluate` with the raw real points. ``save_dir`` (optional)
    receives ``syn_<label>_eps_<ε>_seed_<s>.pkl`` in the reference's format.
    """
    views = [TrajectoryView(sequence=tuple(c)) for c in chains]
    runs: Runs = {}
    for epsilon in epsilons:
        for seed in seeds:
            t0 = time.perf_counter()
            gen = LDPTraceGenerator(
                bbox=grid.bbox,
                epsilon=epsilon,
                n_rows=grid.n_rows,
                n_cols=grid.n_cols,
                quantile=quantile,
                seed=seed,
            )
            gen.fit(views)
            t1 = time.perf_counter()
            syn = [
                list(s.payload)
                for s in gen.generate(len(chains), seed=seed + _GENERATE_SEED_OFFSET)
            ]
            syn_points = sample_points(grid, syn, np.random.default_rng(seed + _POINTS_SEED_OFFSET))
            t2 = time.perf_counter()
            metrics = evaluate(
                chains,
                syn,
                grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            t3 = time.perf_counter()
            record: dict[str, Any] = {
                **metrics,
                "l_k": int(gen.l_k),
                "report_epsilon": gen.report_epsilon,
                "n_synthetic": len(syn),
                "synthetic_mean_length": float(np.mean([len(c) for c in syn])),
                "fit_s": round(t1 - t0, 3),
                "generate_s": round(t2 - t1, 3),
                "metrics_s": round(t3 - t2, 3),
            }
            if save_dir is not None:
                out = Path(save_dir) / f"syn_{label}_eps_{eps_key(epsilon)}_seed_{seed}.pkl"
                out.parent.mkdir(parents=True, exist_ok=True)
                save_reference_synthesis(out, syn_points)
                record["synthesis_path"] = str(out)
            runs.setdefault(eps_key(epsilon), {})[str(seed)] = record
            _progress(label, epsilon, seed, record)
    return runs


def score_synthesis(
    chains: Chains,
    raw_points: Points,
    grid: Grid,
    pattern: str,
    epsilons: Sequence[float],
    seeds: Sequence[int],
    label: str = "reference",
) -> Runs:
    """Score saved synthetic point files with our metrics; the reference-with-our-metrics column.

    Each file's points are mapped onto ``grid`` (chains for the cell metrics, the points
    themselves for the point metrics), so a synthesis saved by the reference and one saved
    by :func:`run_synthesis` are scored the same way.
    """
    _check_pattern(pattern, epsilons, seeds)
    runs: Runs = {}
    for epsilon in epsilons:
        for seed in seeds:
            path = expand_pattern(pattern, epsilon, seed)
            t0 = time.perf_counter()
            syn_points = load_reference_synthesis(path)
            syn = points_to_chains(grid, syn_points)
            metrics = evaluate(
                chains,
                syn,
                grid,
                np.random.default_rng(seed),
                real_raw_points=raw_points,
                syn_points=syn_points,
            )
            record: dict[str, Any] = {
                **metrics,
                "n_synthetic": len(syn),
                "synthetic_mean_length": float(np.mean([len(c) for c in syn])),
                "metrics_s": round(time.perf_counter() - t0, 3),
                "synthesis_path": str(path),
            }
            runs.setdefault(eps_key(epsilon), {})[str(seed)] = record
            _progress(label, epsilon, seed, record)
    return runs


def parse_reference_log(text: str) -> dict[str, float]:
    """The nine metrics and ``l_k`` (the logged ``Quantile``) of one reference run's console log.

    Matches the ``logger.info`` lines of the reference ``main.py`` (``Kendall_tau:`` has
    no space, ``Pattern F1 error`` is the F1 score itself); the last occurrence wins.
    Raises ``ValueError`` naming the lines that are missing.
    """
    out: dict[str, float] = {}
    missing: list[str] = []
    for name, pattern in _LOG_PATTERNS.items():
        matches = re.findall(pattern, text)
        if not matches:
            missing.append(name)
            continue
        try:
            out[name] = float(matches[-1])
        except ValueError as err:
            raise ValueError(f"cannot parse {name!r} from {matches[-1]!r}") from err
    if missing:
        raise ValueError(f"reference log lacks: {', '.join(missing)}")
    out["l_k"] = int(out["l_k"])
    return out


def parse_reference_logs(pattern: str, epsilons: Sequence[float], seeds: Sequence[int]) -> Runs:
    """One :func:`parse_reference_log` record per (epsilon, seed); the reference-own column."""
    _check_pattern(pattern, epsilons, seeds)
    runs: Runs = {}
    for epsilon in epsilons:
        for seed in seeds:
            path = expand_pattern(pattern, epsilon, seed)
            record: dict[str, Any] = dict(parse_reference_log(path.read_text(encoding="utf-8")))
            record["log_path"] = str(path)
            runs.setdefault(eps_key(epsilon), {})[str(seed)] = record
    return runs


# --- summaries -------------------------------------------------------------------------


def summarize(runs: Runs) -> dict[str, dict[str, dict[str, float]]]:
    """Per epsilon and metric: ``mean``, ``min``, ``max`` and ``n`` over the seeds present.

    Covers the nine metrics and ``l_k`` when a record carries it; a ``nan`` in any seed
    makes the mean ``nan`` (reported, not hidden).
    """
    out: dict[str, dict[str, dict[str, float]]] = {}
    for eps, by_seed in runs.items():
        table: dict[str, dict[str, float]] = {}
        for name in (*METRIC_NAMES, *_EXTRA_ROWS):
            values = [float(r[name]) for r in by_seed.values() if r.get(name) is not None]
            if not values:
                continue
            arr = np.asarray(values)
            table[name] = {
                "mean": float(arr.mean()),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "n": float(len(values)),
            }
        out[eps] = table
    return out


def _cell(stat: dict[str, float] | None, digits: int) -> str:
    if stat is None:
        return "—"
    if math.isnan(stat["mean"]):
        return "nan"
    if stat["min"] == stat["max"]:
        return f"{stat['mean']:.{digits}f}"
    return f"{stat['mean']:.{digits}f} [{stat['min']:.{digits}f}; {stat['max']:.{digits}f}]"


def compare_table(results: Sequence[dict[str, Any]], digits: int = 4) -> str:
    """Markdown table: one row per (epsilon, metric), one column per result (its ``label``).

    Cells are ``mean [min; max]`` over seeds (the bare mean when all seeds agree).
    ``l_k`` is appended per epsilon for the sides that record it.
    """
    if not results:
        raise ValueError("compare_table needs at least one result")
    labels = [str(r.get("label", f"side {i + 1}")) for i, r in enumerate(results)]
    summaries = [summarize(r["runs"]) for r in results]
    eps_keys = sorted({eps for s in summaries for eps in s}, key=float)
    lines = [
        "| ε | metric | " + " | ".join(labels) + " |",
        "|---|---|" + "---|" * len(labels),
    ]
    for eps in eps_keys:
        for name in (*METRIC_NAMES, *_EXTRA_ROWS):
            stats = [s.get(eps, {}).get(name) for s in summaries]
            if all(st is None for st in stats):
                continue
            row_digits = 1 if name in _EXTRA_ROWS else digits
            cells = " | ".join(_cell(st, row_digits) for st in stats)
            lines.append(f"| {eps} | {name} | {cells} |")
    return "\n".join(lines)


def _progress(label: str, epsilon: float, seed: int, record: dict[str, Any]) -> None:
    timing = " ".join(
        f"{k}={record[k]}" for k in ("fit_s", "generate_s", "metrics_s") if k in record
    )
    l_k = f" l_k={record['l_k']}" if "l_k" in record else ""
    print(
        f"[{label}] eps={eps_key(epsilon)} seed={seed}{l_k} "
        f"density={record['density_error']:.4f} trip={record['trip_error']:.4f} {timing}",
        flush=True,
    )


def _git_commit() -> str:
    """Best-effort current commit of this repository, for provenance."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _result(label: str, source: dict[str, Any], runs: Runs) -> dict[str, Any]:
    return {"label": label, "source": source, "git_commit": _git_commit(), "runs": runs}


# --- CLI -------------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--dat", help="trajectories in the reference .dat format (the real side)")
    p.add_argument("--grid", type=int, default=6, help="grid is --grid x --grid cells (default 6)")
    p.add_argument(
        "--bbox", type=float, nargs=4, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT")
    )
    p.add_argument(
        "--stats", help="porto_stats.json whose grid_bbox defines the grid (instead of --bbox)"
    )
    p.add_argument("--epsilons", type=float, nargs="+", default=[0.5, 1.0, 1.5])
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    p.add_argument("--quantile", type=float, default=0.9, help="length quantile L_k (default 0.9)")
    p.add_argument("--max-trajectories", type=int, default=None, help="first N records only")
    p.add_argument("--label", default=None, help="column label in the JSON and tables")
    p.add_argument("--out", default=None, help="JSON output path")
    p.add_argument(
        "--save-synthesis", default=None, metavar="DIR", help="save the port's synthetic points"
    )
    p.add_argument(
        "--score-synthesis",
        default=None,
        metavar="PATTERN",
        help="score saved synthetic point files ({eps}/{seed} placeholders), no synthesis",
    )
    p.add_argument(
        "--reference-log",
        default=None,
        metavar="PATTERN",
        help="parse reference console logs ({eps}/{seed} placeholders); needs no --dat",
    )
    p.add_argument(
        "--compare", nargs="+", default=None, metavar="JSON", help="print the comparison table"
    )
    return p


def main(argv: Sequence[str] | None = None) -> None:
    """Run one side (or the comparison) and print its table; optionally write the JSON."""
    args = _parser().parse_args(argv)
    modes = [m for m in ("compare", "reference_log", "score_synthesis") if getattr(args, m)]
    if len(modes) > 1:
        raise SystemExit("--compare, --reference-log and --score-synthesis are mutually exclusive")

    if args.compare:
        if args.dat:
            raise SystemExit("--compare reads JSON results only; drop --dat")
        results = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.compare]
        print(compare_table(results))
        return

    if args.reference_log:
        runs = parse_reference_logs(args.reference_log, args.epsilons, args.seeds)
        result = _result(args.label or "reference (own metrics)", {"log": args.reference_log}, runs)
    else:
        if not args.dat:
            raise SystemExit("--dat is required unless --compare or --reference-log is given")
        if (args.bbox is None) == (args.stats is None):
            raise SystemExit("give exactly one of --bbox or --stats")
        if args.grid < 2:
            raise SystemExit(f"--grid must be >= 2, got {args.grid}")
        if args.stats:
            grid = grid_from_stats(args.stats, args.grid)
        else:
            lon0, lat0, lon1, lat1 = (float(v) for v in args.bbox)
            grid = Grid(bbox=(lon0, lat0, lon1, lat1), n_rows=args.grid, n_cols=args.grid)
        t0 = time.perf_counter()
        chains, raw_points = load_dat(args.dat, grid, args.max_trajectories)
        print(
            f"read {len(chains)} trajectories, {sum(len(p) for p in raw_points)} points "
            f"in {time.perf_counter() - t0:.1f}s; grid {grid.n_rows}x{grid.n_cols} "
            f"over {list(grid.bbox)}",
            flush=True,
        )
        source: dict[str, Any] = {
            "dat": args.dat,
            "n_trajectories": len(chains),
            "max_trajectories": args.max_trajectories,
            "grid": {"bbox": list(grid.bbox), "n_rows": grid.n_rows, "n_cols": grid.n_cols},
            "quantile": args.quantile,
        }
        if args.score_synthesis:
            label = args.label or "reference (our metrics)"
            runs = score_synthesis(
                chains, raw_points, grid, args.score_synthesis, args.epsilons, args.seeds, label
            )
            source["synthesis"] = args.score_synthesis
        else:
            label = args.label or "port"
            runs = run_synthesis(
                chains,
                raw_points,
                grid,
                args.epsilons,
                args.seeds,
                args.quantile,
                args.save_synthesis,
                label,
            )
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
