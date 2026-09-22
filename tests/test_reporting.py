"""Tests for the P7 reporting layer: run.json aggregation, risk matrix, report rendering."""

import csv
import json
import math
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest

from test_orchestrator import GEOIND_REF, geoind_config, write_config
from trajguard.datamodel import MetricValue
from trajguard.experiments.orchestrator import run
from trajguard.reporting.report import (
    export_tables,
    generate_report,
    load_results,
    risk_matrix,
    summarize_by_attack,
)
from trajguard.reporting.results_schema import ResultRow, write_results_csv

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


def test_load_results_parses_families_without_known_points(tmp_path: Path) -> None:
    """Reconstruction, POI, and membership ids carry no :k<N> suffix — the loader
    must parse them instead of rejecting the whole run.json (1c–1e regression)."""
    record = run_record(
        "families",
        [
            metric(
                "reconstruction:protected:geo_indistinguishability:epsilon=10.0",
                "mean_spatial_error_m",
                4.1,
            ),
            metric("poi_inference:protected:none", "home_error_m", 0.0),
            metric("membership_inference:synthetic:markov:order=1", "auc", 0.9),
        ],
    )
    runs = load_results(write_results(tmp_path, [record]))
    rows = {(r.attack, r.target): r for r in runs[0].rows}
    recon = rows[("reconstruction", "protected:geo_indistinguishability:epsilon=10.0")]
    assert recon.known_points is None and recon.mechanism == "geo_indistinguishability"
    assert rows[("poi_inference", "protected:none")].scope == "protected"
    mia = rows[("membership_inference", "synthetic:markov:order=1")]
    assert mia.scope == "synthetic" and mia.mechanism == "markov" and mia.value == 0.9


def test_parse_result_id_reads_the_distance_and_gallery_suffixes() -> None:
    """Only the non-default distance and gallery are spelled out, in that order and only
    after `:k<N>`; the defaults `dtw` and `rematched` stay implicit, so the ids measured
    in S4 keep their meaning."""
    from trajguard.reporting.report import _parse_result_id

    assert _parse_result_id("reidentification:raw:k3") == (
        "reidentification",
        "raw",
        3,
        "dtw",
        "rematched",
    )
    assert _parse_result_id("reidentification:protected:none:k3:dtw_norm") == (
        "reidentification",
        "protected:none",
        3,
        "dtw_norm",
        "rematched",
    )
    assert _parse_result_id("reidentification:protected:none:k3:release") == (
        "reidentification",
        "protected:none",
        3,
        "dtw",
        "release",
    )
    assert _parse_result_id("reidentification:protected:none:k3:dtw_norm:release") == (
        "reidentification",
        "protected:none",
        3,
        "dtw_norm",
        "release",
    )
    assert _parse_result_id("utility:protected:none") == (
        "utility",
        "protected:none",
        None,
        None,
        None,
    )
    # an attacker suffix only ever qualifies a knowledge level, never an arm on its own
    with pytest.raises(ValueError, match="k<N>"):
        _parse_result_id("reidentification:protected:none:release")


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


def test_risk_matrix_keeps_both_attacker_distances_apart(tmp_path: Path) -> None:
    """Both distances on one arm are two columns, not conflicting values of one; the
    `dtw` column keeps the label and the cells it had before `dtw_norm` existed."""
    record = run_record(
        "reid_both",
        [
            metric("reidentification:raw:k3", "top1_acc", 0.28, 0.1, 0.45),
            metric("reidentification:raw:k3:dtw_norm", "top1_acc", 0.52, 0.35, 0.7),
            metric("reidentification:protected:none:k3", "top1_acc", 0.28),
            metric("reidentification:protected:none:k3:dtw_norm", "top1_acc", 0.52),
        ],
    )
    runs = load_results(write_results(tmp_path, [record]))
    (m,) = risk_matrix(runs)
    assert m.columns == (
        ("reidentification", "top1_acc"),
        ("reidentification [dtw_norm]", "top1_acc"),
    )
    assert m.cells[("raw", "reidentification")].value == 0.28
    assert m.cells[("raw", "reidentification [dtw_norm]")].value == 0.52
    assert m.targets == ("raw", "protected:none")

    sections = summarize_by_attack(runs)
    assert [s.attack for s in sections] == ["reidentification", "reidentification [dtw_norm]"]
    assert all(len(s.rows) == 2 for s in sections)  # both arms in both sections

    report = generate_report(tmp_path / "results", tmp_path / "reports").read_text()
    assert "reidentification [dtw_norm] — top1_acc" in report


