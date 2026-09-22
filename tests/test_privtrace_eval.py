"""The PrivTrace validation harness (``experiments/privtrace_eval.py``) on ``tiny.dat``."""

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from trajguard.datasets.ldptrace_dat import read_dat
from trajguard.evaluation.ldptrace_metrics import METRIC_NAMES
from trajguard.experiments import privtrace_eval as pe
from trajguard.experiments.ldptrace_eval import reference_cells
from trajguard.representation import Grid
from trajguard.synthesis.adaptive_grid import AdaptiveGrid

FIXTURES = Path(__file__).parent / "fixtures"
TINY_DAT = FIXTURES / "ldptrace_dat" / "tiny.dat"
# tiny.dat: five trajectories of 3/2/1/3/4 points in 0..6 x 0..6 (fixtures README).
TINY_POINTS = [
    [(0.5, 0.5), (1.5, 0.5), (2.5, 1.5)],
    [(0.5, 0.5), (3.5, 1.5)],
    [(2.5, 2.5)],
    [(4.5, 4.5), (4.6, 4.4), (5.5, 5.5)],
    [(5.5, 0.5), (4.5, 1.5), (3.5, 2.5), (2.5, 3.5)],
]
HUGE_EPS = 1e4  # Laplace noise negligible, as in test_privtrace.py
EPS_KEY = "10000.0"
FIRST_LEVEL_K = 2
EVAL_N = 3


def _tiny() -> pe.Points:
    return pe.load_points(TINY_DAT)


def _eval_grid(points: pe.Points) -> Grid:
    return Grid(bbox=pe.reference_bbox(points), n_rows=EVAL_N, n_cols=EVAL_N)


# --- inputs --------------------------------------------------------------------------------


def test_reference_bbox_extends_by_the_raw_span() -> None:
    """Data min/max ± 1e-5 · span on each axis; spans chosen so the numbers are exact."""
    points = [np.array([[0.0, 0.0], [100000.0, 50.0]]), np.array([[10.0, 200000.0]])]
    assert pe.reference_bbox(points) == (-1.0, -2.0, 100001.0, 200002.0)

    tiny = _tiny()  # x and y both span 0.5 .. 5.5
    assert pe.reference_bbox(tiny) == pytest.approx((0.49995, 0.49995, 5.50005, 5.50005), abs=1e-12)

    with pytest.raises(ValueError, match="at least one trajectory"):
        pe.reference_bbox([])
    with pytest.raises(ValueError, match="degenerate"):
        pe.reference_bbox([np.array([[1.0, 2.0], [1.0, 3.0]])])  # no spread in x


def test_load_points_reads_tiny_dat() -> None:
    points = _tiny()
    assert [len(p) for p in points] == [3, 2, 1, 3, 4]
    assert all(p.shape[1] == 2 and p.dtype == float for p in points)
    assert points[1].tolist() == [[0.5, 0.5], [3.5, 1.5]]  # (x, y) = (lon, lat) as in the file

    first_two = pe.load_points(TINY_DAT, max_trajectories=2)
    assert [p.tolist() for p in first_two] == [[list(xy) for xy in t] for t in TINY_POINTS[:2]]
    with pytest.raises(ValueError, match="max_trajectories"):
        pe.load_points(TINY_DAT, max_trajectories=0)


def test_write_subset_round_trip(tmp_path: Path) -> None:
    """The subset file is the reference's own format and reads back to the same points."""
    dst = tmp_path / "sub" / "subset.dat"
    assert pe.write_subset(TINY_DAT, dst, 2) == 2
    records = list(read_dat(dst))
    assert [record_id for record_id, _ in records] == ["0", "1"]  # renumbered 0..n-1
    assert [poly for _, poly in records] == TINY_POINTS[:2]

    raw = dst.read_bytes()
    assert raw.startswith(b"#0:\n>0:0.500000,0.500000;1.500000,0.500000;")  # no space, 6 decimals
    assert b"\r" not in raw  # LF endings
    assert raw.count(b"#") == 2


# --- chains without the king's walk ----------------------------------------------------------


