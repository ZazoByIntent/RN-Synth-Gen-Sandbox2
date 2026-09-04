"""Tests for the cells representation of the orchestrator (PR B2 of the LDPTrace validation).

Fixture-only, no network and no map: ``geolife_onroad`` end to end under
``dataset.representation: cells`` (membership inference against ``markov`` and
``ldptrace`` on a 6x6 grid), ``tiny.dat`` for the pool unit test, and the pre-pipeline
rejections that keep the vertical slice honest.
"""

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from test_orchestrator import FIXTURES, base_config, write_config
from trajguard.experiments.orchestrator import (
    ConsistencyError,
    _cell_pool,
    _version_hash,
    load_config,
    run,
)

TINY_DAT = FIXTURES / "ldptrace_dat" / "tiny.dat"
# Chains of tiny.dat on the 6x6 grid over 0..6 x 0..6 (fixtures/ldptrace_dat/README.md).
TINY_CHAINS = {
    "ldptrace_dat/0": (0, 1, 8),
    "ldptrace_dat/1": (0, 7, 8, 9),
    "ldptrace_dat/2": (14,),
    "ldptrace_dat/3": (28, 35),
    "ldptrace_dat/4": (5, 10, 15, 20),
}
NO_CLEANING = {"max_speed_kmh": 1.0e9, "min_points": 1, "min_length_m": 0, "resample_s": 0}
FIXTURE_GRID = {"n_rows": 6, "n_cols": 6, "bbox": [116.30, 39.98, 116.32, 39.995]}


def cells_config(tmp_path: Path) -> dict[str, Any]:
    """base_config's population in the cells representation: no map, no matching, MIA only."""
    cfg = base_config(tmp_path, tmp_path / "maps")
    del cfg["map"]
    del cfg["map_matching"]
    cfg["dataset"]["representation"] = "cells"
    cfg["dataset"]["grid"] = dict(FIXTURE_GRID)
    cfg["privacy_mechanisms"] = []
    cfg["synthetic_generators"] = [
        {"id": "markov", "params": {"order": 1}},
        {"id": "ldptrace", "params": {"epsilon": 600.0}},  # OUE noise vanishes at this budget
    ]
    cfg["attacks"] = [
        {
            "type": "membership_inference",
            "target_scope": ["synthetic"],
            "attacker": {"n_shadow": 8, "subsample": 0.5},
            "fprs": [0.25],  # 4 non-members at fixture scale
        }
    ]
    return cfg


def tiny_config(tmp_path: Path) -> dict[str, Any]:
    """tiny.dat through the ldptrace_dat loader on its 6x6 unit grid, cleaning switched off."""
    cfg = cells_config(tmp_path)
    cfg["dataset"] = {
        "id": "ldptrace_dat",
        "path": str(TINY_DAT),
        "representation": "cells",
        "grid": {"n_rows": 6, "n_cols": 6, "bbox": [0.0, 0.0, 6.0, 6.0]},
    }
    cfg["cleaning"] = dict(NO_CLEANING)
    return cfg


def _unreachable(cfg: dict[str, Any]) -> dict[str, Any]:
    """Point the dataset at a missing path: a rejection that came late would crash instead."""
    cfg["dataset"]["path"] = str(Path(cfg["dataset"]["path"]) / "does_not_exist")
    return cfg


# --- end to end ---------------------------------------------------------------------


