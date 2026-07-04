"""Geolife GPS trajectory loader (design §2.2, module 2)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from trajguard.datamodel import RawTrajectory
from trajguard.datasets.base import DatasetLoader
from trajguard.experiments.registry import register

_HEADER_LINES = 6
_FIELDS_PER_LINE = 7


@register("dataset", "geolife")
class GeolifeLoader(DatasetLoader):
    """Parses Geolife v1.3 ``.plt`` files under ``<root>/Data/<user>/Trajectory/``."""

    dataset_id = "geolife"
    native_region = "beijing"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def iter_trajectories(self) -> Iterator[RawTrajectory]:
        """Yield one RawTrajectory per .plt file, sorted by user then start time.

        Points are (lat, lon, unix_ts) triples; altitude (feet, -777 = invalid)
        is dropped at import since no planned attack uses it.
        """
        for plt_path in sorted((self.root / "Data").glob("*/Trajectory/*.plt")):
            user_id = plt_path.parent.parent.name
            points = _parse_plt(plt_path)
            if not points:
                continue
            yield RawTrajectory(
                traj_id=f"geolife/{user_id}/{plt_path.stem}",
                user_id=user_id,
                dataset_id=self.dataset_id,
                points=tuple(points),
                start_t=points[0][2],
                end_t=points[-1][2],
                n_points=len(points),
                source_file=str(plt_path),
            )


def _parse_plt(path: Path) -> list[tuple[float, float, float]]:
    """Parse one .plt into (lat, lon, unix_ts) triples, skipping malformed lines.

    Format: 6 header lines, then ``lat,lon,0,alt_ft,days_since_1899-12-30,date,time``
    per point; date/time strings are GMT (Geolife user guide).
    """
    points: list[tuple[float, float, float]] = []
    with path.open() as fh:
        for i, line in enumerate(fh):
            if i < _HEADER_LINES:
                continue
            parts = line.strip().split(",")
            if len(parts) != _FIELDS_PER_LINE:
                continue
            try:
                lat, lon = float(parts[0]), float(parts[1])
                stamp = datetime.strptime(f"{parts[5]} {parts[6]}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            points.append((lat, lon, stamp.replace(tzinfo=UTC).timestamp()))
    return points
