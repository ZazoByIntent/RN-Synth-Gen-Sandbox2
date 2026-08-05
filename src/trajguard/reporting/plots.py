"""Per-family headline metrics and plots over unified results-table rows (wave-2 O5).

The single home of the headline-metric-per-family mapping: the orchestrator
(matrix.csv, per-run plots) and ``report.py`` (risk matrix, summaries) both import
it from here, so the two layers cannot disagree about what a family's headline is.
Plot inputs are rows of the unified results table (``ResultRow``,
docs/REZULTATI_SHEMA.md) — structured columns only, never re-parsed id strings.
Every plot follows the ``plot_tradeoff`` conventions: matplotlib imported lazily
with the Agg backend, non-finite values skipped, and no file written for a family
the run has no matching rows for.
"""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from trajguard.reporting.results_schema import ResultRow

# Headline metric per attack family; a family whose preferred metric is absent
# (or that is not listed) falls back to its first metric, sorted — nothing is
# silently dropped. Names match what the attack modules emit.
HEADLINE_PREFERENCE = {
    "reidentification": "top1_acc",
    "membership_inference": "auc",
    "reconstruction": "mean_spatial_error_m",
    "poi_inference": "home_error_m",
}

_SCOPE_ORDER = {"raw": 0, "protected": 1, "synthetic": 2}


def headline_metric(family: str, present: Sequence[str]) -> str:
    """The family's preferred headline metric when present, else the first sorted one."""
    ordered = sorted(set(present))
    if not ordered:
        raise ValueError(f"no metrics present for family {family!r}")
    preferred = HEADLINE_PREFERENCE.get(family)
    return preferred if preferred in ordered else ordered[0]


def is_share_metric(name: str) -> bool:
    """True for metrics on the 0–1 scale (schema unit convention), False for e.g. metres."""
    if name == "auc" or name.startswith("tpr@"):
        return True
    return name.endswith(("_acc", "_localised", "_rate"))


def target_sort_key(row: ResultRow) -> tuple[Any, ...]:
    """Display order for target arms from structured columns: raw, identity, then params."""
    return (
        _SCOPE_ORDER.get(row.scope, len(_SCOPE_ORDER)),
        0 if row.arm_id in ("", "none") else 1,
        row.arm_id,
        math.inf if row.epsilon is None else row.epsilon,
        math.inf if row.unit_m is None else row.unit_m,
        row.target_ref,
    )


def headline_rows(rows: Sequence[ResultRow], family: str) -> tuple[str, list[ResultRow]]:
    """The family's headline metric and its row per target arm, ordered for display.

    Families with a knowledge knob (reidentification) emit one row per
    known_points level; the arm is represented by its largest level, matching
    the risk matrix in ``trajguard report``.
    """
    fam = [r for r in rows if r.family == family]
    headline = headline_metric(family, [r.value.name for r in fam])
    by_target: dict[str, list[ResultRow]] = {}
    for r in fam:
        if r.value.name == headline:
            by_target.setdefault(r.target_ref, []).append(r)
    picked = [
        max(target_rows, key=lambda r: -1 if r.known_points is None else r.known_points)
        for target_rows in by_target.values()
    ]
    picked.sort(key=target_sort_key)
    return headline, picked


def _families(rows: Sequence[ResultRow]) -> list[str]:
    """Attack families present in the rows (utility rows describe arms, not attacks)."""
    return sorted({r.family for r in rows if r.family != "utility"})


def _plt() -> Any:
    """Lazy matplotlib import with the Agg backend, keeping ``import trajguard`` light."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _headline_points(rows: Sequence[ResultRow], family: str) -> tuple[str, list[ResultRow]]:
    """The family's headline-metric rows with finite values (every knowledge level)."""
    fam = [r for r in rows if r.family == family]
    headline = headline_metric(family, [r.value.name for r in fam])
    return headline, [r for r in fam if r.value.name == headline and math.isfinite(r.value.value)]


def _ci_segments(ax: Any, xs: Sequence[Any], grp: Sequence[ResultRow], color: Any) -> None:
    """Vertical within-run bootstrap CI segment per point that recorded one."""
    for x, r in zip(xs, grp, strict=True):
        if r.value.ci_low is not None and r.value.ci_high is not None:
            ax.vlines(x, r.value.ci_low, r.value.ci_high, color=color, alpha=0.6)