def test_points_to_cell_sequences_drops_only_the_bridging() -> None:
    """The visited cells with duplicates collapsed; bridging them gives the chain back."""
    points = _tiny()
    grid = _eval_grid(points)
    sequences = pe.points_to_cell_sequences(grid, points)
    chains = pe.points_to_chains(grid, points)

    for xy, sequence, chain in zip(points, sequences, chains, strict=True):
        cells = reference_cells(grid, xy)
        assert sequence == [c for i, c in enumerate(cells) if i == 0 or cells[i - 1] != c]
        assert grid.chain(sequence) == chain
    # On the 3x3 grid every tiny.dat step stays inside or next to its cell, so nothing is
    # bridged and the two representations coincide.
    assert sequences == chains
    assert pe.interpolated_share(chains, sequences) == 0.0

    # On a 6x6 grid trajectory 1 — (0.5, 0.5) to (3.5, 1.5) — jumps two columns.
    fine = Grid(bbox=pe.reference_bbox(points), n_rows=6, n_cols=6)
    fine_sequences = pe.points_to_cell_sequences(fine, points)
    fine_chains = pe.points_to_chains(fine, points)
    assert fine_sequences[1] == [0, 9] and fine_chains[1] == [0, 7, 8, 9]
    assert len(fine_sequences[1]) < len(fine_chains[1])
    for sequence, chain in zip(fine_sequences, fine_chains, strict=True):
        assert fine.chain(sequence) == chain
    assert pe.interpolated_share(fine_chains, fine_sequences) == pytest.approx(2 / 14)


def test_interpolated_share_counts_the_inserted_cells() -> None:
    assert pe.interpolated_share([[0, 1, 2, 5], [4]], [[0, 5], [4]]) == pytest.approx(2 / 5)
    assert pe.interpolated_share([[0, 1]], [[0, 1]]) == 0.0
    assert pe.interpolated_share([], []) == 0.0  # nothing scored, nothing interpolated
    assert pe.interpolated_share([[]], [[]]) == 0.0

    with pytest.raises(ValueError, match="shorter than its unbridged sequence"):
        pe.interpolated_share([[0, 1]], [[0, 1, 2]])
    with pytest.raises(ValueError, match="1 chains but 2 sequences"):
        pe.interpolated_share([[0]], [[0], [1]])


# --- leaf sampling -------------------------------------------------------------------------


def _leaf_grid() -> AdaptiveGrid:
    """A 2x2 level-1 grid over 0..6 x 0..6 whose first cell is split 3x3 (12 leaf states)."""
    grid = AdaptiveGrid.build((0.0, 0.0, 6.0, 6.0), 2, np.array([1000.0, 0.0, 0.0, 0.0]), 5)
    assert grid.kappa == (3, 1, 1, 1) and grid.n_states == 12
    return grid


def test_sample_leaf_points_stays_inside_the_leaves() -> None:
    grid = _leaf_grid()
    payloads = [[0, 5, 11], [4]]
    points = pe.sample_leaf_points(grid, payloads, np.random.default_rng(0))
    assert [len(p) for p in points] == [3, 2]  # the 1-state walk is padded to two points
    for payload, xy in zip([payloads[0], [4, 4]], points, strict=True):
        for state, (x, y) in zip(payload, xy, strict=True):
            x0, y0, x1, y1 = grid.state_bounds(state)
            assert x0 <= x <= x1 and y0 <= y <= y1
    # The padded pair is drawn twice, not copied.
    assert points[1][0].tolist() != points[1][1].tolist()

    again = pe.sample_leaf_points(grid, payloads, np.random.default_rng(0))
    assert [p.tolist() for p in again] == [p.tolist() for p in points]
    other = pe.sample_leaf_points(grid, payloads, np.random.default_rng(1))
    assert [p.tolist() for p in other] != [p.tolist() for p in points]

    with pytest.raises(ValueError, match="no states"):
        pe.sample_leaf_points(grid, [[]], np.random.default_rng(0))


# --- the port side -------------------------------------------------------------------------


