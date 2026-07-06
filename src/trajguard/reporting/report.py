"""Aggregate results/ into tables, a risk matrix, plots, and a Markdown report (design §2.2 #10)."""

import csv
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from jinja2 import Environment, PackageLoader

from trajguard.reporting.tradeoff import TradeoffPoint, plot_tradeoff

# Headline metric per attack family for the risk matrix; a family whose preferred
# metric is absent (or that is not listed) falls back to its first metric, sorted —
# nothing is silently dropped. Names match what the attack modules emit.
_HEADLINE_PREFERENCE = {
    "reidentification": "top1_acc",
    "membership_inference": "auc",
    "reconstruction": "mean_spatial_error_m",
    "poi_inference": "home_error_m",
}
_TRADEOFF_PRIVACY = "top1_acc"
_TRADEOFF_UTILITY = "cell_js_divergence"
_SPLIT_ORDER = ("train", "test", "shadow", "attack")
_EXPORT_FORMATS = ("csv", "parquet")


# --- parsed result rows -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricRow:
    """One metric value from a run.json, with its result_id parsed into columns."""

    exp_id: str
    attack: str  # attack family, or "utility"
    target: str  # full target ref: raw | protected:<mech>[:<params>]
    scope: str  # raw | protected | synthetic
    mechanism: str  # "" for raw
    params: str  # "" or "epsilon=1.0,unit_m=25.0"
    known_points: int | None
    metric: str
    value: float | None
    ci_low: float | None
    ci_high: float | None


@dataclass(frozen=True, slots=True)
class RunInfo:
    """Provenance, arm stats, and parsed metric rows of one experiment run."""

    exp_id: str
    config_hash: str
    git_commit: str
    seed: int
    created_at: str
    n_matched: int
    n_dropped: int
    split_counts: tuple[tuple[str, int], ...]
    runtime_s: float
    bootstrap_n: int | None
    bootstrap_ci: float | None
    arms: tuple[tuple[str, dict[str, Any]], ...]
    rows: tuple[MetricRow, ...]

    @property
    def split_label(self) -> str:
        """Human-readable split sizes, canonical splits first."""
        if not self.split_counts:
            return "–"
        order = {s: i for i, s in enumerate(_SPLIT_ORDER)}
        items = sorted(self.split_counts, key=lambda kv: (order.get(kv[0], len(order)), kv[0]))
        return ", ".join(f"{k}={v}" for k, v in items)

    @property
    def bootstrap_label(self) -> str:
        """Bootstrap sample count and CI level, when the run recorded them."""
        if self.bootstrap_n is None:
            return "–"
        ci = f", {self.bootstrap_ci:.0%} CI" if self.bootstrap_ci is not None else ""
        return f"n={self.bootstrap_n}{ci}"


def _parse_target_ref(ref: str) -> tuple[str, str, str]:
    """Target ref → (scope, mechanism, params); loud on anything unrecognised."""
    if ref == "raw":
        return "raw", "", ""
    scope, _, rest = ref.partition(":")
    mech, _, params = rest.partition(":")
    if scope not in {"protected", "synthetic"} or not mech:
        raise ValueError(f"unrecognised target ref {ref!r}")
    return scope, mech, params


def _parse_result_id(result_id: str) -> tuple[str, str, int | None]:
    """result_id → (attack family, target ref, known_points); loud on junk."""
    parts = result_id.split(":")
    if parts[0] == "utility" and len(parts) >= 2:
        target = ":".join(parts[1:])
        _parse_target_ref(target)
        return "utility", target, None
    tail = re.fullmatch(r"k(\d+)", parts[-1]) if len(parts) >= 3 else None
    if tail is None:
        raise ValueError(f"unrecognised result_id {result_id!r}")
    target = ":".join(parts[1:-1])
    _parse_target_ref(target)
    return parts[0], target, int(tail.group(1))


def _params_key(params: str) -> tuple[tuple[str, float], ...]:
    """Numeric sort key for a params string, so epsilon=2.0 sorts before epsilon=10.0.

    Non-numeric values map to inf: they sort after numeric ones and stay in
    input order among themselves (sorted() is stable).
    """
    keyed: list[tuple[str, float]] = []
    for pair in params.split(","):
        if not pair:
            continue
        name, _, value = pair.partition("=")
        try:
            keyed.append((name, float(value)))
        except ValueError:
            keyed.append((name, math.inf))
    return tuple(keyed)


