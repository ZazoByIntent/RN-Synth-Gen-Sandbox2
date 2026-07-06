"""Property / POI inference attack: home & work from stay-points (design §6.4, Primault 2019)."""

import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from trajguard.attacks.base import Attack, BackgroundKnowledge
from trajguard.datamodel import AttackResult, CleanTrajectory
from trajguard.datasets.cleaning import haversine_m
from trajguard.evaluation.metrics import bootstrap_ci
from trajguard.experiments.registry import register

LatLon = tuple[float, float]
Point = tuple[float, float, float]  # (lat, lon, t) with t in Unix epoch seconds


@dataclass(frozen=True, slots=True)
class _Stay:
    """One stay-point: dwell centroid (lat, lon), representative epoch time, and support size."""

    lat: float
    lon: float
    t: float
    n: int


@dataclass(frozen=True, slots=True)
class HomeWork:
    """One user's inferred and true home/work locations (lat, lon); None where unresolved."""

    user_id: str
    est_home: LatLon | None
    est_work: LatLon | None
    true_home: LatLon | None
    true_work: LatLon | None


@register("attack", "poi_inference")
class PoiInferenceAttack(Attack):
    """Infers a user's home and work from stay-point clustering (design §6.4, Primault 2019).

    Deliberately simple — no external POI layer, no attribute classifier: cluster each user's
    ``(lat, lon, t)`` points into stay-points (a run staying within ``radius_m`` for at least
    ``dwell_s``), then estimate home as the centroid of night-hour stays and work as the centroid
    of day-hour stays. The attack works in GPS degrees with haversine distances because geo-ind
    releases GPS points (``privacy/geoind.py``); ground truth is the same procedure on the
    unprotected trajectories passed as ``aux``. ``target_scope`` is ``{"protected", "synthetic"}``
    per design §6.4, but the Markov generator emits edge sequences with no coordinates or
    timestamps, so only ``protected`` releases are meaningful today (``tests/test_attribute.py``
    also exercises the raw sanity baseline directly). This attack consumes clean GPS points, not
    the matched pool the orchestrator's reidentification-shaped run loop supplies, so it is not
    wired in there yet — a config naming it is rejected up front. Local time is
    ``UTC + tz_offset_h``; Geolife timestamps are GMT and Beijing is +8.
    """

    target_scope = {"protected", "synthetic"}

    def __init__(
        self,
        dwell_s: float = 300.0,
        radius_m: float = 200.0,
        home_hours: tuple[int, int] = (22, 7),
        work_hours: tuple[int, int] = (9, 18),
        tz_offset_h: float = 8.0,
    ) -> None:
        """Attacker's stay-point thresholds and the local-time window for home vs work."""
        if dwell_s <= 0:
            raise ValueError(f"dwell_s must be > 0, got {dwell_s}")
        if radius_m <= 0:
            raise ValueError(f"radius_m must be > 0, got {radius_m}")
        self.dwell_s = float(dwell_s)
        self.radius_m = float(radius_m)
        self.home_hours = home_hours
        self.work_hours = work_hours
        self.tz_offset_h = float(tz_offset_h)

    def configure(self, knowledge: BackgroundKnowledge) -> None:
        """No stochastic knowledge: stay-point inference is deterministic."""

    def run(
        self, target: Sequence[CleanTrajectory], aux: Sequence[CleanTrajectory]
    ) -> AttackResult:
        """Estimate home/work per user from ``target``; truth from unprotected ``aux``.

        ``target`` is the attacked release (a geo-ind-noised pool, or the raw pool for the sanity
        baseline); ``aux`` is the unprotected pool. Users are matched by ``user_id``. The
        orchestrator stamps ``exp_id``/``target_data_ref`` onto the result.
        """
        started = time.perf_counter()
        estimated = self._home_work_by_user(target)
        truth = self._home_work_by_user(aux)
        preds: list[HomeWork] = []
        for user in sorted(truth):
            est_home, est_work = estimated.get(user, (None, None))
            true_home, true_work = truth[user]
            preds.append(HomeWork(user, est_home, est_work, true_home, true_work))
        return AttackResult(
            result_id="poi_inference",
            attack_id="poi_inference",
            exp_id="",  # stamped by the orchestrator
            target_data_ref="protected",  # stamped by the orchestrator
            predictions=tuple(preds),
            scores=tuple(_dist(p.est_home, p.true_home) for p in preds),
            ground_truth_ref="clean.user_id home/work stay-points",
            runtime_s=time.perf_counter() - started,
        )

    def _home_work_by_user(
        self, trajs: Sequence[CleanTrajectory]
    ) -> dict[str, tuple[LatLon | None, LatLon | None]]:
        """Per user: (home, work) centroids over all their stay-points, split by local hour."""
        by_user: dict[str, list[_Stay]] = defaultdict(list)
        for tr in trajs:
            by_user[tr.user_id].extend(self._stay_points(tr.points))
        out: dict[str, tuple[LatLon | None, LatLon | None]] = {}
        for user, stays in by_user.items():
            night = [s for s in stays if self._in(self._local_hour(s.t), self.home_hours)]
            day = [s for s in stays if self._in(self._local_hour(s.t), self.work_hours)]
            out[user] = (self._centroid(night), self._centroid(day))
        return out

    def _stay_points(self, points: Sequence[Point]) -> list[_Stay]:
        """Time-ordered stay-points: maximal runs within ``radius_m`` spanning >= ``dwell_s``."""
        n = len(points)
        stays: list[_Stay] = []
        i = 0
        while i < n:
            j = i + 1
            while (
                j < n
                and haversine_m(points[i][0], points[i][1], points[j][0], points[j][1])
                <= self.radius_m
            ):
                j += 1
            if points[j - 1][2] - points[i][2] >= self.dwell_s:
                seg = points[i:j]
                lat = sum(p[0] for p in seg) / len(seg)
                lon = sum(p[1] for p in seg) / len(seg)
                stays.append(_Stay(lat, lon, points[i][2], len(seg)))
                i = j
            else:
                i += 1
        return stays

    def _local_hour(self, t: float) -> float:
        """Local wall-clock hour (fractional) of an epoch time under ``tz_offset_h``."""
        dt = datetime.fromtimestamp(t, UTC)
        return (dt.hour + dt.minute / 60.0 + self.tz_offset_h) % 24.0

    @staticmethod
    def _centroid(stays: Sequence[_Stay]) -> LatLon | None:
        """Support-weighted (lat, lon) centroid of stay-points; None when there are none."""
        if not stays:
            return None
        weight = sum(s.n for s in stays)
        lat = sum(s.lat * s.n for s in stays) / weight
        lon = sum(s.lon * s.n for s in stays) / weight
        return (lat, lon)

    @staticmethod
    def _in(hour: float, window: tuple[int, int]) -> bool:
        """Whether ``hour`` falls in ``[start, end)``, wrapping past midnight when start > end."""
        start, end = window
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end