def test_cells_mode_runs_membership_inference_end_to_end(tmp_path: Path) -> None:
    cfg = cells_config(tmp_path)
    values = run(write_config(tmp_path, cfg))

    auc = {v.result_id: v.value for v in values if v.name == "auc"}
    assert set(auc) == {
        "membership_inference:synthetic:markov:order=1",
        "membership_inference:synthetic:ldptrace:epsilon=600.0",
    }
    assert all(0.0 <= a <= 1.0 for a in auc.values())
    # markov memorizes the train chains: the non-private ceiling beats chance
    assert auc["membership_inference:synthetic:markov:order=1"] > 0.5
    assert {v.name for v in values} == {"auc", "tpr@fpr=0.25"}

    entries = list((tmp_path / "cache").iterdir())
    assert len(entries) == 1
    cached = {p.name for p in entries[0].iterdir()}
    assert cached == {"clean.parquet", "chains.parquet", "meta.json"}
    record = json.loads((tmp_path / "out" / "run.json").read_text())
    assert record["representation"] == "cells"
    assert record["n_matched"] == 8 and record["n_dropped"] == 0
    assert sum(record["split_counts"].values()) == 8
    assert record["warnings"] == []
    # the fitted ldptrace target's public facts are recorded per arm (PR C); markov has none
    ldptrace_arm = record["arms"]["synthetic:ldptrace:epsilon=600.0"]
    assert 1 <= ldptrace_arm["l_k"] <= 36 and ldptrace_arm["report_epsilon"] > 0
    assert "synthetic:markov:order=1" not in record["arms"]

    rows = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    assert rows and all(r["family"] == "membership_inference" for r in rows)
    for r in rows:
        assert r["n_rematch_dropped"] == ""  # nothing is re-matched in the cells representation
        assert r["epsilon"] == ("600.0" if r["arm_id"] == "ldptrace" else "")
        assert int(r["n_members"]) + int(r["n_nonmembers"]) == int(r["n_pool"])

    # the second run reads the cached chains and reproduces the values
    assert [v.value for v in run(write_config(tmp_path, cfg))] == [v.value for v in values]
    assert len(list((tmp_path / "cache").iterdir())) == 1


def test_cells_mode_with_a_map_block_never_loads_the_map(tmp_path: Path) -> None:
    """A map block is allowed (and T1-checked) in the cells representation but never built."""
    cfg = cells_config(tmp_path)
    cfg["map"] = {
        "source": "osm",
        "region": "beijing",
        "bbox": [116.30, 39.98, 116.32, 39.995],
        "crs": "EPSG:32650",
        "dir": str(tmp_path / "no_such_maps"),
    }
    values = run(write_config(tmp_path, cfg))
    assert {v.result_id for v in values} == {
        "membership_inference:synthetic:markov:order=1",
        "membership_inference:synthetic:ldptrace:epsilon=600.0",
    }


# --- the pool ---------------------------------------------------------------------------


def test_cell_pool_on_tiny_dat_matches_fixture_readme(tmp_path: Path) -> None:
    cfg = load_config(write_config(tmp_path, tiny_config(tmp_path)))
    chains, clean_by_id, split_counts = _cell_pool(cfg)

    assert {c.traj_id: c.chain for c in chains} == TINY_CHAINS
    assert sorted(c.user_id for c in chains) == ["0", "1", "2", "3", "4"]
    assert set(clean_by_id) == set(TINY_CHAINS)
    assert sum(split_counts.values()) == 5
    assert all(clean_by_id[c.traj_id].split in split_counts for c in chains)

    # the second call rehydrates the Parquet cache
    cache = cfg.cache_dir / _version_hash(cfg)
    assert {p.name for p in cache.iterdir()} == {"clean.parquet", "chains.parquet", "meta.json"}
    again, again_clean, again_counts = _cell_pool(cfg)
    assert again == chains and again_counts == split_counts
    assert again_clean == clean_by_id
    meta = json.loads((cache / "meta.json").read_text())
    assert meta["representation"] == "cells" and meta["dropped"] == 0
    assert meta["grid"] == {"n_rows": 6, "n_cols": 6, "bbox": [0.0, 0.0, 6.0, 6.0]}


# --- rejections before the pipeline -----------------------------------------------------


