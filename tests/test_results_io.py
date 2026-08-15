"""Tests for reading unified results tables back and aggregating across seeds."""

import csv
import math
from dataclasses import replace
from pathlib import Path

import pytest

from trajguard.datamodel import MetricValue
from trajguard.reporting.plots import plot_by_epsilon
from trajguard.reporting.results_io import (
    LoadedRow,
    RunProvenance,
    aggregate_over_seeds,
    read_results_csv,
)
from trajguard.reporting.results_schema import ResultRow, write_results_csv

PROVENANCE = {
    "exp_id": "exp",
    "config_hash": "a1b2c3d4e5f60718",
    "git_commit": "c" * 40,
    "seed": 3,
    "split_seed": 42,
    "max_users": None,
    "created_at": "2026-08-05T12:00:00+00:00",
}


def _metric(name: str, value: float, ci: bool = True) -> MetricValue:
    return MetricValue(
        metric_id=f"x:{name}",
        result_id="reidentification:protected:geo_indistinguishability:epsilon=1.0:k5",
        name=name,
        value=value,
        ci_low=value - 0.1 if ci else None,
        ci_high=value + 0.1 if ci else None,
        n_bootstrap=200 if ci else None,
    )


def _row(value: MetricValue) -> ResultRow:
    return ResultRow(
        value=value,
        family="reidentification",
        scope="protected",
        arm_id="geo_indistinguishability",
        target_ref="protected:geo_indistinguishability:epsilon=1.0",
        epsilon=1.0,
        unit_m=50.0,
        known_points=5,
        n_pool=8,
        n_gallery_users=2,
        n_probes=8,
        n_rematch_dropped=1,
        attack_runtime_s=0.25,
        peak_memory_mb=12.5,
    )


def _loaded(seed: int, value: float, **overrides: object) -> LoadedRow:
    prov = RunProvenance(
        exp_id="exp",
        config_hash="a1b2c3d4e5f60718",
        git_commit="c" * 40,
        seed=seed,
        split_seed=42,
        max_users=None,
        created_at="2026-08-05T12:00:00+00:00",
    )
    row = replace(_row(_metric("top1_acc", value)), **overrides)  # type: ignore[arg-type]
    return LoadedRow(provenance=prov, row=row, run_runtime_s=2.0)


def test_read_results_csv_round_trips(tmp_path: Path) -> None:
    """Every column survives write -> read; blanks come back as None (nan for value)."""
    full = _row(_metric("top1_acc", 0.5))
    sparse = ResultRow(
        value=_metric("home_error_m", float("nan"), ci=False),
        family="poi_inference",
        scope="protected",
        arm_id="geo_indistinguishability",
        target_ref="protected:geo_indistinguishability:epsilon=0.1",
        epsilon=0.1,
    )
    path = tmp_path / "results.csv"
    write_results_csv(path, PROVENANCE, [full, sparse], run_runtime_s=1.5)

    loaded = read_results_csv(path)
    assert len(loaded) == 2
    first, second = loaded

    assert first.provenance == RunProvenance(
        exp_id="exp",
        config_hash="a1b2c3d4e5f60718",
        git_commit="c" * 40,
        seed=3,
        split_seed=42,
        max_users=None,
        created_at="2026-08-05T12:00:00+00:00",
    )
    assert first.run_runtime_s == 1.5
    # The metric round-trips except metric_id, which the CSV does not carry.
    same_id = replace(full.value, metric_id=first.row.value.metric_id)
    assert first.row == replace(full, value=same_id)
    assert first.row.value.result_id == full.value.result_id

    assert second.row.family == "poi_inference" and second.row.epsilon == 0.1
    assert math.isnan(second.row.value.value)  # blank value cell -> non-finite again
    assert second.row.value.ci_low is None and second.row.value.n_bootstrap is None
    assert second.row.unit_m is None and second.row.known_points is None


def test_read_results_csv_rejects_foreign_header(tmp_path: Path) -> None:
    """A table whose header differs from RESULTS_COLUMNS fails loudly, never misaligns."""
    path = tmp_path / "results.csv"
    with path.open("w", newline="") as fh:
        csv.writer(fh).writerow(["exp_id", "unexpected", "columns"])
    with pytest.raises(ValueError, match="header"):
        read_results_csv(path)


def test_aggregate_over_seeds_means_and_student_t_ci() -> None:
    """Across-seed mean and Student-t 95% CI; bootstrap fields do not survive."""
    records = [_loaded(1, 0.4), _loaded(2, 0.5), _loaded(3, 0.6)]
    (agg,) = aggregate_over_seeds(records)

    assert agg.value.value == pytest.approx(0.5)
    half = 4.303 * 0.1 / math.sqrt(3)  # t(df=2) * std(ddof=1) / sqrt(n)
    assert agg.value.ci_low == pytest.approx(0.5 - half)
    assert agg.value.ci_high == pytest.approx(0.5 + half)
    assert agg.value.n_bootstrap is None  # the CI is across seeds, not bootstrap
    assert agg.value.result_id == records[0].row.value.result_id
    # Identity and pivot axes are preserved; runtimes are averaged.
    assert agg.family == "reidentification" and agg.epsilon == 1.0 and agg.known_points == 5
    assert agg.attack_runtime_s == pytest.approx(0.25)
    assert agg.n_pool == 8  # identical across seeds -> kept


def test_aggregate_over_seeds_drops_counts_that_differ() -> None:
    """Per-seed counts (e.g. n_rematch_dropped under fresh noise) do not pretend."""
    records = [_loaded(1, 0.4), _loaded(2, 0.5, n_rematch_dropped=3)]
    (agg,) = aggregate_over_seeds(records)
    assert agg.n_rematch_dropped is None
    assert agg.n_pool == 8  # still identical -> still kept


def test_aggregate_over_seeds_rejects_duplicate_seed() -> None:
    """The same run loaded twice (e.g. master + per-run table) must not bias the mean."""
    with pytest.raises(ValueError, match="seed"):
        aggregate_over_seeds([_loaded(1, 0.4), _loaded(1, 0.4), _loaded(2, 0.5)])


def test_aggregate_over_seeds_keeps_experiments_apart() -> None:
    """Rows that share a result_id but not (exp_id, config_hash) never merge."""
    other = _loaded(1, 0.9)
    other = LoadedRow(
        provenance=replace(other.provenance, config_hash="ffffffffffffffff"),
        row=other.row,
        run_runtime_s=other.run_runtime_s,
    )
    agg = aggregate_over_seeds([_loaded(1, 0.4), _loaded(2, 0.6), other])
    values = sorted(r.value.value for r in agg)
    assert values == pytest.approx([0.5, 0.9])


def test_aggregated_rows_feed_the_existing_plots(tmp_path: Path) -> None:
    """The bridge output plugs straight into reporting.plots without adaptation."""
    rows = aggregate_over_seeds([_loaded(1, 0.4), _loaded(2, 0.6)])
    written = plot_by_epsilon(rows, tmp_path)
    assert written == [tmp_path / "by_epsilon_reidentification.png"]
    assert written[0].exists()