def test_run_synthesis_records_and_determinism() -> None:
    points = _tiny()
    grid = _eval_grid(points)
    runs = pe.run_synthesis(points, grid, FIRST_LEVEL_K, [HUGE_EPS], [1, 2])
    assert set(runs) == {EPS_KEY} and set(runs[EPS_KEY]) == {"1", "2"}
    for record in runs[EPS_KEY].values():
        assert set(METRIC_NAMES) <= set(record)
        assert record["n_states"] >= FIRST_LEVEL_K**2
        assert 0 <= record["n_second_order"] <= record["n_states"]
        assert 0 <= record["n_split_cells"] <= FIRST_LEVEL_K**2 and record["max_kappa"] >= 1
        assert sum(record["stage_epsilons"]) == pytest.approx(HUGE_EPS)
        assert record["n_synthetic"] == len(points) and record["synthetic_mean_length"] >= 1
        assert record["synthetic_mean_points"] >= 2  # every walk yields at least two points
        # the D-4.3 walk-length cap: recorded per run, not tabulated
        assert {"max_redraws", "n_capped_walks", "n_redrawn_walks"} <= set(record)
        assert record["max_redraws"] == 20  # the generator's default
        for name in ("n_capped_walks", "n_redrawn_walks"):
            assert isinstance(record[name], int) and record[name] >= 0, name
        assert record["n_capped_walks"] <= record["n_synthetic"]
        assert all(record[k] >= 0 for k in ("fit_s", "generate_s", "metrics_s"))
        # cell metrics are always finite; the length/diameter bins can be empty at n = 5
        for name in ("density_error", "trip_error", "coverage_kendall_tau", "pattern_f1"):
            assert math.isfinite(record[name])
        # the second, unbridged scoring pass stores all nine metrics plus the share
        assert {f"nobridge_{name}" for name in METRIC_NAMES} <= set(record)
        assert 0.0 <= record["interpolated_share"] <= 1.0
        # length and diameter read the raw real points and the synthetic points, never a
        # chain, so the two passes must agree on them by construction
        for name in ("length_error", "diameter_error"):
            unbridged = record[f"nobridge_{name}"]
            if math.isnan(record[name]):
                assert math.isnan(unbridged), name
            else:
                assert unbridged == record[name], name
        assert record["mask_non_adjacent"] is False

    masked = pe.run_synthesis(points, grid, FIRST_LEVEL_K, [HUGE_EPS], [1], mask_non_adjacent=True)
    assert masked[EPS_KEY]["1"]["mask_non_adjacent"] is True

    again = pe.run_synthesis(points, grid, FIRST_LEVEL_K, [HUGE_EPS], [1, 2])
    strip = lambda r: {k: v for k, v in r.items() if not k.endswith("_s")}  # noqa: E731
    for seed in ("1", "2"):
        assert json.dumps(strip(runs[EPS_KEY][seed]), sort_keys=True) == json.dumps(
            strip(again[EPS_KEY][seed]), sort_keys=True
        )


def test_scoring_own_saved_synthesis_reproduces_the_run(tmp_path: Path) -> None:
    """The reference-side path (file → points → chains → metrics) equals the port's own run."""
    points = _tiny()
    grid = _eval_grid(points)
    runs = pe.run_synthesis(points, grid, FIRST_LEVEL_K, [HUGE_EPS], [1, 2], save_dir=tmp_path)
    pattern = str(tmp_path / "syn_port_eps_{eps}_seed_{seed}.txt")
    scored = pe.score_synthesis(points, grid, pattern, [HUGE_EPS], [1, 2])
    for seed in ("1", "2"):
        ran, got = runs[EPS_KEY][seed], scored[EPS_KEY][seed]
        assert Path(ran["synthesis_path"]) == Path(got["synthesis_path"])
        assert got["n_synthetic"] == ran["n_synthetic"]
        assert got["synthetic_mean_points"] == ran["synthetic_mean_points"]
        assert got["interpolated_share"] == ran["interpolated_share"]
        for name in (*METRIC_NAMES, *(f"nobridge_{n}" for n in METRIC_NAMES)):
            if math.isnan(ran[name]):
                assert math.isnan(got[name]), name
            else:
                # The saved file keeps six decimals; everything else is bit-identical.
                assert got[name] == pytest.approx(ran[name], abs=1e-9), name


# --- summaries -----------------------------------------------------------------------------


