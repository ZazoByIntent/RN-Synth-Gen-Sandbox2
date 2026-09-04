"""Utility metrics of the LDPTrace paper (Du et al., PVLDB 2023), verbatim from the authors' code.

Pure functions over two populations — a real one and a synthetic one — for the
differential validation of the ``ldptrace`` port (``docs/NACRT_LDPTRACE_VALIDACIJA.md``).
Every definition follows ``LDPTrace/code/{experiment,utils,trajectory,main}.py`` at
github.com/zealscott/LDPTrace (read 2 Sep 2026), quirks included, so that these
functions applied to the reference implementation's own synthetic output reproduce the
numbers it prints. Nothing here is registered or wired into the orchestrator; the
paired/unpaired metrics of ``evaluation/utility.py`` are untouched.

Two input kinds:

- **Cell chains** (``Chains``): per trajectory a sequence of row-major cell indices of
  a :class:`Grid`, consecutive duplicates collapsed and every step 8-adjacent — the
  reference's ``trajectory_point2grid(..., interp=True)``, the port's
  ``LDPTraceGenerator.cell_sequence`` and its payloads. Used by the density, hotspot,
  Kendall, trip and pattern metrics.
- **Points** (``Points``): per trajectory an ``(n_points, 2)`` array of ``(x, y)`` in
  the axes of ``grid.bbox`` (x along longitude, y along latitude; any unit — every
  metric is scale-free). Used by the point query, length and diameter metrics. The
  reference evaluates the real side of length/diameter on the raw GPS points and the
  synthetic side — plus both sides of the point query — on one uniform random point
  per chain cell; :func:`sample_points` reproduces that conversion and
  :func:`evaluate` applies the same split.

Direction: seven metrics are errors (lower is better); ``coverage_kendall_tau`` and
``pattern_f1`` are scores (higher is better). The reference prints the latter under
the label "Pattern F1 error", but the value it prints is F1 itself — the name here
says what the number is.

Jensen–Shannon divergence is the reference's ``utils.jensen_shannon_distance``:
``0.5·KL(p, m) + 0.5·KL(q, m)`` with the **natural logarithm** (maximum ln 2 ≈ 0.693),
``1e-8`` smoothing inside the log ratio only, no square root. It is not the base-2
``_jsd_bits`` of ``evaluation/utility.py``.

Deviations from the reference, each also noted at the function:

- Ties in a top-k ranking break deterministically (count descending, then cell index
  or pattern ascending). The reference breaks them by insertion order after a seeded
  shuffle of its database, which cannot be reproduced; values agree whenever no tie
  sits exactly at the cut-off.
- Division by zero is guarded: an empty top-k intersection gives F1 = 0 and a
  histogram left without mass gives ``nan`` (the reference raises or warns).
- The point query's random centres come from the caller's seeded ``rng`` instead of
  Python's global ``random``; the reference's own AvRE is matched in distribution,
  not to the digit.
- The grid's flat index is row-major with rows along y; the reference's is
  ``i·n + j`` with ``i`` along x. No metric value depends on the numbering except
  tie-breaking.
"""

import math
from collections.abc import Sequence

import numpy as np

from trajguard.representation import Grid

Chains = Sequence[Sequence[int]]
Points = Sequence[np.ndarray]

_SMOOTHING = 1e-8  # reference utils.kl_divergence: log((p + 1e-8) / (q + 1e-8))
_PAIR_BLOCK = 1_000_000  # pairwise-distance rows per block (memory bound for long tracks)


# --- shared pieces -----------------------------------------------------------------


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    """Reference ``utils.kl_divergence``: Σ p · ln((p + 1e-8) / (q + 1e-8))."""
    return float(np.sum(np.log((p + _SMOOTHING) / (q + _SMOOTHING)) * p))


def _jsd(p: np.ndarray, q: np.ndarray) -> float:
    """Reference ``utils.jensen_shannon_distance``: 0.5·KL(p, m) + 0.5·KL(q, m), m = (p + q)/2."""
    m = (p + q) / 2.0
    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def _normalized(counts: np.ndarray) -> np.ndarray:
    """Counts scaled to sum 1; all-``nan`` when there is no mass (guarded 0/0)."""
    total = float(counts.sum())
    if total <= 0.0:
        return np.full(len(counts), np.nan)
    result: np.ndarray = counts / total
    return result