def test_cells_mode_rejects_attacks_other_than_membership(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["attacks"] = [
        {
            "type": "reidentification",
            "attacker": {"known_points": [3], "distance": "dtw"},
            "target_scope": ["raw"],
        }
    ]
    with pytest.raises(ValueError, match="segments representation"):
        run(write_config(tmp_path, cfg))


def test_cells_mode_rejects_network_generators(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["synthetic_generators"].append({"id": "rn_ldp_synth", "params": {"epsilon": 2.0}})
    with pytest.raises(ValueError, match="rn_ldp_synth.*requires a road network"):
        run(write_config(tmp_path, cfg))


def test_cells_mode_rejects_privacy_mechanisms(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["privacy_mechanisms"] = [{"id": "none"}]
    with pytest.raises(ValueError, match="privacy_mechanisms"):
        run(write_config(tmp_path, cfg))


def test_cells_mode_requires_a_grid(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    del cfg["dataset"]["grid"]
    with pytest.raises(ValueError, match="grid"):
        run(write_config(tmp_path, cfg))


@pytest.mark.parametrize(
    ("grid", "match"),
    [
        ({"n_rows": 1, "n_cols": 6, "bbox": [0.0, 0.0, 6.0, 6.0]}, "at least 2x2"),
        ({"n_rows": 6, "n_cols": 6, "bbox": [0.0, 0.0, 6.0]}, "dataset.grid.bbox"),
        ({"n_rows": 6, "n_cols": 6, "bbox": [6.0, 0.0, 0.0, 6.0]}, "min < max"),
    ],
)
def test_cells_mode_rejects_a_bad_grid(tmp_path: Path, grid: dict[str, Any], match: str) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["dataset"]["grid"] = grid
    with pytest.raises(ValueError, match=match):
        run(write_config(tmp_path, cfg))


def test_unknown_representation_rejected(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["dataset"]["representation"] = "graph"
    with pytest.raises(ValueError, match="representation"):
        run(write_config(tmp_path, cfg))


def test_segments_mode_still_requires_map_and_matching(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    del cfg["map"]
    with pytest.raises(ValueError, match="missing required key .*map"):
        run(write_config(tmp_path, cfg))
    cfg = base_config(tmp_path, tmp_path / "maps")
    del cfg["map_matching"]
    with pytest.raises(ValueError, match="missing required key .*map_matching"):
        run(write_config(tmp_path, cfg))


def test_segments_mode_rejects_a_grid(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["dataset"]["grid"] = dict(FIXTURE_GRID)
    with pytest.raises(ValueError, match="only used by dataset.representation: cells"):
        run(write_config(tmp_path, cfg))


def test_cells_mode_keeps_the_consistency_check_when_a_map_is_given(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["map"] = {
        "source": "osm",
        "region": "ljubljana",
        "bbox": [116.30, 39.98, 116.32, 39.995],
        "crs": "EPSG:32650",
        "dir": str(tmp_path / "maps"),
    }
    with pytest.raises(ConsistencyError, match="ljubljana"):
        run(write_config(tmp_path, cfg))


def test_ldptrace_dat_rejects_any_map(tmp_path: Path) -> None:
    cfg = tiny_config(tmp_path)
    cfg["map"] = {
        "source": "osm",
        "region": "beijing",
        "bbox": [0.0, 0.0, 6.0, 6.0],
        "crs": "EPSG:32650",
        "dir": str(tmp_path / "maps"),
    }
    with pytest.raises(ConsistencyError, match="'none'"):
        run(write_config(tmp_path, cfg))


def test_generator_grid_params_must_agree_with_the_grid(tmp_path: Path) -> None:
    cfg = _unreachable(cells_config(tmp_path))
    cfg["synthetic_generators"] = [{"id": "ldptrace", "params": {"epsilon": 600.0, "n_rows": 5}}]
    with pytest.raises(ValueError, match="n_rows=5.*contradicts dataset.grid"):
        run(write_config(tmp_path, cfg))
    # the same value as the grid is redundant, not contradictory: the arm runs
    cfg = cells_config(tmp_path)
    cfg["synthetic_generators"] = [{"id": "ldptrace", "params": {"epsilon": 600.0, "n_rows": 6}}]
    values = run(write_config(tmp_path, cfg))
    assert {v.result_id for v in values} == {
        "membership_inference:synthetic:ldptrace:epsilon=600.0,n_rows=6"
    }


# --- the version hash -------------------------------------------------------------------


def test_version_hash_separates_the_representations(tmp_path: Path) -> None:
    """The segments key is untouched; cells adds representation + grid to the key."""
    cfg = base_config(tmp_path, tmp_path / "maps")  # map + matching stay in both variants
    segments = _version_hash(load_config(write_config(tmp_path, cfg)))
    cfg["dataset"]["representation"] = "cells"
    cfg["dataset"]["grid"] = dict(FIXTURE_GRID)
    cells = _version_hash(load_config(write_config(tmp_path, cfg)))
    assert segments != cells
    cfg["dataset"]["grid"]["n_rows"] = 8
    finer = _version_hash(load_config(write_config(tmp_path, cfg)))
    assert finer != cells
    cfg["dataset"]["grid"]["n_rows"] = 6
    cfg["dataset"]["grid"]["bbox"] = [116.30, 39.98, 116.33, 39.995]
    assert _version_hash(load_config(write_config(tmp_path, cfg))) not in {segments, cells, finer}
