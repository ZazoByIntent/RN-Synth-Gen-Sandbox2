"""Trajectory representation adapters (design §2.2, module 4)."""

from collections.abc import Sequence
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

    def adjacent(self, a: int, b: int) -> bool:
        """True when ``b`` is one of ``a``'s eight neighbours (Chebyshev distance 1)."""
        ra, ca = divmod(a, self.n_cols)
        rb, cb = divmod(b, self.n_cols)
        return a != b and max(abs(ra - rb), abs(ca - cb)) == 1

    def chain(self, cells: Sequence[int]) -> list[int]:
        """8-connected chain through ``cells``: duplicates collapsed, gaps bridged by a king's walk.

        Consecutive repeats of a cell are dropped; between two non-adjacent cells the
        LDPTrace reference's greedy walk (``GridMap.find_shortest_path``) is inserted —
        each step moves the row toward the target if it differs and the column toward
        the target if it differs, i.e. diagonally first, then straight. Idempotent on
        chains that are already valid, ``[]`` for no cells; an index outside the grid
        raises ValueError.
        """
        chain: list[int] = []
        for raw in cells:
            cell = int(raw)
            if not 0 <= cell < self.n_cells:
                raise ValueError(f"cell {cell} lies outside the {self.n_rows}x{self.n_cols} grid")
            if chain and chain[-1] == cell:
                continue
            if chain and not self.adjacent(chain[-1], cell):
                chain.extend(self._king_walk(chain[-1], cell))
            chain.append(cell)
        return chain

    def _king_walk(self, a: int, b: int) -> list[int]:
        """Cells strictly between ``a`` and ``b`` on the reference greedy king's-move walk."""
        r, c = divmod(a, self.n_cols)
        rb, cb = divmod(b, self.n_cols)
        out: list[int] = []
        while True:
            if r != rb:
                r += 1 if rb > r else -1
            if c != cb:
                c += 1 if cb > c else -1
            if (r, c) == (rb, cb):
                return out
            out.append(r * self.n_cols + c)


class TrajectoryView:
    """Uniform access to different representations of one trajectory.

    Wraps the clean (GPS) and/or matched (road-segment) form, or — when neither
    exists — a bare ``sequence`` of engine symbols: edge ids in the segments
    representation, grid-cell indices in the cells representation. Generators and the
    membership attack read :meth:`as_sequence`, which serves both. Each ``as_*`` view
    raises ValueError when the form it needs was not provided.
    """

    def __init__(
        self,
        clean: CleanTrajectory | None = None,
        matched: MatchedTrajectory | None = None,
        sequence: tuple[int, ...] | None = None,
    ) -> None:
        if clean is None and matched is None and sequence is None:
            raise ValueError(
                "TrajectoryView needs a clean and/or matched trajectory or a bare sequence"
            )
        self.clean = clean
        self.matched = matched
        self.sequence = sequence

    @property
    def traj_id(self) -> str:
        """Trajectory id from the clean, else the matched form; empty for a bare sequence."""
        if self.clean is not None:
            return self.clean.traj_id
        if self.matched is not None:
            return self.matched.traj_id
        return ""

    @property
    def user_id(self) -> str:
        """Owning user id (ground truth for attacks); empty for a bare sequence."""
        if self.clean is not None:
            return self.clean.user_id
        if self.matched is not None:
            return self.matched.user_id
        return ""

    @property
    def split(self) -> str | None:
        """Dataset split label; None when no clean form is wrapped."""
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
        """Road-segment view: the matched edge_id sequence (never the bare sequence)."""
        return self._matched().edge_seq

    def as_sequence(self) -> tuple[int, ...]:
        """Engine sequence: the bare ``sequence`` when given, else the matched edge_seq."""
        if self.sequence is not None:
            return self.sequence
        if self.matched is not None:
            return self.matched.edge_seq
        raise ValueError("sequence view requires a bare sequence or a matched trajectory")

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