def _require_populations(real: Sequence[object], syn: Sequence[object]) -> None:
    if len(real) == 0 or len(syn) == 0:
        raise ValueError("both populations must be non-empty")


def _flat_cells(chains: Chains, n_cells: int) -> tuple[np.ndarray, np.ndarray]:
    """(trajectory index, cell) of every chain element, validated against the grid."""
    lengths = np.fromiter((len(chain) for chain in chains), dtype=np.int64, count=len(chains))
    if lengths.size and lengths.min() < 1:
        raise ValueError("cell chains must be non-empty")
    cells = np.fromiter(
        (int(c) for chain in chains for c in chain), dtype=np.int64, count=int(lengths.sum())
    )
    if cells.size and (cells.min() < 0 or cells.max() >= n_cells):
        raise ValueError(f"cell index out of range for a grid with {n_cells} cells")
    owners = np.repeat(np.arange(len(chains), dtype=np.int64), lengths)
    return owners, cells


def _visit_counts(chains: Chains, n_cells: int) -> np.ndarray:
    """Reference ``get_real_density``: one unit per chain element (revisits count again)."""
    _, cells = _flat_cells(chains, n_cells)
    return np.bincount(cells, minlength=n_cells).astype(float)


def _pass_counts(chains: Chains, n_cells: int) -> np.ndarray:
    """Reference ``pass_through`` counting: distinct trajectories touching each cell."""
    owners, cells = _flat_cells(chains, n_cells)
    keys = np.unique(owners * n_cells + cells)
    return np.bincount(keys % n_cells, minlength=n_cells).astype(float)


def _trip_counts(chains: Chains, n_cells: int) -> np.ndarray:
    """Reference ``get_start_end_dist``: counts over ``start · N + end`` (N² bins)."""
    _flat_cells(chains, n_cells)  # validation only
    starts = np.fromiter((int(chain[0]) for chain in chains), dtype=np.int64, count=len(chains))
    ends = np.fromiter((int(chain[-1]) for chain in chains), dtype=np.int64, count=len(chains))
    return np.bincount(starts * n_cells + ends, minlength=n_cells * n_cells).astype(float)


def _top_cells(density: np.ndarray, k: int) -> list[int]:
    """Indices of the k largest densities; ties by lower index (stable sort, as the reference)."""
    order = np.argsort(-density, kind="stable")
    return [int(i) for i in order[:k]]


def _stack_points(points: Points) -> np.ndarray:
    """All points of a population as one ``(P, 2)`` float array."""
    arrays = [np.asarray(p, dtype=float).reshape(-1, 2) for p in points]
    return np.concatenate(arrays) if arrays else np.empty((0, 2))


# --- cell-chain metrics --------------------------------------------------------------


def density_error(real: Chains, syn: Chains, grid: Grid) -> float:
    """Reference "Density Error": JSD between the normalised cell-visit histograms.

    One count per chain element over the ``grid.n_cells`` cells (a cell revisited later
    in the same chain counts again), each side normalised by its own total.
    """
    _require_populations(real, syn)
    p = _normalized(_visit_counts(real, grid.n_cells))
    q = _normalized(_visit_counts(syn, grid.n_cells))
    return _jsd(p, q)


def hotspot_query_error(real: Chains, syn: Chains, grid: Grid, k: int = 5) -> float:
    """Reference "Hotspot Query Error": ``1 − NDCG@k`` of the synthetic top-k cells.

    Both sides rank cells by normalised visit density (ties to the lower index). The
    synthetic cell at rank ``i`` has relevance ``1 / (its rank in the real top-k + 1)``
    when it is among the real top-k, else 0; DCG discounts by ``1 / log2(i + 2)`` and
    the ideal DCG assumes relevances ``1, 1/2, …, 1/k`` in that order. ``k`` defaults to
    the reference's hard-coded 5.
    """
    _require_populations(real, syn)
    if not 1 <= k <= grid.n_cells:
        raise ValueError(f"k must be in [1, {grid.n_cells}], got {k}")
    real_top = _top_cells(_normalized(_visit_counts(real, grid.n_cells)), k)
    syn_top = _top_cells(_normalized(_visit_counts(syn, grid.n_cells)), k)
    real_rank = {cell: i for i, cell in enumerate(real_top)}
    positions = np.arange(1, k + 1, dtype=float)
    discount = 1.0 / np.log2(positions + 1.0)
    relevance = np.array([1.0 / (real_rank[c] + 1) if c in real_rank else 0.0 for c in syn_top])
    dcg = float(np.sum(relevance * discount))
    idcg = float(np.sum((1.0 / positions) * discount))
    return 1.0 - dcg / idcg


