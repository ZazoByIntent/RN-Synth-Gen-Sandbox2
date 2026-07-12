"""Reidentification / linkage attack (design §6.1, de Montjoye 2013)."""

import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import AttackResult, MatchedTrajectory
from trajguard.experiments.registry import register
from trajguard.geometry import dtw


@dataclass(frozen=True, slots=True)
class Ranking:
    """One probe's linkage result: the true user and gallery users ranked by distance."""

    true_user: str
    users: tuple[str, ...]  # gallery user ids, nearest first (deduped to min distance)
    distances: tuple[float, ...]  # aligned DTW distances


@register("attack", "reidentification")
class ReidentificationAttack(Attack):
    """Links a probe trajectory to a known individual by nearest-neighbour DTW.

    Probes come from ``aux`` (the attacker's raw knowledge, design §6.1) when
    given, else from ``target`` itself (leave-one-out over one pool). Every probe
    trajectory whose user has at least two trajectories in the probe source is
    attacked: the attacker knows ``known_points`` evenly-spaced points of it and
    searches the gallery (``target`` minus the probe's own traj_id) for the
    nearest match, deduplicated to one distance per user. Keeping the probe set
    fixed on the raw pool makes raw and protected arms comparable: a probe whose
    user has no surviving gallery trajectory simply fails to link (indicator 0),
    it is never dropped from the denominator.
    """

    target_scope = {"raw", "protected"}

    def __init__(self) -> None:
        self._knowledge = BackgroundKnowledge(known_points=5)

    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """Set the attacker's background knowledge (k points, distance)."""
        if knowledge.distance != "dtw":
            raise ValueError(f"reidentification implements only 'dtw', got {knowledge.distance!r}")
        self._knowledge = knowledge

    def run(self, target: Sequence[MatchedTrajectory], aux: Any = None) -> AttackResult:
        """Reidentify probes (from ``aux``, or ``target`` itself) against ``target``.

        The orchestrator stamps ``exp_id`` and ``target_data_ref`` onto the result.
        """
        started = time.perf_counter()
        probes: Sequence[MatchedTrajectory] = target if aux is None else aux
        by_user: dict[str, list[int]] = defaultdict(list)
        for i, traj in enumerate(probes):
            by_user[traj.user_id].append(i)
        probeable = {u for u, idxs in by_user.items() if len(idxs) >= 2}

        gallery_coords = [_xy(t) for t in target]
        probe_coords = gallery_coords if aux is None else [_xy(t) for t in probes]
        rankings: list[Ranking] = []
        for i, traj in enumerate(probes):
            if traj.user_id not in probeable:
                continue
            known = _evenly_spaced(probe_coords[i], self._knowledge.known_points)
            best: dict[str, float] = {}
            for j, other in enumerate(target):
                if other.traj_id == traj.traj_id:
                    continue
                d = dtw(known, gallery_coords[j])
                if other.user_id not in best or d < best[other.user_id]:
                    best[other.user_id] = d
            ranked = sorted(best.items(), key=lambda kv: kv[1])
            rankings.append(
                Ranking(
                    true_user=traj.user_id,
                    users=tuple(u for u, _ in ranked),
                    distances=tuple(d for _, d in ranked),
                )
            )

        return AttackResult(
            result_id=f"reidentification:k{self._knowledge.known_points}",
            attack_id="reidentification",
            exp_id="",  # stamped by the orchestrator
            target_data_ref="raw",  # stamped by the orchestrator
            predictions=tuple(rankings),
            scores=tuple(r.distances for r in rankings),
            ground_truth_ref="matched.user_id",
            runtime_s=time.perf_counter() - started,
        )


def _xy(traj: MatchedTrajectory) -> np.ndarray:
    """Extract the snapped (x, y) sequence in projected metres."""
    return np.array([(p[0], p[1]) for p in traj.matched_points], dtype=float)


def _evenly_spaced(seq: np.ndarray, k: int) -> np.ndarray:
    """Return k evenly-spaced points of seq (all points when k >= len)."""
    n = len(seq)
    if k >= n:
        return seq
    idx = np.linspace(0, n - 1, k).round().astype(int)
    sampled: np.ndarray = seq[idx]
    return sampled
