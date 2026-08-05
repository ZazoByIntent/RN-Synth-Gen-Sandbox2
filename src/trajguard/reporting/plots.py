"""Per-family headline metrics and plots over unified results-table rows (wave-2 O5).

The single home of the headline-metric-per-family mapping: the orchestrator
(matrix.csv, per-run plots) and ``report.py`` (risk matrix, summaries) both import
it from here, so the two layers cannot disagree about what a family's headline is.
Plot inputs are rows of the unified results table (``ResultRow``,
docs/REZULTATI_SHEMA.md) — structured columns only, never re-parsed id strings.
"""

from collections.abc import Sequence

# Headline metric per attack family; a family whose preferred metric is absent
# (or that is not listed) falls back to its first metric, sorted — nothing is
# silently dropped. Names match what the attack modules emit.
HEADLINE_PREFERENCE = {
    "reidentification": "top1_acc",
    "membership_inference": "auc",
    "reconstruction": "mean_spatial_error_m",
    "poi_inference": "home_error_m",
}


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
