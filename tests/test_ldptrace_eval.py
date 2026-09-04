"""The LDPTrace validation harness (``experiments/ldptrace_eval.py``) on ``tiny.dat``."""

import json
import math
import pickle
from pathlib import Path

import numpy as np
import pytest

from trajguard.evaluation.ldptrace_metrics import METRIC_NAMES
from trajguard.experiments import ldptrace_eval as le
from trajguard.representation import Grid

FIXTURES = Path(__file__).parent / "fixtures"
TINY_DAT = FIXTURES / "ldptrace_dat" / "tiny.dat"
TINY_GRID = Grid(bbox=(0.0, 0.0, 6.0, 6.0), n_rows=6, n_cols=6)
# Chains of tiny.dat on that grid (fixtures/ldptrace_dat/README.md).
TINY_CHAINS = [[0, 1, 8], [0, 7, 8, 9], [14], [28, 35], [5, 10, 15, 20]]
HUGE_EPS = 600.0  # OUE noise negligible, as in test_ldptrace.py

REFERENCE_LOG = """\
2026-09-04 10:00:00,001 Reading porto dataset...
2026-09-04 10:00:20,002 Quantile: 7
2026-09-04 10:05:00,003 Experiment: Density Error...
2026-09-04 10:05:01,004 Density Error: 0.0123
2026-09-04 10:05:01,005 Experiment: Hotspot Query Error...
2026-09-04 10:05:01,006 Hotspot Query Error: 0.25
2026-09-04 10:05:01,007 Experiment: Query AvRE...
2026-09-04 10:05:09,008 Point Query AvRE: 0.4
2026-09-04 10:05:09,009 Experiment: Kendall-tau...
2026-09-04 10:05:09,010 Kendall_tau:0.61
2026-09-04 10:05:09,011 Experiment: Trip error...
2026-09-04 10:05:10,012 Trip error: 0.3
2026-09-04 10:05:10,013 Experiment: Diameter error...
2026-09-04 10:06:10,014 Diameter error: 0.05
2026-09-04 10:06:10,015 Experiment: Length error...
2026-09-04 10:06:20,016 Length error: 0.07
2026-09-04 10:06:20,017 Experiment: Pattern mining errors...
2026-09-04 10:07:00,018 Pattern F1 error: 0.55
2026-09-04 10:07:00,019 Pattern support error: 0.8
"""


def _tiny() -> tuple[le.Chains, le.Points]:
    return le.load_dat(TINY_DAT, TINY_GRID)


# --- inputs --------------------------------------------------------------------------------


def test_load_dat_matches_fixture_readme() -> None:
    chains, points = _tiny()
    assert chains == TINY_CHAINS
    assert [len(p) for p in points] == [3, 2, 1, 3, 4]
    assert all(p.shape[1] == 2 and p.dtype == float for p in points)
    assert points[1].tolist() == [[0.5, 0.5], [3.5, 1.5]]  # (x, y) = (lon, lat) as in the file

    first_two, _ = le.load_dat(TINY_DAT, TINY_GRID, max_trajectories=2)
    assert first_two == TINY_CHAINS[:2]
    with pytest.raises(ValueError, match="max_trajectories"):
        le.load_dat(TINY_DAT, TINY_GRID, max_trajectories=0)


def test_reference_cells_follow_the_closed_interval_rule() -> None:
    """Inner edges belong to the lower cell (reference ``in_cell``), unlike ``Grid.cell_of``."""
    inside = np.array([[0.5, 0.5], [2.5, 1.5], [5.5, 5.5]])
    assert le.reference_cells(TINY_GRID, inside) == [0, 8, 35]
    assert le.reference_cells(TINY_GRID, inside) == [TINY_GRID.cell_of(y, x) for x, y in inside]
    edges = np.array([[2.0, 0.5], [0.5, 3.0], [0.0, 0.0], [6.0, 6.0]])
    # x = 2.0 -> col 1, y = 3.0 -> row 2; the outer corners stay in the corner cells
    assert le.reference_cells(TINY_GRID, edges) == [1, 12, 0, 35]
    assert [TINY_GRID.cell_of(y, x) for x, y in edges[:2]] == [2, 18]  # half-open: upper cell
    with pytest.raises(ValueError, match="outside the grid"):
        le.reference_cells(TINY_GRID, np.array([[6.5, 1.0]]))
    # The Porto column edge -8.620002 is a six-decimal coordinate real points hit (0.5 % of
    # trips); the reference arithmetic puts it in column 2, Grid.cell_of in column 3.
    porto = Grid(
        bbox=(-8.640001, 41.140007000000004, -8.600003000000001, 41.169996999999995),
        n_rows=6,
        n_cols=6,
    )
    assert le.reference_cells(porto, np.array([[-8.620002, 41.14674]])) == [1 * 6 + 2]
    assert porto.cell_of(41.14674, -8.620002) == 1 * 6 + 3


