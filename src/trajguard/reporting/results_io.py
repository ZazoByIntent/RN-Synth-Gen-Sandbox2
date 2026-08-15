"""Read unified results tables back into rows and aggregate them across seeds.

The inverse direction of ``results_schema.write_results_csv``: ``read_results_csv``
turns a per-run ``results.csv`` or the concatenated ``reports/results_master.csv``
back into structured ``ResultRow`` objects (plus the provenance block the row
itself does not carry), and ``aggregate_over_seeds`` folds repetition runs into
one row per metric whose value is the across-seed mean and whose CI is the
Student-t 95% interval *across repetitions* — reusing the statistics from
``experiments.repeat``, never mixing them with the within-run bootstrap CI.
Aggregated rows plug straight into the ``reporting.plots`` functions.

Consumers (this module, the plot functions, and the S4 analysis notebook
``notebooks/03_s4_sweep.ipynb``) all depend on ``RESULTS_COLUMNS`` staying
stable; a table with a foreign header fails loudly here, mirroring
``report.merge_results_tables``.
"""

import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from pathlib import Path

from trajguard.datamodel import MetricValue
from trajguard.experiments.repeat import t_ppf_975
from trajguard.reporting.results_schema import RESULTS_COLUMNS, ResultRow

_INT_COLUMNS = frozenset(
    {
        "seed",
        "split_seed",
        "max_users",
        "known_points",
        "n_shadow",
        "n_bootstrap",
        "n_pool",
        "n_gallery_users",
        "n_probes",
        "n_rematch_dropped",
        "n_members",
        "n_nonmembers",
    }
)
_FLOAT_COLUMNS = frozenset(
    {
        "epsilon",
        "unit_m",
        "value",
        "ci_low",
        "ci_high",
        "spent_budget",
        "attack_runtime_s",
        "peak_memory_mb",
        "run_runtime_s",
    }
)

# Count/statistic fields that may legitimately differ between seeds (fresh noise
# per seed): kept in an aggregated row only when identical across all its seeds.
_PER_SEED_STAT_FIELDS = (
    "n_shadow",
    "n_pool",
    "n_gallery_users",
    "n_probes",
    "n_rematch_dropped",
    "n_members",
    "n_nonmembers",
    "spent_budget",
)


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """The provenance block repeated on every row of one run (schema columns 1-7)."""

    exp_id: str
    config_hash: str
    git_commit: str
    seed: int | None
    split_seed: int | None
    max_users: int | None
    created_at: str


@dataclass(frozen=True, slots=True)
class LoadedRow:
    """One results-table row read back: provenance + structured row + run runtime."""

    provenance: RunProvenance
    row: ResultRow
    run_runtime_s: float | None


def _parse(column: str, cell: str) -> str | int | float | None:
    """One cell back to its schema type; blank cells become None."""
    if cell == "":
        return None
    if column in _INT_COLUMNS:
        return int(cell)
    if column in _FLOAT_COLUMNS:
        return float(cell)
    return cell


