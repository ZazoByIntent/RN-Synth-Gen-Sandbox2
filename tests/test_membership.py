"""Tests for the LiRA-lite membership-inference attack."""

import numpy as np
import pytest

from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.membership import (
    MembershipInferenceAttack,
    MembershipScore,
    membership_report,
)
from trajguard.datamodel import MatchedTrajectory
from trajguard.evaluation.roc import roc_auc, tpr_at_fpr
from trajguard.experiments import registry
from trajguard.representation import TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator


def seq_view(edge_seq: tuple[int, ...]) -> TrajectoryView:
    matched = MatchedTrajectory(
        traj_id="",
        user_id="",
        map_id="osm_test",
        edge_seq=edge_seq,
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    return TrajectoryView(matched=matched)


# Universe of trajectories with private vocabularies: sequence i uses edges 100*i..+3,
# so a generator that trained on i memorises it and one that did not floors its log-prob.
UNIVERSE = [tuple(100 * i + j for j in range(4)) for i in range(12)]
MEMBERS = list(range(6))  # the real generator trains on these
CANDIDATES = [(i, i in set(MEMBERS)) for i in range(12)]


def real_generator() -> MarkovGenerator:
    gen = MarkovGenerator(order=1)
    gen.fit([seq_view(UNIVERSE[i]) for i in MEMBERS])
    return gen


def run_attack(seed: int = 0) -> MembershipInferenceAttack:
    attack = MembershipInferenceAttack(n_shadow=16)
    attack.configure(BackgroundKnowledge(known_points=0, seed=seed))
    return attack


def test_registered() -> None:
    assert registry.get("attack", "membership_inference") is MembershipInferenceAttack


def test_reports_auc_and_tpr_at_fpr() -> None:
    result = run_attack().run(real_generator(), (UNIVERSE, CANDIDATES))
    report = membership_report(result)
    assert set(report) == {"auc", "tpr@fpr=0.001", "tpr@fpr=0.01"}
    assert all(0.0 <= v <= 1.0 for v in report.values())
    # members are memorised, non-members floored -> the attack separates them clearly
    assert report["auc"] >= 0.75


def test_predictions_carry_ground_truth() -> None:
    result = run_attack().run(real_generator(), (UNIVERSE, CANDIDATES))
    assert len(result.predictions) == len(CANDIDATES)
    assert all(isinstance(p, MembershipScore) for p in result.predictions)
    # a real member scores above a real non-member on average
    member_scores = [p.score for p in result.predictions if p.is_member]
    nonmember_scores = [p.score for p in result.predictions if not p.is_member]
    assert np.mean(member_scores) > np.mean(nonmember_scores)


def test_deterministic_in_seed() -> None:
    gen = real_generator()
    first = run_attack(seed=3).run(gen, (UNIVERSE, CANDIDATES))
    second = run_attack(seed=3).run(gen, (UNIVERSE, CANDIDATES))
    assert [p.score for p in first.predictions] == [p.score for p in second.predictions]


def test_roc_auc_ranks_and_ties() -> None:
    # perfectly separated
    assert roc_auc(np.array([2.0, 3.0, 0.0, 1.0]), np.array([1, 1, 0, 0])) == 1.0
    # inverted
    assert roc_auc(np.array([0.0, 1.0, 2.0, 3.0]), np.array([1, 1, 0, 0])) == 0.0
    # all tied -> chance
    assert roc_auc(np.array([1.0, 1.0, 1.0, 1.0]), np.array([1, 1, 0, 0])) == 0.5


def test_tpr_at_fpr_zero_false_positive_regime() -> None:
    scores = np.array([5.0, 4.0, 1.0, 0.0])  # both members outrank both non-members
    labels = np.array([1, 1, 0, 0])
    assert tpr_at_fpr(scores, labels, 0.001) == 1.0
    # a non-member on top blocks the zero-FP operating point
    blocked = np.array([9.0, 5.0, 4.0, 0.0])
    assert tpr_at_fpr(blocked, np.array([0, 1, 1, 0]), 0.001) == 0.0


def test_tpr_at_fpr_is_tie_safe_and_order_invariant() -> None:
    # all scores tied: no threshold separates the classes, so the only zero-FP point is
    # TPR=0 — and it must not depend on how equal scores happen to be ordered.
    assert tpr_at_fpr(np.array([5.0, 5.0, 5.0]), np.array([1, 0, 1]), 0.001) == 0.0
    assert tpr_at_fpr(np.array([5.0, 5.0, 5.0]), np.array([0, 1, 1]), 0.001) == 0.0
    # a member tied with the top non-member cannot be counted ahead of it at low FPR
    tied_top = np.array([9.0, 9.0, 4.0, 0.0])
    assert tpr_at_fpr(tied_top, np.array([1, 0, 1, 0]), 0.001) == 0.0
    # relax the target until the whole tie group (1 TP, 1 FP) is admissible -> TPR 1.0
    assert tpr_at_fpr(tied_top, np.array([1, 0, 1, 0]), 0.5) == 1.0


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError, match="n_shadow"):
        MembershipInferenceAttack(n_shadow=1)
    with pytest.raises(ValueError, match="subsample"):
        MembershipInferenceAttack(subsample=1.5)


def test_shadow_factory_is_called_once_per_shadow_with_its_index() -> None:
    calls: list[int] = []

    def factory(k: int) -> MarkovGenerator:
        calls.append(k)
        return MarkovGenerator(order=1)

    attack = MembershipInferenceAttack(n_shadow=4, shadow_factory=factory)
    attack.configure(BackgroundKnowledge(known_points=0, seed=0))
    result = attack.run(real_generator(), (UNIVERSE, CANDIDATES))
    assert calls == [0, 1, 2, 3]
    assert len(result.predictions) == len(CANDIDATES)


def test_default_shadow_factory_matches_previous_behaviour() -> None:
    """Passing no factory must reproduce the historical MarkovGenerator shadows exactly."""
    gen = real_generator()
    default = run_attack(seed=7).run(gen, (UNIVERSE, CANDIDATES))
    explicit = MembershipInferenceAttack(
        n_shadow=16, shadow_factory=lambda _k: MarkovGenerator(order=1, alpha=1.0)
    )
    explicit.configure(BackgroundKnowledge(known_points=0, seed=7))
    via_factory = explicit.run(gen, (UNIVERSE, CANDIDATES))
    assert [p.score for p in default.predictions] == [p.score for p in via_factory.predictions]