def _fake_runs(
    density: list[float],
    n_states: list[int] | None = None,
    nobridge_density: list[float] | None = None,
) -> pe.Runs:
    runs: pe.Runs = {"1.0": {}}
    for i, seed in enumerate(("1", "2")):
        record: dict[str, Any] = dict.fromkeys(METRIC_NAMES, 0.0)
        record["density_error"] = density[i]
        if n_states is not None:
            record["n_states"] = n_states[i]
            record["n_second_order"] = 2
            record["synthetic_mean_length"] = 3.5
        if nobridge_density is not None:
            record.update({f"nobridge_{name}": 0.0 for name in METRIC_NAMES})
            record["nobridge_density_error"] = nobridge_density[i]
            record["nobridge_point_query_avre"] = 0.7
            record["interpolated_share"] = 0.5
        runs["1.0"][seed] = record
    return runs


def test_summarize_covers_metrics_port_only_and_no_bridge_rows() -> None:
    summary = pe.summarize(_fake_runs([0.1, 0.3], n_states=[4, 6], nobridge_density=[0.4, 0.6]))[
        "1.0"
    ]
    assert summary["density_error"] == {"mean": 0.2, "min": 0.1, "max": 0.3, "n": 2}
    assert summary["n_states"] == {"mean": 5.0, "min": 4.0, "max": 6.0, "n": 2}
    assert summary["synthetic_mean_length"]["mean"] == 3.5
    assert summary["nobridge_density_error"] == {"mean": 0.5, "min": 0.4, "max": 0.6, "n": 2}
    assert summary["interpolated_share"] == {"mean": 0.5, "min": 0.5, "max": 0.5, "n": 2}
    # the point query moves without bridging too (its real side follows the real chains)
    assert summary["nobridge_point_query_avre"] == {"mean": 0.7, "min": 0.7, "max": 0.7, "n": 2}
    # only the seven metrics of NOBRIDGE_METRICS are summarized, not all nine: length and
    # diameter read points only, so their unbridged values repeat the bridged ones
    assert "nobridge_length_error" not in summary
    assert "nobridge_diameter_error" not in summary

    plain = pe.summarize(_fake_runs([0.1, 0.3]))["1.0"]
    assert "n_states" not in plain
    assert "nobridge_density_error" not in plain and "interpolated_share" not in plain


def test_compare_table_layout() -> None:
    port = {
        "label": "port",
        "runs": _fake_runs([0.1, 0.3], n_states=[4, 6], nobridge_density=[0.4, 0.6]),
    }
    ref = {"label": "reference", "runs": _fake_runs([0.2, 0.2])}
    table = pe.compare_table([port, ref])
    lines = table.splitlines()
    assert lines[0] == "| ε | metric | port | reference |"
    # header, rule, nine metrics, three port-only rows, seven no-bridge rows + the share
    assert len(lines) == 2 + len(METRIC_NAMES) + 3 + 8
    density = next(line for line in lines if "| density_error |" in line)
    assert density == "| 1.0 | density_error | 0.2000 [0.1000; 0.3000] | 0.2000 |"
    assert lines[-11] == "| 1.0 | n_states | 5.0 [4.0; 6.0] | — |"
    assert lines[-9] == "| 1.0 | synthetic_mean_length | 3.5 | — |"
    # the no-bridge block comes last, in NOBRIDGE_METRICS order, share included
    block = [line.split(" | ")[1] for line in lines[-8:]]
    assert block == [
        *(f"nobridge_{name}" for name in pe.NOBRIDGE_METRICS),
        "interpolated_share",
    ]
    assert block[2] == "nobridge_point_query_avre"  # in METRIC_NAMES order, after the hotspots
    assert lines[-8] == "| 1.0 | nobridge_density_error | 0.5000 [0.4000; 0.6000] | — |"
    assert lines[-1] == "| 1.0 | interpolated_share | 0.5000 | — |"
    # length and diameter cannot move without bridging, so they are not repeated
    assert "nobridge_length_error" not in table and "nobridge_diameter_error" not in table
    with pytest.raises(ValueError, match="at least one"):
        pe.compare_table([])


# --- CLI -----------------------------------------------------------------------------------


def test_cli_write_subset_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dst = tmp_path / "subset.dat"
    pe.main(["--dat", str(TINY_DAT), "--max-trajectories", "3", "--write-subset", str(dst)])
    assert "written 3 trajectories" in capsys.readouterr().out
    assert len(list(read_dat(dst))) == 3
    with pytest.raises(SystemExit, match="needs --max-trajectories"):
        pe.main(["--dat", str(TINY_DAT), "--write-subset", str(dst)])


