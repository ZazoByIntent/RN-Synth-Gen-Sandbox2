"""Tests for the experiment orchestrator on the committed fixtures (no network)."""

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajguard.experiments.orchestrator import ConsistencyError, load_config, run

FIXTURES = Path(__file__).parent / "fixtures"


def base_config(tmp_path: Path, maps_dir: Path, region: str = "beijing") -> dict[str, Any]:
    """A fixture-scale config: on-road Geolife fixtures + a small committed network."""
    return {
        "experiment": {
            "id": "test_reid",
            "seed": 42,
            "output_dir": str(tmp_path / "out"),
            "cache_dir": str(tmp_path / "cache"),
            "protected_dir": str(tmp_path / "protected"),
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
    cfg["attacks"][0]["type"] = "no_such_attack"
    with pytest.raises(KeyError, match="no_such_attack"):
        run(write_config(tmp_path, cfg))


def test_unconstructible_attack_fails_before_pipeline(tmp_path: Path) -> None:
    # reconstruction needs epsilon, which the orchestrator cannot supply; the config
    # points at an empty maps dir, so passing requires failing before any pipeline work.
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {
        "type": "reconstruction",
        "attacker": {"known_points": [3]},
        "target_scope": ["protected"],
    }
    with pytest.raises(ValueError, match="'reconstruction' takes constructor params"):
        run(write_config(tmp_path, cfg))


def test_poi_inference_attack_rejected_before_pipeline(tmp_path: Path) -> None:
    # poi_inference constructs with all-default args, so it clears the constructor probe;
    # it consumes clean GPS, not the matched pool, so the run loop would crash after the
    # pipeline. An empty maps dir means passing requires failing before any pipeline work.
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {
        "type": "poi_inference",
        "attacker": {"known_points": [3]},
        "target_scope": ["protected"],
    }
    with pytest.raises(ValueError, match="not wired into the orchestrator"):
        run(write_config(tmp_path, cfg))


def test_data_raw_guard_catches_absolute_path_from_any_cwd(
    tmp_path: Path, beijing_maps_dir: Path
) -> None:
    # An absolute path into a data/raw dir that is NOT under cwd: the old cwd-anchored
    # guard would have missed it; the component-based guard rejects it wherever it lives.
    cfg = base_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["cache_dir"] = str(tmp_path / "data" / "raw" / "cache")
    with pytest.raises(ValueError, match="immutable"):
        run(write_config(tmp_path, cfg))


def test_version_hash_tracks_built_map_snapshot(tmp_path: Path, beijing_maps_dir: Path) -> None:
    # Rebuilding the map in place (new OSM snapshot, same bbox) must change the pool-cache
    # key so the stale processed pool is not silently reused.
    from trajguard.experiments.orchestrator import _version_hash

    cfg = load_config(write_config(tmp_path, base_config(tmp_path, beijing_maps_dir)))
    before = _version_hash(cfg)
    meta_path = beijing_maps_dir / "beijing" / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta["osm_timestamp"] = "2099-01-01 00:00:00"
    meta_path.write_text(json.dumps(meta))
    assert _version_hash(cfg) != before


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


# --- P5: perturbing mechanisms, parameter grids, utility metrics, tradeoff -------

GEOIND_REF = "geo_indistinguishability:epsilon=10.0,unit_m=25.0"


def geoind_config(tmp_path: Path, maps_dir: Path) -> dict[str, Any]:
    """base_config plus a survivable geo-ind arm (mean noise 2*25/10 = 5 m) + utility."""
    cfg = base_config(tmp_path, maps_dir)
    cfg["privacy_mechanisms"] = [
        {"id": "none"},
        {"id": "geo_indistinguishability", "params": {"epsilon": [10.0], "unit_m": 25.0}},
    ]
    cfg["metrics"]["utility"] = ["cell_js_divergence", "length_dist_error"]
    cfg["metrics"]["utility_grid"] = {"n_rows": 10, "n_cols": 10}
    cfg["reporting"] = {"export": ["csv"], "plots": ["tradeoff"]}
    return cfg


def test_param_grid_expands_into_one_variant_per_combination(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    # YAML int 1 must mean the same arm as 1.0 (canonicalized refs and cache keys)
    cfg["privacy_mechanisms"] = [
        {"id": "none"},
        {"id": "geo_indistinguishability", "params": {"epsilon": [0.1, 1, 10.0]}},
    ]
    loaded = load_config(write_config(tmp_path, cfg))
    assert [m.ref for m in loaded.mechanisms] == [
        "none",
        "geo_indistinguishability:epsilon=0.1",
        "geo_indistinguishability:epsilon=1.0",
        "geo_indistinguishability:epsilon=10.0",
    ]


def test_perturbing_mechanism_rematches_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    values = run(write_config(tmp_path, geoind_config(tmp_path, beijing_maps_dir)))

    # the perturbed arm was attacked, and its release survived re-matching
    geoind_prefix = f"reidentification:protected:{GEOIND_REF}"
    assert [v for v in values if v.result_id.startswith(geoind_prefix)], "geo-ind arm not attacked"
    arms = json.loads((tmp_path / "out" / "run.json").read_text())["arms"]
    geo_arm = arms[f"protected:{GEOIND_REF}"]
    assert geo_arm["n_pool"] > 0, "survivable noise still emptied the re-matched pool"
    assert geo_arm["n_rematch_dropped"] == 8 - geo_arm["n_pool"]
    assert geo_arm["spent_budget"] and geo_arm["spent_budget"] > 0
    # probes stay fixed on the raw pool in every arm (comparable denominators)
    assert geo_arm["n_probes"] == arms["raw"]["n_probes"]

    # utility: identity release diverges nowhere; the noisy release diverges somewhere
    utility = {(v.result_id, v.name): v.value for v in values if v.result_id.startswith("utility")}
    assert utility[("utility:protected:none", "cell_js_divergence")] == 0.0
    assert utility[("utility:protected:none", "length_dist_error")] == 0.0
    assert utility[(f"utility:protected:{GEOIND_REF}", "cell_js_divergence")] > 0.0
    assert utility[(f"utility:protected:{GEOIND_REF}", "length_dist_error")] > 0.0

    # only the perturbing mechanism needs a protected cache entry (identity is free)
    entries = list((tmp_path / "protected").iterdir())
    assert len(entries) == 1
    expected_files = {"matched.parquet", "clean.parquet", "meta.json"}
    assert {p.name for p in entries[0].iterdir()} == expected_files
    meta = json.loads((entries[0] / "meta.json").read_text())
    assert meta["mechanism"] == GEOIND_REF and meta["spent_budget"] > 0


def test_matrix_and_tradeoff_artifacts_written(tmp_path: Path, beijing_maps_dir: Path) -> None:
    run(write_config(tmp_path, geoind_config(tmp_path, beijing_maps_dir)))

    with (tmp_path / "out" / "matrix.csv").open() as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["target", "k=3", "k=5"]
    assert [r[0] for r in rows[1:]] == ["raw", "protected:none", f"protected:{GEOIND_REF}"]
    for row in rows[1:]:
        for cell in row[1:]:
            assert 0.0 <= float(cell) <= 1.0
    assert (tmp_path / "out" / "tradeoff.png").stat().st_size > 0


def test_protected_pool_cache_is_reused(tmp_path: Path, beijing_maps_dir: Path) -> None:
    config_path = write_config(tmp_path, geoind_config(tmp_path, beijing_maps_dir))
    first = run(config_path)
    assert len(list((tmp_path / "protected").iterdir())) == 1
    second = run(config_path)  # warm protected cache: same values, no new entries
    assert [v.value for v in first] == [v.value for v in second]
    assert len(list((tmp_path / "protected").iterdir())) == 1


def test_tradeoff_plot_requires_utility_metric(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["reporting"] = {"export": ["csv"], "plots": ["tradeoff"]}
    with pytest.raises(ValueError, match="cell_js_divergence"):
        run(write_config(tmp_path, cfg))


def test_unknown_utility_metric_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["metrics"]["utility"] = ["od_matrix_error"]
    with pytest.raises(ValueError, match="od_matrix_error"):
        run(write_config(tmp_path, cfg))


def test_unknown_plot_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["reporting"] = {"export": ["csv"], "plots": ["heatmap"]}
    with pytest.raises(ValueError, match="heatmap"):
        run(write_config(tmp_path, cfg))


def test_misspelled_mechanism_param_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["privacy_mechanisms"] = [
        {"id": "geo_indistinguishability", "params": {"epsilonn": 1.0}},
    ]
    with pytest.raises(ValueError, match="rejected its params"):
        run(write_config(tmp_path, cfg))


def test_protected_dir_under_data_raw_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["experiment"]["protected_dir"] = "data/raw/protected"
    with pytest.raises(ValueError, match="immutable"):
        run(write_config(tmp_path, cfg))
