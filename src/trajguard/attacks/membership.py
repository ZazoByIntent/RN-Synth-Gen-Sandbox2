"""Membership-inference attack, LiRA-lite (design §6.2, Carlini 2022)."""

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import AttackResult, MatchedTrajectory
from trajguard.evaluation.roc import roc_auc, tpr_at_fpr
from trajguard.experiments.registry import register
from trajguard.representation import TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator

EdgeSeq = tuple[int, ...]
_MIN_SD = 1e-6  # floor on the shadow-score std so the likelihood ratio stays finite


class ShadowGenerator(Protocol):
    """What LiRA needs from a shadow generator: fit on views, score edge sequences."""

    def fit(self, train: Sequence[TrajectoryView]) -> None: ...

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float: ...


@dataclass(frozen=True, slots=True)
class MembershipScore:
    """One candidate's LiRA score and its ground-truth membership (for evaluation)."""

    score: float
    is_member: bool


@register("attack", "membership_inference")
class MembershipInferenceAttack(Attack):
    """LiRA-lite: shadow generators + a Gaussian likelihood-ratio membership score.

    For each candidate the attacker splits ``n_shadow`` shadow generators (trained on
    random subsets of a shadow pool) into IN (trained with the candidate) and OUT
    (without), fits a Gaussian to the candidate's ``sequence_log_prob`` under each
    group, and scores the log-prob under the real generator as the log-likelihood
    ratio ``logN(obs; in) - logN(obs; out)``. Higher ⇒ more likely a training member.
    Reports TPR@FPR ∈ {0.001, 0.01} and AUC via :func:`membership_report`.

    Shadows default to ``MarkovGenerator(order, alpha)``; an honest attack against a
    different generator class passes ``shadow_factory`` (called with the shadow index,
    so implementations can derive distinct per-shadow seeds).
    """

    target_scope = {"synthetic"}

    def __init__(
        self,
        n_shadow: int = 16,
        order: int = 1,
        alpha: float = 1.0,
        subsample: float = 0.5,
        shadow_factory: Callable[[int], ShadowGenerator] | None = None,
    ) -> None:
        """LiRA-lite with ``n_shadow`` shadow generators each on a ``subsample`` of the pool."""
        if n_shadow < 2:
            raise ValueError(f"n_shadow must be >= 2, got {n_shadow}")
        if not 0.0 < subsample < 1.0:
            raise ValueError(f"subsample must be in (0, 1), got {subsample}")
        self.n_shadow = n_shadow
        self.order = order
        self.alpha = alpha
        self.subsample = subsample
        self._shadow_factory: Callable[[int], ShadowGenerator] = shadow_factory or (
            lambda _k: MarkovGenerator(order=order, alpha=alpha)
        )
        self._seed = 0

    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """Store the seed used to draw shadow training subsets."""
        self._seed = knowledge.seed

    def run(self, target: Any, aux: Any) -> AttackResult:
        """Score membership of candidate indices against the real generator ``target``.

        ``target`` is the real fitted generator (exposes ``sequence_log_prob``).
        ``aux`` is ``(shadow_pool, candidates)`` where ``shadow_pool`` is a sequence of
        edge sequences and ``candidates`` a sequence of ``(pool_index, is_member)``.
        The orchestrator stamps ``exp_id``/``target_data_ref`` onto the result.
        """
        started = time.perf_counter()
        shadow_pool, candidates = aux
        pool: list[EdgeSeq] = [tuple(s) for s in shadow_pool]
        rng = np.random.default_rng(self._seed)
        shadows, shadow_members = self._train_shadows(pool, rng)

        preds: list[MembershipScore] = []
        for idx, is_member in candidates:
            seq = pool[idx]
            in_lp = [
                g.sequence_log_prob(seq)
                for g, mem in zip(shadows, shadow_members, strict=True)
                if idx in mem
            ]
            out_lp = [
                g.sequence_log_prob(seq)
                for g, mem in zip(shadows, shadow_members, strict=True)
                if idx not in mem
            ]
            obs = float(target.sequence_log_prob(seq))
            preds.append(MembershipScore(_log_lr(obs, in_lp, out_lp), bool(is_member)))

        return AttackResult(
            result_id="membership_inference",
            attack_id="membership_inference",
            exp_id="",  # stamped by the orchestrator
            target_data_ref="synthetic",  # stamped by the orchestrator
            predictions=tuple(preds),
            scores=tuple(p.score for p in preds),
            ground_truth_ref="is_member",
            runtime_s=time.perf_counter() - started,
        )

    def _train_shadows(
        self, pool: list[EdgeSeq], rng: np.random.Generator
    ) -> tuple[list[ShadowGenerator], list[set[int]]]:
        """Fit ``n_shadow`` generators, each on a random subset; record the indices each saw."""
        k = max(1, round(self.subsample * len(pool)))
        shadows: list[ShadowGenerator] = []
        members: list[set[int]] = []
        for shadow_idx in range(self.n_shadow):
            idx = {int(i) for i in rng.choice(len(pool), size=k, replace=False)}
            gen = self._shadow_factory(shadow_idx)
            gen.fit([_seq_view(pool[i]) for i in sorted(idx)])
            shadows.append(gen)
            members.append(idx)
        return shadows, members


def membership_report(
    result: AttackResult, fprs: Sequence[float] = (0.001, 0.01)
) -> dict[str, float]:
    """AUC and TPR at each target FPR from a membership attack's embedded ground truth."""
    scores = np.array([p.score for p in result.predictions], dtype=float)
    labels = np.array([1 if p.is_member else 0 for p in result.predictions], dtype=int)
    report = {"auc": roc_auc(scores, labels)}
    for f in fprs:
        report[f"tpr@fpr={f}"] = tpr_at_fpr(scores, labels, f)
    return report


def _log_lr(obs: float, in_lp: list[float], out_lp: list[float]) -> float:
    """Gaussian log-likelihood ratio of ``obs`` under the IN vs OUT shadow scores."""
    if not in_lp or not out_lp:
        return 0.0
    return _log_normal_pdf(obs, *_gaussian(in_lp)) - _log_normal_pdf(obs, *_gaussian(out_lp))


def _gaussian(xs: list[float]) -> tuple[float, float]:
    """Mean and (floored) unbiased std of a shadow-score sample.

    ``ddof=1`` (Carlini 2022's estimator) for n>1; a singleton group has no spread, so
    it falls to the floor ``_MIN_SD`` rather than the NaN ``std(ddof=1)`` would give.
    """
    arr = np.asarray(xs, dtype=float)
    sd = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return float(arr.mean()), max(sd, _MIN_SD)


def _log_normal_pdf(x: float, mu: float, sd: float) -> float:
    """Log density of ``x`` under N(mu, sd^2)."""
    return -0.5 * math.log(2.0 * math.pi * sd * sd) - (x - mu) ** 2 / (2.0 * sd * sd)


def _seq_view(edge_seq: EdgeSeq) -> TrajectoryView:
    """Wrap a bare edge sequence in a matched-only view so a generator can fit on it."""
    matched = MatchedTrajectory(
        traj_id="",
        user_id="",
        map_id="",
        edge_seq=edge_seq,
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    return TrajectoryView(matched=matched)