def test_cli_run_score_and_compare(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    common = [
        "--dat",
        str(TINY_DAT),
        "--first-level-k",
        str(FIRST_LEVEL_K),
        "--eval-grid",
        str(EVAL_N),
        "--epsilons",
        str(HUGE_EPS),
        "--seeds",
        "1",
    ]
    port_json = tmp_path / "port.json"
    pe.main([*common, "--save-synthesis", str(tmp_path / "syn"), "--out", str(port_json)])
    out = capsys.readouterr().out
    assert "eval grid 3x3" in out and "real interpolated share 0.0000" in out
    port = json.loads(port_json.read_text())
    assert port["label"] == "port" and port["source"]["n_trajectories"] == 5
    assert port["source"]["first_level_k"] == FIRST_LEVEL_K
    assert port["source"]["eval_grid"]["n_rows"] == EVAL_N
    assert port["source"]["bbox"] == port["source"]["eval_grid"]["bbox"]
    assert port["source"]["real_interpolated_share"] == 0.0  # nothing bridged on the 3x3 grid
    assert port["source"]["mask_non_adjacent"] is False
    record = port["runs"][EPS_KEY]["1"]
    assert set(METRIC_NAMES) <= set(record) and record["synthesis_path"].endswith("seed_1.txt")

    ref_json = tmp_path / "ref.json"
    pattern = str(tmp_path / "syn" / "syn_port_eps_{eps}_seed_{seed}.txt")
    pe.main([*common, "--score-synthesis", pattern, "--label", "scored", "--out", str(ref_json)])
    scored = json.loads(ref_json.read_text())
    assert scored["source"]["synthesis"] == pattern
    for name in METRIC_NAMES:
        got = scored["runs"][EPS_KEY]["1"][name]
        if math.isnan(record[name]):
            assert math.isnan(got), name
        else:
            assert got == pytest.approx(record[name], abs=1e-9), name

    capsys.readouterr()
    pe.main(["--compare", str(port_json), str(ref_json)])
    out = capsys.readouterr().out
    assert out.startswith("real interpolated share (port): 0.0000\n")
    assert "real interpolated share (scored): 0.0000\n" in out
    assert "| ε | metric | port | scored |" in out
    assert f"| {EPS_KEY} | density_error |" in out
    assert f"| {EPS_KEY} | n_states |" in out and " | — |" in out  # port-only row
    assert f"| {EPS_KEY} | nobridge_density_error |" in out
    assert f"| {EPS_KEY} | nobridge_point_query_avre |" in out
    assert f"| {EPS_KEY} | interpolated_share |" in out


def test_cli_mask_non_adjacent_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The flag reaches the generator and is recorded on both the source and every run."""
    out_json = tmp_path / "masked.json"
    pe.main(
        [
            "--dat",
            str(TINY_DAT),
            "--first-level-k",
            str(FIRST_LEVEL_K),
            "--eval-grid",
            str(EVAL_N),
            "--epsilons",
            str(HUGE_EPS),
            "--seeds",
            "1",
            "--mask-non-adjacent",
            "--label",
            "port_masked",
            "--out",
            str(out_json),
        ]
    )
    capsys.readouterr()
    masked = json.loads(out_json.read_text())
    assert masked["label"] == "port_masked"
    assert masked["source"]["mask_non_adjacent"] is True
    assert masked["runs"][EPS_KEY]["1"]["mask_non_adjacent"] is True


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--epsilons", "1"], "--dat is required"),
        (["--compare", "a.json", "--dat", str(TINY_DAT)], "drop --dat"),
        (["--compare", "a.json", "--score-synthesis", "x"], "mutually exclusive"),
        (["--dat", str(TINY_DAT), "--eval-grid", "1"], "--eval-grid must be"),
        (["--dat", str(TINY_DAT), "--first-level-k", "1"], "--first-level-k must be"),
        (
            ["--dat", str(TINY_DAT), "--score-synthesis", "x", "--mask-non-adjacent"],
            "means nothing when",
        ),
    ],
)
def test_cli_argument_errors(argv: list[str], match: str) -> None:
    with pytest.raises(SystemExit, match=match):
        pe.main(argv)
