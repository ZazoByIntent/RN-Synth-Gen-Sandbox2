"""Parameter-recovery simulation of ULDP synthesis (P6; docs/NACRT_ULDP_SINTEZA.md §5.5).

Synthetic users are drawn by the public simulator under **planted** true parameters
that differ from the shared public prior (:func:`planted_truth`; never estimated from
Geolife). Every user's single report is produced by the production phone side of
``uldp_synth`` and fitted by its production server side
(``UldpGenerator.collect_reports`` then ``fit_from_reports``), so the tested path is the
path every real run takes. For each module (``c3``, ``c2``, ``c1``, ``all``), epsilon,
roster size n and seeded repetition the run records whether the module's gate rejected
the prior and how far the fitted parameters lie from the truth and from the prior.

Population, per (module, repetition): ``max(n)`` trips simulated under that module's
truth, one trip per user; smaller rosters are the first n users of the same population
(nested), so the curves over n share their draws within a repetition. With one trip per
user and homogeneous users, a phone's uniform draw among its trips has the law of a
single trip anyway (finding F2), so more trips per user would not change any report law.

Output (``--out``, a directory that must not exist yet or be empty):

- ``recovery_runs.csv``: one row per module, epsilon, n, repetition and parameter;
- ``recovery_summary.csv``: per module, epsilon, n and parameter, the gate rejection
  rate with its 95 % Wilson interval and the mean and 2.5-97.5 % range over repetitions
  of the error against the truth, the shift away from the prior and the share of the
  prior-truth gap closed; the prior's own error is the reference;
- ``run.json``: grid, planted truth, prior, map, Monte Carlo sizes and wall time.

Run: ``uv run python -m trajguard.experiments.uldp_recovery --out results/uldp_recovery``.
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.maps.base import RoadNetwork
from trajguard.maps.osm import OSMMapSource
from trajguard.representation import TrajectoryView
from trajguard.synthesis.public_sim import (
    N_PERIODS,
    PERIODS,
    REGIME_CATALOGUE,
    PublicSimulator,
    SimParams,
    prior_params,
)
from trajguard.synthesis.uldp_synth import (
    BAND_ORIGINS,
    C1_TRIPS_PER_REGIME,
    CONFUSION_TRIPS_PER_REGIME,
    GATE_DRAWS,
    MODULES,
    C1Fit,
    C2Fit,
    C3Fit,
    CompositeFit,
    UldpSynthGenerator,
    gravity_od_shares,
)

#: Plan §5.5 grid: roster sizes, epsilons and at least 20 seeded repetitions.
DEFAULT_NS = (10, 25, 91, 300, 1000, 3000, 10000)
DEFAULT_EPSILONS = (0.5, 2.0, 8.0)
DEFAULT_REPS = 20
DEFAULT_SEED = 20261014

#: Planted truth (SESSION DECISION, public and arbitrary; nothing is read from Geolife).
#: C3: regime weights (walk, bike, motorised), away from the uniform prior.
TRUE_REGIME_WEIGHTS = (0.15, 0.25, 0.60)
#: C2: departure-period shares (night, am_peak, midday, pm_peak, evening): peaks heavier
#: and night lighter than the prior's uniform day.
TRUE_DEPARTURE_SHARES = (0.10, 0.20, 0.35, 0.20, 0.15)
#: C2: intra-zone origin-destination cells of the gravity prior table are multiplied by
#: this factor before renormalising (more short, local trips than the prior).
TRUE_INTRAZONE_FACTOR = 2.0
#: C1: speed level (every period's speed factor) and gravity decay (per second of
#: free-flow cost, i.e. one e-fold per 30 minutes).
TRUE_SPEED_LEVEL = 0.7
TRUE_DECAY_PER_S = 1.0 / 1800.0

#: Parameters scored per module. The composite's truth carries an OD table, under which
#: the simulator's gravity decay is inert, so the composite's decay has no truth to score.
MODULE_PARAMS: dict[str, tuple[str, ...]] = {
    "c3": ("regime_weights",),
    "c2": ("od_shares", "departure_shares"),
    "c1": ("log_speed_level", "decay_per_h"),
    "all": ("regime_weights", "od_shares", "departure_shares", "log_speed_level"),
}
#: Module whose gate decides each parameter.
PARAM_OWNER = {
    "regime_weights": "c3",
    "od_shares": "c2",
    "departure_shares": "c2",
    "log_speed_level": "c1",
    "decay_per_h": "c1",
}
#: Seed stream tags, so populations and generator seeds never share draws.
_POP_STREAM = 1
_GEN_STREAM = 2

_RUN_FIELDS = (
    "module",
    "epsilon",
    "n",
    "rep",
    "parameter",
    "gate_rejected",
    "err_truth",
    "err_prior",
    "shift_from_prior",
)
_SUMMARY_FIELDS = (
    "module",
    "epsilon",
    "n",
    "parameter",
    "reps",
    "rejection_rate",
    "rejection_lo",
    "rejection_hi",
    "err_truth_mean",
    "err_truth_lo",
    "err_truth_hi",
    "err_prior",
    "shift_mean",
    "shift_lo",
    "shift_hi",
    "gap_closed_mean",
    "gap_closed_lo",
    "gap_closed_hi",
)


def planted_truth(sim: PublicSimulator, module: str) -> SimParams:
    """The planted true simulator parameters of one module's population (others stay prior)."""
    prior = prior_params()
    od = gravity_od_shares(sim, prior).reshape(sim.n_zones, sim.n_zones)
    od[np.diag_indices(sim.n_zones)] *= TRUE_INTRAZONE_FACTOR
    od_shares = tuple(float(x) for x in (od / od.sum()).ravel())
    level = (TRUE_SPEED_LEVEL,) * N_PERIODS
    if module == "c3":
        return replace(prior, regime_weights=TRUE_REGIME_WEIGHTS)
    if module == "c2":
        return replace(prior, od_shares=od_shares, departure_shares=TRUE_DEPARTURE_SHARES)
    if module == "c1":
        regimes = tuple(replace(r, distance_decay_per_s=TRUE_DECAY_PER_S) for r in prior.regimes)
        return replace(prior, regimes=regimes, period_speed_factors=level)
    if module == "all":
        return replace(
            prior,
            regime_weights=TRUE_REGIME_WEIGHTS,
            od_shares=od_shares,
            departure_shares=TRUE_DEPARTURE_SHARES,
            period_speed_factors=level,
        )
    raise ValueError(f"unknown module {module!r}; expected one of {MODULES}")