def read_results_csv(path: str | Path) -> list[LoadedRow]:
    """Read a ``results.csv`` / ``results_master.csv`` back into ``LoadedRow`` objects.

    The header must equal ``RESULTS_COLUMNS`` exactly — a foreign header is a
    loud error, never silently misaligned columns. A blank ``value`` cell (the
    writer blanks non-finite values) becomes ``nan``, so degenerate arms stay
    visible in tables and are skipped by the plots. ``metric_id`` is not stored
    in the CSV and is synthesized as ``<result_id>:<metric>``.
    """
    path = Path(path)
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = tuple(next(reader, ()))
        if header != RESULTS_COLUMNS:
            raise ValueError(
                f"{path} header does not match RESULTS_COLUMNS "
                f"(docs/REZULTATI_SHEMA.md); got {header}"
            )
        loaded: list[LoadedRow] = []
        for cells in reader:
            rec = {c: _parse(c, cell) for c, cell in zip(RESULTS_COLUMNS, cells, strict=True)}
            value = MetricValue(
                metric_id=f"{rec['result_id']}:{rec['metric']}",
                result_id=str(rec["result_id"]),
                name=str(rec["metric"]),
                value=float("nan") if rec["value"] is None else float(rec["value"]),
                ci_low=rec["ci_low"],  # type: ignore[arg-type]
                ci_high=rec["ci_high"],  # type: ignore[arg-type]
                n_bootstrap=rec["n_bootstrap"],  # type: ignore[arg-type]
            )
            row_fields = {
                f.name: rec[f.name]
                # "value" is the MetricValue field, not the CSV's numeric column.
                for f in fields(ResultRow)
                if f.name != "value" and f.name in RESULTS_COLUMNS
            }
            # String provenance written as blank (e.g. git_commit outside a
            # checkout) comes back as "" rather than None, matching the writer.
            prov_fields = {
                f.name: ("" if rec[f.name] is None and f.name not in _INT_COLUMNS else rec[f.name])
                for f in fields(RunProvenance)
            }
            loaded.append(
                LoadedRow(
                    provenance=RunProvenance(**prov_fields),  # type: ignore[arg-type]
                    row=ResultRow(value=value, **row_fields),  # type: ignore[arg-type]
                    run_runtime_s=rec["run_runtime_s"],  # type: ignore[arg-type]
                )
            )
    return loaded


def _mean_or_none(values: Sequence[float | None]) -> float | None:
    finite = [v for v in values if v is not None and math.isfinite(v)]
    return sum(finite) / len(finite) if finite else None


def _identical_or_none(values: Sequence[object]) -> object:
    return values[0] if all(v == values[0] for v in values) else None


def aggregate_over_seeds(records: Sequence[LoadedRow]) -> list[ResultRow]:
    """Fold repetition rows into one ``ResultRow`` per metric with an across-seed CI.

    Groups by ``(exp_id, config_hash, result_id, metric)`` — the run seed is
    deliberately not part of ``config_hash``, so repetitions of one experiment
    share the group while distinct experiments never merge. Within a group the
    seeds must be distinct (the same run loaded twice would bias the mean).
    The value becomes the mean over finite per-seed values and the CI the
    Student-t 95% interval across repetitions (``n_bootstrap`` is cleared: this
    is not a bootstrap interval). Runtimes and memory are averaged; per-seed
    counts are kept only when identical across seeds, else blanked.
    """
    groups: dict[tuple[str, str, str, str], list[LoadedRow]] = {}
    for rec in records:
        key = (
            rec.provenance.exp_id,
            rec.provenance.config_hash,
            rec.row.value.result_id,
            rec.row.value.name,
        )
        groups.setdefault(key, []).append(rec)

    out: list[ResultRow] = []
    for key, grp in sorted(groups.items()):
        seeds = [rec.provenance.seed for rec in grp]
        if len(set(seeds)) != len(seeds):
            raise ValueError(
                f"duplicate seed among repetitions of {key}: {seeds} "
                "(was the same run loaded twice, e.g. master + per-run table?)"
            )
        vals = [rec.row.value.value for rec in grp if math.isfinite(rec.row.value.value)]
        if not vals:
            mean, ci_low, ci_high = float("nan"), None, None
        elif len(vals) == 1:
            mean = ci_low = ci_high = vals[0]
        else:
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
            half = t_ppf_975(len(vals) - 1) * math.sqrt(var) / math.sqrt(len(vals))
            ci_low, ci_high = mean - half, mean + half
        first = grp[0].row
        stats = {
            name: _identical_or_none([getattr(rec.row, name) for rec in grp])
            for name in _PER_SEED_STAT_FIELDS
        }
        out.append(
            replace(
                first,
                value=replace(
                    first.value,
                    metric_id=f"{first.value.result_id}:{first.value.name}",
                    value=mean,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    n_bootstrap=None,
                ),
                attack_runtime_s=_mean_or_none([rec.row.attack_runtime_s for rec in grp]),
                peak_memory_mb=_mean_or_none([rec.row.peak_memory_mb for rec in grp]),
                **stats,  # type: ignore[arg-type]
            )
        )
    return out
