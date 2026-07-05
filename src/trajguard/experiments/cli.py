"""Command-line entry point: ``trajguard run <config>`` (design §10, argparse)."""

import argparse
from collections import defaultdict

from trajguard.datamodel import MetricValue
from trajguard.experiments.orchestrator import load_config, run


def _print_summary(config_path: str) -> None:
    """Run an experiment and print a per-target metric table with bootstrap CIs."""
    values = run(config_path)
    cfg = load_config(config_path)

    by_result: dict[str, list[MetricValue]] = defaultdict(list)
    for v in values:
        by_result[v.result_id].append(v)

    print(f"\nexperiment: {cfg.exp_id}")
    print(f"results:    {cfg.output_dir}/metrics.csv\n")
    header = f"{'target : k':<28} {'metric':<12} {'value':>7}  95% CI"
    print(header)
    print("-" * len(header))
    for result_id in sorted(by_result):
        label = result_id.removeprefix("reidentification:")
        for v in by_result[result_id]:
            ci = f"[{v.ci_low:.3f}, {v.ci_high:.3f}]" if v.ci_low is not None else ""
            print(f"{label:<28} {v.name:<12} {v.value:>7.3f}  {ci}")


def main() -> None:
    """Parse arguments and dispatch subcommands."""
    parser = argparse.ArgumentParser(prog="trajguard", description="Trajectory privacy benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run an experiment from a YAML config")
    run_p.add_argument("config", help="path to an experiment YAML")
    args = parser.parse_args()

    if args.command == "run":
        _print_summary(args.config)


if __name__ == "__main__":
    main()
