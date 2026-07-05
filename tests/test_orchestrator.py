"""Tests for the experiment orchestrator on the committed fixtures (no network)."""

import csv
import shutil
from pathlib import Path

import pytest
import yaml

from trajguard.experiments.orchestrator import ConsistencyError, run

FIXTURES = Path(__file__).parent / "fixtures"


def base_config(tmp_path: Path, maps_dir: Path, region: str = "beijing") -> dict:
    """A fixture-scale config: on-road Geolife fixtures + a small committed network."""
    return {
        "experiment": {
            "id": "test_reid",
            "seed": 42,
            "output_dir": str(tmp_path / "out"),
            "cache_dir": str(tmp_path / "cache"),
        },
        "map": {
            "source": "osm",
            "region": region,
            "bbox": [116.30, 39.98, 116.32, 39.995],
            "crs": "EPSG:32650",
            "dir": str(maps_dir),
        },
        "dataset": {
            "id": "geolife",
            "path": str(FIXTURES / "geolife_onroad"),
            "native_region": "beijing",
        },
        "cleaning": {"max_speed_kmh": 200, "min_points": 20, "min_length_m": 500, "resample_s": 5},
        "map_matching": {
            "matcher": "leuven",
            "k_candidates": 8,
            "radius_m": 50,
            "gps_error_m": 20,
            "min_match_score": 0.6,
        },
        "split": {
            "scheme": "by_user",
            "fractions": {"train": 0.5, "test": 0.2, "shadow": 0.2, "attack": 0.1},
        },
        "privacy_mechanisms": [{"id": "none"}],
        "attacks": [
            {
                "type": "reidentification",
                "attacker": {"known_points": [3, 5], "distance": "dtw"},
                "target_scope": ["raw", "protected"],
            }
        ],
        "metrics": {
            "privacy": ["top1_acc", "topk_acc", "linkage_rate"],
            "top_k": 5,
            "bootstrap": {"n": 200, "ci": 0.95},
        },
    }


@pytest.fixture()
def beijing_maps_dir(tmp_path: Path) -> Path:
    """Copy the committed beijing_fixture network into a 'beijing' dir (matches native_region)."""
    src = FIXTURES / "maps" / "beijing_fixture"
    dst = tmp_path / "maps" / "beijing"
    shutil.copytree(src, dst)
    return tmp_path / "maps"


def write_config(tmp_path: Path, cfg: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_run_end_to_end_writes_metrics(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    values = run(write_config(tmp_path, cfg))

    metrics_csv = tmp_path / "out" / "metrics.csv"
    assert metrics_csv.exists()
    rows = list(csv.DictReader(metrics_csv.open()))
    names = {r["metric"] for r in rows}
    assert {"top1_acc", "top5_acc", "linkage_rate"} <= names
    # raw and protected:none arms both present
    refs = {r["result_id"].split(":")[1] for r in rows}
    assert "raw" in refs and "protected" in refs
    for v in values:
        assert 0.0 <= v.value <= 1.0
        assert v.ci_low is not None and v.ci_high is not None
        assert v.ci_low <= v.value <= v.ci_high
    # only 2 users in the fixture -> everyone is within top-5
    for v in values:
        if v.name == "top5_acc":
            assert v.value == 1.0
    assert (tmp_path / "out" / "run.json").exists()


def test_identity_protection_matches_raw(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """NoProtection is identity, so protected:none metrics equal the raw metrics."""
    values = run(write_config(tmp_path, base_config(tmp_path, beijing_maps_dir)))
    raw = {
        (v.name, v.result_id.rsplit(":", 1)[-1]): v.value for v in values if "raw" in v.result_id
    }
    prot = {
        (v.name, v.result_id.rsplit(":", 1)[-1]): v.value
        for v in values
        if "protected" in v.result_id
    }
    assert raw == prot


def test_consistency_check_rejects_ljubljana_geolife(
    tmp_path: Path, beijing_maps_dir: Path
) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir, region="ljubljana")
    with pytest.raises(ConsistencyError, match="ljubljana"):
        run(write_config(tmp_path, cfg))


def test_run_is_deterministic(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    first = run(write_config(tmp_path, cfg))
    second = run(write_config(tmp_path, cfg))
    assert [v.value for v in first] == [v.value for v in second]


def test_matched_pool_is_cached(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    config_path = write_config(tmp_path, cfg)
    run(config_path)
    cache_files = list((tmp_path / "cache").glob("*.pkl"))
    assert len(cache_files) == 1  # matched pool cached by version hash
    assert cache_files[0].stem  # non-empty version hash filename
    run(config_path)  # second run reuses the cache without error
    assert len(list((tmp_path / "cache").glob("*.pkl"))) == 1