def _normalised(x: Sequence[float]) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    out: np.ndarray = a / a.sum()
    return out


def param_values(params: SimParams, prior_od: np.ndarray) -> dict[str, np.ndarray]:
    """The scored parameters of a SimParams (an unset OD table is the gravity prior's)."""
    od = prior_od if params.od_shares is None else _normalised(params.od_shares)
    levels = np.asarray(params.period_speed_factors, dtype=np.float64)
    decays = np.asarray([r.distance_decay_per_s for r in params.regimes], dtype=np.float64)
    return {
        "regime_weights": _normalised(params.regime_weights),
        "od_shares": od,
        "departure_shares": _normalised(params.departure_shares),
        "log_speed_level": np.array([math.log(float(levels.mean()))]),
        "decay_per_h": np.array([3600.0 * float(decays.mean())]),
    }


def param_error(a: np.ndarray, b: np.ndarray) -> float:
    """L1 distance of two shares vectors, absolute difference of two scalars."""
    return float(np.abs(a - b).sum())


def gate_flags(fitted: C1Fit | C2Fit | C3Fit | CompositeFit, module: str) -> dict[str, bool]:
    """Whether each owning module's gate rejected the prior."""
    if isinstance(fitted, CompositeFit):
        return {
            "c1": fitted.c1.gate_rejected,
            "c2": fitted.c2.gate_rejected,
            "c3": fitted.c3.gate_rejected,
        }
    return {module: bool(fitted.gate_rejected)}


def simulated_users(
    sim: PublicSimulator,
    truth: SimParams,
    n: int,
    rng: np.random.Generator,
    bbox: tuple[float, float, float, float],
) -> list[TrajectoryView]:
    """One simulated timed trip per user ``u00000``, ``u00001``, ... as a train view."""
    views = []
    for u, route in enumerate(sim.simulate(truth, n, rng)):
        user = f"u{u:05d}"
        t0, t1 = route.visits[0].t_enter, route.visits[-1].t_exit
        clean = CleanTrajectory(
            traj_id=f"{user}-0",
            user_id=user,
            points=((0.0, 0.0, t0), (0.0, 0.0, t1)),
            bbox=bbox,
            duration_s=t1 - t0,
            length_m=0.0,
            mean_speed=0.0,
            cleaning_flags=(),
            split="train",
        )
        matched = MatchedTrajectory(
            traj_id=f"{user}-0",
            user_id=user,
            map_id="recovery",
            edge_seq=route.edge_seq,
            matched_points=(),
            match_score=1.0,
            frac_matched=1.0,
        )
        views.append(TrajectoryView(clean=clean, matched=matched))
    return views


