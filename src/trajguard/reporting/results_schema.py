"""The unified results-table schema (docs/REZULTATI_SHEMA.md) as code.

One flat table, one row per metric value per run: run provenance repeated on every
row, identity and pivot-axis columns filled at the source from the orchestrator's
structured specs — never parsed back out of ``result_id`` strings. ``RESULTS_COLUMNS``
is the single source of truth for the column set and order; ``tests/test_results_schema.py``
asserts the docs file mentions every column, so code and document cannot drift apart
silently. Blank cells mean "not applicable for this family/arm" or "non-finite value",
matching the ``metrics.csv`` convention.
"""

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trajguard.datamodel import MetricValue

RESULTS_COLUMNS: tuple[str, ...] = (
    # run provenance (repeated on every row)
    "exp_id",
    "config_hash",
    "git_commit",
    "seed",
    "split_seed",
    "max_users",
    "created_at",
    # row identity
    "family",
    "scope",
    "arm_id",
    "target_ref",
    "result_id",
    # pivot axes
    "epsilon",
    "unit_m",
    "known_points",
    "n_shadow",
    # metric
    "metric",
    "value",
    "ci_low",
    "ci_high",
    "n_bootstrap",
    # arm statistics
    "n_pool",
    "n_gallery_users",
    "n_probes",
    "n_rematch_dropped",
    "n_members",
    "n_nonmembers",
    "spent_budget",
    # runtime
    "attack_runtime_s",
    "run_runtime_s",
)

PROVENANCE_COLUMNS: tuple[str, ...] = RESULTS_COLUMNS[:7]


@dataclass(frozen=True, slots=True)
class ResultRow:
    """One metric value with its structured identity, pivot axes, and arm statistics.

    ``None`` fields render as blank cells. ``value`` carries the metric itself
    (name, point value, bootstrap CI) exactly as it goes into ``metrics.csv``.
    """

    value: MetricValue
    family: str  # attack family (reidentification, reconstruction, ...) or "utility"
    scope: str  # raw | protected | synthetic
    arm_id: str  # mechanism/generator registry id; "" for raw
    target_ref: str  # full arm label, e.g. protected:geo_indistinguishability:epsilon=1.0
    epsilon: float | None = None
    unit_m: float | None = None
    known_points: int | None = None
    n_shadow: int | None = None
    n_pool: int | None = None
    n_gallery_users: int | None = None
    n_probes: int | None = None
    n_rematch_dropped: int | None = None
    n_members: int | None = None
    n_nonmembers: int | None = None
    spent_budget: float | None = None
    attack_runtime_s: float | None = None


def _cell(x: Any) -> Any:
    """None and non-finite floats become blank cells (the metrics.csv convention)."""
    if x is None:
        return ""
    if isinstance(x, float) and not math.isfinite(x):
        return ""
    return x


def write_results_csv(
    path: Path,
    provenance: Mapping[str, Any],
    rows: Sequence[ResultRow],
    run_runtime_s: float,
) -> None:
    """Write one run's rows as ``results.csv``, following ``RESULTS_COLUMNS`` exactly.

    ``provenance`` must supply every column in ``PROVENANCE_COLUMNS``; rows are
    emitted as name-keyed records, so a column can never land in the wrong slot.
    """
    missing = set(PROVENANCE_COLUMNS) - set(provenance)
    if missing:
        raise ValueError(f"results.csv provenance is missing {sorted(missing)}")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(RESULTS_COLUMNS))
        writer.writeheader()
        for row in rows:
            v = row.value
            record: dict[str, Any] = {
                **{k: provenance[k] for k in PROVENANCE_COLUMNS},
                "family": row.family,
                "scope": row.scope,
                "arm_id": row.arm_id,
                "target_ref": row.target_ref,
                "result_id": v.result_id,
                "epsilon": row.epsilon,
                "unit_m": row.unit_m,
                "known_points": row.known_points,
                "n_shadow": row.n_shadow,
                "metric": v.name,
                "value": v.value,
                "ci_low": v.ci_low,
                "ci_high": v.ci_high,
                "n_bootstrap": v.n_bootstrap,
                "n_pool": row.n_pool,
                "n_gallery_users": row.n_gallery_users,
                "n_probes": row.n_probes,
                "n_rematch_dropped": row.n_rematch_dropped,
                "n_members": row.n_members,
                "n_nonmembers": row.n_nonmembers,
                "spent_budget": row.spent_budget,
                "attack_runtime_s": row.attack_runtime_s,
                "run_runtime_s": run_runtime_s,
            }
            writer.writerow({k: _cell(val) for k, val in record.items()})
