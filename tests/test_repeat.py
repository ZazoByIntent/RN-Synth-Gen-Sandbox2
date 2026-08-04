"""Tests for the thin repetition runner on the committed fixtures (no network)."""

import csv
import json
import math
from pathlib import Path

import pytest

from test_orchestrator import beijing_maps_dir, geoind_config, write_config
from trajguard.datamodel import MetricValue
from trajguard.experiments.repeat import aggregate, run_repetitions, t_ppf_975

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here


def _mv(result_id: str, name: str, value: float) -> MetricValue:
    return MetricValue(
        metric_id=f"{result_id}:{name}",
        result_id=result_id,
        name=name,
        value=value,
        ci_low=value,
        ci_high=value,
        n_bootstrap=0,
    )


def test_aggregate_mean_and_t_interval() -> None:
    values = {s: [_mv("r", "top1_acc", v)] for s, v in zip((1, 2, 3), (0.4, 0.5, 0.6), strict=True)}
    (summary,) = aggregate(values)
    assert summary.n == 3
    assert summary.mean == pytest.approx(0.5)
    half = 4.303 * 0.1 / math.sqrt(3)  # t(df=2) * sample std / sqrt(n)
    assert summary.ci_low == pytest.approx(0.5 - half)
    assert summary.ci_high == pytest.approx(0.5 + half)


def test_aggregate_drops_non_finite_and_handles_empty_group() -> None:
    values = {
        1: [_mv("r", "m", 0.2), _mv("dead", "m", float("nan"))],
        2: [_mv("r", "m", float("nan")), _mv("dead", "m", float("nan"))],
    }
    by_key = {(s.result_id, s.metric): s for s in aggregate(values)}
    survivor = by_key[("r", "m")]
    assert (survivor.n, survivor.mean) == (1, pytest.approx(0.2))
    assert survivor.ci_low == survivor.ci_high == survivor.mean  # degenerate CI at n=1
    dead = by_key[("dead", "m")]
    assert dead.n == 0 and dead.mean is None


def test_t_table_is_conservative_between_entries() -> None:
    assert t_ppf_975(2) == 4.303
    assert t_ppf_975(22) == 2.086  # falls back to df=20, the wider interval
    assert t_ppf_975(1000) == 1.980
    with pytest.raises(ValueError, match="degrees of freedom"):
        t_ppf_975(0)


def test_seed_validation() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        run_repetitions("unused.yaml", [1])
    with pytest.raises(ValueError, match="distinct"):
        run_repetitions("unused.yaml", [1, 1])


def test_run_repetitions_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["split_seed"] = 7
    summaries = run_repetitions(write_config(tmp_path, cfg), [1, 2])

    # per-seed artifacts plus the aggregate, over one shared pool cache
    for seed in (1, 2):
        assert (tmp_path / "out" / f"seed{seed}" / "run.json").exists()
    assert len(list((tmp_path / "cache").iterdir())) == 1
    rows = list(csv.DictReader((tmp_path / "out" / "repetitions.csv").open()))
    assert {r["metric"] for r in rows} >= {"top1_acc", "linkage_rate"}
    by_key = {(s.result_id, s.metric): s for s in summaries}
    for row in rows:
        s = by_key[(row["result_id"], row["metric"])]
        assert int(row["n_repetitions"]) == s.n
        if s.mean is not None:
            assert float(row["mean"]) == pytest.approx(s.mean)
            assert s.ci_low is not None and s.ci_high is not None
            assert s.ci_low <= s.mean <= s.ci_high

    # the split is identical across repetitions (pinned by split_seed)
    counts = [
        json.loads((tmp_path / "out" / f"seed{s}" / "run.json").read_text())["split_counts"]
        for s in (1, 2)
    ]
    assert counts[0] == counts[1]
