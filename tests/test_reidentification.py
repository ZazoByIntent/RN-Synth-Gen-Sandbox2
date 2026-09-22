"""Tests for the reidentification attack and the privacy metrics."""

import numpy as np
import pytest

from trajguard.attacks.base import BackgroundKnowledge
from trajguard.attacks.reidentification import (
    PointTrace,
    Ranking,
    ReidentificationAttack,
    _evenly_spaced,
)
from trajguard.datamodel import AttackResult, MatchedTrajectory
from trajguard.evaluation.metrics import LinkageRate, TopKAccuracy, bootstrap_ci, evaluate
from trajguard.experiments import registry


def mt(traj_id: str, user: str, pts: list[tuple[float, float]]) -> MatchedTrajectory:
    return MatchedTrajectory(
        traj_id=traj_id,
        user_id=user,
        map_id="osm_test",
        edge_seq=(1, 2),
        matched_points=tuple((x, y, float(i), 0.0) for i, (x, y) in enumerate(pts)),
        match_score=0.9,
        frac_matched=1.0,
    )


# two users on separate parts of the plane, each with two near-parallel trajectories,
# plus a single-trajectory distractor user.
POOL = [
    mt("A1", "A", [(0, 0), (1, 0), (2, 0), (3, 0)]),
    mt("A2", "A", [(0, 0.1), (1, 0.1), (2, 0.1), (3, 0.1)]),
    mt("B1", "B", [(0, 10), (0, 11), (0, 12), (0, 13)]),
    mt("B2", "B", [(0.1, 10), (0.1, 11), (0.1, 12), (0.1, 13)]),
    mt("C1", "C", [(5, 5), (5, 6), (5, 7)]),  # single trajectory -> gallery-only distractor
]


def test_attack_registered() -> None:
    assert registry.get("attack", "reidentification") is ReidentificationAttack


def test_evenly_spaced_uses_all_when_k_exceeds_length() -> None:
    seq = np.array([(0.0, 0.0), (1.0, 1.0)])
    assert len(_evenly_spaced(seq, 10)) == 2
    assert len(_evenly_spaced(seq, 1)) == 1


def test_probes_link_to_correct_user() -> None:
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=4))
    result = attack.run(POOL)
    # A and B have >=2 trajectories -> 4 probes; C (single) is never probed
    assert len(result.predictions) == 4
    for ranking in result.predictions:
        assert ranking.users[0] == ranking.true_user  # nearest gallery user is correct
        assert ranking.true_user in {"A", "B"}
        # users are deduplicated (one distance per gallery user)
        assert len(ranking.users) == len(set(ranking.users))
        assert list(ranking.distances) == sorted(ranking.distances)


def test_probes_from_aux_keep_population_fixed_across_arms() -> None:
    """With aux probes, the denominator stays the raw pool even if the gallery shrank."""
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=4))
    shrunken_gallery = [t for t in POOL if t.traj_id != "A2"]  # A2 "did not survive"
    result = attack.run(shrunken_gallery, aux=POOL)
    assert len(result.predictions) == 4  # probes still defined by the raw pool
    by_probe = {r.true_user: r for r in result.predictions}
    # B is untouched, still linked; A lost a gallery trajectory but stays in the denominator
    assert by_probe["B"].users[0] == "B"
    for ranking in result.predictions:
        assert len(ranking.users) == len(set(ranking.users))


def test_empty_gallery_yields_failed_links_not_missing_probes() -> None:
    """An empty (or fully dropped) release: every probe fails, none disappears."""
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=4))
    result = attack.run([], aux=POOL)
    assert len(result.predictions) == 4
    for ranking in result.predictions:
        assert ranking.users == ()
    # metrics read 0.0 (failed links), not NaN (missing probes)
    assert TopKAccuracy(1).compute(result) == {"top1_acc": 0.0}
    assert LinkageRate().compute(result) == {"linkage_rate": 0.0}


def make_result(rankings: list[Ranking]) -> AttackResult:
    return AttackResult(
        result_id="r",
        attack_id="reidentification",
        exp_id="e",
        target_data_ref="raw",
        predictions=tuple(rankings),
        scores=tuple(r.distances for r in rankings),
        ground_truth_ref="matched.user_id",
        runtime_s=0.0,
    )


def test_top_k_and_linkage_values() -> None:
    result = make_result(
        [
            Ranking("A", ("A", "B"), (1.0, 2.0)),
            Ranking("B", ("A", "B"), (1.0, 2.0)),
        ]
    )
    assert TopKAccuracy(1).compute(result) == {"top1_acc": 0.5}
    assert TopKAccuracy(2).compute(result) == {"top2_acc": 1.0}
    assert LinkageRate().compute(result) == {"linkage_rate": 0.5}


def test_bootstrap_ci_deterministic_and_ordered() -> None:
    indicators = np.array([1.0, 0.0, 1.0, 1.0, 0.0, 1.0])
    rng = np.random.default_rng(0)
    point, lo, hi = bootstrap_ci(indicators, n_bootstrap=500, ci=0.95, rng=rng)
    assert lo <= point <= hi
    assert point == indicators.mean()
    # deterministic in the seed
    again = bootstrap_ci(indicators, 500, 0.95, np.random.default_rng(0))
    assert (point, lo, hi) == again


