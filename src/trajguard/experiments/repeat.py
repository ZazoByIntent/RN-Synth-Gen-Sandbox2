"""Thin repetition runner: one config, several run seeds, CIs across repetitions.

Runs the same experiment once per seed — the population and the user split stay
pinned by ``experiment.split_seed``, resolved at load time — and aggregates every
metric across the repetitions into a mean and a Student-t 95% confidence
interval. This interval measures variance *between* repetitions (fresh mechanism
noise and attacker knowledge per seed) and must not be confused with the per-run
bootstrap CI, which measures resampling uncertainty *within* a single run.

Deliberately a thin harness around :func:`run_experiment` (like
``experiments.rnldp_eval``): no orchestrator changes, no new dependencies —
the t critical values come from a small built-in table instead of scipy.
"""

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from trajguard.datamodel import MetricValue
from trajguard.experiments.orchestrator import load_config, run_experiment

# Two-sided 95% Student-t critical values by degrees of freedom. Lookups between
# entries fall back to the largest tabulated df not exceeding the requested one,
# which has the *larger* critical value — a conservative (wider) interval.
_T_975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    12: 2.179,
    14: 2.145,
    16: 2.120,
    18: 2.101,
    20: 2.086,
    25: 2.060,
    30: 2.042,
    40: 2.021,
    60: 2.000,
    120: 1.980,
}


def t_ppf_975(df: int) -> float:
    """Two-sided 95% Student-t critical value, conservative between table entries."""
    if df < 1:
        raise ValueError(f"degrees of freedom must be >= 1, got {df}")
    candidates = [k for k in _T_975 if k <= df]
    return _T_975[max(candidates)] if candidates else 1.96


@dataclass(frozen=True, slots=True)
class RepetitionSummary:
    """One metric aggregated across repetitions; None fields when no finite value."""

    result_id: str
    metric: str
    n: int  # repetitions that produced a finite value
    mean: float | None
    ci_low: float | None
    ci_high: float | None


def aggregate(values_by_seed: Mapping[int, Sequence[MetricValue]]) -> list[RepetitionSummary]:
    """Mean and Student-t 95% CI per (result_id, metric) across the seeds' values.

    Non-finite values (degenerate arms) are dropped per group; ``n`` counts what
    remains. A single surviving value gets a degenerate CI equal to its mean.
    """
    groups: dict[tuple[str, str], list[float]] = {}
    for _, values in sorted(values_by_seed.items()):
        for v in values:
            groups.setdefault((v.result_id, v.name), []).append(v.value)
    out: list[RepetitionSummary] = []
    for (result_id, metric), raw in groups.items():
        vals = np.array([x for x in raw if math.isfinite(x)], dtype=float)
        n = len(vals)
        if n == 0:
            out.append(RepetitionSummary(result_id, metric, 0, None, None, None))
            continue
        mean = float(vals.mean())
        if n == 1:
            out.append(RepetitionSummary(result_id, metric, 1, mean, mean, mean))
            continue
        half = t_ppf_975(n - 1) * float(vals.std(ddof=1)) / math.sqrt(n)
        out.append(RepetitionSummary(result_id, metric, n, mean, mean - half, mean + half))
    return out


def run_repetitions(config_path: str | Path, seeds: Sequence[int]) -> list[RepetitionSummary]:
    """Run one config once per seed and write ``repetitions.csv`` under output_dir.

    Each repetition writes its usual artifacts to ``<output_dir>/seed<N>``; the
    aggregate lands in ``<output_dir>/repetitions.csv``. Seeds must be distinct
    and at least two, otherwise "across repetitions" has no meaning.
    """
    if len(seeds) < 2:
        raise ValueError(f"need at least 2 seeds for repetitions, got {list(seeds)}")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"seeds must be distinct, got {list(seeds)}")
    cfg = load_config(config_path)
    values_by_seed: dict[int, list[MetricValue]] = {}
    for seed in seeds:
        rep = replace(cfg, seed=seed, output_dir=cfg.output_dir / f"seed{seed}")
        values_by_seed[seed] = run_experiment(rep)
    summaries = aggregate(values_by_seed)
    _write_csv(summaries, cfg.output_dir / "repetitions.csv")
    return summaries


def _write_csv(summaries: Sequence[RepetitionSummary], path: Path) -> None:
    """Write the aggregate as CSV; None fields become blank cells."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["result_id", "metric", "n_repetitions", "mean", "ci_low", "ci_high"])
        for s in summaries:
            writer.writerow([s.result_id, s.metric, s.n, s.mean, s.ci_low, s.ci_high])