def _child_seed(*keys: int) -> int:
    """A deterministic 32-bit seed derived from integer keys."""
    return int(np.random.SeedSequence(list(keys)).generate_state(1)[0])


_NETWORK: RoadNetwork | None = None


def _init_worker(map_args: tuple[str, tuple[float, ...], str, str]) -> None:
    """Load the public map once per worker process."""
    global _NETWORK
    region, bbox, crs, map_dir = map_args
    _NETWORK = OSMMapSource(region, (bbox[0], bbox[1], bbox[2], bbox[3]), crs, map_dir).load()


def run_task(task: dict[str, Any]) -> list[dict[str, Any]]:
    """One (module, repetition): simulate the population, fit every epsilon and n, score."""
    network = _NETWORK
    if network is None:
        raise RuntimeError("run_task needs the map; call _init_worker first")
    module, rep, seed = task["module"], int(task["rep"]), int(task["seed"])
    mi = MODULES.index(module)
    sim = PublicSimulator(network)
    prior = prior_params()
    prior_od = gravity_od_shares(sim, prior)
    truth = planted_truth(sim, module)
    true_v, prior_v = param_values(truth, prior_od), param_values(prior, prior_od)
    pop_rng = np.random.default_rng(np.random.SeedSequence([seed, rep, mi, _POP_STREAM]))
    bbox = network.bbox or (0.0, 0.0, 0.0, 0.0)
    views = simulated_users(sim, truth, max(task["ns"]), pop_rng, bbox)
    users = [v.user_id for v in views]
    rows: list[dict[str, Any]] = []
    for ei, eps in enumerate(task["epsilons"]):
        gen = UldpSynthGenerator(network, epsilon=eps, module=module, **task["mc"])
        for ni, n in enumerate(task["ns"]):
            gen.seed = _child_seed(seed, rep, mi, ei, ni, _GEN_STREAM)
            gen.set_user_roster(users[:n])
            gen.fit_from_reports(gen.collect_reports(views[:n]))
            fit_v = param_values(gen.sim_params(), prior_od)
            flags = gate_flags(gen.fitted, module)
            for p in MODULE_PARAMS[module]:
                rows.append(
                    {
                        "module": module,
                        "epsilon": eps,
                        "n": n,
                        "rep": rep,
                        "parameter": p,
                        "gate_rejected": int(flags[PARAM_OWNER[p] if module == "all" else module]),
                        "err_truth": param_error(fit_v[p], true_v[p]),
                        "err_prior": param_error(prior_v[p], true_v[p]),
                        "shift_from_prior": param_error(fit_v[p], prior_v[p]),
                    }
                )
    return rows


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval of a binomial proportion k / n."""
    if n == 0:
        return math.nan, math.nan
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def summarise(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate run rows over repetitions: rejection rate and error intervals."""
    groups: dict[tuple[str, float, int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[(r["module"], r["epsilon"], r["n"], r["parameter"])].append(r)
    out = []
    for (module, eps, n, p), g in groups.items():
        rej = sum(int(r["gate_rejected"]) for r in g)
        err = np.array([r["err_truth"] for r in g])
        shift = np.array([r["shift_from_prior"] for r in g])
        err_prior = float(g[0]["err_prior"])
        gap = 1.0 - err / err_prior if err_prior > 0 else np.full(len(g), math.nan)
        lo, hi = wilson(rej, len(g))
        out.append(
            {
                "module": module,
                "epsilon": eps,
                "n": n,
                "parameter": p,
                "reps": len(g),
                "rejection_rate": rej / len(g),
                "rejection_lo": lo,
                "rejection_hi": hi,
                "err_truth_mean": float(err.mean()),
                "err_truth_lo": float(np.percentile(err, 2.5)),
                "err_truth_hi": float(np.percentile(err, 97.5)),
                "err_prior": err_prior,
                "shift_mean": float(shift.mean()),
                "shift_lo": float(np.percentile(shift, 2.5)),
                "shift_hi": float(np.percentile(shift, 97.5)),
                "gap_closed_mean": float(gap.mean()),
                "gap_closed_lo": float(np.percentile(gap, 2.5)),
                "gap_closed_hi": float(np.percentile(gap, 97.5)),
            }
        )
    out.sort(key=lambda r: (MODULES.index(r["module"]), r["epsilon"], r["n"], r["parameter"]))
    return out


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def _truth_record(sim: PublicSimulator) -> dict[str, Any]:
    """JSON-ready planted truth per module and the prior."""
    return {
        "prior": asdict(prior_params()),
        "truth": {m: asdict(planted_truth(sim, m)) for m in MODULES},
        "regimes": [r.name for r in REGIME_CATALOGUE],
        "periods": [name for name, _, _ in PERIODS],
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Run the recovery grid against a prebuilt map and write CSV/JSON under ``--out``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="new (or empty) output directory")
    parser.add_argument("--modules", nargs="+", default=list(MODULES), choices=MODULES)
    parser.add_argument("--epsilons", type=float, nargs="+", default=list(DEFAULT_EPSILONS))
    parser.add_argument("--ns", type=int, nargs="+", default=list(DEFAULT_NS))
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--region", default="beijing")
    parser.add_argument("--map-dir", default="maps")
    parser.add_argument("--bbox", type=float, nargs=4, default=[116.20, 39.75, 116.55, 40.05])
    parser.add_argument("--crs", default="EPSG:32650")
    # Public Monte Carlo sizes; lower them only for fast tests.
    parser.add_argument("--confusion-trips", type=int, default=CONFUSION_TRIPS_PER_REGIME)
    parser.add_argument("--gate-draws", type=int, default=GATE_DRAWS)
    parser.add_argument("--band-origins", type=int, default=BAND_ORIGINS)
    parser.add_argument("--moment-trips", type=int, default=C1_TRIPS_PER_REGIME)
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite: {out} exists and is not empty")
    if args.reps < 1 or args.workers < 1 or min(args.ns) < 1:
        raise SystemExit("--reps, --workers and every --ns value must be >= 1")
    out.mkdir(parents=True, exist_ok=True)
    ns = sorted(set(args.ns))
    mc = {
        "confusion_trips": args.confusion_trips,
        "gate_draws": args.gate_draws,
        "band_origins": args.band_origins,
        "moment_trips": args.moment_trips,
    }
    map_args = (args.region, tuple(args.bbox), args.crs, args.map_dir)
    tasks = [
        {"module": m, "rep": rep, "seed": args.seed, "ns": ns, "epsilons": args.epsilons, "mc": mc}
        for rep in range(args.reps)
        for m in args.modules
    ]
    start = time.monotonic()
    rows: list[dict[str, Any]] = []
    if args.workers == 1:
        _init_worker(map_args)
        for i, task in enumerate(tasks):
            rows.extend(run_task(task))
            print(f"[{time.monotonic() - start:7.0f} s] task {i + 1}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(
            args.workers, initializer=_init_worker, initargs=(map_args,)
        ) as ex:
            for i, task_rows in enumerate(ex.map(run_task, tasks)):
                rows.extend(task_rows)
                print(f"[{time.monotonic() - start:7.0f} s] task {i + 1}/{len(tasks)}", flush=True)
    wall = time.monotonic() - start
    summary = summarise(rows)
    _write_csv(out / "recovery_runs.csv", _RUN_FIELDS, rows)
    _write_csv(out / "recovery_summary.csv", _SUMMARY_FIELDS, summary)
    if _NETWORK is None:
        _init_worker(map_args)
    assert _NETWORK is not None
    record = {
        "entry_point": "trajguard.experiments.uldp_recovery",
        "argv": list(sys.argv[1:] if argv is None else argv),
        "map": {"region": args.region, "bbox": args.bbox, "crs": args.crs},
        "grid": {"modules": args.modules, "epsilons": args.epsilons, "ns": ns, "reps": args.reps},
        "seed": args.seed,
        "monte_carlo": mc,
        "workers": args.workers,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "wall_s": round(wall, 1),
        "parameters": MODULE_PARAMS,
        "error_metric": "L1 distance for shares, absolute difference for scalars",
        **_truth_record(PublicSimulator(_NETWORK)),
    }
    (out / "run.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    top = max(ns)
    print(f"wall {wall:.0f} s; largest n = {top}")
    print("module eps parameter          reject  err_truth [2.5-97.5%]   err_prior  gap_closed")
    for r in summary:
        if r["n"] == top:
            print(
                f"{r['module']:<6} {r['epsilon']:<3g} {r['parameter']:<18} "
                f"{r['rejection_rate']:5.2f}  {r['err_truth_mean']:.3f} "
                f"[{r['err_truth_lo']:.3f}-{r['err_truth_hi']:.3f}]   "
                f"{r['err_prior']:.3f}      {r['gap_closed_mean']:+.2f}"
            )
    print(f"written: {out}")


if __name__ == "__main__":
    main()