def coverage_kendall_tau(real: Chains, syn: Chains, grid: Grid) -> float:
    """Reference "Kendall_tau" over per-cell coverage counts (higher is better).

    A cell's count is the number of distinct trajectories passing through it. Over all
    cell pairs ``i < j``: a pair strictly ordered in the real counts is concordant when
    the synthetic counts order it the same way and reversed otherwise (a synthetic tie
    counts as reversed); pairs tied in the real counts are skipped. Returns
    ``(concordant − reversed) / (N(N − 1)/2)`` with ``N = grid.n_cells`` — not the
    tau-b of textbooks.
    """
    _require_populations(real, syn)
    n = grid.n_cells
    a = _pass_counts(real, n)
    s = _pass_counts(syn, n)
    upper = np.triu_indices(n, k=1)
    da = np.sign(a[:, None] - a[None, :])[upper]
    ds = np.sign(s[:, None] - s[None, :])[upper]
    ordered = da != 0
    concordant = int(np.sum(ordered & (ds == da)))
    reversed_ = int(np.sum(ordered & (ds != da)))
    return (concordant - reversed_) / (n * (n - 1) / 2.0)


def trip_error(real: Chains, syn: Chains, grid: Grid) -> float:
    """Reference "Trip error": JSD between the (start cell, end cell) pair distributions.

    Pairs are indexed ``start · N + end`` over ``N²`` bins, start = first and end = last
    element of each chain; each side normalised by its own total.
    """
    _require_populations(real, syn)
    p = _normalized(_trip_counts(real, grid.n_cells))
    q = _normalized(_trip_counts(syn, grid.n_cells))
    return _jsd(p, q)


def _pattern_counts(chains: Chains, min_size: int, max_size: int) -> dict[tuple[int, ...], int]:
    """Reference ``mine_patterns``: contiguous n-grams of length min..max, with multiplicity."""
    if not 1 <= min_size <= max_size:
        raise ValueError(f"need 1 <= min_size <= max_size, got {min_size}, {max_size}")
    counts: dict[tuple[int, ...], int] = {}
    for chain in chains:
        cells = tuple(int(c) for c in chain)
        for size in range(min_size, max_size + 1):
            for i in range(len(cells) - size + 1):
                pattern = cells[i : i + size]
                counts[pattern] = counts.get(pattern, 0) + 1
    return counts


def _top_patterns(counts: dict[tuple[int, ...], int], k: int) -> list[tuple[int, ...]]:
    """The k most frequent patterns; ties by pattern ascending (deterministic, see module doc)."""
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [pattern for pattern, _ in ranked[:k]]


def pattern_f1(
    real: Chains, syn: Chains, k: int = 100, min_size: int = 2, max_size: int = 8
) -> float:
    """Reference "Pattern F1 error" — which prints F1 itself: ``|top-k(real) ∩ top-k(syn)| / k``.

    Patterns are all contiguous cell n-grams of length ``min_size..max_size`` pooled
    into one ranking by support (count with multiplicity across trajectories and
    positions). Precision and recall both equal the intersection size over the nominal
    ``k`` (even when fewer than ``k`` patterns exist), so F1 equals that ratio; an
    empty intersection gives 0.0 where the reference divides by zero. Higher is better.
    """
    _require_populations(real, syn)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    real_top = set(_top_patterns(_pattern_counts(real, min_size, max_size), k))
    syn_top = set(_top_patterns(_pattern_counts(syn, min_size, max_size), k))
    return len(real_top & syn_top) / k


def pattern_support_error(
    real: Chains, syn: Chains, k: int = 100, min_size: int = 2, max_size: int = 8
) -> float:
    """Reference "Pattern support error": mean relative support error of the real top-k patterns.

    ``Σ |support_real(p) − support_syn(p)| / support_real(p) / k`` over the real top-k
    (a pattern absent from the synthetic side contributes 1). Supports are absolute
    counts, so the two populations should have the same number of trajectories, as
    in the reference.
    """
    _require_populations(real, syn)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    real_counts = _pattern_counts(real, min_size, max_size)
    syn_counts = _pattern_counts(syn, min_size, max_size)
    error = 0.0
    for pattern in _top_patterns(real_counts, k):
        real_support = real_counts[pattern]
        error += abs(real_support - syn_counts.get(pattern, 0)) / real_support
    return error / k