def test_points_to_chains_round_trips_sampled_points() -> None:
    chains, _ = _tiny()
    from trajguard.evaluation.ldptrace_metrics import sample_points

    points = sample_points(TINY_GRID, chains, np.random.default_rng(0))
    # A one-cell chain samples two points in the same cell; the chain collapses them again.
    assert le.points_to_chains(TINY_GRID, points) == chains


def test_grid_from_stats(tmp_path: Path) -> None:
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps({"grid_bbox": [-8.640001, 41.140007, -8.600003, 41.169997]}))
    grid = le.grid_from_stats(stats, 6)
    assert grid == Grid(bbox=(-8.640001, 41.140007, -8.600003, 41.169997), n_rows=6, n_cols=6)
    stats.write_text(json.dumps({"bbox": [0, 0, 1, 1]}))
    with pytest.raises(ValueError, match="grid_bbox"):
        le.grid_from_stats(stats, 6)


def test_eps_key_and_pattern_expansion() -> None:
    assert le.eps_key(1) == "1.0" and le.eps_key(0.5) == "0.5"  # the reference's f"{args.epsilon}"
    path = le.expand_pattern("out/syn_porto_eps_{eps}_max_0.9_grid_6_seed_{seed}.pkl", 1.0, 3)
    assert path == Path("out/syn_porto_eps_1.0_max_0.9_grid_6_seed_3.pkl")
    with pytest.raises(ValueError, match="no {eps}/{seed} placeholder"):
        le._check_pattern("fixed.pkl", [0.5, 1.0], [1])
    with pytest.raises(ValueError, match="{seed}"):
        le._check_pattern("syn_{eps}.pkl", [0.5], [1, 2])
    with pytest.raises(ValueError, match="{eps}"):
        le._check_pattern("syn_{seed}.pkl", [0.5, 1.0], [1])
    le._check_pattern("fixed.pkl", [0.5], [1])  # one run: a literal path is fine


# --- the port side -------------------------------------------------------------------------


def test_run_synthesis_records_and_determinism() -> None:
    chains, points = _tiny()
    runs = le.run_synthesis(chains, points, TINY_GRID, [HUGE_EPS], [1, 2])
    assert set(runs) == {"600.0"} and set(runs["600.0"]) == {"1", "2"}
    for record in runs["600.0"].values():
        assert set(METRIC_NAMES) <= set(record)
        assert 1 <= record["l_k"] <= 36 and record["report_epsilon"] > 0
        assert record["n_synthetic"] == len(chains) and record["synthetic_mean_length"] >= 1
        assert all(record[k] >= 0 for k in ("fit_s", "generate_s", "metrics_s"))
        # cell metrics are always finite; the length/diameter bins can be empty at n = 5
        for name in ("density_error", "trip_error", "coverage_kendall_tau", "pattern_f1"):
            assert math.isfinite(record[name])
    again = le.run_synthesis(chains, points, TINY_GRID, [HUGE_EPS], [1, 2])
    strip = lambda r: {k: v for k, v in r.items() if not k.endswith("_s")}  # noqa: E731
    for seed in ("1", "2"):
        assert json.dumps(strip(runs["600.0"][seed]), sort_keys=True) == json.dumps(
            strip(again["600.0"][seed]), sort_keys=True
        )


