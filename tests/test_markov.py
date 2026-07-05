"""Tests for the Markov n-gram synthetic generator."""

import pytest

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.experiments import registry
from trajguard.representation import TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator


def view(edges: tuple[int, ...], split: str | None = "train", tid: str = "t") -> TrajectoryView:
    """A view carrying a matched edge sequence and a split label (for the fit guard)."""
    matched = MatchedTrajectory(
        traj_id=tid,
        user_id="u",
        map_id="osm_test",
        edge_seq=edges,
        matched_points=(),
        match_score=0.9,
        frac_matched=1.0,
    )
    clean = CleanTrajectory(
        traj_id=tid,
        user_id="u",
        points=((0.0, 0.0, 0.0),),
        bbox=(0.0, 0.0, 0.0, 0.0),
        duration_s=1.0,
        length_m=1.0,
        mean_speed=1.0,
        cleaning_flags=(),
        split=split,
    )
    return TrajectoryView(clean=clean, matched=matched)


# a small corpus walking the chain 1 -> 2 -> 3 (-> 4)
TRAIN = [
    view((1, 2, 3), tid="a"),
    view((1, 2, 3, 4), tid="b"),
    view((2, 3, 4), tid="c"),
    view((1, 2, 3), tid="d"),
]


def test_registered() -> None:
    assert registry.get("generator", "markov") is MarkovGenerator


def test_generation_deterministic_in_seed() -> None:
    g = MarkovGenerator(order=1)
    g.fit(TRAIN)
    first = [s.payload for s in g.generate(5, seed=7)]
    second = [s.payload for s in g.generate(5, seed=7)]
    assert first == second


def test_generated_edges_within_training_vocabulary() -> None:
    g = MarkovGenerator(order=1)
    g.fit(TRAIN)
    vocab = {1, 2, 3, 4}
    for syn in g.generate(20, seed=1):
        assert set(syn.payload) <= vocab


def test_sequence_log_prob_prefers_training_like() -> None:
    g = MarkovGenerator(order=1)
    g.fit(TRAIN)
    # a chain the model saw scores higher than a chain of never-seen edges
    assert g.sequence_log_prob((1, 2, 3)) > g.sequence_log_prob((9, 8, 7))


def test_synthetic_trajectory_fields() -> None:
    g = MarkovGenerator(order=1)
    g.fit(TRAIN)
    syn = g.generate(1, seed=3)[0]
    assert syn.generator_id == "markov"
    assert syn.trained_on_split == "train"
    assert syn.map_id == "osm_test"
    assert isinstance(syn.payload, tuple)


def test_fit_rejects_non_train_split() -> None:
    with pytest.raises(ValueError, match="train split"):
        MarkovGenerator().fit([view((1, 2, 3), split="test")])


def test_generate_before_fit_raises() -> None:
    with pytest.raises(RuntimeError, match="fit"):
        MarkovGenerator().generate(1, seed=0)


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError, match="order"):
        MarkovGenerator(order=0)
    with pytest.raises(ValueError, match="alpha"):
        MarkovGenerator(alpha=0.0)
