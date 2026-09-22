"""Tests for the per-run plots over unified results-table rows (wave-2 O5)."""

from pathlib import Path
from typing import Any

import pytest

from trajguard.datamodel import MetricValue
from trajguard.reporting import plots
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
    distance: str | None = None,
    ci: bool = True,
    runtime: float | None = 0.5,
) -> ResultRow:
    result_id = f"{family}:{target_ref}" + (f":k{known_points}" if known_points else "")
    if distance is not None and distance != "dtw":
        result_id += f":{distance}"
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
        distance=distance,
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


# --- attacker distance: dtw vs dtw_norm -------------------------------------------


def _raw_reid(value: float, k: int, distance: str) -> ResultRow:
    return _row(
        "reidentification",
        "raw",
        "top1_acc",
        value,
        scope="raw",
        arm_id="",
        known_points=k,
        distance=distance,
    )


def test_headline_rows_represents_an_arm_by_its_default_distance() -> None:
    """One row per arm: `dtw` represents it even when `dtw_norm` measured a larger k,
    so the risk matrix and the bar plots keep their pre-dtw_norm meaning."""
    both = [_raw_reid(0.3, 5, "dtw"), _raw_reid(0.6, 10, "dtw_norm")]
    _, picked = headline_rows(both, "reidentification")
    assert [(r.known_points, r.distance) for r in picked] == [(5, "dtw")]
    # a run that measured only the normalised attacker is still represented
    _, only_norm = headline_rows([_raw_reid(0.6, 10, "dtw_norm")], "reidentification")
    assert [(r.known_points, r.distance) for r in only_norm] == [(10, "dtw_norm")]


def _capture_line_labels(monkeypatch: pytest.MonkeyPatch, labels: list[str]) -> None:
    """Record the legend label of every line a plot draws, before the figure is saved."""
    save = plots._save

    def capture(plt: object, fig: Any, path: Path) -> Path:
        labels.extend(str(line.get_label()) for line in fig.axes[0].lines)
        return save(plt, fig, path)

    monkeypatch.setattr(plots, "_save", capture)


def test_plot_by_knowledge_draws_one_line_per_arm_and_distance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [
        _raw_reid(0.3, 3, "dtw"),
        _raw_reid(0.4, 5, "dtw"),
        _raw_reid(0.6, 3, "dtw_norm"),
        _raw_reid(0.7, 5, "dtw_norm"),
    ]
    labels: list[str] = []
    _capture_line_labels(monkeypatch, labels)
    (written,) = plot_by_knowledge(rows, tmp_path)
    assert written.name == "by_knowledge_reidentification.png"
    # the default distance keeps the bare arm label; only the second one is spelled out
    assert labels == ["raw", "raw [dtw_norm]"]


def test_plot_by_epsilon_draws_one_line_per_arm_and_distance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two distances measured on one arm are two lines, not one zig-zag.

    Without the distance in the group key, the four rows below would share a single
    polyline that jumps between the dtw and the dtw_norm value at each epsilon, under
    one label.
    """
    rows = [
        _row(
            "reidentification",
            f"protected:geo_indistinguishability:epsilon={eps}",
            "top1_acc",
            value,
            epsilon=eps,
            known_points=5,
            distance=distance,
        )
        for eps, distance, value in (
            (1.0, "dtw", 0.3),
            (10.0, "dtw", 0.5),
            (1.0, "dtw_norm", 0.6),
            (10.0, "dtw_norm", 0.8),
        )
    ]
    labels: list[str] = []
    _capture_line_labels(monkeypatch, labels)
    (written,) = plot_by_epsilon(rows, tmp_path)
    assert written.name == "by_epsilon_reidentification.png"
    assert labels == [
        "geo_indistinguishability, k=5",
        "geo_indistinguishability, k=5 [dtw_norm]",
    ]