def test_scoring_own_saved_synthesis_reproduces_the_run(tmp_path: Path) -> None:
    """The reference-side path (points → chains → metrics) equals the port path to the digit."""
    chains, points = _tiny()
    runs = le.run_synthesis(chains, points, TINY_GRID, [HUGE_EPS], [1, 2], save_dir=tmp_path)
    pattern = str(tmp_path / "syn_port_eps_{eps}_seed_{seed}.pkl")
    scored = le.score_synthesis(chains, points, TINY_GRID, pattern, [HUGE_EPS], [1, 2])
    for seed in ("1", "2"):
        ran, got = runs["600.0"][seed], scored["600.0"][seed]
        assert Path(ran["synthesis_path"]) == Path(got["synthesis_path"])
        assert got["n_synthetic"] == ran["n_synthetic"]
        for name in METRIC_NAMES:
            if math.isnan(ran[name]):
                assert math.isnan(got[name]), name
            else:
                assert got[name] == pytest.approx(ran[name], abs=1e-12), name


def test_reference_synthesis_file_validation(tmp_path: Path) -> None:
    good = tmp_path / "good.pkl"
    le.save_reference_synthesis(good, [np.array([[0.5, 0.5], [1.5, 0.5]]), np.array([[2.5, 2.5]])])
    loaded = le.load_reference_synthesis(good)
    assert [p.tolist() for p in loaded] == [[[0.5, 0.5], [1.5, 0.5]], [[2.5, 2.5]]]
    with good.open("rb") as fh:
        assert pickle.load(fh) == [[(0.5, 0.5), (1.5, 0.5)], [(2.5, 2.5)]]  # reference format

    empty = tmp_path / "empty.pkl"
    empty.write_bytes(pickle.dumps([]))
    with pytest.raises(ValueError, match="non-empty list"):
        le.load_reference_synthesis(empty)
    bad = tmp_path / "bad.pkl"
    bad.write_bytes(pickle.dumps([[(0.5, 0.5)], []]))
    with pytest.raises(ValueError, match="trajectory 1"):
        le.load_reference_synthesis(bad)


# --- the reference's own metrics -----------------------------------------------------------


def test_parse_reference_log() -> None:
    parsed = le.parse_reference_log(REFERENCE_LOG)
    assert parsed == {
        "l_k": 7,
        "density_error": 0.0123,
        "hotspot_query_error": 0.25,
        "point_query_avre": 0.4,
        "coverage_kendall_tau": 0.61,
        "trip_error": 0.3,
        "diameter_error": 0.05,
        "length_error": 0.07,
        "pattern_f1": 0.55,
        "pattern_support_error": 0.8,
    }
    assert isinstance(parsed["l_k"], int)
    with pytest.raises(ValueError, match="lacks: trip_error"):
        le.parse_reference_log(REFERENCE_LOG.replace("Trip error: 0.3", "Trip error:"))
    with pytest.raises(ValueError, match="lacks: l_k, density_error"):
        le.parse_reference_log("nothing here")


def test_parse_reference_logs_over_a_pattern(tmp_path: Path) -> None:
    for seed, value in ((1, "0.1"), (2, "0.3")):
        (tmp_path / f"eps0.5_seed{seed}.log").write_text(
            REFERENCE_LOG.replace("Density Error: 0.0123", f"Density Error: {value}")
        )
    runs = le.parse_reference_logs(str(tmp_path / "eps{eps}_seed{seed}.log"), [0.5], [1, 2])
    assert runs["0.5"]["1"]["density_error"] == 0.1 and runs["0.5"]["2"]["density_error"] == 0.3
    assert runs["0.5"]["2"]["log_path"].endswith("eps0.5_seed2.log")


# --- summaries -----------------------------------------------------------------------------


def _fake_runs(values: dict[str, list[float]], l_k: list[int] | None = None) -> le.Runs:
    seeds = ["1", "2"]
    runs: le.Runs = {"0.5": {}}
    for i, seed in enumerate(seeds):
        record = {name: (values[name][i] if name in values else 0.0) for name in METRIC_NAMES}
        if l_k is not None:
            record["l_k"] = l_k[i]
        runs["0.5"][seed] = record
    return runs


def test_summarize_mean_min_max() -> None:
    runs = _fake_runs({"density_error": [0.1, 0.3], "pattern_f1": [0.5, 0.5]}, l_k=[4, 6])
    summary = le.summarize(runs)["0.5"]
    assert summary["density_error"] == {"mean": 0.2, "min": 0.1, "max": 0.3, "n": 2}
    assert summary["pattern_f1"] == {"mean": 0.5, "min": 0.5, "max": 0.5, "n": 2}
    assert summary["l_k"] == {"mean": 5.0, "min": 4, "max": 6, "n": 2}
    nan_runs = _fake_runs({"length_error": [float("nan"), 0.1]})
    assert math.isnan(le.summarize(nan_runs)["0.5"]["length_error"]["mean"])
    assert "l_k" not in le.summarize(nan_runs)["0.5"]