# --- point metrics -------------------------------------------------------------------


def sample_points(grid: Grid, chains: Chains, rng: np.random.Generator) -> list[np.ndarray]:
    """Reference ``trajectory_grid2points``: one uniform random point per chain cell.

    A one-cell chain yields two independent points from that cell (reference rule).
    Points are ``(x, y)`` in the axes of ``grid.bbox``; cell extents follow the grid's
    row-major layout (row along y, column along x).
    """
    min_x, min_y, max_x, max_y = grid.bbox
    step_x = (max_x - min_x) / grid.n_cols
    step_y = (max_y - min_y) / grid.n_rows
    _flat_cells(chains, grid.n_cells)  # validation only
    out: list[np.ndarray] = []
    for chain in chains:
        cells = np.asarray([int(c) for c in chain], dtype=np.int64)
        if len(cells) == 1:
            cells = np.repeat(cells, 2)
        rows, cols = np.divmod(cells, grid.n_cols)
        u = rng.random((len(cells), 2))
        x = min_x + (cols + u[:, 0]) * step_x
        y = min_y + (rows + u[:, 1]) * step_y
        out.append(np.column_stack([x, y]))
    return out


def point_query_avre(
    real: Points,
    syn: Points,
    grid: Grid,
    rng: np.random.Generator,
    n_queries: int = 200,
    size_factor: float = 9.0,
    sanity_bound: float = 0.01,
) -> float:
    """Reference "Point Query AvRE": mean relative error of random square range counts.

    Each query is a square of area ``bbox area / size_factor`` whose centre is uniform
    over ``grid.bbox`` (not clipped to it); its answer is the number of points inside
    the closed square, summed over all trajectories. The error is
    ``|real − syn| / max(real, sanity_bound · total real points)`` averaged over the
    queries. Defaults are the reference's (200 queries, 1/9 of the space, 1 %). The
    reference draws centres from Python's global ``random``; here they come from
    ``rng``, so its own printed value is matched in distribution, not to the digit.
    """
    _require_populations(real, syn)
    if n_queries < 1 or size_factor <= 0 or sanity_bound < 0:
        raise ValueError("need n_queries >= 1, size_factor > 0 and sanity_bound >= 0")
    real_xy = _stack_points(real)
    syn_xy = _stack_points(syn)
    min_x, min_y, max_x, max_y = grid.bbox
    edge = math.sqrt((max_x - min_x) * (max_y - min_y) / size_factor)
    floor = float(len(real_xy)) * sanity_bound
    errors = np.empty(n_queries)
    for i in range(n_queries):
        cx = rng.random() * (max_x - min_x) + min_x
        cy = rng.random() * (max_y - min_y) + min_y
        actual = _count_in_square(real_xy, cx, cy, edge)
        synthetic = _count_in_square(syn_xy, cx, cy, edge)
        errors[i] = abs(actual - synthetic) / max(actual, floor)
    return float(errors.mean())


def _count_in_square(xy: np.ndarray, cx: float, cy: float, edge: float) -> float:
    """Points inside the closed square centred at (cx, cy) with side ``edge``."""
    half = edge / 2.0
    inside = (
        (xy[:, 0] >= cx - half)
        & (xy[:, 0] <= cx + half)
        & (xy[:, 1] >= cy - half)
        & (xy[:, 1] <= cy + half)
    )
    return float(inside.sum())


def _travel_length(xy: np.ndarray) -> float:
    """Reference ``get_travel_distance``: sum of consecutive Euclidean distances."""
    if len(xy) < 2:
        return 0.0
    steps = np.diff(xy, axis=0)
    return float(np.sum(np.sqrt(np.sum(steps * steps, axis=1))))


