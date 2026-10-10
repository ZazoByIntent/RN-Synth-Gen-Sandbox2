"""Parquet round-trip for synthetic trajectories that carry a ``TimedRoute`` payload.

One row per trajectory; the visits are a list of structs
``(edge_id, t_enter, t_exit, dwell_s)``, so DuckDB can ``unnest`` them. Times are
stored as float64 Unix seconds (UTC instants, bit-exact round trip) and the local
offset is written explicitly twice: as the per-row ``utc_offset_s`` column and as
the file's schema metadata ``time_base``.
"""

from collections.abc import Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trajguard.datamodel.entities import LinkVisit, SyntheticTrajectory, TimedRoute

TIME_BASE = "unix_seconds_utc; local = utc + utc_offset_s"
"""Value of the ``time_base`` schema-metadata key of a timed synthetic table."""

_VISIT_TYPE = pa.struct(
    [
        ("edge_id", pa.int64()),
        ("t_enter", pa.float64()),
        ("t_exit", pa.float64()),
        ("dwell_s", pa.float64()),
    ]
)

TIMED_SYNTHETIC_SCHEMA = pa.schema(
    [
        ("syn_id", pa.string()),
        ("generator_id", pa.string()),
        ("params_hash", pa.string()),
        ("trained_on_split", pa.string()),
        ("map_id", pa.string()),
        ("utc_offset_s", pa.int32()),
        ("visits", pa.list_(_VISIT_TYPE)),
    ],
    metadata={"time_base": TIME_BASE},
)


def write_timed_synthetic(path: str | Path, trajs: Sequence[SyntheticTrajectory]) -> None:
    """Write synthetic trajectories with ``TimedRoute`` payloads to one Parquet file."""
    routes: list[TimedRoute] = []
    for t in trajs:
        if not isinstance(t.payload, TimedRoute):
            raise TypeError(f"write_timed_synthetic: {t.syn_id} payload is not a TimedRoute")
        routes.append(t.payload)
    table = pa.table(
        {
            "syn_id": [t.syn_id for t in trajs],
            "generator_id": [t.generator_id for t in trajs],
            "params_hash": [t.params_hash for t in trajs],
            "trained_on_split": [t.trained_on_split for t in trajs],
            "map_id": [t.map_id for t in trajs],
            "utc_offset_s": [r.utc_offset_s for r in routes],
            "visits": [
                [
                    {
                        "edge_id": v.edge_id,
                        "t_enter": v.t_enter,
                        "t_exit": v.t_exit,
                        "dwell_s": v.dwell_s,
                    }
                    for v in r.visits
                ]
                for r in routes
            ],
        },
        schema=TIMED_SYNTHETIC_SCHEMA,
    )
    pq.write_table(table, Path(path))  # type: ignore[no-untyped-call]


def read_timed_synthetic(path: str | Path) -> list[SyntheticTrajectory]:
    """Read a file written by :func:`write_timed_synthetic` back into frozen records."""
    table = pq.read_table(Path(path))  # type: ignore[no-untyped-call]
    meta = table.schema.metadata or {}
    if meta.get(b"time_base") != TIME_BASE.encode():
        raise ValueError(f"read_timed_synthetic: {path} lacks time_base {TIME_BASE!r}")
    return [
        SyntheticTrajectory(
            syn_id=r["syn_id"],
            generator_id=r["generator_id"],
            params_hash=r["params_hash"],
            payload=TimedRoute(
                visits=tuple(
                    LinkVisit(
                        edge_id=int(v["edge_id"]),
                        t_enter=v["t_enter"],
                        t_exit=v["t_exit"],
                        dwell_s=v["dwell_s"],
                    )
                    for v in r["visits"]
                ),
                utc_offset_s=int(r["utc_offset_s"]),
            ),
            trained_on_split=r["trained_on_split"],
            map_id=r["map_id"],
        )
        for r in table.to_pylist()
    ]
