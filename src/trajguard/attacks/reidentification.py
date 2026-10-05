"""Reidentification / linkage attack (design §6.1, de Montjoye 2013).

The attacker's trajectory distance is a configurable knob (``attacker.distance``),
one of the names in ``geometry.DISTANCES``:

* ``dtw`` — the unnormalised dynamic-time-warping cost, and the default. Every
  measured S4 number was produced with it, so it must keep its behaviour and its
  result ids; the id never spells it out.
* ``dtw_norm`` — the same cost divided by ``L``, the number of cells on the optimal
  alignment. The unnormalised sum grows with the number of gallery points, which
  lets short gallery traces win on length rather than on geometry; the normalised
  distance is the per-matched-pair mean and removes that bias (decision of
  22 Sep 2026). Its result ids carry a trailing ``:dtw_norm`` segment.

The attacker's *gallery* (``attacker.gallery``, one of ``base.GALLERIES``) says which
form of the release he holds:

* ``rematched`` — the map-matched (snapped) points of the release that survived
  re-matching, and the default. This is what every measured S4 number used, so the
  ids never spell it out.
* ``release`` — the full released points exactly as published, projected into the map
  CRS by the orchestrator, with no map-matcher in the loop. This attacker is strictly
  stronger: he loses nothing to the re-matching filter, so an arm whose release is too
  noisy to snap back onto the network no longer looks "protected" merely because the
  benchmark's own matcher discarded it. Its result ids carry a trailing ``:release``
  segment. The attack itself knows nothing about coordinate systems; it just reads
  the ``xy`` of a :class:`PointTrace`.
"""

import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from trajguard.attacks.base import DEFAULT_GALLERY, GALLERIES, Attack, BackgroundKnowledge
from trajguard.datamodel import AttackResult, MatchedTrajectory
from trajguard.experiments.registry import register
from trajguard.geometry import DEFAULT_DISTANCE, DISTANCES


def distance_suffix(distance: str) -> str:
    """The ``result_id`` segment naming a non-default attacker distance ("" for ``dtw``)."""
    return "" if distance == DEFAULT_DISTANCE else f":{distance}"


def gallery_suffix(gallery: str) -> str:
    """The ``result_id`` segment naming a non-default gallery ("" for ``rematched``)."""
    return "" if gallery == DEFAULT_GALLERY else f":{gallery}"


@dataclass(frozen=True, slots=True)
class PointTrace:
    """One released trajectory as bare points, already projected into the map CRS.

    The gallery item of the ``release`` mode: ``xy`` holds the full released points
    as an (n, 2) array of metres. Projecting is the orchestrator's job, so the attack
    stays ignorant of coordinate systems.
    """

    traj_id: str
    user_id: str
    xy: np.ndarray


@dataclass(frozen=True, slots=True)
class Ranking:
    """One probe's linkage result: the true user and gallery users ranked by distance."""

    true_user: str
    users: tuple[str, ...]  # gallery user ids, nearest first (deduped to min distance)
    distances: tuple[float, ...]  # aligned distances in the configured distance


@register("attack", "reidentification")
class ReidentificationAttack(Attack):
    """Links a probe trajectory to a known individual by nearest-neighbour distance.

    The distance is the configured one (``dtw`` by default, ``dtw_norm`` for the
    length-normalised variant; see the module docstring). Probes come from ``aux``
    (the attacker's raw knowledge, design §6.1) when given, else from ``target``
    itself (leave-one-out over one pool). Every probe trajectory whose user has
    at least two trajectories in the probe source is
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
        """Set the attacker's background knowledge (k points, distance, gallery)."""
        if knowledge.distance not in DISTANCES:
            raise ValueError(
                f"reidentification supports distances {sorted(DISTANCES)}, "
                f"got {knowledge.distance!r}"
            )
        if knowledge.gallery not in GALLERIES:
            raise ValueError(
                f"reidentification supports galleries {sorted(GALLERIES)}, "
                f"got {knowledge.gallery!r}"
            )
        self._knowledge = knowledge

    def run(
        self, target: Sequence[MatchedTrajectory | PointTrace], aux: Any = None
    ) -> AttackResult:
        """Reidentify probes (from ``aux``, or ``target`` itself) against ``target``.

        The orchestrator stamps ``exp_id`` and ``target_data_ref`` onto the result.
        """
        started = time.perf_counter()
        distance = DISTANCES[self._knowledge.distance]
        probes: Sequence[MatchedTrajectory | PointTrace] = target if aux is None else aux
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
                d = distance(known, gallery_coords[j])
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
            result_id=(
                f"reidentification:k{self._knowledge.known_points}"
                f"{distance_suffix(self._knowledge.distance)}"
                f"{gallery_suffix(self._knowledge.gallery)}"
            ),
            attack_id="reidentification",
            exp_id="",  # stamped by the orchestrator
            target_data_ref="raw",  # stamped by the orchestrator
            predictions=tuple(rankings),
            scores=tuple(r.distances for r in rankings),
            ground_truth_ref="matched.user_id",
            runtime_s=time.perf_counter() - started,
        )


def _xy(traj: MatchedTrajectory | PointTrace) -> np.ndarray:
    """Extract the (x, y) sequence in projected metres (snapped points, or a release)."""
    if isinstance(traj, PointTrace):
        return np.asarray(traj.xy, dtype=float)
    return np.array([(p[0], p[1]) for p in traj.matched_points], dtype=float)


def _evenly_spaced(seq: np.ndarray, k: int) -> np.ndarray:
    """Return k evenly-spaced points of seq (all points when k >= len)."""
    n = len(seq)
    if k >= n:
        return seq
    idx = np.linspace(0, n - 1, k).round().astype(int)
    sampled: np.ndarray = seq[idx]
    return sampled
