"""Trajectory representation adapters (design §2.2, module 4)."""

from dataclasses import dataclass

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory


@dataclass(frozen=True, slots=True)
class Grid:
    """A regular lon/lat grid over a bbox; cells are row-major indices."""

    bbox: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    n_rows: int
    n_cols: int

    @property
    def n_cells(self) -> int:
        """Total number of cells."""
        return self.n_rows * self.n_cols

    def cell_of(self, lat: float, lon: float) -> int:
        """Row-major cell index of a point; out-of-bbox points clamp to border cells."""
        min_lon, min_lat, max_lon, max_lat = self.bbox
        row = int((lat - min_lat) / (max_lat - min_lat) * self.n_rows)
        col = int((lon - min_lon) / (max_lon - min_lon) * self.n_cols)
        row = min(max(row, 0), self.n_rows - 1)
        col = min(max(col, 0), self.n_cols - 1)
        return row * self.n_cols + col


class TrajectoryView:
    """Uniform access to different representations of one trajectory.

    Wraps the clean (GPS) and/or matched (road-segment) form; each ``as_*``
    view raises ValueError when the form it needs was not provided.
    """

    def __init__(
        self,
        clean: CleanTrajectory | None = None,
        matched: MatchedTrajectory | None = None,
    ) -> None:
        if clean is None and matched is None:
            raise ValueError("TrajectoryView needs a clean and/or matched trajectory")
        self.clean = clean
        self.matched = matched

    @property
    def traj_id(self) -> str:
        """Trajectory id (identical in both forms when both are present)."""
        return self.clean.traj_id if self.clean is not None else self._matched().traj_id

    @property
    def user_id(self) -> str:
        """Owning user id (ground truth for attacks)."""
        return self.clean.user_id if self.clean is not None else self._matched().user_id

    @property
    def split(self) -> str | None:
        """Dataset split label; None when only a matched form is wrapped."""
        return self.clean.split if self.clean is not None else None

    @property
    def map_id(self) -> str:
        """Map the trajectory is matched to; empty string when unmatched."""
        return self.matched.map_id if self.matched is not None else ""

    def as_gps(self) -> tuple[tuple[float, float, float], ...]:
        """GPS view: (lat, lon, t) triples from the clean trajectory."""
        if self.clean is None:
            raise ValueError("GPS view requires a clean trajectory")
        return self.clean.points

    def as_segments(self) -> tuple[int, ...]:
        """Road-segment view: the matched edge_id sequence."""
        return self._matched().edge_seq

    def as_cells(self, grid: Grid) -> tuple[int, ...]:
        """Cell view: one grid cell index per GPS point."""
        return tuple(grid.cell_of(lat, lon) for lat, lon, _ in self.as_gps())

    def as_graph_path(self) -> tuple[int, ...]:
        """Graph-path view — deliberate hook, lands with the graph attacks (horizon B)."""
        raise NotImplementedError("graph-path view is a horizon-B hook (design §2.2)")

    def as_poi_visits(self, poi_layer: object) -> tuple[tuple[str, float], ...]:
        """POI-visit view — deliberate hook, lands with attribute inference work."""
        raise NotImplementedError("POI view is a horizon-B hook (design §2.2)")

    def _matched(self) -> MatchedTrajectory:
        if self.matched is None:
            raise ValueError("segment view requires a matched trajectory")
        return self.matched