def _save(plt: Any, fig: Any, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_by_epsilon(rows: Sequence[ResultRow], out_dir: Path) -> list[Path]:
    """One ``by_epsilon_<family>.png`` per family: headline metric vs the arm's ε.

    A line per arm (split further by unit_m and, for families with the knowledge
    knob, per known_points level). Arms without an epsilon (raw, identity,
    non-private generators) have no place on this axis and are left out.
    """
    written: list[Path] = []
    for family in _families(rows):
        headline, finite = _headline_points(rows, family)
        pts = [r for r in finite if r.epsilon is not None]
        if not pts:
            continue
        plt = _plt()
        groups: dict[tuple[str, float | None, int | None], list[ResultRow]] = {}
        for r in pts:
            groups.setdefault((r.arm_id, r.unit_m, r.known_points), []).append(r)
        many_units = len({unit for _, unit, _ in groups}) > 1
        fig, ax = plt.subplots(figsize=(7.0, 5.0))
        for (arm_id, unit_m, k), grp in sorted(
            groups.items(), key=lambda g: (g[0][0], g[0][1] or 0.0, g[0][2] or -1)
        ):
            grp.sort(key=lambda r: r.epsilon or 0.0)
            label = arm_id
            if many_units and unit_m is not None:
                label += f", unit_m={unit_m:g}"
            if k is not None:
                label += f", k={k}"
            xs = [r.epsilon for r in grp]
            (line,) = ax.plot(xs, [r.value.value for r in grp], marker="o", label=label)
            _ci_segments(ax, xs, grp, line.get_color())
        ax.set_xscale("log")
        ax.set_xlabel("epsilon (privacy budget)")
        ax.set_ylabel(headline)
        if is_share_metric(headline):
            ax.set_ylim(-0.05, 1.05)
        ax.set_title(f"{family}: {headline} vs epsilon")
        ax.legend(fontsize=8)
        written.append(_save(plt, fig, out_dir / f"by_epsilon_{family}.png"))
    return written


def plot_by_knowledge(rows: Sequence[ResultRow], out_dir: Path) -> list[Path]:
    """One ``by_knowledge_<family>.png`` per family with a knowledge knob:
    headline metric vs known_points, a line per target arm."""
    written: list[Path] = []
    for family in _families(rows):
        headline, finite = _headline_points(rows, family)
        pts = [r for r in finite if r.known_points is not None]
        if not pts:
            continue
        plt = _plt()
        groups: dict[str, list[ResultRow]] = {}
        order: dict[str, tuple[Any, ...]] = {}
        for r in pts:
            groups.setdefault(r.target_ref, []).append(r)
            order.setdefault(r.target_ref, target_sort_key(r))
        fig, ax = plt.subplots(figsize=(7.0, 5.0))
        for ref in sorted(groups, key=lambda t: order[t]):
            grp = sorted(groups[ref], key=lambda r: r.known_points or 0)
            xs = [r.known_points for r in grp]
            (line,) = ax.plot(xs, [r.value.value for r in grp], marker="o", label=ref)
            _ci_segments(ax, xs, grp, line.get_color())
        ax.set_xlabel("known points (attacker knowledge)")
        ax.set_ylabel(headline)
        if is_share_metric(headline):
            ax.set_ylim(-0.05, 1.05)
        ax.set_title(f"{family}: {headline} vs attacker knowledge")
        ax.legend(fontsize=8)
        written.append(_save(plt, fig, out_dir / f"by_knowledge_{family}.png"))
    return written


def plot_mechanisms(rows: Sequence[ResultRow], out_dir: Path) -> list[Path]:
    """One ``mechanisms_<family>.png`` per family: horizontal bars of the headline
    metric per target arm (reidentification at its largest known_points)."""
    written: list[Path] = []
    for family in _families(rows):
        headline, picked = headline_rows(rows, family)
        picked = [r for r in picked if math.isfinite(r.value.value)]
        if not picked:
            continue
        plt = _plt()
        values = [r.value.value for r in picked]
        lower = [
            max(0.0, r.value.value - r.value.ci_low) if r.value.ci_low is not None else 0.0
            for r in picked
        ]
        upper = [
            max(0.0, r.value.ci_high - r.value.value) if r.value.ci_high is not None else 0.0
            for r in picked
        ]
        fig, ax = plt.subplots(figsize=(7.0, 0.5 * len(picked) + 2.0))
        y = list(range(len(picked)))
        ax.barh(y, values, xerr=(lower, upper), capsize=3)
        ax.set_yticks(y, labels=[r.target_ref for r in picked], fontsize=8)
        ax.invert_yaxis()  # first arm (raw) on top
        ax.set_xlabel(headline)
        if is_share_metric(headline):
            ax.set_xlim(0.0, 1.05)
        ax.set_title(f"{family}: {headline} by arm")
        written.append(_save(plt, fig, out_dir / f"mechanisms_{family}.png"))
    return written


def plot_runtime(rows: Sequence[ResultRow], out_dir: Path) -> list[Path]:
    """``runtime.png``: horizontal bars of attack runtime per attack invocation.

    Rows of one invocation share a result_id and carry the same runtime, so each
    invocation is counted once; labels come from the structured identity columns
    (family, target arm, knowledge level), not from the id string.
    """
    seen: dict[str, ResultRow] = {}
    for r in rows:
        if r.family != "utility" and r.attack_runtime_s is not None:
            seen.setdefault(r.value.result_id, r)
    picked = sorted(
        seen.values(),
        key=lambda r: (r.family, target_sort_key(r), r.known_points or -1),
    )
    if not picked:
        return []
    plt = _plt()
    labels = []
    for r in picked:
        label = f"{r.family}: {r.target_ref}"
        if r.known_points is not None:
            label += f" (k={r.known_points})"
        labels.append(label)
    values = [r.attack_runtime_s for r in picked]
    families = _families(picked)
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    colors = [cycle[families.index(r.family) % len(cycle)] for r in picked]
    fig, ax = plt.subplots(figsize=(8.0, 0.4 * len(picked) + 2.0))
    y = list(range(len(picked)))
    ax.barh(y, values, color=colors)
    ax.set_yticks(y, labels=labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("attack runtime (s)")
    if all(v is not None and v > 0 for v in values):
        ax.set_xscale("log")  # attack runtimes span orders of magnitude
    ax.set_title("attack runtime per invocation")
    return [_save(plt, fig, out_dir / "runtime.png")]