def test_risk_matrix_keeps_both_attacker_galleries_apart(tmp_path: Path) -> None:
    """The released gallery is a second attacker, not a second value of the same one: it
    gets its own column, and the arm's headline stays the rematched/dtw/largest-k row
    even when the release was measured at a larger knowledge level."""
    record = run_record(
        "reid_gallery",
        [
            metric("reidentification:raw:k3", "top1_acc", 0.28, 0.1, 0.45),
            metric("reidentification:raw:k3:dtw_norm", "top1_acc", 0.52),
            metric("reidentification:raw:k5:dtw_norm:release", "top1_acc", 0.61),
        ],
    )
    runs = load_results(write_results(tmp_path, [record]))
    (m,) = risk_matrix(runs)
    assert m.columns == (
        ("reidentification", "top1_acc"),
        ("reidentification [dtw_norm]", "top1_acc"),
        ("reidentification [dtw_norm, release]", "top1_acc"),
    )
    headline = m.cells[("raw", "reidentification")]
    assert headline.value == 0.28 and headline.known_points == 3
    assert m.cells[("raw", "reidentification [dtw_norm]")].value == 0.52
    release = m.cells[("raw", "reidentification [dtw_norm, release]")]
    assert release.value == 0.61 and release.known_points == 5

    sections = summarize_by_attack(runs)
    assert [s.attack for s in sections] == [
        "reidentification",
        "reidentification [dtw_norm]",
        "reidentification [dtw_norm, release]",
    ]

    report = generate_report(tmp_path / "results", tmp_path / "reports").read_text()
    assert "reidentification [dtw_norm, release] — top1_acc" in report


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
    """All four wired families flow through generate_report, including the master table."""
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["output_dir"] = str(tmp_path / "results" / cfg["experiment"]["id"])
    cfg["attacks"].append({"type": "reconstruction", "target_scope": ["protected"]})
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
    # the master table is the per-run results.csv, re-emitted verbatim
    run_rows = list(csv.DictReader((Path(cfg["experiment"]["output_dir"]) / "results.csv").open()))
    master_rows = list(csv.DictReader((tmp_path / "reports" / "results_master.csv").open()))
    assert master_rows == run_rows


def test_master_table_merges_runs_and_rejects_mixed_schemas(tmp_path: Path) -> None:
    from trajguard.reporting.report import merge_results_tables
    from trajguard.reporting.results_schema import RESULTS_COLUMNS

    def one_run(out: Path, exp_id: str) -> None:
        out.mkdir(parents=True)
        value = MetricValue("m:top1_acc", "reidentification:raw:k3", "top1_acc", 0.5, 0.4, 0.6, 10)
        row = ResultRow(
            value=value,
            family="reidentification",
            scope="raw",
            arm_id="",
            target_ref="raw",
            known_points=3,
        )
        provenance = {
            "exp_id": exp_id,
            "config_hash": "h" * 16,
            "git_commit": "c" * 40,
            "seed": 1,
            "split_seed": 1,
            "max_users": None,
            "created_at": "2026-08-05",
        }
        write_results_csv(out / "results.csv", provenance, [row], run_runtime_s=1.0)

    one_run(tmp_path / "results" / "exp_a", "exp_a")
    one_run(tmp_path / "results" / "exp_b" / "seed2", "exp_b")  # repeat-run layout
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    master = merge_results_tables(tmp_path / "results", out_dir)
    assert master is not None
    rows = list(csv.DictReader(master.open()))
    assert len(rows) == 2 and {r["exp_id"] for r in rows} == {"exp_a", "exp_b"}
    assert tuple(rows[0]) == RESULTS_COLUMNS

    # nothing to merge -> None, no file
    assert merge_results_tables(tmp_path / "empty", out_dir) is None
    # a table with a foreign header must fail loudly, not misalign columns
    bad = tmp_path / "results" / "exp_c"
    bad.mkdir()
    (bad / "results.csv").write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="schema"):
        merge_results_tables(tmp_path / "results", out_dir)


