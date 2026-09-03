"""LDPTrace reference-format inputs: the ``.dat`` loader and the Porto → ``.dat`` conversion.

Both halves serve the validation of the ``ldptrace`` port against the authors' code
(``docs/NACRT_LDPTRACE_VALIDACIJA.md``, decisions D-V.2 and D-V.3):

- :class:`LDPTraceDatLoader` reads the text format of the reference implementation
  (github.com/zealscott/LDPTrace, ``read_brinkhoff``): per trajectory a ``#<id>:`` line
  and a ``>0: x,y;x,y;...;`` line, ``x = lon`` and ``y = lat`` in whatever unit the
  file carries. Every trajectory is its own user (the paper's one-user-one-trajectory
  model, so the user split is a trajectory split) and timestamps are synthetic
  ``i·dt_s`` because the format has none. ``native_region = "none"``: the loader has no
  map, so the map/dataset consistency check rejects it with any map; it runs only in the
  cells representation (orchestrator support lands with PR B2).
- Pure functions that turn the Kaggle Porto taxi file into that format:
  :func:`iter_porto_polylines`, :func:`drop_reason`, :func:`convert_porto` and the two
  writers. Filtering is deterministic and seed-free — rows with ``MISSING_DATA == "True"``,
  polylines with fewer than two points and trajectories not entirely inside the chosen
  bbox are dropped (the paper's "central areas" selection). Outputs under ``out_dir``:
  ``porto.dat`` (this loader), ``porto.xz`` (``lzma`` + ``pickle`` of a list of lists of
  ``(lon, lat)`` pairs, what the reference code loads) and ``porto_stats.json`` with the
  bbox of the kept points, ``grid_bbox`` widened by ``1e-6`` on each side (the
  reference's ``dataset_stats`` rule, so both sides share one grid) and the counts per
  drop reason. ``scripts/porto_to_ldptrace_dat.py`` is the command-line wrapper.
"""

import csv
import json
import lzma
import pickle
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

from trajguard.datamodel import RawTrajectory
from trajguard.datasets.base import DatasetLoader
from trajguard.experiments.registry import register

BBox = tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat), as Grid
Polyline = list[tuple[float, float]]  # (lon, lat) pairs — the reference's (x, y)

PORTO_CENTRE_BBOX: BBox = (-8.69, 41.13, -8.55, 41.19)
GRID_MARGIN = 1e-6  # reference dataset_stats: grid bbox = bbox of the points ± 1e-6
DROP_REASONS = ("missing_data", "too_short", "outside_bbox")
_CSV_FIELD_LIMIT = 2**31 - 1  # long Porto polylines exceed csv's 128 kB default
_REQUIRED_COLUMNS = ("TRIP_ID", "MISSING_DATA", "POLYLINE")


@register("dataset", "ldptrace_dat")
class LDPTraceDatLoader(DatasetLoader):
    """Reads trajectories from a ``.dat`` file in the LDPTrace reference text format."""

    dataset_id = "ldptrace_dat"
    native_region = "none"  # no map: cells representation only

    def __init__(self, path: str | Path, dt_s: float = 15.0) -> None:
        """``path`` is the ``.dat`` file; ``dt_s`` spaces the synthetic timestamps."""
        if dt_s <= 0:
            raise ValueError(f"dt_s must be > 0, got {dt_s}")
        self.path = Path(path)
        self.dt_s = float(dt_s)

    def iter_trajectories(self) -> Iterator[RawTrajectory]:
        """Yield one RawTrajectory per record in file order; user = record id, times ``i·dt_s``."""
        for record_id, polyline in read_dat(self.path):
            points = tuple((lat, lon, i * self.dt_s) for i, (lon, lat) in enumerate(polyline))
            yield RawTrajectory(
                traj_id=f"{self.dataset_id}/{record_id}",
                user_id=record_id,
                dataset_id=self.dataset_id,
                points=points,
                start_t=0.0,
                end_t=points[-1][2],
                n_points=len(points),
                source_file=str(self.path),
            )


# -- .dat format ------------------------------------------------------------------------


def read_dat(path: str | Path) -> Iterator[tuple[str, Polyline]]:
    """Parse ``#<id>:`` / ``>0: x,y;...;`` record pairs; a malformed line raises with its number."""
    path = Path(path)
    pending: str | None = None
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                if pending is not None:
                    raise ValueError(f"{path}:{lineno}: record {pending!r} has no point line")
                if len(line) < 3 or not line.endswith(":"):
                    raise ValueError(f"{path}:{lineno}: expected '#<id>:', got {line!r}")
                pending = line[1:-1]
            elif line.startswith(">"):
                if pending is None:
                    raise ValueError(f"{path}:{lineno}: point line without a preceding '#<id>:'")
                yield pending, _parse_points(line, path, lineno)
                pending = None
            else:
                raise ValueError(f"{path}:{lineno}: unexpected line {line!r}")
    if pending is not None:
        raise ValueError(f"{path}: record {pending!r} at end of file has no point line")


def _parse_points(line: str, path: Path, lineno: int) -> Polyline:
    """``>0: x,y;x,y;...;`` → [(x, y), …]; empty records and bad tokens are errors."""
    _, sep, body = line.partition(":")
    if not sep:
        raise ValueError(f"{path}:{lineno}: expected '>0: x,y;...;', got {line!r}")
    points: Polyline = []
    for token in body.split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            x, y = (float(v) for v in token.split(","))
        except ValueError as err:
            raise ValueError(f"{path}:{lineno}: bad point {token!r}") from err
        points.append((x, y))
    if not points:
        raise ValueError(f"{path}:{lineno}: record has no points")
    return points