def test_compare_table_layout() -> None:
    port = {"label": "port", "runs": _fake_runs({"density_error": [0.1, 0.3]}, l_k=[4, 6])}
    ref = {"label": "reference", "runs": _fake_runs({"density_error": [0.2, 0.2]})}
    table = le.compare_table([port, ref])
    lines = table.splitlines()
    assert lines[0] == "| ε | metric | port | reference |"
    assert len(lines) == 2 + len(METRIC_NAMES) + 1  # header, rule, nine metrics, l_k
    density = next(line for line in lines if "| density_error |" in line)
    assert density == "| 0.5 | density_error | 0.2000 [0.1000; 0.3000] | 0.2000 |"
    assert lines[-1] == "| 0.5 | l_k | 5.0 [4.0; 6.0] | — |"
    with pytest.raises(ValueError, match="at least one"):
        le.compare_table([])


# --- CLI -----------------------------------------------------------------------------------


def test_cli_run_score_and_compare(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    common = [
        "--dat",
        str(TINY_DAT),
        "--bbox",
        "0",
        "0",
        "6",
        "6",
        "--epsilons",
        "600",
        "--seeds",
        "1",
    ]
    port_json = tmp_path / "port.json"
    le.main([*common, "--save-synthesis", str(tmp_path / "syn"), "--out", str(port_json)])
    port = json.loads(port_json.read_text())
    assert port["label"] == "port" and port["source"]["n_trajectories"] == 5
    assert port["source"]["grid"] == {"bbox": [0.0, 0.0, 6.0, 6.0], "n_rows": 6, "n_cols": 6}
    record = port["runs"]["600.0"]["1"]
    assert set(METRIC_NAMES) <= set(record) and record["synthesis_path"].endswith("seed_1.pkl")

    ref_json = tmp_path / "ref.json"
    pattern = str(tmp_path / "syn" / "syn_port_eps_{eps}_seed_{seed}.pkl")
    le.main([*common, "--score-synthesis", pattern, "--label", "scored", "--out", str(ref_json)])
    scored = json.loads(ref_json.read_text())["runs"]["600.0"]["1"]
    for name in METRIC_NAMES:
        if math.isnan(record[name]):
            assert math.isnan(scored[name]), name
        else:
            assert scored[name] == pytest.approx(record[name], abs=1e-12), name

    capsys.readouterr()
    le.main(["--compare", str(port_json), str(ref_json)])
    out = capsys.readouterr().out
    assert out.startswith("| ε | metric | port | scored |") and "| 600.0 | density_error |" in out


def test_cli_reference_log_mode(tmp_path: Path) -> None:
    (tmp_path / "eps0.5_seed1.log").write_text(REFERENCE_LOG)
    out = tmp_path / "own.json"
    le.main(
        [
            "--reference-log",
            str(tmp_path / "eps{eps}_seed{seed}.log"),
            "--epsilons",
            "0.5",
            "--seeds",
            "1",
            "--out",
            str(out),
        ]
    )
    result = json.loads(out.read_text())
    assert result["label"] == "reference (own metrics)"
    assert (
        result["runs"]["0.5"]["1"]["pattern_f1"] == 0.55 and result["runs"]["0.5"]["1"]["l_k"] == 7
    )


@pytest.mark.parametrize(
    ("argv", "match"),
    [
        (["--dat", str(TINY_DAT)], "exactly one of --bbox or --stats"),
        (
            ["--dat", str(TINY_DAT), "--bbox", "0", "0", "6", "6", "--stats", "x.json"],
            "exactly one",
        ),
        (["--epsilons", "1"], "--dat is required"),
        (["--compare", "a.json", "--dat", str(TINY_DAT)], "drop --dat"),
        (["--compare", "a.json", "--reference-log", "x"], "mutually exclusive"),
        (["--dat", str(TINY_DAT), "--bbox", "0", "0", "6", "6", "--grid", "1"], "--grid must be"),
    ],
)
def test_cli_argument_errors(argv: list[str], match: str) -> None:
    with pytest.raises(SystemExit, match=match):
        le.main(argv)
