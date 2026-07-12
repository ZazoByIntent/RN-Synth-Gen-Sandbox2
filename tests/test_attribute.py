"""Tests for the POI / attribute inference attack (P6.5, design §6.4)."""

import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from trajguard.attacks.attribute import HomeWork, PoiInferenceAttack, attribute_report
from trajguard.datamodel import CleanTrajectory
from trajguard.experiments import registry
from trajguard.privacy.geoind import GeoIndistinguishability
from trajguard.representation import TrajectoryView

_BEIJING = timezone(timedelta(hours=8))


def _epoch(day: int, hour: int) -> float:
    """Unix seconds for a Beijing wall-clock time (so local-hour classification is exact)."""
    return datetime(2008, 11, day, hour, 0, tzinfo=_BEIJING).timestamp()


def _dwell(
    traj_id: str, user: str, loc: tuple[float, float], day: int, hour: int
) -> CleanTrajectory:
    """A trajectory dwelling at one spot: 8 points 60 s apart (420 s span) at a fixed hour."""
    lat, lon = loc
    pts = tuple((lat, lon, _epoch(day, hour) + i * 60.0) for i in range(8))
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    return CleanTrajectory(
        traj_id=traj_id,
        user_id=user,
        points=pts,
        bbox=(min(lons), min(lats), max(lons), max(lats)),
        duration_s=pts[-1][2] - pts[0][2],
        length_m=0.0,
        mean_speed=0.0,
        cleaning_flags=(),
        split=None,
    )


# Three users, each dwelling at a home (Beijing 02:00 -> night) and a work spot
# (Beijing 12:00 -> day); home and work are ~2 km apart, users are far apart.
_USERS = {
    "A": ((39.900, 116.400), (39.920, 116.420)),
    "B": ((39.950, 116.300), (39.970, 116.330)),
    "C": ((39.850, 116.500), (39.870, 116.470)),
}
RAW = [
    t
    for user, (home, work) in _USERS.items()
    for t in (_dwell(f"{user}-home", user, home, 1, 2), _dwell(f"{user}-work", user, work, 1, 12))
]


def _attack() -> PoiInferenceAttack:
    return PoiInferenceAttack(dwell_s=120.0, radius_m=300.0)


def _protect(raw: list[CleanTrajectory], epsilon: float, seed: int = 0) -> list[CleanTrajectory]:
    """Geo-ind-protect every trajectory with the real planar-Laplace mechanism."""
    mech = GeoIndistinguishability(epsilon=epsilon, unit_m=100.0, seed=seed)
    out: list[CleanTrajectory] = []
    for tr in raw:
        payload = mech.apply(TrajectoryView(clean=tr)).payload
        pts = tuple((float(lat), float(lon), float(t)) for lat, lon, t in payload)
        out.append(replace(tr, points=pts))
    return out


def test_attack_registered() -> None:
    assert registry.get("attack", "poi_inference") is PoiInferenceAttack
    assert PoiInferenceAttack.target_scope == {"protected", "synthetic"}


def test_stay_points_finds_the_dwell() -> None:
    home = (39.900, 116.400)
    stays = _attack()._stay_points(_dwell("A-home", "A", home, 1, 2).points)
    assert len(stays) == 1
    assert math.isclose(stays[0].lat, home[0]) and math.isclose(stays[0].lon, home[1])
    assert stays[0].n == 8


def test_raw_sanity_is_exact() -> None:
    """On unprotected data the estimate equals the ground truth -> zero error, all localised."""
    report = attribute_report(_attack().run(RAW, RAW))
    assert report["home_error_m"] == (0.0, 0.0, 0.0)
    assert report["work_error_m"] == (0.0, 0.0, 0.0)
    assert report["home_localised"] == (1.0, 1.0, 1.0)
    assert report["work_localised"] == (1.0, 1.0, 1.0)


def test_predictions_recover_home_and_work() -> None:
    result = _attack().run(RAW, RAW)
    preds = {p.user_id: p for p in result.predictions}
    assert set(preds) == set(_USERS)
    for user, (home, work) in _USERS.items():
        p: HomeWork = preds[user]
        assert p.est_home is not None and math.isclose(p.est_home[0], home[0])
        assert p.est_work is not None and math.isclose(p.est_work[0], work[0])


def test_geoind_sweep_reports_distance_with_ci() -> None:
    """DoD: geo-ind protected at eps {0.1, 1, 10} reports distances with bootstrap CI, and the
    attack degrades as the noise grows — strong eps localises home to metres, weak eps fails."""
    keys = {"home_error_m", "work_error_m", "home_localised", "work_localised"}
    reports = {
        eps: attribute_report(_attack().run(_protect(RAW, eps), RAW)) for eps in (10.0, 1.0, 0.1)
    }

    for report in reports.values():
        assert set(report) == keys
        for point, lo, hi in report.values():
            # eps=0.1 dissolves every stay-point -> NaN (nothing localised); skip its CI check
            if math.isfinite(point):
                assert lo <= point <= hi

    strong, mid, weak = reports[10.0], reports[1.0], reports[0.1]
    # Strong protection is barely protection: home pinned within a few metres, everyone localised.
    assert math.isfinite(strong["home_error_m"][0]) and strong["home_error_m"][0] < 20.0
    assert strong["home_localised"] == (1.0, 1.0, 1.0)
    # Error grows monotonically with the noise (raw 0 <= eps10 <= eps1), staying inside threshold.
    assert 0.0 <= strong["home_error_m"][0] <= mid["home_error_m"][0] < 200.0
    assert mid["home_localised"][0] == 1.0
    # Weak protection defeats the attack outright: no user localised.
    assert weak["home_localised"][0] == 0.0
    assert weak["work_localised"][0] == 0.0
    assert strong["home_localised"][0] > weak["home_localised"][0]


def test_report_is_deterministic() -> None:
    first = attribute_report(_attack().run(_protect(RAW, 1.0, seed=7), RAW), seed=3)
    second = attribute_report(_attack().run(_protect(RAW, 1.0, seed=7), RAW), seed=3)
    assert first == second
