"""Membership-inference scoring curves: numpy-only AUC and TPR at a target FPR (design §6.2).

Score-based, not per-probe 0/1 indicators, so these are plain functions (like
``evaluation.utility``) rather than ``SampledMetric`` subclasses. Carlini 2022 argues
TPR at low FPR is the honest MIA metric; AUC is reported alongside it.
"""

import numpy as np


def _average_ranks(x: np.ndarray) -> np.ndarray:
    """1-based ranks of ``x`` with ties assigned their average rank."""
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    ranks = np.empty(len(x), dtype=float)
    i, n = 0, len(x)
    while i < n:
        j = i
        while j + 1 < n and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2.0  # mean of 1-based ranks i+1..j+1
        i = j + 1
    return ranks


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based ROC AUC (Mann-Whitney U) for scores vs binary labels (1 = member).

    Ties get averaged ranks, so the estimate is exact even when scores collide;
    returns 0.5 when either class is empty.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels)
    n_pos = int((labels == 1).sum())
    n_neg = int((labels == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = _average_ranks(scores)
    sum_pos = float(ranks[labels == 1].sum())
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def tpr_at_fpr(scores: np.ndarray, labels: np.ndarray, fpr_target: float) -> float:
    """Highest TPR reachable at FPR <= ``fpr_target`` over all score thresholds.

    With few negatives the only admissible operating point below a tiny target is
    zero false positives, so this reads as "fraction of members outranking every
    non-member" — the Carlini low-FPR regime. NaN when either class is empty.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels)
    n_pos = int((labels == 1).sum())
    n_neg = int((labels == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(-scores, kind="mergesort")
    sorted_scores = scores[order]
    lab = labels[order]
    tp = np.cumsum(lab == 1)
    fp = np.cumsum(lab == 0)
    # Tied scores share a threshold: a real classifier must take a whole tie group as
    # positive or none of it, so only the last index of each equal-score run is a
    # reachable operating point. Walking element-by-element would expose partial-tie
    # prefixes that no threshold can produce, inflating the reported TPR.
    boundary = np.ones(len(sorted_scores), dtype=bool)
    boundary[:-1] = sorted_scores[:-1] != sorted_scores[1:]
    tpr = tp[boundary] / n_pos
    fpr = fp[boundary] / n_neg
    admissible = fpr <= fpr_target
    return float(tpr[admissible].max()) if bool(admissible.any()) else 0.0