def _target_order(ref: str) -> tuple[Any, ...]:
    """Display order for target arms: raw, then identity, then by mechanism/params."""
    scope, mech, params = _parse_target_ref(ref)
    if scope == "raw":
        return (0,)
    if mech == "none":
        return (1, scope)
    return (2, scope, mech, _params_key(params))


def _opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _metric_row(exp_id: str, entry: dict[str, Any]) -> MetricRow:
    attack, target, known_points = _parse_result_id(str(entry["result_id"]))
    scope, mechanism, params = _parse_target_ref(target)
    return MetricRow(
        exp_id=exp_id,
        attack=attack,
        target=target,
        scope=scope,
        mechanism=mechanism,
        params=params,
        known_points=known_points,
        metric=str(entry["metric"]),
        value=_opt_float(entry["value"]),
        ci_low=_opt_float(entry["ci_low"]),
        ci_high=_opt_float(entry["ci_high"]),
    )


def _load_run(path: Path) -> RunInfo:
    data = json.loads(path.read_text())
    try:
        exp_id = str(data["exp_id"])
        boot = data.get("bootstrap") or {}
        arms = tuple(
            sorted(
                ((str(ref), dict(arm)) for ref, arm in data.get("arms", {}).items()),
                key=lambda kv: _target_order(kv[0]),
            )
        )
        return RunInfo(
            exp_id=exp_id,
            config_hash=str(data.get("config_hash", "")),
            git_commit=str(data.get("git_commit", "")),
            seed=int(data["seed"]),
            created_at=str(data.get("created_at", "")),
            n_matched=int(data.get("n_matched", 0)),
            n_dropped=int(data.get("n_dropped", 0)),
            split_counts=tuple(sorted(data.get("split_counts", {}).items())),
            runtime_s=float(data.get("runtime_s", 0.0)),
            bootstrap_n=int(boot["n"]) if "n" in boot else None,
            bootstrap_ci=float(boot["ci"]) if "ci" in boot else None,
            arms=arms,
            rows=tuple(_metric_row(exp_id, entry) for entry in data["metrics"]),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError(f"{path}: malformed run.json ({err})") from err


def load_results(results_dir: str | Path) -> list[RunInfo]:
    """Load every results/<exp_id>/run.json; loud when there is nothing to report."""
    root = Path(results_dir)
    run_files = sorted(root.glob("*/run.json"))
    if not run_files:
        raise FileNotFoundError(
            f"no run.json found under {root}/*/ — run an experiment first (trajguard run <config>)"
        )
    return [_load_run(path) for path in run_files]


# --- tables -----------------------------------------------------------------------

_EXPORT_COLUMNS = (
    "exp_id",
    "attack",
    "target",
    "scope",
    "mechanism",
    "params",
    "known_points",
    "metric",
    "value",
    "ci_low",
    "ci_high",
)


def export_tables(
    runs: Sequence[RunInfo], out_dir: Path, formats: Sequence[str] = _EXPORT_FORMATS
) -> tuple[Path, ...]:
    """Write the tidy long-format metric table as metrics_long.{csv,parquet}."""
    unknown = set(formats) - set(_EXPORT_FORMATS)
    if unknown:
        raise ValueError(f"unsupported export formats {sorted(unknown)}")
    rows = [row for run in runs for row in run.rows]
    written: list[Path] = []
    if "csv" in formats:
        path = out_dir / "metrics_long.csv"
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(_EXPORT_COLUMNS)
            for r in rows:
                writer.writerow(
                    [
                        r.exp_id,
                        r.attack,
                        r.target,
                        r.scope,
                        r.mechanism,
                        r.params,
                        "" if r.known_points is None else r.known_points,
                        r.metric,
                        "" if r.value is None else r.value,
                        "" if r.ci_low is None else r.ci_low,
                        "" if r.ci_high is None else r.ci_high,
                    ]
                )
        written.append(path)
    if "parquet" in formats:
        path = out_dir / "metrics_long.parquet"
        pq.write_table(  # type: ignore[no-untyped-call]
            pa.table(
                {
                    "exp_id": [r.exp_id for r in rows],
                    "attack": [r.attack for r in rows],
                    "target": [r.target for r in rows],
                    "scope": [r.scope for r in rows],
                    "mechanism": [r.mechanism for r in rows],
                    "params": [r.params for r in rows],
                    "known_points": pa.array([r.known_points for r in rows], pa.int64()),
                    "metric": [r.metric for r in rows],
                    "value": pa.array([r.value for r in rows], pa.float64()),
                    "ci_low": pa.array([r.ci_low for r in rows], pa.float64()),
                    "ci_high": pa.array([r.ci_high for r in rows], pa.float64()),
                }
            ),
            path,
        )
        written.append(path)
    return tuple(written)


# --- risk matrix ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskCell:
    """One risk-matrix cell: the headline metric for (target arm, attack family)."""

    value: float | None
    ci_low: float | None
    ci_high: float | None
    known_points: int | None
    exp_id: str


@dataclass(frozen=True, slots=True)
class RiskMatrix:
    """Attack × mechanism × params pivot for one pipeline (config-hash) group."""

    config_hash: str
    exp_ids: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]  # (attack family, headline metric)
    targets: tuple[str, ...]
    cells: dict[tuple[str, str], RiskCell]  # (target, attack) -> cell


