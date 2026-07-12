"""One-time by-user dataset split into train/test/shadow/attack (design §5, step 5)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import get_args

import numpy as np

from trajguard.datamodel import CleanTrajectory, Split

_SPLIT_ORDER: tuple[Split, ...] = get_args(Split)


def split_by_user(
    trajs: Sequence[CleanTrajectory], fractions: Mapping[str, float], seed: int
) -> list[CleanTrajectory]:
    """Assign every user (and all their trajectories) to exactly one split.

    User-level stratification guarantees zero user overlap between splits —
    in particular between train and attack (fair MIA, design T3). Deterministic
    in ``seed`` and independent of the input trajectory order. Returns new
    CleanTrajectory objects with ``split`` set; inputs are not mutated.
    """
    unknown = set(fractions) - set(_SPLIT_ORDER)
    if unknown:
        raise ValueError(f"unknown split names {sorted(unknown)}; expected {_SPLIT_ORDER}")
    total = sum(fractions.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"fractions must sum to 1, got {total}")

    users = sorted({t.user_id for t in trajs})
    rng = np.random.default_rng(seed)
    shuffled = [users[i] for i in rng.permutation(len(users))]

    counts = _largest_remainder(len(users), fractions)
    assignment: dict[str, Split] = {}
    start = 0
    for name in _SPLIT_ORDER:
        for user in shuffled[start : start + counts[name]]:
            assignment[user] = name
        start += counts[name]

    return [replace(t, split=assignment[t.user_id]) for t in trajs]


def _largest_remainder(n: int, fractions: Mapping[str, float]) -> dict[Split, int]:
    """Apportion n items to the splits so counts sum to n exactly."""
    quotas = {name: n * fractions.get(name, 0.0) for name in _SPLIT_ORDER}
    counts = {name: int(q) for name, q in quotas.items()}
    leftover = n - sum(counts.values())
    by_remainder = sorted(_SPLIT_ORDER, key=lambda s: quotas[s] - counts[s], reverse=True)
    for name in by_remainder[:leftover]:
        counts[name] += 1
    return counts
