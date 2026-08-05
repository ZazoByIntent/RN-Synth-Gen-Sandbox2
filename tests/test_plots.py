"""Tests for the per-run plots over unified results-table rows (wave-2 O5)."""

from pathlib import Path

import pytest

from trajguard.datamodel import MetricValue
from trajguard.reporting.plots import (
    headline_metric,
    headline_rows,
    is_share_metric,
    plot_by_epsilon,
    plot_by_knowledge,
    plot_mechanisms,
    plot_runtime,
)
from trajguard.reporting.results_schema import ResultRow


def _row(
    family: str,
    target_ref: str,
    metric: str,
    value: float,
    *,
    scope: str = "protected",
    arm_id: str = "geo_indistinguishability",
    epsilon: float | None = None,
    unit_m: float | None = None,
    known_points: int | None = None,
    ci: bool = True,
    runtime: float | None = 0.5,
) -> ResultRow:
    result_id = f"{family}:{target_ref}" + (f":k{known_points}" if known_points else "")
    return ResultRow(
        value=MetricValue(
            metric_id=f"{result_id}:{metric}",
            result_id=result_id,
            name=metric,
            value=value,
            ci_low=value - 0.05 if ci else None,
            ci_high=value + 0.05 if ci else None,
            n_bootstrap=200 if ci else None,
        ),
        family=family,
        scope=scope,
        arm_id=arm_id,
        target_ref=target_ref,
        epsilon=epsilon,
        unit_m=unit_m,
        known_points=known_points,
        attack_runtime_s=runtime,
    )


def _geoind_grid(family: str = "reidentification", metric: str = "top1_acc") -> list[ResultRow]:
    """Headline rows of one family over a two-ε geo-ind grid, reid-style at k∈{3,5}."""
    rows = []
    for eps in (1.0, 10.0):
        ref = f"protected:geo_indistinguishability:epsilon={eps}"
        ks: tuple[int | None, ...] = (3, 5) if family == "reidentification" else (None,)
        for k in ks:
            rows.append(_row(family, ref, metric, 0.2 + eps / 20, epsilon=eps, known_points=k))
    return rows


def test_headline_metric_prefers_the_family_metric_then_falls_back() -> None:
    assert headline_metric("reidentification", ["linkage_rate", "top1_acc"]) == "top1_acc"
    assert headline_metric("reidentification", ["linkage_rate", "topk_acc"]) == "linkage_rate"
    assert headline_metric("unknown_family", ["b_metric", "a_metric"]) == "a_metric"
    with pytest.raises(ValueError, match="no metrics present"):
        headline_metric("reidentification", [])


def test_is_share_metric_follows_the_schema_unit_convention() -> None:
    assert all(
        is_share_metric(m)
        for m in ("top1_acc", "auc", "tpr@fpr=0.01", "home_localised", "linkage_rate")
    )
    assert not any(is_share_metric(m) for m in ("home_error_m", "hausdorff_m", "dtw_m"))


def test_headline_rows_picks_max_known_points_per_arm_in_display_order() -> None:
    rows = [
        _row("reidentification", "raw", "top1_acc", 0.9, scope="raw", arm_id="", known_points=3),
        _row("reidentification", "raw", "top1_acc", 0.95, scope="raw", arm_id="", known_points=5),
        *_geoind_grid(),
        # a non-headline metric must never be picked
        _row("reidentification", "raw", "linkage_rate", 0.1, scope="raw", arm_id=""),
    ]
    headline, picked = headline_rows(rows, "reidentification")
    assert headline == "top1_acc"
    assert [r.target_ref for r in picked] == [
        "raw",
        "protected:geo_indistinguishability:epsilon=1.0",
        "protected:geo_indistinguishability:epsilon=10.0",
    ]
    assert all(r.known_points == 5 for r in picked)


def test_plot_by_epsilon_writes_one_file_per_family(tmp_path: Path) -> None:
    rows = _geoind_grid() + _geoind_grid("reconstruction", "mean_spatial_error_m")
    written = plot_by_epsilon(rows, tmp_path)
    assert [p.name for p in written] == [
        "by_epsilon_reconstruction.png",
        "by_epsilon_reidentification.png",
    ]
    assert all(p.stat().st_size > 0 for p in written)


def test_plot_by_epsilon_skips_families_without_an_epsilon_axis(tmp_path: Path) -> None:
    rows = [
        _row("reidentification", "raw", "top1_acc", 0.9, scope="raw", arm_id="", known_points=5),
        _row("reidentification", "protected:none", "top1_acc", 0.9, arm_id="none", known_points=5),
    ]
    assert plot_by_epsilon(rows, tmp_path) == []
    assert list(tmp_path.iterdir()) == []


def test_plot_by_knowledge_covers_only_families_with_the_knob(tmp_path: Path) -> None:
    rows = [
        _row("reidentification", "raw", "top1_acc", 0.9, scope="raw", arm_id="", known_points=3),
        _row("reidentification", "raw", "top1_acc", 0.95, scope="raw", arm_id="", known_points=5),
        *_geoind_grid(),
        *_geoind_grid("reconstruction", "mean_spatial_error_m"),  # no knowledge knob
    ]
    written = plot_by_knowledge(rows, tmp_path)
    assert [p.name for p in written] == ["by_knowledge_reidentification.png"]
    assert written[0].stat().st_size > 0


def test_plot_mechanisms_writes_one_file_per_family(tmp_path: Path) -> None:
    rows = [
        _row("reidentification", "raw", "top1_acc", 0.9, scope="raw", arm_id="", known_points=5),
        *_geoind_grid(),
        _row("poi_inference", "protected:none", "home_error_m", 0.0, arm_id="none"),
    ]
    written = plot_mechanisms(rows, tmp_path)
    assert [p.name for p in written] == [
        "mechanisms_poi_inference.png",
        "mechanisms_reidentification.png",
    ]
    assert all(p.stat().st_size > 0 for p in written)


def test_plot_runtime_counts_each_attack_invocation_once(tmp_path: Path) -> None:
    rows = [
        # two metric rows of the same invocation (same result_id) — one bar
        _row("reidentification", "raw", "top1_acc", 0.9, scope="raw", arm_id="", known_points=5),
        _row("reidentification", "raw", "topk_acc", 0.95, scope="raw", arm_id="", known_points=5),
        _row("reconstruction", "protected:geo_indistinguishability:epsilon=1.0", "dtw_m", 12.0),
        # utility rows carry no attack runtime and never enter the plot
        _row("utility", "protected:none", "cell_js_divergence", 0.01, arm_id="none", runtime=None),
    ]
    (path,) = plot_runtime(rows, tmp_path)
    assert path.name == "runtime.png" and path.stat().st_size > 0


def test_plot_runtime_without_runtimes_writes_nothing(tmp_path: Path) -> None:
    rows = [_row("utility", "protected:none", "cell_js_divergence", 0.01, runtime=None)]
    assert plot_runtime(rows, tmp_path) == []
    assert list(tmp_path.iterdir()) == []