def risk_matrix(runs: Sequence[RunInfo]) -> tuple[RiskMatrix, ...]:
    """Pivot attack results into one risk matrix per pipeline group.

    Runs are grouped by config_hash (same map/dataset/cleaning/matching/split/seed):
    only within such a group are arms population-comparable, so only there do rows
    merge across experiments. Each cell holds the family's headline metric at the
    largest known_points available for that arm.
    """
    groups: dict[str, list[RunInfo]] = {}
    for run in runs:
        groups.setdefault(run.config_hash, []).append(run)
    return tuple(_group_matrix(h, groups[h]) for h in sorted(groups))


def _group_matrix(config_hash: str, runs: list[RunInfo]) -> RiskMatrix:
    rows = [r for run in runs for r in run.rows if r.attack != "utility"]
    columns: list[tuple[str, str]] = []
    cells: dict[tuple[str, str], RiskCell] = {}
    for attack in sorted({r.attack for r in rows}):
        attack_rows = [r for r in rows if r.attack == attack]
        present = sorted({r.metric for r in attack_rows})
        preferred = _HEADLINE_PREFERENCE.get(attack)
        headline = preferred if preferred in present else present[0]
        columns.append((attack, headline))
        headline_rows = [r for r in attack_rows if r.metric == headline]
        for target in {r.target for r in headline_rows}:
            target_rows = [r for r in headline_rows if r.target == target]
            k_max = max(-1 if r.known_points is None else r.known_points for r in target_rows)
            best = sorted(
                (
                    r
                    for r in target_rows
                    if (-1 if r.known_points is None else r.known_points) == k_max
                ),
                key=lambda r: r.exp_id,
            )
            if len({r.value for r in best}) > 1:
                raise ValueError(
                    f"conflicting {attack}/{headline} values for target {target!r} within "
                    f"pipeline {config_hash}: {[(r.exp_id, r.value) for r in best]} — "
                    "results/ mixes incompatible runs"
                )
            top = best[0]
            cells[(target, attack)] = RiskCell(
                top.value, top.ci_low, top.ci_high, top.known_points, top.exp_id
            )
    targets = sorted({target for target, _ in cells}, key=_target_order)
    return RiskMatrix(
        config_hash=config_hash,
        exp_ids=tuple(run.exp_id for run in runs),
        columns=tuple(columns),
        targets=tuple(targets),
        cells=cells,
    )


def _write_risk_matrix_csv(matrices: Sequence[RiskMatrix], path: Path) -> Path:
    """Flat CSV of every matrix (values only; CIs live in metrics_long)."""
    columns = sorted({col for m in matrices for col in m.columns})
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pipeline", "target", *[f"{a}:{metric}" for a, metric in columns]])
        for m in matrices:
            for target in m.targets:
                row: list[Any] = [m.config_hash, target]
                for attack, _ in columns:
                    cell = m.cells.get((target, attack))
                    row.append("" if cell is None or cell.value is None else cell.value)
                writer.writerow(row)
    return path


# --- per-attack summaries ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SummaryRow:
    """One summary-table row: a target arm at one attacker knowledge level."""

    target: str
    known_points: int | None
    cells: dict[str, MetricRow]  # metric name -> row


@dataclass(frozen=True, slots=True)
class AttackSection:
    """All metrics of one attack family (or 'utility') within one experiment run."""

    exp_id: str
    attack: str
    metrics: tuple[str, ...]
    rows: tuple[SummaryRow, ...]