def test_evaluate_builds_metric_values() -> None:
    result = make_result(
        [Ranking("A", ("A", "B"), (1.0, 2.0)), Ranking("B", ("B", "A"), (1.0, 2.0))]
    )
    values = evaluate(result, [TopKAccuracy(1), LinkageRate()], n_bootstrap=200, ci=0.95, seed=1)
    assert {v.name for v in values} == {"top1_acc", "linkage_rate"}
    for v in values:
        assert v.n_bootstrap == 200
        assert v.ci_low is not None and v.ci_high is not None
        assert v.ci_low <= v.value <= v.ci_high
        assert v.result_id == "r"


def test_unsupported_distance_rejected() -> None:
    attack = ReidentificationAttack()
    with pytest.raises(ValueError, match="dtw"):
        attack.configure(BackgroundKnowledge(known_points=4, distance="hausdorff"))


# --- attacker distance: dtw vs dtw_norm -------------------------------------------

# User A drives 590 m along a straight line; user B has a two-point decoy trace 150 m
# off that line. A's two identical traces make A probeable (and give each probe a
# gallery trace of its own user), B's single trace is gallery-only.
LONG_LINE = [(i * 10.0, 0.0) for i in range(60)]
LENGTH_BIAS_POOL = [
    mt("A1", "A", LONG_LINE),
    mt("A2", "A", LONG_LINE),
    mt("B1", "B", [(295.0, 150.0), (305.0, 150.0)]),
]


def _top1_users(distance: str) -> set[str]:
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=3, distance=distance))
    result = attack.run(LENGTH_BIAS_POOL)
    assert len(result.predictions) == 2  # only A has two trajectories, so only A is probed
    return {r.users[0] for r in result.predictions}


def test_dtw_norm_removes_the_short_gallery_bias() -> None:
    """The unnormalised DTW sum grows with the gallery trace's length, so the short
    decoy B wins against A's own 60-point trace; dividing by the alignment length
    (decision of 22 Sep 2026) ranks the true user A first."""
    assert _top1_users("dtw") == {"B"}
    assert _top1_users("dtw_norm") == {"A"}


def test_dtw_norm_is_accepted_and_named_in_the_default_result_id() -> None:
    """Only the non-default distance is spelled out (the orchestrator restates the id)."""
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=3, distance="dtw_norm"))
    assert attack.run(POOL).result_id == "reidentification:k3:dtw_norm"
    attack.configure(BackgroundKnowledge(known_points=3, distance="dtw"))
    assert attack.run(POOL).result_id == "reidentification:k3"


# --- attacker gallery: rematched (snapped points) vs release (full released points) ---

# The same pool expressed as released point traces: the orchestrator projects the
# released GPS points into the map CRS and hands them over as bare (x, y) arrays.
POINT_POOL = [
    PointTrace(
        traj_id=t.traj_id,
        user_id=t.user_id,
        xy=np.array([(p[0], p[1]) for p in t.matched_points], dtype=float),
    )
    for t in POOL
]


def test_point_traces_are_attacked_exactly_like_matched_ones() -> None:
    """The gallery mode only changes where the points come from, not the linkage."""
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=3))
    matched = attack.run(POOL)
    attack.configure(BackgroundKnowledge(known_points=3, gallery="release"))
    released = attack.run(POINT_POOL)

    assert len(released.predictions) == len(matched.predictions)
    for from_points, from_matched in zip(released.predictions, matched.predictions, strict=True):
        assert from_points.true_user == from_matched.true_user
        assert from_points.users == from_matched.users
        assert from_points.distances == pytest.approx(from_matched.distances)
    metrics = [TopKAccuracy(1), LinkageRate()]
    as_values = {
        v.name: v.value for v in evaluate(released, metrics, n_bootstrap=100, ci=0.95, seed=1)
    }
    expected = {
        v.name: v.value for v in evaluate(matched, metrics, n_bootstrap=100, ci=0.95, seed=1)
    }
    assert as_values == expected


def test_release_gallery_is_named_in_the_result_id_after_the_distance() -> None:
    """Distance first, gallery last; the default gallery stays implicit."""
    attack = ReidentificationAttack()
    attack.configure(BackgroundKnowledge(known_points=3, distance="dtw_norm", gallery="release"))
    assert attack.run(POINT_POOL).result_id == "reidentification:k3:dtw_norm:release"
    attack.configure(BackgroundKnowledge(known_points=3, gallery="release"))
    assert attack.run(POINT_POOL).result_id == "reidentification:k3:release"
    attack.configure(BackgroundKnowledge(known_points=3, gallery="rematched"))
    assert attack.run(POOL).result_id == "reidentification:k3"


def test_unsupported_gallery_rejected() -> None:
    attack = ReidentificationAttack()
    with pytest.raises(ValueError, match="supports galleries"):
        attack.configure(BackgroundKnowledge(known_points=4, gallery="raw_cells"))
