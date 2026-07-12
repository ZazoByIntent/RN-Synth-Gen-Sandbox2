"""Tests for the (kind, name) implementation registry."""

from collections.abc import Iterator
from typing import Any

import pytest

from trajguard.attacks.base import Attack
from trajguard.datamodel import AttackResult
from trajguard.datasets.base import DatasetLoader
from trajguard.evaluation.base import Metric
from trajguard.experiments import registry
from trajguard.maps.base import MapSource
from trajguard.matching.base import MapMatcher
from trajguard.privacy.base import PrivacyMechanism
from trajguard.synthesis.base import SyntheticGenerator

ALL_ABCS = [
    MapSource,
    DatasetLoader,
    MapMatcher,
    PrivacyMechanism,
    SyntheticGenerator,
    Attack,
    Metric,
]


@pytest.fixture(autouse=True)
def clean_registry() -> Iterator[None]:
    """Snapshot and restore the module-level registry around each test."""
    snapshot = dict(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)


class DummyAttack(Attack):
    """Minimal concrete Attack used to exercise registration."""

    target_scope = {"raw"}

    def configure(self, knowledge: Any) -> None:
        """No-op."""

    def run(self, target: Any, aux: Any) -> AttackResult:
        """Never called in these tests."""
        raise NotImplementedError


def test_register_and_get_roundtrip() -> None:
    registry.register("attack", "dummy")(DummyAttack)
    assert registry.get("attack", "dummy") is DummyAttack


def test_duplicate_registration_rejected() -> None:
    registry.register("attack", "dummy")(DummyAttack)
    with pytest.raises(ValueError, match="duplicate"):
        registry.register("attack", "dummy")(DummyAttack)


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError, match="unknown kind"):
        registry.register("nonsense", "dummy")(DummyAttack)


def test_wrong_abc_rejected() -> None:
    with pytest.raises(ValueError, match="must subclass"):
        registry.register("metric", "dummy")(DummyAttack)


def test_get_unknown_name_raises_with_available() -> None:
    registry.register("attack", "dummy")(DummyAttack)
    with pytest.raises(KeyError, match="dummy"):
        registry.get("attack", "missing")


@pytest.mark.parametrize("abc", ALL_ABCS)
def test_abcs_refuse_direct_instantiation(abc: type) -> None:
    with pytest.raises(TypeError):
        abc()