def summarize_by_attack(runs: Sequence[RunInfo]) -> tuple[AttackSection, ...]:
    """One section per (run, attack family), metrics pivoted into columns."""
    sections: list[AttackSection] = []
    for run in runs:
        for attack in sorted({r.attack for r in run.rows}):
            attack_rows = [r for r in run.rows if r.attack == attack]
            present = sorted({r.metric for r in attack_rows})
            preferred = _HEADLINE_PREFERENCE.get(attack)
            if preferred in present:
                metrics = (preferred, *[m for m in present if m != preferred])
            else:
                metrics = tuple(present)
            keys = sorted(
                {(r.target, r.known_points) for r in attack_rows},
                key=lambda tk: (_target_order(tk[0]), -1 if tk[1] is None else tk[1]),
            )
            rows = tuple(
                SummaryRow(
                    target=target,
                    known_points=k,
                    cells={
                        r.metric: r
                        for r in attack_rows
                        if r.target == target and r.known_points == k
                    },
                )
                for target, k in keys
            )
            sections.append(AttackSection(run.exp_id, attack, metrics, rows))
    return tuple(sections)


# --- tradeoff plots ---------------------------------------------------------------


def _tradeoff_points(run: RunInfo) -> list[TradeoffPoint]:
    """Rebuild the P5 tradeoff points (cell JSD vs top1_acc at max k) from run rows."""
    utility = {
        r.target: r.value
        for r in run.rows
        if r.attack == "utility" and r.metric == _TRADEOFF_UTILITY
    }
    privacy = [
        r
        for r in run.rows
        if r.attack != "utility" and r.metric == _TRADEOFF_PRIVACY and r.known_points is not None
    ]
    if not utility or not privacy:
        return []
    k_max = max(r.known_points for r in privacy if r.known_points is not None)
    points: list[TradeoffPoint] = []
    for r in sorted(
        (r for r in privacy if r.known_points == k_max), key=lambda r: _target_order(r.target)
    ):
        if r.value is None:
            continue
        x = 0.0 if r.target == "raw" else utility.get(r.target)
        points.append((math.nan if x is None else x, r.value, r.target))
    return points


# --- report rendering -------------------------------------------------------------


def _fmt(value: float | None) -> str:
    """Number for the report: 3 decimals, dash for missing/non-finite."""
    return "–" if value is None or not math.isfinite(value) else f"{value:.3f}"


def _fmt_cell(cell: RiskCell | None) -> str:
    if cell is None or cell.value is None:
        return "–"
    text = _fmt(cell.value)
    if cell.ci_low is not None and cell.ci_high is not None:
        text += f" [{_fmt(cell.ci_low)}, {_fmt(cell.ci_high)}]"
    if cell.known_points is not None:
        text += f" @k={cell.known_points}"
    return text


def _fmt_vci(row: MetricRow | None) -> str:
    if row is None or row.value is None:
        return "–"
    text = _fmt(row.value)
    if row.ci_low is not None and row.ci_high is not None:
        text += f" [{_fmt(row.ci_low)}, {_fmt(row.ci_high)}]"
    return text


def _environment() -> Environment:
    env = Environment(
        loader=PackageLoader("trajguard.reporting"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["num"] = _fmt
    env.filters["cell"] = _fmt_cell
    env.filters["vci"] = _fmt_vci
    return env


def _refuse_raw_write(path: Path) -> None:
    """Enforce the data/raw immutability rule for the report output directory."""
    raw_root = (Path.cwd() / "data" / "raw").resolve()
    resolved = path.resolve()
    if resolved == raw_root or raw_root in resolved.parents:
        raise ValueError(f"output dir {str(path)!r} is under data/raw/, which is immutable")


def generate_report(results_dir: str | Path = "results", out_dir: str | Path = "reports") -> Path:
    """One command: aggregate results/ into reports/ (tables, risk matrix, plots, report.md)."""
    out = Path(out_dir)
    _refuse_raw_write(out)
    runs = load_results(results_dir)
    out.mkdir(parents=True, exist_ok=True)

    table_files = export_tables(runs, out)
    matrices = risk_matrix(runs)
    matrix_file = _write_risk_matrix_csv(matrices, out / "risk_matrix.csv")
    sections = summarize_by_attack(runs)

    plots: list[dict[str, str]] = []
    for run in runs:
        points = _tradeoff_points(run)
        if points:
            filename = f"tradeoff_{run.exp_id}.png"
            plot_tradeoff(points, out / filename)
            plots.append({"exp_id": run.exp_id, "filename": filename})

    report = (
        _environment()
        .get_template("report.md.j2")
        .render(
            generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            results_dir=str(results_dir),
            runs=runs,
            matrices=matrices,
            attack_sections=[s for s in sections if s.attack != "utility"],
            utility_sections=[s for s in sections if s.attack == "utility"],
            plots=plots,
            files=[p.name for p in (*table_files, matrix_file)],
        )
    )
    path = out / "report.md"
    path.write_text(report)
    return path
