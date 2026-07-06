"""Command-line entry points: ``trajguard run|report`` (design §10, argparse)."""

import argparse
from collections import defaultdict

from trajguard.datamodel import MetricValue
from trajguard.experiments.orchestrator import load_config, run_experiment
from trajguard.reporting.report import generate_report


def _print_summary(config_path: str) -> None:
    """Run an experiment and print a per-target metric table with bootstrap CIs."""
    cfg = load_config(config_path)
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


def main() -> None:
    """Parse arguments and dispatch subcommands."""
    parser = argparse.ArgumentParser(prog="trajguard", description="Trajectory privacy benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run an experiment from a YAML config")
    run_p.add_argument("config", help="path to an experiment YAML")
    report_p = sub.add_parser("report", help="aggregate results/ into a Markdown risk report")
    report_p.add_argument("--results", default="results", help="directory of experiment outputs")
    report_p.add_argument("--out", default="reports", help="directory to write the report into")
    args = parser.parse_args()

    if args.command == "run":
        _print_summary(args.config)
    elif args.command == "report":
        print(f"report: {generate_report(args.results, args.out)}")


if __name__ == "__main__":
    main()
