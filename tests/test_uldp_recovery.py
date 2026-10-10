"""P6 parameter-recovery entry point ``trajguard.experiments.uldp_recovery`` on the fixture map."""

import csv
import json
from pathlib import Path

import pytest

from trajguard.experiments.uldp_recovery import TRUE_REGIME_WEIGHTS, main, planted_truth, wilson
from trajguard.maps.base import RoadNetwork
from trajguard.synthesis.public_sim import PublicSimulator, prior_params

FIXTURE_MAP = [
    "--region",
    "beijing_fixture",
    "--map-dir",
    str(Path(__file__).parent / "fixtures" / "maps"),
    "--bbox",
    "116.30",
    "39.98",
    "116.32",
    "39.995",
]
FAST = ["--gate-draws", "2000", "--confusion-trips", "40"]


def test_entry_point_recovers_a_planted_c3_weight_shift(tmp_path: Path) -> None:
    """At epsilon 8 the C3 gate rejects and the fitted weights close most of the prior-truth gap."""
    out = tmp_path / "rec"
    main(
        ["--out", str(out), "--modules", "c3", "--epsilons", "8", "--ns", "20", "300"]
        + ["--reps", "2"]
        + FIXTURE_MAP
        + FAST
    )
    with (out / "recovery_summary.csv").open(encoding="utf-8") as fh:
        rows = {int(r["n"]): r for r in csv.DictReader(fh)}
    big = rows[300]
    assert big["parameter"] == "regime_weights" and int(big["reps"]) == 2
    assert float(big["rejection_rate"]) == 1.0
    assert float(big["err_truth_mean"]) < 0.3 * float(big["err_prior"])
    assert float(big["gap_closed_mean"]) > 0.7
    with (out / "recovery_runs.csv").open(encoding="utf-8") as fh:
        assert len(list(csv.DictReader(fh))) == 2 * 2  # two n x two repetitions
    record = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert record["truth"]["c3"]["regime_weights"] == list(TRUE_REGIME_WEIGHTS)
    assert record["grid"]["ns"] == [20, 300]
    with pytest.raises(SystemExit):  # never overwrites an existing result
        main(["--out", str(out), "--modules", "c3"] + FIXTURE_MAP)


def test_planted_truth_moves_only_its_module_and_differs_from_the_prior(
    fixture_network: RoadNetwork,
) -> None:
    sim = PublicSimulator(fixture_network)
    prior = prior_params()
    c3, c2, c1 = (planted_truth(sim, m) for m in ("c3", "c2", "c1"))
    assert c3.regime_weights != prior.regime_weights and c3.od_shares is None
    assert c2.od_shares is not None and c2.regime_weights == prior.regime_weights
    assert c2.departure_shares != prior.departure_shares
    assert c1.period_speed_factors != prior.period_speed_factors and c1.od_shares is None
    assert all(r.distance_decay_per_s > 0 for r in c1.regimes)
    assert sum(planted_truth(sim, "all").od_shares or ()) == pytest.approx(1.0)


def test_wilson_interval_contains_the_proportion() -> None:
    lo, hi = wilson(3, 20)
    assert 0.0 < lo < 0.15 < hi < 1.0
    assert wilson(20, 20)[1] == 1.0
