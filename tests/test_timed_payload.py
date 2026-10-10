"""P1: the timed synthetic payload (TimedRoute) and its Parquet round trip."""

from datetime import timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from trajguard.datamodel import (
    BEIJING_UTC_OFFSET_S,
    LinkVisit,
    SyntheticTrajectory,
    TimedRoute,
)
from trajguard.datamodel.timed_io import (
    TIME_BASE,
    read_timed_synthetic,
    write_timed_synthetic,
)

# 2008-10-23 01:53:04 UTC, a Geolife-era instant -> 09:53:04 local time in Beijing.
T0 = 1224726784.0


def _route() -> TimedRoute:
    """Three links; the middle one holds a 120 s stop inside a 150 s visit."""
    return TimedRoute(
        visits=(
            LinkVisit(edge_id=17, t_enter=T0, t_exit=T0 + 12.5),
            LinkVisit(edge_id=4, t_enter=T0 + 12.5, t_exit=T0 + 162.5, dwell_s=120.0),
            LinkVisit(edge_id=2**40, t_enter=T0 + 170.0, t_exit=T0 + 181.25),
        ),
        utc_offset_s=BEIJING_UTC_OFFSET_S,
    )


def test_timed_route_derived_fields_and_local_time() -> None:
    """Edge sequence, departure/arrival and the UTC+8 local clock follow from the visits."""
    r = _route()
    assert r.edge_seq == (17, 4, 2**40)
    assert r.departure_t == T0
    assert r.arrival_t == T0 + 181.25
    assert r.visits[1].moving_s == pytest.approx(30.0)
    local = r.to_local(r.departure_t)
    assert local.utcoffset() == timedelta(hours=8)
    assert (local.hour, local.minute, local.second) == (9, 53, 4)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"edge_id": 1, "t_enter": 10.0, "t_exit": 9.0},
        {"edge_id": 1, "t_enter": 10.0, "t_exit": 20.0, "dwell_s": 11.0},
        {"edge_id": 1, "t_enter": 10.0, "t_exit": 20.0, "dwell_s": -1.0},
        {"edge_id": 1, "t_enter": float("nan"), "t_exit": 20.0},
    ],
)
def test_link_visit_rejects_inconsistent_times(kwargs: dict[str, float]) -> None:
    """Exit before entry, a dwell outside the visit and NaN times are rejected."""
    with pytest.raises(ValueError):
        LinkVisit(**kwargs)


def test_timed_route_rejects_overlap_empty_and_bad_offset() -> None:
    """Overlapping visits, an empty route and an offset beyond ±14 h are rejected."""
    a = LinkVisit(edge_id=1, t_enter=0.0, t_exit=10.0)
    b = LinkVisit(edge_id=2, t_enter=5.0, t_exit=15.0)
    with pytest.raises(ValueError):
        TimedRoute(visits=(a, b), utc_offset_s=BEIJING_UTC_OFFSET_S)
    with pytest.raises(ValueError):
        TimedRoute(visits=(), utc_offset_s=BEIJING_UTC_OFFSET_S)
    with pytest.raises(ValueError):
        TimedRoute(visits=(a,), utc_offset_s=15 * 3600)


def test_parquet_round_trip_is_exact(tmp_path: Path) -> None:
    """Writing and reading back gives equal frozen records and records the time base."""
    syn = [
        SyntheticTrajectory(
            syn_id=f"uldp:{i}",
            generator_id="uldp_test",
            params_hash="abc123",
            payload=_route(),
            trained_on_split="train",
            map_id="beijing-test",
        )
        for i in range(3)
    ]
    path = tmp_path / "synthetic_timed.parquet"
    write_timed_synthetic(path, syn)
    assert read_timed_synthetic(path) == syn
    meta = pq.read_schema(path).metadata  # type: ignore[no-untyped-call]
    assert meta[b"time_base"] == TIME_BASE.encode()


def test_writer_rejects_untimed_payload(tmp_path: Path) -> None:
    """Existing generators' bare edge-sequence payloads are not silently written as timed."""
    plain = SyntheticTrajectory("s0", "markov", "h", (1, 2, 3), "train", "m")
    with pytest.raises(TypeError):
        write_timed_synthetic(tmp_path / "x.parquet", [plain])
