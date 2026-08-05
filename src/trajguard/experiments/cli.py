"""Command-line entry points: ``trajguard run|report`` (design §10, argparse)."""

import argparse
from collections import defaultdict
from dataclasses import replace

from trajguard.datamodel import MetricValue
from trajguard.experiments.orchestrator import load_config, run_experiment
from trajguard.experiments.repeat import run_repetitions
from trajguard.reporting.report import generate_report


def _print_summary(config_path: str, seed: int | None = None) -> None:
    """Run an experiment and print a per-target metric table with bootstrap CIs.

    ``seed`` overrides the run seed for repetition runs: split_seed (resolved at
    load time from the YAML) stays put, so only the stochastic downstream steps
    change, and results land in a per-seed subdirectory instead of overwriting.
    """
    cfg = load_config(config_path)
    if seed is not None:
        cfg = replace(cfg, seed=seed, output_dir=cfg.output_dir / f"seed{seed}")
    values = run_experiment(cfg)

    by_result: dict[str, list[MetricValue]] = defaultdict(list)
    for v in values:
        by_result[v.result_id].append(v)

    print(f"\nexperiment: {cfg.exp_id}")
    print(f"results:    {cfg.output_dir}/metrics.csv\n")
    # mechanism-variant refs make result ids long; size the columns to the data
    rwidth = max([len(r) for r in by_result] + [len("result")])
    mwidth = max([len(v.name) for v in values] + [len("metric")])
    header = f"{'result':<{rwidth}} {'metric':<{mwidth}} {'value':>9}  {cfg.bootstrap_ci:.0%} CI"
    print(header)
    print("-" * len(header))
    for result_id in sorted(by_result):
        for v in by_result[result_id]:
            ci = (
                f"[{v.ci_low:.3f}, {v.ci_high:.3f}]"
                if v.ci_low is not None and v.ci_high is not None
                else ""
            )
            print(f"{result_id:<{rwidth}} {v.name:<{mwidth}} {v.value:>9.3f}  {ci}")


def _print_repetitions(config_path: str, seeds: list[int]) -> None:
    """Run the config once per seed and print the across-repetition aggregate."""
    cfg = load_config(config_path)
    summaries = run_repetitions(config_path, seeds)

    print(f"\nexperiment: {cfg.exp_id}  seeds: {seeds}  split_seed: {cfg.split_seed}")
    print(f"aggregate:  {cfg.output_dir}/repetitions.csv\n")
    rwidth = max([len(s.result_id) for s in summaries] + [len("result")])
    mwidth = max([len(s.metric) for s in summaries] + [len("metric")])
    header = f"{'result':<{rwidth}} {'metric':<{mwidth}} {'n':>2} {'mean':>9}  95% CI (repetitions)"
    print(header)
    print("-" * len(header))
    for s in summaries:
        if s.mean is None:
            print(f"{s.result_id:<{rwidth}} {s.metric:<{mwidth}} {s.n:>2} {'-':>9}")
            continue
        ci = f"[{s.ci_low:.3f}, {s.ci_high:.3f}]" if s.ci_low is not None else ""
        print(f"{s.result_id:<{rwidth}} {s.metric:<{mwidth}} {s.n:>2} {s.mean:>9.3f}  {ci}")


def main() -> None:
    """Parse arguments and dispatch subcommands."""
    parser = argparse.ArgumentParser(prog="trajguard", description="Trajectory privacy benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run an experiment from a YAML config")
    run_p.add_argument("config", help="path to an experiment YAML")
    run_p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="override the run seed (repetitions: the split stays pinned by "
        "experiment.split_seed; results go to <output_dir>/seed<N>)",
    )
    rep_p = sub.add_parser(
        "repeat", help="run one config under several run seeds and aggregate across repetitions"
    )
    rep_p.add_argument("config", help="path to an experiment YAML")
    rep_p.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        required=True,
        help="distinct run seeds, at least two; the population and split stay "
        "pinned by experiment.split_seed",
    )
    report_p = sub.add_parser("report", help="aggregate results/ into a Markdown risk report")
    report_p.add_argument("--results", default="results", help="directory of experiment outputs")
    report_p.add_argument("--out", default="reports", help="directory to write the report into")
    args = parser.parse_args()

    if args.command == "run":
        _print_summary(args.config, seed=args.seed)
    elif args.command == "repeat":
        _print_repetitions(args.config, args.seeds)
    elif args.command == "report":
        print(f"report: {generate_report(args.results, args.out)}")


if __name__ == "__main__":
    main()
