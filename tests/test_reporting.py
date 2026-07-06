"""Tests for the P7 reporting layer: run.json aggregation, risk matrix, report rendering."""

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest

from test_orchestrator import GEOIND_REF, geoind_config, write_config
from trajguard.experiments.orchestrator import run
from trajguard.reporting.report import (
    export_tables,
    generate_report,
    load_results,
    risk_matrix,
)

FIXTURES = Path(__file__).parent / "fixtures"


def metric(
    result_id: str,
    name: str,
    value: float | None,
    lo: float | None = None,
    hi: float | None = None,
) -> dict[str, Any]:
    return {"result_id": result_id, "metric": name, "value": value, "ci_low": lo, "ci_high": hi}


def run_record(
    exp_id: str,
    metrics: list[dict[str, Any]],
    config_hash: str = "hash-a",
    arms: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A run.json payload mirroring orchestrator._write_results()."""
    return {
        "exp_id": exp_id,
        "config_hash": config_hash,
        "git_commit": "0123456789abcdef",
        "seed": 42,
        "created_at": "2026-07-06T12:00:00+00:00",
        "n_matched": 8,
        "n_dropped": 2,
        "split_counts": {"train": 4, "test": 2, "shadow": 1, "attack": 1},
        "bootstrap": {"n": 200, "ci": 0.95},
        "arms": arms or {"raw": {"n_pool": 8, "n_probes": 8}},
        "runtime_s": 1.5,
        "metrics": metrics,
    }


def write_results(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    root = tmp_path / "results"
    for record in records:
        exp_dir = root / record["exp_id"]
        exp_dir.mkdir(parents=True)
        (exp_dir / "run.json").write_text(json.dumps(record))
    return root


def baseline_record() -> dict[str, Any]:
    return run_record(
        "reid_baseline",
        [
            metric("reidentification:raw:k3", "top1_acc", 0.5, 0.25, 0.75),
            metric("reidentification:raw:k10", "top1_acc", 0.75, 0.5, 1.0),
            metric("reidentification:raw:k10", "top5_acc", 1.0, 1.0, 1.0),
            metric("reidentification:protected:none:k10", "top1_acc", 0.75, 0.5, 1.0),
        ],
    )


def geoind_record() -> dict[str, Any]:
    eps2 = "protected:geo_indistinguishability:epsilon=2.0"
    eps10 = "protected:geo_indistinguishability:epsilon=10.0"
    return run_record(
        "reid_geoind",
        [
            # same pipeline (config_hash), so the raw cell must dedupe with the baseline run
            metric("reidentification:raw:k10", "top1_acc", 0.75, 0.5, 1.0),
            metric(f"reidentification:{eps2}:k10", "top1_acc", 0.25, 0.0, 0.5),
            metric(f"reidentification:{eps10}:k10", "top1_acc", 0.5, 0.25, 0.75),
            metric(f"utility:{eps2}", "cell_js_divergence", 0.4, 0.3, 0.5),
            metric(f"utility:{eps10}", "cell_js_divergence", 0.1, 0.05, 0.15),
        ],
        arms={
            "raw": {"n_pool": 8, "n_probes": 8},
            eps2: {"n_pool": 5, "n_probes": 8, "n_rematch_dropped": 3, "spent_budget": 80.0},
        },
    )


# --- loading and parsing ----------------------------------------------------------


def test_load_results_parses_result_ids(tmp_path: Path) -> None:
    runs = load_results(write_results(tmp_path, [geoind_record()]))
    rows = {(r.attack, r.target, r.known_points, r.metric): r for r in runs[0].rows}

    attacked = rows[
        ("reidentification", "protected:geo_indistinguishability:epsilon=2.0", 10, "top1_acc")
    ]
    assert attacked.scope == "protected"
    assert attacked.mechanism == "geo_indistinguishability"
    assert attacked.params == "epsilon=2.0"
    assert attacked.value == 0.25

    util = rows[
        ("utility", "protected:geo_indistinguishability:epsilon=2.0", None, "cell_js_divergence")
    ]
    assert util.known_points is None and util.value == 0.4

    raw = rows[("reidentification", "raw", 10, "top1_acc")]
    assert raw.scope == "raw" and raw.mechanism == "" and raw.params == ""


def test_load_results_rejects_junk_result_id(tmp_path: Path) -> None:
    record = run_record("bad", [metric("garbage", "top1_acc", 0.5)])
    with pytest.raises(ValueError, match="garbage"):
        load_results(write_results(tmp_path, [record]))


def test_missing_results_dir_is_loud(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="run.json"):
        load_results(tmp_path / "nowhere")


# --- risk matrix ------------------------------------------------------------------


def test_risk_matrix_pivots_headline_at_max_k(tmp_path: Path) -> None:
    runs = load_results(write_results(tmp_path, [baseline_record(), geoind_record()]))
    matrices = risk_matrix(runs)

    assert len(matrices) == 1  # same config_hash -> one population-comparable group
    m = matrices[0]
    assert m.exp_ids == ("reid_baseline", "reid_geoind")
    assert m.columns == (("reidentification", "top1_acc"),)
    # raw first, identity next, then numeric param order (2.0 before 10.0)
    assert m.targets == (
        "raw",
        "protected:none",
        "protected:geo_indistinguishability:epsilon=2.0",
        "protected:geo_indistinguishability:epsilon=10.0",
    )
    raw_cell = m.cells[("raw", "reidentification")]
    assert raw_cell.value == 0.75 and raw_cell.known_points == 10  # k=10 beats k=3
    eps2 = m.cells[("protected:geo_indistinguishability:epsilon=2.0", "reidentification")]
    assert eps2.value == 0.25 and eps2.exp_id == "reid_geoind"


def test_risk_matrix_conflicting_values_are_loud(tmp_path: Path) -> None:
    a = baseline_record()
    b = geoind_record()
    b["metrics"][0] = metric("reidentification:raw:k10", "top1_acc", 0.9, 0.8, 1.0)
    runs = load_results(write_results(tmp_path, [a, b]))
    with pytest.raises(ValueError, match="conflicting"):
        risk_matrix(runs)


def test_risk_matrix_groups_by_config_hash(tmp_path: Path) -> None:
    a = baseline_record()
    b = geoind_record()
    b["config_hash"] = "hash-b"
    b["metrics"][0] = metric("reidentification:raw:k10", "top1_acc", 0.9, 0.8, 1.0)
    matrices = risk_matrix(load_results(write_results(tmp_path, [a, b])))
    assert [m.config_hash for m in matrices] == ["hash-a", "hash-b"]  # no cross-group merge


def test_risk_matrix_headline_falls_back_for_unknown_attack(tmp_path: Path) -> None:
    record = run_record(
        "novel",
        [
            metric("novel_attack:raw:k3", "zzz_score", 0.4),
            metric("novel_attack:raw:k3", "aaa_score", 0.6),
        ],
    )
    (m,) = risk_matrix(load_results(write_results(tmp_path, [record])))
    assert m.columns == (("novel_attack", "aaa_score"),)  # first sorted metric, not dropped


# --- tables -----------------------------------------------------------------------


def test_export_tables_roundtrip(tmp_path: Path) -> None:
    runs = load_results(write_results(tmp_path, [geoind_record()]))
    out = tmp_path / "reports"
    out.mkdir()
    written = export_tables(runs, out)
    assert [p.name for p in written] == ["metrics_long.csv", "metrics_long.parquet"]

    with (out / "metrics_long.csv").open() as fh:
        csv_rows = list(csv.DictReader(fh))
    assert len(csv_rows) == len(runs[0].rows)

    table = pq.read_table(out / "metrics_long.parquet").to_pylist()
    by_key = {(r["target"], r["known_points"], r["metric"]): r for r in table}
    attacked = by_key[("protected:geo_indistinguishability:epsilon=2.0", 10, "top1_acc")]
    assert attacked["value"] == 0.25 and attacked["ci_low"] == 0.0
    util = by_key[("protected:geo_indistinguishability:epsilon=2.0", None, "cell_js_divergence")]
    assert util["value"] == 0.4  # utility rows keep a null known_points


def test_export_tables_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="xlsx"):
        export_tables([], tmp_path, formats=("xlsx",))


# --- report generation ------------------------------------------------------------


def test_generate_report_writes_all_artifacts(tmp_path: Path) -> None:
    results = write_results(tmp_path, [baseline_record(), geoind_record()])
    out = tmp_path / "reports"
    report_path = generate_report(results, out)

    text = report_path.read_text()
    assert "# trajguard risk report" in text
    assert "reid_baseline" in text and "reid_geoind" in text
    assert "reidentification — top1_acc" in text  # risk matrix column
    assert "0.750 [0.500, 1.000] @k=10" in text  # raw headline cell with CI and k
    assert "protected:geo_indistinguishability:epsilon=2.0" in text
    assert "n=200, 95% CI" in text  # bootstrap provenance
    assert "cell_js_divergence" in text  # utility section
    assert "tradeoff_reid_geoind.png" in text  # only the run with utility gets a plot
    assert "tradeoff_reid_baseline.png" not in text

    assert (out / "metrics_long.csv").exists()
    assert (out / "metrics_long.parquet").exists()
    assert (out / "tradeoff_reid_geoind.png").stat().st_size > 0
    with (out / "risk_matrix.csv").open() as fh:
        matrix_rows = list(csv.DictReader(fh))
    assert matrix_rows[0]["target"] == "raw"
    assert matrix_rows[0]["reidentification:top1_acc"] == "0.75"


def test_generate_report_out_dir_under_data_raw_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="immutable"):
        generate_report(tmp_path, "data/raw/reports")


# --- integration: report over a real orchestrator run ------------------------------


@pytest.fixture()
def beijing_maps_dir(tmp_path: Path) -> Path:
    """Copy the committed beijing_fixture network into a 'beijing' dir (matches native_region)."""
    src = FIXTURES / "maps" / "beijing_fixture"
    dst = tmp_path / "maps" / "beijing"
    shutil.copytree(src, dst)
    return tmp_path / "maps"


def test_report_from_real_orchestrator_run(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["output_dir"] = str(tmp_path / "results" / cfg["experiment"]["id"])
    run(write_config(tmp_path, cfg))

    report_path = generate_report(tmp_path / "results", tmp_path / "reports")

    text = report_path.read_text()
    assert "## Risk matrix" in text
    assert "reidentification — top1_acc" in text
    assert f"protected:{GEOIND_REF}" in text
    assert "## Arm health" in text
    assert (tmp_path / "reports" / "risk_matrix.csv").exists()
    assert (tmp_path / "reports" / "metrics_long.parquet").exists()
    assert (tmp_path / "reports" / "tradeoff_test_reid.png").stat().st_size > 0