def test_master_table_fills_the_attacker_columns_for_legacy_runs(tmp_path: Path) -> None:
    """A results/ tree mixing tables written before `distance`, before `gallery`, and
    after both merges into one master table with the current header: the old
    reidentification rows get `dtw` / `rematched`, every other old family a blank cell,
    and a column the old table already had keeps its own value."""
    from trajguard.reporting.report import merge_results_tables
    from trajguard.reporting.results_schema import RESULTS_COLUMNS

    def write_run(exp_id: str, rows: list[ResultRow], drop: int) -> None:
        """One per-run table, with `drop` trailing columns cut as the older writers did."""
        out = tmp_path / "results" / exp_id
        out.mkdir(parents=True)
        provenance = {
            "exp_id": exp_id,
            "config_hash": "h" * 16,
            "git_commit": "c" * 40,
            "seed": 1,
            "split_seed": 1,
            "max_users": None,
            "created_at": "2026-08-05",
        }
        path = out / "results.csv"
        write_results_csv(path, provenance, rows, run_runtime_s=1.0)
        if drop:
            with path.open(newline="") as fh:
                cells = [row[: len(row) - drop] for row in csv.reader(fh)]
            with path.open("w", newline="") as fh:
                csv.writer(fh).writerows(cells)

    util_id = "utility:protected:none"
    util = ResultRow(
        value=MetricValue(
            f"{util_id}:cell_js_divergence", util_id, "cell_js_divergence", 0.4, None, None, None
        ),
        family="utility",
        scope="protected",
        arm_id="none",
        target_ref="protected:none",
    )
    write_run("exp_pre_distance", [reid_raw_row(0.5), util], drop=2)
    write_run("exp_pre_gallery", [replace(reid_raw_row(0.45), distance="dtw_norm"), util], drop=1)
    write_run(
        "exp_new",
        [replace(reid_raw_row(0.4), distance="dtw_norm", gallery="release")],
        drop=0,
    )

    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    master = merge_results_tables(tmp_path / "results", out_dir)
    assert master is not None
    rows = list(csv.DictReader(master.open()))
    assert tuple(rows[0]) == RESULTS_COLUMNS
    attacker = {(r["exp_id"], r["family"]): (r["distance"], r["gallery"]) for r in rows}
    assert attacker[("exp_pre_distance", "reidentification")] == ("dtw", "rematched")
    assert attacker[("exp_pre_distance", "utility")] == ("", "")
    # the pre-gallery table already carried its own distance; only `gallery` is filled in
    assert attacker[("exp_pre_gallery", "reidentification")] == ("dtw_norm", "rematched")
    assert attacker[("exp_pre_gallery", "utility")] == ("", "")
    assert attacker[("exp_new", "reidentification")] == ("dtw_norm", "release")


# --- seed<N>/ repetition layout (S4-4) --------------------------------------------


REID_RAW = "reidentification:raw:k10"
MIA_ID = "membership_inference:synthetic:markov:order=1"


def seed_run_record(
    exp_id: str, seed: int, metrics: list[dict[str, Any]], config_hash: str = "hash-a"
) -> dict[str, Any]:
    record = run_record(exp_id, metrics, config_hash=config_hash)
    record["seed"] = seed
    return record


