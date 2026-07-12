"""Tests for the deterministic by-user split on the fixture trajectories."""

import random
from pathlib import Path

import pytest

from trajguard.datamodel import CleanTrajectory
from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.datasets.split import split_by_user

FRACTIONS = {"train": 0.5, "test": 0.2, "shadow": 0.2, "attack": 0.1}  # design §8


@pytest.fixture()
def cleaned(geolife_root: Path, onroad_root: Path) -> list[CleanTrajectory]:
    """All fixture trajectories that survive cleaning: 26 trajectories, 7 users."""
    cfg = CleaningConfig()
    out = []
    for root in (geolife_root, onroad_root):
        for raw in GeolifeLoader(root).iter_trajectories():
            c = clean(raw, cfg)
            if c is not None:
                out.append(c)
    assert len(out) == 26
    assert len({t.user_id for t in out}) == 7
    return out


def assignment_of(trajs: list[CleanTrajectory]) -> dict[str, str]:
    users: dict[str, str] = {}
    for t in trajs:
        assert t.split is not None
        assert users.setdefault(t.user_id, t.split) == t.split  # one split per user
    return users


def test_same_seed_same_split(cleaned: list[CleanTrajectory]) -> None:
    a = assignment_of(split_by_user(cleaned, FRACTIONS, seed=42))
    b = assignment_of(split_by_user(cleaned, FRACTIONS, seed=42))
    assert a == b


def test_different_seed_different_split(cleaned: list[CleanTrajectory]) -> None:
    a = assignment_of(split_by_user(cleaned, FRACTIONS, seed=42))
    b = assignment_of(split_by_user(cleaned, FRACTIONS, seed=43))
    assert a != b


def test_independent_of_input_order(cleaned: list[CleanTrajectory]) -> None:
    shuffled = list(cleaned)
    random.Random(7).shuffle(shuffled)  # test-only shuffle of input order
    assert assignment_of(split_by_user(cleaned, FRACTIONS, seed=42)) == assignment_of(
        split_by_user(shuffled, FRACTIONS, seed=42)
    )


def test_no_user_overlap_between_train_and_attack(cleaned: list[CleanTrajectory]) -> None:
    labelled = split_by_user(cleaned, FRACTIONS, seed=42)
    train_users = {t.user_id for t in labelled if t.split == "train"}
    attack_users = {t.user_id for t in labelled if t.split == "attack"}
    assert train_users
    assert attack_users
    assert not train_users & attack_users


def test_largest_remainder_counts(cleaned: list[CleanTrajectory]) -> None:
    users = assignment_of(split_by_user(cleaned, FRACTIONS, seed=42))
    counts = {name: sum(1 for s in users.values() if s == name) for name in FRACTIONS}
    # 7 users, quotas 3.5/1.4/1.4/0.7 -> floors 3/1/1/0, remainders give train+1, attack+1
    assert counts == {"train": 4, "test": 1, "shadow": 1, "attack": 1}


def test_inputs_not_mutated(cleaned: list[CleanTrajectory]) -> None:
    split_by_user(cleaned, FRACTIONS, seed=42)
    assert all(t.split is None for t in cleaned)


def test_bad_fractions_rejected(cleaned: list[CleanTrajectory]) -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        split_by_user(cleaned, {"train": 0.5, "test": 0.2}, seed=42)
    with pytest.raises(ValueError, match="unknown split"):
        split_by_user(cleaned, {"train": 0.5, "validation": 0.5}, seed=42)
