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


# --- repetitions: split_seed pins the population, seed varies the noise ----------


def test_version_hash_ignores_run_seed_when_split_seed_pinned(tmp_path: Path) -> None:
    from trajguard.experiments.orchestrator import _version_hash

    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["experiment"]["split_seed"] = 7
    cfg["experiment"]["seed"] = 1
    first = _version_hash(load_config(write_config(tmp_path, cfg)))
    cfg["experiment"]["seed"] = 2
    second = _version_hash(load_config(write_config(tmp_path, cfg)))
    assert first == second  # repetition runs share the cleaned/matched pool cache
    cfg["experiment"]["split_seed"] = 8
    assert _version_hash(load_config(write_config(tmp_path, cfg))) != first


def test_repetition_seeds_share_pool_but_not_noise(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """Two run seeds under one split_seed: one pool cache, one protected release each."""
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["experiment"]["split_seed"] = 7
    for seed in (1, 2):
        cfg["experiment"]["seed"] = seed
        cfg["experiment"]["output_dir"] = str(tmp_path / "out" / f"seed{seed}")
        run(write_config(tmp_path, cfg))
    assert len(list((tmp_path / "cache").iterdir())) == 1  # same population and split
    assert len(list((tmp_path / "protected").iterdir())) == 2  # fresh noise per seed
    record = json.loads((tmp_path / "out" / "seed2" / "run.json").read_text())
    assert record["seed"] == 2 and record["split_seed"] == 7


def test_max_users_limits_population(tmp_path: Path, beijing_maps_dir: Path) -> None:
    cfg = base_config(tmp_path, beijing_maps_dir)
    cfg["dataset"]["max_users"] = 1  # the fixture has 2 users
    run(write_config(tmp_path, cfg))
    record = json.loads((tmp_path / "out" / "run.json").read_text())
    assert record["max_users"] == 1
    assert record["arms"]["raw"]["n_gallery_users"] == 1


def test_invalid_max_users_rejected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["dataset"]["max_users"] = 0
    with pytest.raises(ValueError, match="max_users"):
        run(write_config(tmp_path, cfg))


# --- loud failures for config knobs the orchestrator does not (yet) support ------


def test_unknown_attack_type_fails_loudly(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["type"] = "no_such_attack"
    with pytest.raises(KeyError, match="no_such_attack"):
        run(write_config(tmp_path, cfg))


def test_reconstruction_rejects_reid_attacker_keys(tmp_path: Path) -> None:
    # epsilon/unit_m come from the mechanism arm, and known_points has no meaning
    # here — a reid-style attacker section on reconstruction is a config mistake.
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {
        "type": "reconstruction",
        "attacker": {"known_points": [3]},
        "target_scope": ["protected"],
    }
    with pytest.raises(ValueError, match="unsupported for reconstruction"):
        run(write_config(tmp_path, cfg))


def test_reconstruction_requires_geoind_arm(tmp_path: Path) -> None:
    # base_config has only the identity mechanism: nothing to invert, fail before
    # the pipeline (the empty maps dir would crash any pipeline work).
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {"type": "reconstruction", "target_scope": ["protected"]}
    with pytest.raises(ValueError, match="geo_indistinguishability"):
        run(write_config(tmp_path, cfg))


def test_reconstruction_target_scope_must_be_protected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {"type": "reconstruction", "target_scope": ["raw", "protected"]}
    with pytest.raises(ValueError, match="must be \\['protected'\\]"):
        run(write_config(tmp_path, cfg))


def test_poi_inference_rejects_reid_attacker_keys(tmp_path: Path) -> None:
    # known_points/distance have no meaning for stay-point clustering — a
    # reid-style attacker section on poi_inference is a config mistake.
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {
        "type": "poi_inference",
        "attacker": {"known_points": [3]},
        "target_scope": ["protected"],
    }
    with pytest.raises(ValueError, match="unsupported for poi_inference"):
        run(write_config(tmp_path, cfg))


def test_poi_inference_target_scope_must_be_protected(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {"type": "poi_inference", "target_scope": ["raw", "protected"]}
    with pytest.raises(ValueError, match="must be \\['protected'\\] for poi_inference"):
        run(write_config(tmp_path, cfg))


def test_poi_inference_rejects_bad_stay_point_knobs(tmp_path: Path) -> None:
    # The attack constructor validates its knobs; the probe must fire before any
    # pipeline work (the empty maps dir would crash any pipeline stage).
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0] = {
        "type": "poi_inference",
        "attacker": {"dwell_s": -5},
        "target_scope": ["protected"],
    }
    with pytest.raises(ValueError, match="dwell_s"):
        run(write_config(tmp_path, cfg))


def test_poi_inference_requires_a_mechanism_arm(tmp_path: Path) -> None:
    # With no mechanisms there are no protected arms and the attack would
    # silently produce no rows — fail loudly before the pipeline instead.
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["privacy_mechanisms"] = []
    cfg["attacks"][0] = {"type": "poi_inference", "target_scope": ["protected"]}
    with pytest.raises(ValueError, match="privacy_mechanisms"):
        run(write_config(tmp_path, cfg))


# --- 1e: membership inference against synthetic generator arms -------------------


def mia_config(tmp_path: Path, maps_dir: Path) -> dict[str, Any]:
    """base_config with the MIA attack against a markov generator arm."""
    cfg = base_config(tmp_path, maps_dir)
    cfg["privacy_mechanisms"] = []
    cfg["synthetic_generators"] = [{"id": "markov", "params": {"order": 1}}]
    cfg["attacks"] = [
        {
            "type": "membership_inference",
            "target_scope": ["synthetic"],
            "attacker": {"n_shadow": 8, "subsample": 0.5},
            "fprs": [0.25],  # fixture scale: few non-members, so the FPR floor is coarse
        }
    ]
    return cfg


def test_membership_rejects_reid_attacker_keys(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["attacker"] = {"known_points": [3]}
    with pytest.raises(ValueError, match="unsupported for membership_inference"):
        run(write_config(tmp_path, cfg))


def test_membership_target_scope_must_be_synthetic(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["target_scope"] = ["protected"]
    with pytest.raises(ValueError, match="must be \\['synthetic'\\]"):
        run(write_config(tmp_path, cfg))


def test_membership_requires_a_generator_arm(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["synthetic_generators"] = []
    with pytest.raises(ValueError, match="synthetic_generators"):
        run(write_config(tmp_path, cfg))


def test_membership_rejects_bad_fprs(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["fprs"] = [1.5]
    with pytest.raises(ValueError, match="fprs"):
        run(write_config(tmp_path, cfg))


def test_membership_rejects_bad_lira_knobs(tmp_path: Path) -> None:
    # The attack constructor validates n_shadow >= 2; the probe must fire before
    # any pipeline work (the empty maps dir would crash any pipeline stage).
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["attacks"][0]["attacker"] = {"n_shadow": 1}
    with pytest.raises(ValueError, match="n_shadow"):
        run(write_config(tmp_path, cfg))


def test_unknown_generator_fails_loudly(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["synthetic_generators"] = [{"id": "no_such_generator"}]
    with pytest.raises(KeyError, match="no_such_generator"):
        run(write_config(tmp_path, cfg))


def test_misspelled_generator_param_rejected(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")
    cfg["synthetic_generators"] = [{"id": "markov", "params": {"orderr": 1}}]
    with pytest.raises(ValueError, match="rejected its params"):
        run(write_config(tmp_path, cfg))


def _mia_traj(traj_id: str, user: str, split: str, edges: tuple[int, ...]) -> tuple[Any, Any]:
    """A minimal (matched, clean) pair carrying just an edge sequence and a split label."""
    from trajguard.datamodel import CleanTrajectory, MatchedTrajectory

    matched = MatchedTrajectory(
        traj_id=traj_id,
        user_id=user,
        map_id="beijing",
        edge_seq=edges,
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    clean = CleanTrajectory(
        traj_id=traj_id,
        user_id=user,
        points=((0.0, 0.0, 0.0),),
        bbox=(0.0, 0.0, 0.0, 0.0),
        duration_s=0.0,
        length_m=0.0,
        mean_speed=0.0,
        cleaning_flags=(),
        split=split,
    )
    return matched, clean


def test_mia_pool_builds_the_strict_shadow_protocol() -> None:
    """Shadow split first as the attacker's base, then train members, then test
    non-members as labelled candidates; the attack split stays out entirely."""
    from trajguard.experiments.orchestrator import _mia_pool

    pairs = [
        _mia_traj("t1", "u1", "train", (1, 2)),
        _mia_traj("t2", "u1", "train", (2, 3)),
        _mia_traj("s1", "u2", "shadow", (7, 8)),
        _mia_traj("e1", "u3", "test", (4, 5)),
        _mia_traj("a1", "u4", "attack", (9, 9)),
    ]
    matched = [m for m, _ in pairs]
    clean_by_id = {c.traj_id: c for _, c in pairs}
    pool, candidates, train_m = _mia_pool(matched, clean_by_id)
    assert pool == [(7, 8), (1, 2), (2, 3), (4, 5)]
    assert candidates == [(1, True), (2, True), (3, False)]
    assert [m.traj_id for m in train_m] == ["t1", "t2"]


def test_mia_pool_requires_members_and_nonmembers() -> None:
    from trajguard.experiments.orchestrator import _mia_pool

    pairs = [_mia_traj("t1", "u1", "train", (1, 2))]
    matched = [m for m, _ in pairs]
    clean_by_id = {c.traj_id: c for _, c in pairs}
    with pytest.raises(ValueError, match="non-members"):
        _mia_pool(matched, clean_by_id)


def test_membership_inference_runs_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """End to end: one MIA row set per generator arm, score-based metrics without CI."""
    cfg = mia_config(tmp_path, beijing_maps_dir)
    values = run(write_config(tmp_path, cfg))

    mia = [v for v in values if v.result_id.startswith("membership_inference:")]
    assert {v.result_id for v in mia} == {"membership_inference:synthetic:markov:order=1"}
    by_name = {v.name: v for v in mia}
    assert set(by_name) == {"auc", "tpr@fpr=0.25"}
    auc = by_name["auc"]
    assert 0.0 <= auc.value <= 1.0
    # markov memorizes the tiny fixture train split: the non-private ceiling beats chance
    assert auc.value > 0.5
    # score-based metrics carry no within-run CI by design; repeat gives the interval
    assert auc.ci_low is None and auc.ci_high is None and auc.n_bootstrap is None
    rows = list(csv.DictReader((tmp_path / "out" / "metrics.csv").open()))
    mia_rows = [r for r in rows if r["result_id"].startswith("membership_inference:")]
    assert mia_rows and all(r["ci_low"] == "" and r["ci_high"] == "" for r in mia_rows)
    # deterministic under the same seeds
    assert [v.value for v in run(write_config(tmp_path, cfg))] == [v.value for v in values]


def test_membership_runs_against_rn_ldp_synth_arm(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """The private generator arm builds via the injected network and per-shadow seeds."""
    cfg = mia_config(tmp_path, beijing_maps_dir)
    cfg["synthetic_generators"].append(
        {
            "id": "rn_ldp_synth",
            "params": {"epsilon": 80.0, "n_rows": 10, "n_cols": 10, "l_max": 12},
        }
    )
    cfg["attacks"][0]["attacker"] = {"n_shadow": 4, "subsample": 0.5}
    values = run(write_config(tmp_path, cfg))

    mia = {v.result_id for v in values if v.result_id.startswith("membership_inference:")}
    assert mia == {
        "membership_inference:synthetic:markov:order=1",
        "membership_inference:synthetic:rn_ldp_synth:epsilon=80.0,l_max=12,n_cols=10,n_rows=10",
    }
    rn = {v.name: v.value for v in values if "rn_ldp_synth" in v.result_id}
    assert set(rn) == {"auc", "tpr@fpr=0.25"}
    assert 0.0 <= rn["auc"] <= 1.0


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


def test_reconstruction_runs_against_geoind_arms_only(
    tmp_path: Path, beijing_maps_dir: Path
) -> None:
    """End to end: reconstruction inverts the geo-ind release, skips the identity arm."""
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["attacks"].append({"type": "reconstruction", "target_scope": ["protected"]})
    values = run(write_config(tmp_path, cfg))

    recon = [v for v in values if v.result_id.startswith("reconstruction:")]
    assert {v.result_id for v in recon} == {f"reconstruction:protected:{GEOIND_REF}"}
    by_name = {v.name: v for v in recon}
    assert set(by_name) == {"hausdorff_m", "dtw_m", "mean_spatial_error_m"}
    for v in by_name.values():
        assert v.value is not None and v.value > 0.0
        assert v.ci_low is not None and v.ci_high is not None
        assert v.ci_low <= v.value <= v.ci_high
    # per-point metrics stay at the noise scale (mean radius 2*25/10 = 5 m);
    # dtw_m is a path-summed distance, so it is only checked for finiteness above
    assert by_name["hausdorff_m"].value < 100.0
    # the MAP estimate must beat the raw noisy release on average: with the
    # Gamma(2, b=2.5 m) radius the released points sit ~5 m off, the smoother less
    assert by_name["mean_spatial_error_m"].value < 5.0
    # reconstruction rows land in metrics.csv alongside the reid rows
    rows = list(csv.DictReader((tmp_path / "out" / "metrics.csv").open()))
    assert any(r["result_id"].startswith("reconstruction:") for r in rows)
    # the matrix pivots the family's headline metric next to the reid column;
    # only the geo-ind arm has a reconstruction value (the identity arm is skipped)
    matrix = list(csv.DictReader((tmp_path / "out" / "matrix.csv").open()))
    by_target = {r["target"]: r for r in matrix}
    assert float(by_target[f"protected:{GEOIND_REF}"]["reconstruction:mean_spatial_error_m"]) > 0.0
    assert by_target["raw"]["reconstruction:mean_spatial_error_m"] == ""
    # each family with utility on its arms gets its own tradeoff plot
    assert (tmp_path / "out" / "tradeoff.png").stat().st_size > 0
    assert (tmp_path / "out" / "tradeoff_reconstruction.png").stat().st_size > 0


def test_poi_inference_runs_against_protected_arms(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """End to end: POI rows per protected arm; the identity arm is the ~zero-error sanity check."""
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    # Fixture trajectories are short drives, not dwells: widen the stay-point radius
    # past the fixture bbox (~2 km) and shrink the dwell time below the trajectory
    # span so every trajectory yields one stay-point, and let both hour windows
    # cover the whole day so home and work always resolve (cf. tests/test_attribute.py).
    cfg["attacks"].append(
        {
            "type": "poi_inference",
            "target_scope": ["protected"],
            "attacker": {
                "dwell_s": 10,
                "radius_m": 5000,
                "home_hours": [0, 24],
                "work_hours": [0, 24],
            },
            "threshold_m": 200,
        }
    )
    values = run(write_config(tmp_path, cfg))

    poi = [v for v in values if v.result_id.startswith("poi_inference:")]
    assert {v.result_id for v in poi} == {
        "poi_inference:protected:none",
        f"poi_inference:protected:{GEOIND_REF}",
    }
    by_arm: dict[str, dict[str, Any]] = {}
    for v in poi:
        by_arm.setdefault(v.result_id, {})[v.name] = v
    names = {"home_error_m", "work_error_m", "home_localised", "work_localised"}
    for arm in by_arm.values():
        assert set(arm) == names
    # Identity arm releases the raw points: exact recovery is a sanity value, not protection.
    identity = by_arm["poi_inference:protected:none"]
    assert identity["home_error_m"].value == 0.0
    assert identity["work_error_m"].value == 0.0
    assert identity["home_localised"].value == 1.0
    assert identity["work_localised"].value == 1.0
    # The geo-ind arm (mean displacement 5 m) leaves a small nonzero centroid error,
    # still inside the 200 m localisation threshold, with a bootstrap CI around it.
    noisy = by_arm[f"poi_inference:protected:{GEOIND_REF}"]
    err = noisy["home_error_m"]
    assert 0.0 < err.value < 200.0
    assert err.ci_low is not None and err.ci_high is not None
    assert err.ci_low <= err.value <= err.ci_high
    assert noisy["home_localised"].value == 1.0
    # POI rows land in metrics.csv and pivot into the matrix's poi_inference column.
    rows = list(csv.DictReader((tmp_path / "out" / "metrics.csv").open()))
    assert any(r["result_id"].startswith("poi_inference:") for r in rows)
    matrix = list(csv.DictReader((tmp_path / "out" / "matrix.csv").open()))
    by_target = {r["target"]: r for r in matrix}
    assert by_target["protected:none"]["poi_inference:home_error_m"] == "0.0"
    assert float(by_target[f"protected:{GEOIND_REF}"]["poi_inference:home_error_m"]) > 0.0
    assert by_target["raw"]["poi_inference:home_error_m"] == ""
    assert (tmp_path / "out" / "tradeoff_poi_inference.png").stat().st_size > 0


# --- wave 2 (O4): the unified results table, docs/REZULTATI_SHEMA.md ---------------


def test_results_csv_follows_schema(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """Every run writes results.csv per the schema: same rows as metrics.csv, plus
    provenance, structured identity/axis columns, arm stats, and runtimes."""
    from trajguard.reporting.results_schema import RESULTS_COLUMNS

    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["attacks"].append({"type": "reconstruction", "target_scope": ["protected"]})
    values = run(write_config(tmp_path, cfg))

    with (tmp_path / "out" / "results.csv").open() as fh:
        reader = csv.reader(fh)
        assert tuple(next(reader)) == RESULTS_COLUMNS
    rows = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    assert len(rows) == len(values)  # one results row per metric value, same order
    assert [r["result_id"] for r in rows] == [v.result_id for v in values]

    for r in rows:
        # provenance repeated on every row
        assert r["exp_id"] == "test_reid" and r["seed"] == "42" and r["split_seed"] == "42"
        assert len(r["config_hash"]) == 16 and r["created_at"]
        assert float(r["run_runtime_s"]) > 0.0

    by_family: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_family.setdefault(r["family"], []).append(r)
    assert set(by_family) == {"reidentification", "reconstruction", "utility"}

    raw = [r for r in by_family["reidentification"] if r["scope"] == "raw"]
    assert raw and all(r["arm_id"] == "" and r["epsilon"] == "" for r in raw)
    assert {r["known_points"] for r in by_family["reidentification"]} == {"3", "5"}
    geo = [r for r in by_family["reidentification"] if r["arm_id"] == "geo_indistinguishability"]
    assert geo and all(r["epsilon"] == "10.0" and r["unit_m"] == "25.0" for r in geo)
    assert all(float(r["attack_runtime_s"]) >= 0.0 for r in by_family["reidentification"])

    recon = by_family["reconstruction"]
    assert all(
        r["epsilon"] == "10.0" and r["known_points"] == "" and r["scope"] == "protected"
        for r in recon
    )
    # utility rows describe the arm, not an attack: no attack runtime
    assert all(r["attack_runtime_s"] == "" for r in by_family["utility"])
    # arm statistics match run.json
    arms = json.loads((tmp_path / "out" / "run.json").read_text())["arms"]
    for r in geo:
        assert int(r["n_pool"]) == arms[f"protected:{GEOIND_REF}"]["n_pool"]
        assert int(r["n_rematch_dropped"]) == arms[f"protected:{GEOIND_REF}"]["n_rematch_dropped"]


def test_results_csv_membership_columns(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """MIA rows carry the generator axis columns and the member/non-member counts."""
    cfg = mia_config(tmp_path, beijing_maps_dir)
    run(write_config(tmp_path, cfg))
    rows = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    mia = [r for r in rows if r["family"] == "membership_inference"]
    assert mia and all(r["scope"] == "synthetic" and r["arm_id"] == "markov" for r in mia)
    for r in mia:
        assert r["n_shadow"] == "8" and r["epsilon"] == ""  # markov has no epsilon
        assert int(r["n_members"]) + int(r["n_nonmembers"]) == int(r["n_pool"])
        assert r["ci_low"] == "" and r["ci_high"] == ""  # score-based: no within-run CI


def test_matrix_and_tradeoff_artifacts_written(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """matrix.csv pivots each family's headline metric (reid at max known_points)."""
    run(write_config(tmp_path, geoind_config(tmp_path, beijing_maps_dir)))

    with (tmp_path / "out" / "matrix.csv").open() as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["target", "reidentification:top1_acc"]
    assert [r[0] for r in rows[1:]] == ["raw", "protected:none", f"protected:{GEOIND_REF}"]
    for row in rows[1:]:
        assert 0.0 <= float(row[1]) <= 1.0
    # the pivoted cell is the value at the largest known_points level (k=5)
    results = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    (raw_k5,) = [
        r
        for r in results
        if r["target_ref"] == "raw" and r["metric"] == "top1_acc" and r["known_points"] == "5"
    ]
    assert rows[1][1] == raw_k5["value"]
    assert (tmp_path / "out" / "tradeoff.png").stat().st_size > 0


def test_protected_pool_cache_is_reused(tmp_path: Path, beijing_maps_dir: Path) -> None:
    config_path = write_config(tmp_path, geoind_config(tmp_path, beijing_maps_dir))
    first = run(config_path)
    assert len(list((tmp_path / "protected").iterdir())) == 1
    second = run(config_path)  # warm protected cache: same values, no new entries
    assert [v.value for v in first] == [v.value for v in second]
    assert len(list((tmp_path / "protected").iterdir())) == 1


def test_planned_plots_written_end_to_end(tmp_path: Path, beijing_maps_dir: Path) -> None:
    """The four wave-2 plots come out of one run when reporting.plots asks for them."""
    cfg = geoind_config(tmp_path, beijing_maps_dir)
    cfg["reporting"]["plots"] = ["tradeoff", "by_epsilon", "by_knowledge", "mechanisms", "runtime"]
    run(write_config(tmp_path, cfg))
    for name in (
        "tradeoff.png",
        "by_epsilon_reidentification.png",
        "by_knowledge_reidentification.png",
        "mechanisms_reidentification.png",
        "runtime.png",
    ):
        assert (tmp_path / "out" / name).stat().st_size > 0, name


def test_by_knowledge_plot_requires_a_knowledge_attack(tmp_path: Path) -> None:
    cfg = mia_config(tmp_path, tmp_path / "maps")  # membership inference has no known_points
    cfg["reporting"] = {"export": ["csv"], "plots": ["by_knowledge"]}
    with pytest.raises(ValueError, match="by_knowledge"):
        run(write_config(tmp_path, cfg))


def test_by_epsilon_plot_requires_an_arm(tmp_path: Path) -> None:
    cfg = base_config(tmp_path, tmp_path / "maps")
    cfg["privacy_mechanisms"] = []
    cfg["attacks"][0]["target_scope"] = ["raw"]
    cfg["reporting"] = {"export": ["csv"], "plots": ["by_epsilon"]}
    with pytest.raises(ValueError, match="by_epsilon"):
        run(write_config(tmp_path, cfg))


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
