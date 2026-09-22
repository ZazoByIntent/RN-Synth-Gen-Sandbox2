"""Tests for the unified results-table schema (docs/REZULTATI_SHEMA.md)."""

import csv
from pathlib import Path

import pytest

from trajguard.datamodel import MetricValue
from trajguard.experiments.repeat import REPETITIONS_COLUMNS
from trajguard.reporting.results_schema import (
    LEGACY_RESULTS_COLUMNS,
    LEGACY_RESULTS_HEADERS,
    PROVENANCE_COLUMNS,
    RESULTS_COLUMNS,
    ResultRow,
    write_results_csv,
)

DOC = Path(__file__).parent.parent / "docs" / "REZULTATI_SHEMA.md"

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
        result_id="reidentification:raw:k5",
        name=name,
        value=value,
        ci_low=value - 0.1 if ci else None,
        ci_high=value + 0.1 if ci else None,
        n_bootstrap=200 if ci else None,
    )


def test_schema_columns_are_unique_and_documented() -> None:
    """Every column the code writes is named in docs/REZULTATI_SHEMA.md — the doc is
    the agreed template, so code and document must not drift apart silently."""
    assert len(RESULTS_COLUMNS) == len(set(RESULTS_COLUMNS))
    assert set(PROVENANCE_COLUMNS) <= set(RESULTS_COLUMNS)
    doc = DOC.read_text()
    missing = [c for c in RESULTS_COLUMNS if f"`{c}`" not in doc]
    assert not missing, f"columns not documented in {DOC.name}: {missing}"


def test_repetitions_columns_are_documented_and_lead_with_provenance() -> None:
    """The across-seeds file follows the same rule: every column is named in the doc,
    and it opens with the two run-provenance columns, like `results.csv`."""
    assert len(REPETITIONS_COLUMNS) == len(set(REPETITIONS_COLUMNS))
    assert REPETITIONS_COLUMNS[:2] == ("exp_id", "config_hash")
    doc = DOC.read_text()
    missing = [c for c in REPETITIONS_COLUMNS if f"`{c}`" not in doc]
    assert not missing, f"columns not documented in {DOC.name}: {missing}"


def test_write_results_csv_follows_column_order(tmp_path: Path) -> None:
    row = ResultRow(
        value=_metric("top1_acc", 0.5),
        family="reidentification",
        scope="raw",
        arm_id="",
        target_ref="raw",
        known_points=5,
        n_pool=8,
        n_gallery_users=2,
        n_probes=8,
        n_rematch_dropped=0,
        attack_runtime_s=0.25,
        peak_memory_mb=12.5,
    )
    path = tmp_path / "results.csv"
    write_results_csv(path, PROVENANCE, [row], run_runtime_s=1.5)

    with path.open() as fh:
        reader = csv.reader(fh)
        header = tuple(next(reader))
        cells = next(reader)
    assert header == RESULTS_COLUMNS
    record = dict(zip(header, cells, strict=True))
    assert record["exp_id"] == "exp" and record["seed"] == "3" and record["split_seed"] == "42"
    assert record["max_users"] == ""  # None -> blank
    assert record["family"] == "reidentification" and record["scope"] == "raw"
    assert record["known_points"] == "5" and record["epsilon"] == ""
    assert record["metric"] == "top1_acc" and record["value"] == "0.5"
    assert record["attack_runtime_s"] == "0.25" and record["run_runtime_s"] == "1.5"
    assert record["peak_memory_mb"] == "12.5"


def test_attacker_axes_are_appended_at_the_end_of_the_header(tmp_path: Path) -> None:
    """The two attacker axes were appended at the end, `distance` first and
    `gallery` after it — the one change older readers can absorb — and
    LEGACY_RESULTS_HEADERS names the headers written before each of them."""
    assert RESULTS_COLUMNS[-2] == "distance"
    assert RESULTS_COLUMNS[-1] == "gallery"
    assert LEGACY_RESULTS_HEADERS == (RESULTS_COLUMNS[:-1], RESULTS_COLUMNS[:-2])
    assert LEGACY_RESULTS_COLUMNS is LEGACY_RESULTS_HEADERS[0]

    row = ResultRow(
        value=_metric("top1_acc", 0.5),
        family="reidentification",
        scope="raw",
        arm_id="",
        target_ref="raw",
        known_points=5,
        distance="dtw_norm",
        gallery="release",
    )
    without_gallery = ResultRow(
        value=_metric("cell_js_divergence", 0.4),
        family="utility",
        scope="raw",
        arm_id="",
        target_ref="raw",
    )
    path = tmp_path / "results.csv"
    write_results_csv(path, PROVENANCE, [row, without_gallery], run_runtime_s=1.5)

    with path.open() as fh:
        reader = csv.reader(fh)
        header = tuple(next(reader))
        reid, util = next(reader), next(reader)
    assert header[-2:] == ("distance", "gallery")
    assert reid[-2] == "dtw_norm" and reid[-1] == "release"
    assert util[-2] == "" and util[-1] == ""  # None -> blank, like every other axis


def test_write_results_csv_blanks_none_and_non_finite(tmp_path: Path) -> None:
    row = ResultRow(
        value=_metric("home_error_m", float("nan"), ci=False),
        family="poi_inference",
        scope="protected",
        arm_id="geo_indistinguishability",
        target_ref="protected:geo_indistinguishability:epsilon=0.1",
        epsilon=0.1,
        spent_budget=float("inf"),
    )
    path = tmp_path / "results.csv"
    write_results_csv(path, PROVENANCE, [row], run_runtime_s=1.0)
    record = next(csv.DictReader(path.open()))
    assert record["value"] == "" and record["ci_low"] == "" and record["n_bootstrap"] == ""
    assert record["spent_budget"] == ""  # non-finite -> blank, like metrics.csv
    assert record["epsilon"] == "0.1"


def test_write_results_csv_missing_provenance_is_loud(tmp_path: Path) -> None:
    incomplete = {k: v for k, v in PROVENANCE.items() if k != "split_seed"}
    with pytest.raises(ValueError, match="split_seed"):
        write_results_csv(tmp_path / "results.csv", incomplete, [], run_runtime_s=0.0)