def _diameter(xy: np.ndarray) -> float:
    """Reference ``get_diameter``: largest pairwise Euclidean distance (blocked for memory)."""
    n = len(xy)
    if n < 2:
        return 0.0
    best = 0.0
    step = max(1, _PAIR_BLOCK // n)
    for start in range(0, n, step):
        diff = xy[start : start + step, None, :] - xy[None, :, :]
        best = max(best, float(np.sqrt(np.max(np.sum(diff * diff, axis=2)))))
    return best


def _bucket_counts(
    real_values: np.ndarray, syn_values: np.ndarray, n_buckets: int
) -> tuple[np.ndarray, np.ndarray]:
    """Reference binning of ``calculate_length_error`` / ``calculate_diameter_error``, verbatim.

    Bucket width is ``(max(real) − min(real)) / n_buckets`` but the edges start at 0,
    so bucket ``i`` is the closed interval ``[i·w, (i + 1)·w]``: values above
    ``max(real) − min(real)`` fall into no bucket and are dropped, and a value exactly
    on an inner edge is counted in both adjacent buckets. The range comes from the
    real side only.
    """
    width = (float(real_values.max()) - float(real_values.min())) / n_buckets
    lower = np.arange(n_buckets, dtype=float) * width
    upper = lower + width

    def count(values: np.ndarray) -> np.ndarray:
        inside = (values[:, None] >= lower[None, :]) & (values[:, None] <= upper[None, :])
        counts: np.ndarray = inside.sum(axis=0).astype(float)
        return counts

    return count(real_values), count(syn_values)


def _binned_jsd(real_values: np.ndarray, syn_values: np.ndarray, n_buckets: int) -> float:
    if n_buckets < 1:
        raise ValueError(f"n_buckets must be >= 1, got {n_buckets}")
    real_counts, syn_counts = _bucket_counts(real_values, syn_values, n_buckets)
    return _jsd(_normalized(real_counts), _normalized(syn_counts))


def length_error(real: Points, syn: Points, n_buckets: int = 20) -> float:
    """Reference "Length error": JSD of binned travel lengths (sum of consecutive distances).

    Binning as in :func:`_bucket_counts` (20 buckets by default, reference quirks
    included); a side left without mass after the binning gives ``nan``.
    """
    _require_populations(real, syn)
    real_len = np.array([_travel_length(np.asarray(p, dtype=float).reshape(-1, 2)) for p in real])
    syn_len = np.array([_travel_length(np.asarray(p, dtype=float).reshape(-1, 2)) for p in syn])
    return _binned_jsd(real_len, syn_len, n_buckets)


def diameter_error(real: Points, syn: Points, n_buckets: int = 20) -> float:
    """Reference "Diameter error": JSD of binned diameters (largest pairwise distance).

    Same binning as :func:`length_error`.
    """
    _require_populations(real, syn)
    real_diam = np.array([_diameter(np.asarray(p, dtype=float).reshape(-1, 2)) for p in real])
    syn_diam = np.array([_diameter(np.asarray(p, dtype=float).reshape(-1, 2)) for p in syn])
    return _binned_jsd(real_diam, syn_diam, n_buckets)


# --- all nine at once ----------------------------------------------------------------

METRIC_NAMES: tuple[str, ...] = (
    "density_error",
    "hotspot_query_error",
    "point_query_avre",
    "coverage_kendall_tau",
    "trip_error",
    "diameter_error",
    "length_error",
    "pattern_f1",
    "pattern_support_error",
)


def evaluate(
    real: Chains,
    syn: Chains,
    grid: Grid,
    rng: np.random.Generator,
    *,
    real_raw_points: Points | None = None,
    syn_points: Points | None = None,
) -> dict[str, float]:
    """All nine metrics with the reference's input split, keyed by function name.

    Cell-chain metrics use ``real``/``syn`` directly. Point metrics follow ``main.py``:
    the point query compares one random point per cell of the real chains
    (``orig_sampled_trajectories``) with ``syn_points``; length and diameter compare
    ``real_raw_points`` — the raw GPS trajectories in the reference, defaulting to the
    same sampled real points when the caller has none — with ``syn_points``, which
    default to :func:`sample_points` of the synthetic chains (the reference's
    ``convert_grid_to_raw``). Reference defaults for k, queries and buckets apply.
    """
    real_sampled = sample_points(grid, real, rng)
    if syn_points is None:
        syn_points = sample_points(grid, syn, rng)
    if real_raw_points is None:
        real_raw_points = real_sampled
    return {
        "density_error": density_error(real, syn, grid),
        "hotspot_query_error": hotspot_query_error(real, syn, grid),
        "point_query_avre": point_query_avre(real_sampled, syn_points, grid, rng),
        "coverage_kendall_tau": coverage_kendall_tau(real, syn, grid),
        "trip_error": trip_error(real, syn, grid),
        "diameter_error": diameter_error(real_raw_points, syn_points),
        "length_error": length_error(real_raw_points, syn_points),
        "pattern_f1": pattern_f1(real, syn),
        "pattern_support_error": pattern_support_error(real, syn),
    }