def write_seed_run(root: Path, record: dict[str, Any], rows: list[ResultRow]) -> Path:
    """One seed<N>/ repetition run: run.json plus the matching results.csv."""
    seed_dir = root / record["exp_id"] / f"seed{record['seed']}"
    seed_dir.mkdir(parents=True)
    (seed_dir / "run.json").write_text(json.dumps(record))
    provenance = {
        "exp_id": record["exp_id"],
        "config_hash": record["config_hash"],
        "git_commit": record["git_commit"],
        "seed": record["seed"],
        "split_seed": 1,
        "max_users": None,
        "created_at": record["created_at"],
    }
    write_results_csv(seed_dir / "results.csv", provenance, rows, run_runtime_s=1.0)
    return seed_dir


def reid_raw_row(value: float) -> ResultRow:
    mv = MetricValue(f"{REID_RAW}:top1_acc", REID_RAW, "top1_acc", value, None, None, None)
    return ResultRow(
        value=mv,
        family="reidentification",
        scope="raw",
        arm_id="",
        target_ref="raw",
        known_points=10,
    )


def mia_row(name: str, value: float, n_nonmembers: int = 3) -> ResultRow:
    mv = MetricValue(f"{MIA_ID}:{name}", MIA_ID, name, value, None, None, None)
    return ResultRow(
        value=mv,
        family="membership_inference",
        scope="synthetic",
        arm_id="markov",
        target_ref="synthetic:markov:order=1",
        n_members=15,
        n_nonmembers=n_nonmembers,
    )


def test_load_results_aggregates_seed_layout(tmp_path: Path) -> None:
    """Three seed runs fold into one RunInfo: mean value + Student-t 95% CI per arm."""
    root = tmp_path / "results"
    for seed, value in [(1, 0.4), (2, 0.5), (3, 0.6)]:
        record = seed_run_record("reid_rep", seed, [metric(REID_RAW, "top1_acc", value)])
        write_seed_run(root, record, [reid_raw_row(value)])
    (run_info,) = load_results(root)
    assert run_info.seeds == (1, 2, 3)
    assert run_info.seed_label == "1, 2, 3"
    (row,) = run_info.rows  # one row per (arm, metric), not one per seed
    assert row.attack == "reidentification" and row.target == "raw" and row.known_points == 10
    assert row.value == pytest.approx(0.5)
    half = 4.303 * 0.1 / math.sqrt(3)  # t(df=2) * std(ddof=1) / sqrt(n)
    assert row.ci_low == pytest.approx(0.5 - half)
    assert row.ci_high == pytest.approx(0.5 + half)


def test_load_results_mixes_flat_and_seed_experiments(tmp_path: Path) -> None:
    root = write_results(tmp_path, [baseline_record()])
    for seed, value in [(1, 0.4), (2, 0.6)]:
        record = seed_run_record("reid_rep", seed, [metric(REID_RAW, "top1_acc", value)])
        write_seed_run(root, record, [reid_raw_row(value)])
    runs = {r.exp_id: r for r in load_results(root)}
    assert set(runs) == {"reid_baseline", "reid_rep"}
    assert runs["reid_baseline"].seeds == (42,)  # flat runs load unchanged
    assert runs["reid_rep"].rows[0].value == pytest.approx(0.5)


def test_mixed_layouts_in_one_experiment_dir_rejected(tmp_path: Path) -> None:
    root = write_results(tmp_path, [baseline_record()])
    record = seed_run_record("reid_baseline", 1, [metric(REID_RAW, "top1_acc", 0.4)])
    write_seed_run(root, record, [reid_raw_row(0.4)])
    with pytest.raises(ValueError, match="ambiguous"):
        load_results(root)


def test_seed_run_without_results_csv_rejected(tmp_path: Path) -> None:
    root = tmp_path / "results"
    record = seed_run_record("reid_rep", 1, [metric(REID_RAW, "top1_acc", 0.4)])
    seed_dir = write_seed_run(root, record, [reid_raw_row(0.4)])
    (seed_dir / "results.csv").unlink()
    with pytest.raises(ValueError, match="results.csv"):
        load_results(root)


