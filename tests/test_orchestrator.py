"""Tests for the experiment orchestrator on the committed fixtures (no network)."""

import csv
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory, ProtectedTrajectory
from trajguard.experiments.orchestrator import ConsistencyError, _protected_pool, run
from trajguard.privacy.base import PrivacyMechanism
from trajguard.representation import TrajectoryView

FIXTURES = Path(__file__).parent / "fixtures"


def base_config(tmp_path: Path, maps_dir: Path, region: str = "beijing") -> dict[str, Any]:
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


def write_config(tmp_path: Path, cfg: dict[str, Any]) -> Path:
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


def test_matched_pool_is_cached_as_parquet(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    config_path = write_config(tmp_path, cfg)
    run(config_path)
    entries = list((tmp_path / "cache").iterdir())
    assert len(entries) == 1  # matched pool cached under one version-hash directory
    files = {p.name for p in entries[0].iterdir()}
    assert files == {"matched.parquet", "clean.parquet", "meta.json"}
    run(config_path)  # second run reuses the cache without error
    assert len(list((tmp_path / "cache").iterdir())) == 1


# --- loud failures for config knobs the orchestrator does not (yet) support ------


def test_unknown_attack_type_fails_loudly(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["type"] = "membership_inference"
    with pytest.raises(KeyError, match="membership_inference"):
        run(write_config(tmp_path, cfg))


def test_unknown_map_source_fails_loudly(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["map"]["source"] = "postgis"
    with pytest.raises(KeyError, match="postgis"):
        run(write_config(tmp_path, cfg))


def test_unsupported_split_scheme_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["split"]["scheme"] = "random"
    with pytest.raises(ValueError, match="by_user"):
        run(write_config(tmp_path, cfg))


def test_unknown_export_format_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["reporting"] = {"export": ["xlsx"]}
    with pytest.raises(ValueError, match="xlsx"):
        run(write_config(tmp_path, cfg))


def test_synthetic_target_scope_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["target_scope"] = ["raw", "synthetic"]
    with pytest.raises(ValueError, match="synthetic"):
        run(write_config(tmp_path, cfg))


def test_cache_dir_under_data_raw_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["experiment"]["cache_dir"] = "data/raw/cache"
    with pytest.raises(ValueError, match="immutable"):
        run(write_config(tmp_path, cfg))


# --- the protected arm goes through PrivacyMechanism.apply -----------------------


class _ShiftMechanism(PrivacyMechanism):
    """Test double: a mechanism that visibly perturbs its input."""

    guarantee = "geo-ind"

    def apply(self, traj: TrajectoryView, **params: Any) -> ProtectedTrajectory:
        shifted = tuple((lat + 0.001, lon, t) for lat, lon, t in traj.as_gps())
        return ProtectedTrajectory(
            traj_id=f"shift/{traj.traj_id}",
            source_traj_id=traj.traj_id,
            mechanism_id="shift",
            params_hash="test",
            guarantee=self.guarantee,
            epsilon=1.0,
            payload=shifted,
            map_id=traj.map_id,
        )

    def spent_budget(self) -> float | None:
        return 1.0


def test_perturbing_mechanism_is_rejected_until_p5() -> None:
    clean = CleanTrajectory(
        traj_id="t1",
        user_id="u",
        points=((39.98, 116.31, 0.0), (39.99, 116.31, 5.0)),
        bbox=(116.31, 39.98, 116.31, 39.99),
        duration_s=5.0,
        length_m=1100.0,
        mean_speed=10.0,
        cleaning_flags=(),
    )
    matched = MatchedTrajectory(
        traj_id="t1",
        user_id="u",
        map_id="m",
        edge_seq=(1,),
        matched_points=((0.0, 0.0, 0.0, 0.0),),
        match_score=1.0,
        frac_matched=1.0,
    )
    with pytest.raises(NotImplementedError, match="P5"):
        _protected_pool(_ShiftMechanism(), "shift", [matched], {"t1": clean})