def write_dat(path: str | Path, trajs: Iterable[Sequence[tuple[float, float]]]) -> int:
    """Write ``(lon, lat)`` polylines as ``#<i>:`` / ``>0: x,y;...;`` records; returns the count."""
    n = 0
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        for i, poly in enumerate(trajs):
            body = ";".join(f"{float(x)!r},{float(y)!r}" for x, y in poly)
            fh.write(f"#{i}:\n>0: {body};\n")
            n += 1
    return n


def write_reference_xz(path: str | Path, trajs: Iterable[Sequence[tuple[float, float]]]) -> None:
    """Pickle the polylines inside an ``lzma`` container, the form the reference code loads."""
    payload = [[(float(x), float(y)) for x, y in poly] for poly in trajs]
    with lzma.open(path, "wb") as fh:
        pickle.dump(payload, fh)


# -- Porto (Kaggle train.csv) -----------------------------------------------------------


def iter_porto_polylines(csv_path: str | Path) -> Iterator[tuple[str, bool, Polyline]]:
    """Stream ``(trip_id, missing_data, polyline)`` rows from the Kaggle ``train.csv``."""
    csv.field_size_limit(_CSV_FIELD_LIMIT)
    with Path(csv_path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in _REQUIRED_COLUMNS if c not in (reader.fieldnames or ())]
        if missing:
            raise ValueError(f"{csv_path}: missing columns {missing}")
        for row in reader:
            poly = [(float(x), float(y)) for x, y in json.loads(row["POLYLINE"])]
            yield row["TRIP_ID"], row["MISSING_DATA"] == "True", poly


def drop_reason(
    missing_data: bool, polyline: Sequence[tuple[float, float]], bbox: BBox
) -> str | None:
    """Why the reference-style selection drops a trajectory; ``None`` when it is kept."""
    if missing_data:
        return "missing_data"
    if len(polyline) < 2:
        return "too_short"
    min_lon, min_lat, max_lon, max_lat = bbox
    if not all(min_lon <= x <= max_lon and min_lat <= y <= max_lat for x, y in polyline):
        return "outside_bbox"
    return None


def convert_porto(
    csv_path: str | Path,
    out_dir: str | Path,
    bbox: BBox = PORTO_CENTRE_BBOX,
    max_trajectories: int | None = None,
) -> dict[str, Any]:
    """Filter the Kaggle file into ``porto.dat``, ``porto.xz`` and ``porto_stats.json``.

    Deterministic, no seed. ``max_trajectories`` stops reading after that many kept
    trajectories (smoke runs); ``n_read`` then counts only the rows consumed. Refuses to
    write anywhere under a ``data/raw/`` directory. Returns the stats dict it wrote.
    """
    csv_path, out_dir = Path(csv_path), Path(out_dir)
    _validate_bbox(bbox)
    if max_trajectories is not None and max_trajectories < 1:
        raise ValueError(f"max_trajectories must be >= 1, got {max_trajectories}")
    _reject_raw_dir(out_dir)

    kept: list[Polyline] = []
    dropped = dict.fromkeys(DROP_REASONS, 0)
    n_read = n_points = 0
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for _trip_id, missing, poly in iter_porto_polylines(csv_path):
        n_read += 1
        reason = drop_reason(missing, poly, bbox)
        if reason is not None:
            dropped[reason] += 1
            continue
        kept.append(poly)
        n_points += len(poly)
        for x, y in poly:
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
        if max_trajectories is not None and len(kept) >= max_trajectories:
            break
    if not kept:
        raise ValueError(f"{csv_path}: no trajectory survived the filter {bbox}")

    out_dir.mkdir(parents=True, exist_ok=True)
    write_dat(out_dir / "porto.dat", kept)
    write_reference_xz(out_dir / "porto.xz", kept)
    stats: dict[str, Any] = {
        "source": str(csv_path),
        "bbox_filter": list(bbox),
        "max_trajectories": max_trajectories,
        "n_read": n_read,
        "n_kept": len(kept),
        "n_dropped": dropped,
        "n_points": n_points,
        "bbox": [min_x, min_y, max_x, max_y],
        "grid_bbox": [
            min_x - GRID_MARGIN,
            min_y - GRID_MARGIN,
            max_x + GRID_MARGIN,
            max_y + GRID_MARGIN,
        ],
    }
    (out_dir / "porto_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def _validate_bbox(bbox: BBox) -> None:
    if len(bbox) != 4:
        raise ValueError(f"bbox needs 4 numbers (min_lon, min_lat, max_lon, max_lat), got {bbox}")
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (min_lon < max_lon and min_lat < max_lat):
        raise ValueError(f"bbox must satisfy min < max on both axes, got {bbox}")


def _reject_raw_dir(out_dir: Path) -> None:
    """``data/raw/`` is immutable input: refuse any output path inside it."""
    parts = out_dir.resolve().parts
    for a, b in zip(parts, parts[1:], strict=False):
        if a == "data" and b == "raw":
            raise ValueError(f"refusing to write under data/raw/: {out_dir}")
