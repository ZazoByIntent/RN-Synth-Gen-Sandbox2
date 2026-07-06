"""Smoke tests for the RN-LDP-Synth evidence sweep (tiny parameters, seconds-fast)."""

import numpy as np

from trajguard.experiments.rnldp_eval import _table, run_eval, seed_population
from trajguard.maps.base import RoadNetwork


def test_seed_population_is_deterministic_and_on_road(fixture_network: RoadNetwork) -> None:
    a = seed_population(fixture_network, n=6, min_edges=3, seed=4)
    b = seed_population(fixture_network, n=6, min_edges=3, seed=4)
    assert [v.as_segments() for v in a] == [v.as_segments() for v in b]
    assert all(len(v.as_segments()) >= 3 for v in a)


def test_run_eval_shape_and_determinism(fixture_network: RoadNetwork) -> None:
    kwargs = {"epsilons": [80.0], "n_shadow": 4, "n_pop": 8, "seed": 1}
    first = run_eval(fixture_network, **kwargs)
    second = run_eval(fixture_network, **kwargs)
    assert first == second
    assert set(first["arms"]) == {"rn_ldp_synth@eps=80", "markov (non-private ceiling)"}
    for arm in first["arms"].values():
        assert set(arm) == {"mia", "utility"}
        assert set(arm["mia"]) == {"auc", "tpr@fpr=0.01", "tpr@fpr=0.1"}
        assert 0.0 <= arm["mia"]["auc"] <= 1.0
        assert np.isfinite(arm["utility"]["cell_jsd"])
        assert np.isfinite(arm["utility"]["length_w1_m"])
    table = _table(first)
    assert table.count("|") > 10 and "rn_ldp_synth@eps=80" in table
