"""Name-based registry mapping (kind, name) to concrete implementation classes."""

from collections.abc import Callable
from typing import TypeVar

from trajguard.attacks.base import Attack
from trajguard.datasets.base import DatasetLoader
from trajguard.evaluation.base import Metric
from trajguard.maps.base import MapSource
from trajguard.matching.base import MapMatcher
from trajguard.privacy.base import PrivacyMechanism
from trajguard.synthesis.base import SyntheticGenerator

_KIND_TO_ABC: dict[str, type] = {
    "map_source": MapSource,
    "dataset": DatasetLoader,
    "matcher": MapMatcher,
    "mechanism": PrivacyMechanism,
    "generator": SyntheticGenerator,
    "attack": Attack,
    "metric": Metric,
}

_REGISTRY: dict[tuple[str, str], type] = {}

C = TypeVar("C", bound=type)


def register(kind: str, name: str) -> Callable[[C], C]:
    """Class decorator registering an implementation under (kind, name)."""

    def decorator(cls: C) -> C:
        abc = _KIND_TO_ABC.get(kind)
        if abc is None:
            raise ValueError(f"unknown kind {kind!r}; expected one of {sorted(_KIND_TO_ABC)}")
        if not issubclass(cls, abc):
            raise ValueError(f"{cls.__name__} must subclass {abc.__name__} to be a {kind!r}")
        key = (kind, name)
        if key in _REGISTRY:
            raise ValueError(f"duplicate registration {key!r}, held by {_REGISTRY[key].__name__}")
        _REGISTRY[key] = cls
        return cls

    return decorator


def get(kind: str, name: str) -> type:
    """Return the class registered under (kind, name)."""
    try:
        return _REGISTRY[(kind, name)]
    except KeyError:
        available = sorted(n for k, n in _REGISTRY if k == kind)
        raise KeyError(f"no {kind!r} named {name!r} registered; available: {available}") from None
