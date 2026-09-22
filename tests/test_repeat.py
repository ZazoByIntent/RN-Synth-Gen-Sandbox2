"""Tests for the thin repetition runner on the committed fixtures (no network)."""

import csv
import json
import math
from pathlib import Path

import pytest

from test_orchestrator import beijing_maps_dir, geoind_config, write_config
from trajguard.datamodel import MetricValue
from trajguard.experiments.repeat import (
    REPETITIONS_COLUMNS,
    aggregate,
    read_run_provenance,
    run_repetitions,
    t_ppf_975,
)

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


def test_read_run_provenance_rejects_disagreeing_seeds(tmp_path: Path) -> None:
    for seed, config_hash in ((1, "a" * 16), (2, "b" * 16)):
        run_dir = tmp_path / f"seed{seed}"
        run_dir.mkdir()
        (run_dir / "run.json").write_text(json.dumps({"exp_id": "exp", "config_hash": config_hash}))
    with pytest.raises(ValueError, match="must share exp_id and config_hash") as excinfo:
        read_run_provenance(tmp_path, [1, 2])
    message = str(excinfo.value)
    assert "seed1=" in message and "seed2=" in message  # the message names both culprits
    assert "a" * 16 in message and "b" * 16 in message


def test_read_run_provenance_rejects_missing_or_incomplete_run_json(tmp_path: Path) -> None:
    (tmp_path / "seed1").mkdir()
    (tmp_path / "seed1" / "run.json").write_text(
        json.dumps({"exp_id": "exp", "config_hash": "a" * 16})
    )
    with pytest.raises(ValueError, match="seed2 wrote no run.json"):
        read_run_provenance(tmp_path, [1, 2])

    (tmp_path / "seed2").mkdir()
    (tmp_path / "seed2" / "run.json").write_text(json.dumps({"exp_id": "exp"}))
    with pytest.raises(ValueError, match="seed2 run.json lacks config_hash"):
        read_run_provenance(tmp_path, [1, 2])

    (tmp_path / "seed2" / "run.json").write_text(
        json.dumps({"exp_id": None, "config_hash": "a" * 16})
    )
    with pytest.raises(ValueError, match="seed2 run.json lacks exp_id"):
        read_run_provenance(tmp_path, [1, 2])


def test_run_repetitions_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["split_seed"] = 7
    summaries = run_repetitions(write_config(tmp_path, cfg), [1, 2])

    # per-seed artifacts plus the aggregate, over one shared pool cache
    for seed in (1, 2):
        assert (tmp_path / "out" / f"seed{seed}" / "run.json").exists()
    assert len(list((tmp_path / "cache").iterdir())) == 1
    with (tmp_path / "out" / "repetitions.csv").open() as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames or ()) == REPETITIONS_COLUMNS
        rows = list(reader)
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
    runs = [json.loads((tmp_path / "out" / f"seed{s}" / "run.json").read_text()) for s in (1, 2)]
    assert runs[0]["split_counts"] == runs[1]["split_counts"]

    # provenance on every row, taken from what the repetitions actually wrote
    assert runs[0]["exp_id"] == runs[1]["exp_id"]
    assert runs[0]["config_hash"] == runs[1]["config_hash"]
    assert {r["exp_id"] for r in rows} == {runs[0]["exp_id"]}
    assert {r["config_hash"] for r in rows} == {runs[0]["config_hash"]}