def _dist(a: LatLon | None, b: LatLon | None) -> float:
    """Haversine metres between two (lat, lon) points; NaN if either is unresolved."""
    if a is None or b is None:
        return float("nan")
    return haversine_m(a[0], a[1], b[0], b[1])


def attribute_report(
    result: AttackResult,
    threshold_m: float = 200.0,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    seed: int = 0,
) -> dict[str, tuple[float, float, float]]:
    """Per-metric (mean, ci_low, ci_high) over users: home/work error (m) and localised fraction.

    Error means are taken over users the attack actually localised (an estimate exists); the
    localised fraction is over every user with a ground-truth location, so a user the attack
    fails to place counts as not-localised rather than silently vanishing.
    """
    home_err: list[float] = []
    work_err: list[float] = []
    home_loc: list[float] = []
    work_loc: list[float] = []
    for p in result.predictions:
        if p.true_home is not None:
            d = _dist(p.est_home, p.true_home)
            home_loc.append(1.0 if p.est_home is not None and d <= threshold_m else 0.0)
            if p.est_home is not None:
                home_err.append(d)
        if p.true_work is not None:
            d = _dist(p.est_work, p.true_work)
            work_loc.append(1.0 if p.est_work is not None and d <= threshold_m else 0.0)
            if p.est_work is not None:
                work_err.append(d)
    rng = np.random.default_rng(seed)
    return {
        "home_error_m": bootstrap_ci(np.array(home_err, dtype=float), n_bootstrap, ci, rng),
        "work_error_m": bootstrap_ci(np.array(work_err, dtype=float), n_bootstrap, ci, rng),
        "home_localised": bootstrap_ci(np.array(home_loc, dtype=float), n_bootstrap, ci, rng),
        "work_localised": bootstrap_ci(np.array(work_loc, dtype=float), n_bootstrap, ci, rng),
    }