def test_seed_runs_disagreeing_on_provenance_rejected(tmp_path: Path) -> None:
    root = tmp_path / "results"
    a = seed_run_record("reid_rep", 1, [metric(REID_RAW, "top1_acc", 0.4)])
    b = seed_run_record("reid_rep", 2, [metric(REID_RAW, "top1_acc", 0.5)], config_hash="hash-b")
    write_seed_run(root, a, [reid_raw_row(0.4)])
    write_seed_run(root, b, [reid_raw_row(0.5)])
    with pytest.raises(ValueError, match="config_hash"):
        load_results(root)


def test_generate_report_masks_stored_unmeasurable_tpr(tmp_path: Path) -> None:
    """Retro-mask (S4-2): a stored artifact tpr@fpr survives in results.csv from an old
    campaign; the report must suppress it with a warning while auc stays intact."""
    root = tmp_path / "results"
    for seed, auc in [(1, 0.60), (2, 0.62), (3, 0.61)]:
        record = seed_run_record(
            "mia_rep",
            seed,
            [metric(MIA_ID, "auc", auc), metric(MIA_ID, "tpr@fpr=0.001", 0.067)],
        )
        write_seed_run(root, record, [mia_row("auc", auc), mia_row("tpr@fpr=0.001", 0.067)])
    out = tmp_path / "reports"
    text = generate_report(root, out).read_text()

    assert "## Warnings" in text
    assert "tpr@fpr=0.001 needs >= 1000 non-members, runs have 3" in text
    with (out / "metrics_long.csv").open() as fh:
        rows = {r["metric"]: r for r in csv.DictReader(fh)}
    assert rows["tpr@fpr=0.001"]["value"] == ""  # suppressed, not 0.067
    assert float(rows["auc"]["value"]) == pytest.approx(0.61)
    # the MIA headline metric is auc, so the risk matrix keeps a finite cell
    with (out / "risk_matrix.csv").open() as fh:
        (matrix_row,) = list(csv.DictReader(fh))
    assert float(matrix_row["membership_inference:auc"]) == pytest.approx(0.61)


def test_flat_run_json_warnings_surface_in_report(tmp_path: Path) -> None:
    record = baseline_record()
    record["warnings"] = [f"{MIA_ID}: tpr@fpr=0.1 needs >= 10 non-members, run has 4"]
    root = write_results(tmp_path, [record])
    text = generate_report(root, tmp_path / "reports").read_text()
    assert "## Warnings" in text
    assert "needs >= 10 non-members, run has 4" in text


def test_seeded_experiment_gets_one_tradeoff_plot(tmp_path: Path) -> None:
    """Aggregation leaves one RunInfo per experiment, so seed runs cannot collide on
    the tradeoff_<exp_id>.png filename."""
    eps2 = "protected:geo_indistinguishability:epsilon=2.0"

    def rows_for(value: float) -> list[ResultRow]:
        reid = MetricValue(
            f"reidentification:{eps2}:k10:top1_acc",
            f"reidentification:{eps2}:k10",
            "top1_acc",
            value,
            None,
            None,
            None,
        )
        util = MetricValue(
            f"utility:{eps2}:cell_js_divergence",
            f"utility:{eps2}",
            "cell_js_divergence",
            0.4,
            None,
            None,
            None,
        )
        return [
            ResultRow(
                value=reid,
                family="reidentification",
                scope="protected",
                arm_id="geo_indistinguishability",
                target_ref=eps2,
                epsilon=2.0,
                known_points=10,
            ),
            ResultRow(
                value=util,
                family="utility",
                scope="protected",
                arm_id="geo_indistinguishability",
                target_ref=eps2,
                epsilon=2.0,
            ),
        ]

    root = tmp_path / "results"
    for seed, value in [(1, 0.2), (2, 0.3)]:
        record = seed_run_record(
            "geoind_rep",
            seed,
            [
                metric(f"reidentification:{eps2}:k10", "top1_acc", value),
                metric(f"utility:{eps2}", "cell_js_divergence", 0.4),
            ],
        )
        write_seed_run(root, record, rows_for(value))
    out = tmp_path / "reports"
    generate_report(root, out)
    assert [p.name for p in sorted(out.glob("tradeoff_*.png"))] == ["tradeoff_geoind_rep.png"]
