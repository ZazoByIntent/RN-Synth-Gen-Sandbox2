"""ULDP modules C3 (regime vote), C2 (OD shares), C1 (moments) and the composite of ``uldp_synth``.

GRR debiasing, the F7 gate, EM recovery, privacy tests 1-4 of docs/NACRT_ULDP_SINTEZA.md
§6.2 and an end-to-end fit/generate (direct and through the orchestrator).
"""

import csv
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from test_orchestrator import base_config, beijing_maps_dir, write_config
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory, TimedRoute
from trajguard.experiments import registry
from trajguard.experiments.orchestrator import _generator_facts, run
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.ldp import grr_perturb
from trajguard.representation import TrajectoryView
from trajguard.synthesis.public_sim import (
    REGIME_CATALOGUE,
    PublicSimulator,
    SimParams,
    prior_params,
)
from trajguard.synthesis.uldp_arms import (
    UldpOracleGenerator,
    UldpPriorGenerator,
    simulator_params_hash,
)
from trajguard.synthesis.uldp_base import (
    ReportSpace,
    UserReport,
    canary_log_ratio,
    log_prob_unchanged_under_view_swap,
    params_unchanged_under_view_swap,
    randomiser_log_ratio,
    validate_report,
)
from trajguard.synthesis.uldp_synth import (
    C1_BINS,
    C2_QUESTION_GROUPS,
    DECAY_MAX_PER_S,
    GATE_ALPHA,
    N_COST_BANDS,
    C3Public,
    LengthSample,
    UldpSynthGenerator,
    c1_bin,
    c1_server_fit,
    composite_layout,
    cost_band,
    em_mixture_weights,
    grr_channel,
    grr_frequencies,
    grr_noise_cov,
    hm_bin_probs,
    hm_bound,
    hm_perturb,
    kl_furness,
    pm_density,
    question_count,
    solve_decay,
    solve_speed_level,
)

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here

BBOX = (116.30, 39.98, 116.32, 39.995)
WALK, BIKE, CAR = REGIME_CATALOGUE
N_DRAWS = 3000
TOL = 0.3  # about five standard errors of a log-ratio bin at 3000 draws
# Small Monte Carlo sizes keep the suite fast; production keeps the module defaults.
FAST = {"confusion_trips": 40, "gate_draws": 2000}


def _view(user: str, i: int, edge_seq: tuple[int, ...], duration: float) -> TrajectoryView:
    t0 = 1_222_819_200.0  # 2008-10-01 08:00 in Beijing
    clean = CleanTrajectory(
        traj_id=f"{user}-{i}",
        user_id=user,
        points=((39.981, 116.301, t0), (39.994, 116.319, t0 + duration)),
        bbox=BBOX,
        duration_s=duration,
        length_m=1000.0,
        mean_speed=1000.0 / duration,
        cleaning_flags=(),
        split="train",
    )
    matched = MatchedTrajectory(
        traj_id=f"{user}-{i}",
        user_id=user,
        map_id="osm_beijing_fixture",
        edge_seq=edge_seq,
        matched_points=(),
        match_score=1.0,
        frac_matched=1.0,
    )
    return TrajectoryView(clean=clean, matched=matched)


def _trips(sim: PublicSimulator, n: int, seed: int) -> list[tuple[int, ...]]:
    return [r.edge_seq for r in sim.simulate(SimParams(), n, np.random.default_rng(seed))]


def _users(sim: PublicSimulator, n_users: int, regime_of: list, seed: int) -> list[TrajectoryView]:
    """User u gets one to three trips timed exactly at regime_of[u]'s jitter-free speed."""
    seqs = _trips(sim, 3 * n_users, seed)
    views = []
    for u in range(n_users):
        for i in range(1 + u % 3):
            seq = seqs[3 * u + i]
            views.append(_view(f"u{u}", i, seq, sim.route_time_s(seq, regime_of[u])))
    return views


@pytest.fixture(scope="module")
def gen(fixture_network: RoadNetwork) -> UldpSynthGenerator:
    return UldpSynthGenerator(fixture_network, epsilon=1.0, **FAST)  # type: ignore[arg-type]


def _reports(answers: list[int], eps: float) -> list[UserReport]:
    return [UserReport("c3", 0, (float(a),), eps) for a in answers]


# --- server: GRR debiasing, gate, EM -------------------------------------------------------


def test_grr_frequencies_are_unbiased() -> None:
    eps, truth = 1.0, np.array([0.5, 0.3, 0.2])
    expected_counts = 1000 * truth @ grr_channel(3, eps)
    assert grr_frequencies(expected_counts, eps) == pytest.approx(truth)  # exact in expectation
    rng = np.random.default_rng(0)
    labels = np.repeat([0, 1, 2], (truth * 20_000).astype(int))
    reports = [grr_perturb(int(x), 3, eps, rng) for x in labels]
    est = grr_frequencies(np.bincount(reports, minlength=3), eps)
    assert np.abs(est - truth).max() < 0.03  # about four standard errors at n = 20 000


def test_em_recovers_weights_through_the_composed_channel(gen: UldpSynthGenerator) -> None:
    pub = gen.public_params()
    channel = pub.confusion @ grr_channel(3, pub.epsilon)
    truth = np.array([0.6, 0.1, 0.3])
    w = em_mixture_weights(1e6 * truth @ channel, channel, np.full(3, 1 / 3))
    assert w == pytest.approx(truth, abs=1e-3)


def test_gate_keeps_prior_when_reports_match_it(gen: UldpSynthGenerator) -> None:
    pub = gen.public_params()
    n = 300
    counts = np.round(n * pub.prior_reports).astype(int)
    answers = [j for j, c in enumerate(counts) for _ in range(c)]
    fit = UldpSynthGenerator.server_fit(_reports(answers, pub.epsilon), pub)
    assert not fit.gate_rejected and fit.gate_p_value > GATE_ALPHA
    assert fit.regime_weights == pub.prior_weights
    assert fit.counts == tuple(int(c) for c in counts)


def test_gate_rejects_a_clear_departure(gen: UldpSynthGenerator) -> None:
    pub = gen.public_params()
    rng = np.random.default_rng(1)
    answers = [grr_perturb(0, 3, pub.epsilon, rng) for _ in range(300)]  # everyone walks
    fit = UldpSynthGenerator.server_fit(_reports(answers, pub.epsilon), pub)
    assert fit.gate_rejected and fit.gate_p_value < 1e-3 and fit.gate_statistic > 20
    assert fit.regime_weights[0] > 0.8 and sum(fit.regime_weights) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="category index"):
        UldpSynthGenerator.server_fit(_reports([3], pub.epsilon), pub)


# --- phone: one uniformly drawn trip, public default --------------------------------------


def test_phone_labels_follow_the_trip_and_default_to_the_prior(
    gen: UldpSynthGenerator, fixture_network: RoadNetwork
) -> None:
    pub: C3Public = gen.public_params()
    sim = gen.sim
    seq = _trips(sim, 1, 3)[0]
    walker = [_view("w", 0, seq, sim.route_time_s(seq, WALK))]
    strong = UldpSynthGenerator(fixture_network, epsilon=8.0, **FAST).public_params()  # type: ignore[arg-type]
    rng = np.random.default_rng(2)
    labels = [UldpSynthGenerator.encode_user(walker, strong, 0, rng).answer[0] for _ in range(300)]
    assert labels.count(0.0) / 300 > 0.9  # walking-speed trips are labelled walk
    unknown = [TrajectoryView(sequence=(10**12,), user_id="x")]  # not on the map: default
    for views in ((), unknown):
        report = UldpSynthGenerator.encode_user(views, pub, 0, rng)
        assert report.module == "c3" and report.epsilon == pub.epsilon
    assert pub.prior_labels.sum() == pytest.approx(1.0)


# --- privacy tests 1-4 of §6.2 ----------------------------------------------------------------


def _make(network: RoadNetwork):  # type: ignore[no-untyped-def]
    return lambda: UldpSynthGenerator(network, epsilon=1.0, seed=3, **FAST)  # type: ignore[arg-type]


def test_privacy_tests_1_to_4(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    roster = ("u0", "u1", "u2", "u3")  # u3 never has a trip
    train_a = _users(sim, 3, [WALK, BIKE, CAR], seed=4)
    train_b = _users(sim, 3, [CAR, CAR, WALK], seed=5)
    probes = _trips(sim, 3, 6)
    make = _make(fixture_network)
    assert params_unchanged_under_view_swap(make, roster, train_a, train_b)
    assert log_prob_unchanged_under_view_swap(make, roster, train_a, train_b, probes)
    walker = [v for v in train_a if v.user_id == "u0"]
    ratio = randomiser_log_ratio(make(), (), walker, N_DRAWS, seed=7)
    assert ratio <= 1.0 + TOL
    long_seq = tuple(e for s in probes for e in s)
    canary = [_view("u3", 0, long_seq, 1e9), _view("u3", 1, probes[0], 1e-3)]
    assert canary_log_ratio(make, roster, train_a, canary, N_DRAWS, seed=8) <= 1.0 + TOL


# --- end to end ----------------------------------------------------------------------------


def test_fit_generate_and_score_end_to_end(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    n_users = 60
    regimes = [WALK if u % 4 else CAR for u in range(n_users)]  # three quarters walk
    train = _users(sim, n_users, regimes, seed=9)
    gen = UldpSynthGenerator(fixture_network, epsilon=8.0, seed=1, **FAST)  # type: ignore[arg-type]
    gen.set_user_roster([f"u{u}" for u in range(n_users + 5)])  # five users without trips
    gen.fit(train)
    fit = gen.fitted
    assert sum(fit.counts) == n_users + 5
    assert fit.gate_rejected and fit.regime_weights[0] > 0.5 > fit.regime_weights[1]
    out = gen.generate(5, seed=11)
    assert len(out) == 5 and all(isinstance(t.payload, TimedRoute) for t in out)
    assert out[0].syn_id == "uldp_synth/11/0" and out[0].map_id == "osm_beijing_fixture"
    assert [t.payload for t in out] == [t.payload for t in gen.generate(5, seed=11)]
    lp = gen.sequence_log_prob(out[0].payload.edge_seq)
    assert math.isfinite(lp) and lp == sim.log_prob(gen.sim_params(), out[0].payload.edge_seq)
    with pytest.raises(ValueError, match="module"):
        UldpSynthGenerator(fixture_network, epsilon=1.0, module="c9")


def test_a_gate_that_keeps_the_prior_yields_the_shared_prior_arm(
    fixture_network: RoadNetwork,
) -> None:
    gen = UldpSynthGenerator(fixture_network, epsilon=1.0, seed=0, **FAST)  # type: ignore[arg-type]
    pub = gen.public_params()
    assert pub.regimes == prior_params().regimes == REGIME_CATALOGUE
    assert pub.prior_weights == prior_params().regime_weights
    gen.set_user_roster([f"u{u}" for u in range(40)])  # no trips: labels follow M^T pi0
    gen.fit([])
    assert not gen.fitted.gate_rejected
    assert gen.sim_params() == prior_params()
    prior = UldpPriorGenerator(fixture_network)
    prior.fit([])
    ph = simulator_params_hash(gen.sim, gen.sim_params(), zones_per_side=gen.zones_per_side)
    assert ph == prior.generate(1, seed=0)[0].params_hash
    oracle = UldpOracleGenerator(fixture_network)  # estimates weights on the same catalogue
    oracle.set_user_roster(["a"])
    seq = _trips(gen.sim, 1, 12)[0]
    oracle.fit([_view("a", 0, seq, gen.sim.route_time_s(seq, BIKE))])
    assert oracle.params.regimes == REGIME_CATALOGUE
    assert oracle.params.regime_weights == (0.0, 1.0, 0.0)


def test_params_hash_covers_map_and_simulator_version(fixture_network: RoadNetwork) -> None:
    params = SimParams()
    a = simulator_params_hash(PublicSimulator(fixture_network), params, zones_per_side=3)
    b = simulator_params_hash(PublicSimulator(fixture_network, zones_per_side=2), params)
    c = simulator_params_hash(PublicSimulator(fixture_network), params)
    assert a != c and b != c  # extra keys and the map key (zones) both enter


def test_orchestrator_runs_uldp_synth(tmp_path: Path, beijing_maps_dir: Path) -> None:
    from trajguard.experiments import builtins  # noqa: F401  (registration side effect)

    assert registry.get("generator", "uldp_synth") is UldpSynthGenerator
    cfg = base_config(tmp_path, beijing_maps_dir)
    cfg["synthetic_generators"] = [{"id": "uldp_synth", "params": {"epsilon": 2.0, **FAST}}]
    cfg["split"]["fractions"] = {"train": 0.5, "test": 0.5}
    cfg["metrics"]["timed_utility"] = True
    run(write_config(tmp_path, cfg))
    rows = list(csv.DictReader((tmp_path / "out" / "results.csv").open()))
    assert any(r["arm_id"] == "uldp_synth" and r["scope"] == "synthetic" for r in rows)


# === Module C2: origin-destination shares ====================================================

C2_FAST = {"module": "c2", "band_origins": 20, "gate_draws": 2000}
AM_PEAK = 1  # the _view trips depart at 08:00 Beijing time


@pytest.fixture(scope="module")
def gen2(fixture_network: RoadNetwork) -> UldpSynthGenerator:
    return UldpSynthGenerator(fixture_network, epsilon=2.0, **C2_FAST)  # type: ignore[arg-type]


def _c2_reports(per_slot: dict[int, list[int]], eps: float) -> list[UserReport]:
    return [UserReport("c2", q, (float(a),), eps) for q, ans in per_slot.items() for a in ans]


def _expand(counts: np.ndarray) -> list[int]:
    return [j for j, c in enumerate(counts) for _ in range(int(c))]


def _cell(sim: PublicSimulator, seq: tuple[int, ...]) -> int:
    zo, zd = sim.od_zones(seq)
    return zo * sim.n_zones + zd


def _cell_trips(sim: PublicSimulator, n: int, seed: int) -> tuple[int, list[tuple[int, ...]]]:
    """The most frequent OD cell of simulated prior trips and n trips in it."""
    seqs = _trips(sim, 400, seed)
    cells = [_cell(sim, s) for s in seqs]
    top = max(set(cells), key=cells.count)
    in_top = [s for s, c in zip(seqs, cells, strict=True) if c == top]
    return top, [in_top[i % len(in_top)] for i in range(n)]


def test_kl_furness_is_ipf_in_the_noise_free_limit_and_shrinks_to_the_prior() -> None:
    q = np.array([0.1, 0.2, 0.3, 0.4])  # 2 x 2 table, row-major
    rows, cols = np.arange(4) // 2, np.arange(4) % 2
    flat = np.array([[0.25, -0.25], [-0.25, 0.25]])  # diag(rho) - rho rho^T at rho = 1/2
    t_rows, t_cols = np.array([0.5, 0.5]), np.array([0.6, 0.4])

    def fit(scale: float) -> np.ndarray:
        return kl_furness(q, [(rows, t_rows, scale * flat), (cols, t_cols, scale * flat)])

    hard = fit(1e-12).reshape(2, 2)  # V -> 0: classical Furness / IPF onto the marginals
    assert hard.sum(axis=1) == pytest.approx(t_rows) and hard.sum(axis=0) == pytest.approx(t_cols)
    odds = hard[0, 0] * hard[1, 1] / (hard[0, 1] * hard[1, 0])
    assert odds == pytest.approx(0.1 * 0.4 / (0.2 * 0.3))  # Furness form: Q times factors
    noisy = fit(1e3).reshape(2, 2)  # very noisy reports barely move the prior
    assert np.abs(noisy.ravel() - q).max() < 1e-3
    middle = fit(0.05).reshape(2, 2).sum(axis=0)  # in between: part of the way
    assert 0.4 < middle[0] < 0.6
    own = [(rows, np.array([0.3, 0.7]), flat), (cols, np.array([0.4, 0.6]), flat)]
    assert kl_furness(q, own) == pytest.approx(q)  # reports equal to Q's marginals keep Q
    # A cell Q rules out stays empty, even against a debiased (negative) report.
    q0 = np.array([0.5, 0.0, 0.25, 0.25])
    out = kl_furness(q0, [(cols, np.array([-0.2, 1.2]), 1e-3 * flat)])
    assert out[1] == 0.0 and out.sum() == pytest.approx(1.0) and out.min() >= 0


def test_c2_band_reports_tilt_the_od_table_through_the_scaling(gen2: UldpSynthGenerator) -> None:
    pub = gen2.public_params()
    od_cells, bands = pub.od_band_prior.shape
    assert pub.od_band_prior.sum(axis=1) == pytest.approx(pub.od_prior)  # Q's OD marginal
    # A toy prior where cell 0 holds the short trips: band reports alone move the OD table.
    q = np.zeros((od_cells, bands))
    q[0, 0], q[1, 1] = 0.5, 0.5
    cells = np.arange(q.size)
    target = np.zeros(bands)
    target[0] = 0.9
    target[1] = 0.1
    cov = grr_noise_cov(np.full(bands, 1.0 / bands), 300, pub.epsilon)
    table = kl_furness(q.ravel(), [(cells % bands, target, cov)]).reshape(q.shape)
    assert table.sum(axis=1)[0] > 0.6 > 0.4 > table.sum(axis=1)[1]


def test_gravity_od_shares_match_simulated_prior_trips(gen2: UldpSynthGenerator) -> None:
    sim, pub = gen2.sim, gen2.public_params()
    assert pub.od_prior.sum() == pytest.approx(1.0) and len(pub.od_prior) == 81
    cells = [_cell(sim, s) for s in _trips(sim, 1000, 13)]
    empirical = np.bincount(cells, minlength=81) / len(cells)
    assert np.abs(empirical - pub.od_prior).max() < 0.025  # about four standard errors
    assert not empirical[~pub.od_support].any()  # unhostable cells never occur
    assert pub.band_prior.sum() == pytest.approx(1.0) and len(pub.band_prior) == N_COST_BANDS
    assert tuple(pub.period_prior) == prior_params().departure_shares
    bands = [cost_band(c) for c in (0.0, 599.0, 600.0, 3599.0, 3600.0, math.inf)]
    assert bands == [0, 0, 1, 4, 5, 5]


def test_c2_grr_estimate_is_unbiased(gen2: UldpSynthGenerator) -> None:
    pub = gen2.public_params()
    truth = np.zeros(81)
    truth[[0, 40, 80]] = (0.5, 0.3, 0.2)
    expected = 1000 * truth @ grr_channel(81, pub.epsilon)
    assert grr_frequencies(expected, pub.epsilon) == pytest.approx(truth)  # exact in expectation
    rng = np.random.default_rng(14)
    labels = np.repeat([0, 40, 80], (truth[[0, 40, 80]] * 20_000).astype(int))
    answers = [grr_perturb(int(x), 81, pub.epsilon, rng) for x in labels]
    fit = UldpSynthGenerator.server_fit(_c2_reports({0: answers}, pub.epsilon), pub)
    est = np.asarray(fit.frequencies[0])
    assert np.abs(est - truth).max() < 0.06  # about four standard errors at n = 20 000
    assert fit.counts[1] == (0,) * N_COST_BANDS and fit.frequencies[1] == ()


def test_c2_gate_keeps_prior_when_reports_match_it(gen2: UldpSynthGenerator) -> None:
    pub = gen2.public_params()
    slots = {q: _expand(np.round(300 * pub.prior_reports(g))) for q, g in ((0, 0), (2, 1), (3, 2))}
    fit = UldpSynthGenerator.server_fit(_c2_reports(slots, pub.epsilon), pub)
    assert not fit.gate_rejected and fit.gate_p_value > GATE_ALPHA
    assert fit.od_shares is None and fit.departure_shares == prior_params().departure_shares
    assert fit.band_shares == tuple(pub.band_prior)


def test_c2_gate_rejects_a_clearly_different_od_table(gen2: UldpSynthGenerator) -> None:
    pub = gen2.public_params()
    rng = np.random.default_rng(15)
    cell = 4 * 9 + 4  # everyone travels inside the central zone
    answers = [grr_perturb(cell, 81, pub.epsilon, rng) for _ in range(300)]
    fit = UldpSynthGenerator.server_fit(_c2_reports({1: answers}, pub.epsilon), pub)
    assert fit.gate_rejected and fit.gate_p_value < 1e-3
    od = np.asarray(fit.od_shares)
    assert od.sum() == pytest.approx(1.0) and od.min() >= 0 and int(od.argmax()) == cell
    assert not od[~pub.od_support].any()  # zero on the cells the map cannot host
    assert fit.departure_shares == prior_params().departure_shares  # no period reports
    with pytest.raises(ValueError, match="category index"):
        UldpSynthGenerator.server_fit(_c2_reports({3: [5]}, pub.epsilon), pub)


def test_c2_phone_answers_follow_the_trip_and_default_to_the_prior(
    gen2: UldpSynthGenerator, fixture_network: RoadNetwork
) -> None:
    cell, seqs = _cell_trips(gen2.sim, 2, 16)
    views = [_view("a", i, s, 600.0) for i, s in enumerate(seqs)]
    strong = UldpSynthGenerator(fixture_network, epsilon=8.0, **C2_FAST).public_params()  # type: ignore[arg-type]
    rng = np.random.default_rng(17)
    for question, truth in ((0, cell), (1, cell), (3, AM_PEAK)):
        got = [UldpSynthGenerator.encode_user(views, strong, question, rng) for _ in range(200)]
        assert all(r.module == "c2" and r.question == question for r in got)
        assert [r.answer[0] for r in got].count(float(truth)) / 200 > 0.9
    pub = gen2.public_params()
    unknown = [TrajectoryView(sequence=(10**12,), user_id="x")]  # not on the map: default
    for no_trip in ((), unknown):
        report = UldpSynthGenerator.encode_user(no_trip, pub, 2, rng)
        assert report.epsilon == pub.epsilon and 0 <= report.answer[0] < N_COST_BANDS


def _c2_key(report: UserReport) -> tuple[int, float]:
    """Bin by question group, so the two OD-cell slots pool their draws."""
    return C2_QUESTION_GROUPS[report.question], report.answer[0]


def test_c2_privacy_tests_1_to_4(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    roster = ("u0", "u1", "u2", "u3")  # u3 never has a trip
    train_a = _users(sim, 3, [WALK, BIKE, CAR], seed=4)
    train_b = _users(sim, 3, [CAR, CAR, WALK], seed=5)
    probes = _trips(sim, 3, 6)

    def make() -> UldpSynthGenerator:
        return UldpSynthGenerator(fixture_network, epsilon=1.0, seed=3, **C2_FAST)  # type: ignore[arg-type]

    assert params_unchanged_under_view_swap(make, roster, train_a, train_b)
    assert log_prob_unchanged_under_view_swap(make, roster, train_a, train_b, probes)
    user = [v for v in train_a if v.user_id == "u2"]
    ratio = randomiser_log_ratio(make(), (), user, N_DRAWS, seed=7, key=_c2_key)
    assert 0.3 < ratio <= 1.0 + TOL
    long_seq = tuple(e for s in probes for e in s)
    canary = [_view("u3", 0, long_seq, 1e9), _view("u3", 1, probes[0], 1e-3)]
    ratio = canary_log_ratio(make, roster, train_a, canary, N_DRAWS, seed=8, key=_c2_key)
    assert ratio <= 1.0 + TOL


def test_c2_gate_that_keeps_the_prior_yields_the_shared_prior_arm(
    fixture_network: RoadNetwork,
) -> None:
    gen = UldpSynthGenerator(fixture_network, epsilon=1.0, seed=0, **C2_FAST)  # type: ignore[arg-type]
    gen.set_user_roster([f"u{u}" for u in range(40)])  # no trips: answers follow the prior
    gen.fit([])
    assert not gen.fitted.gate_rejected and sum(map(sum, gen.fitted.counts)) == 40
    assert gen.sim_params() == prior_params()
    prior = UldpPriorGenerator(fixture_network)
    prior.fit([])
    ph = simulator_params_hash(gen.sim, gen.sim_params(), zones_per_side=gen.zones_per_side)
    assert ph == prior.generate(1, seed=0)[0].params_hash


def test_c2_fit_generate_and_score_end_to_end(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    n_users = 80
    cell, seqs = _cell_trips(sim, n_users, 18)
    train = [_view(f"u{u}", 0, seqs[u], 600.0) for u in range(n_users)]
    gen = UldpSynthGenerator(fixture_network, epsilon=8.0, seed=1, **C2_FAST)  # type: ignore[arg-type]
    gen.set_user_roster([f"u{u}" for u in range(n_users + 5)])  # five users without trips
    gen.fit(train)
    fit = gen.fitted
    assert sum(map(sum, fit.counts)) == n_users + 5
    assert fit.gate_rejected and fit.od_shares is not None
    assert int(np.argmax(fit.od_shares)) == cell
    assert int(np.argmax(fit.departure_shares)) == AM_PEAK
    params = gen.sim_params()
    assert params.od_shares == fit.od_shares and params.regimes == REGIME_CATALOGUE
    out = gen.generate(20, seed=11)
    assert len(out) == 20 and all(isinstance(t.payload, TimedRoute) for t in out)
    assert [t.payload for t in out] == [t.payload for t in gen.generate(20, seed=11)]
    assert sum(_cell(sim, t.payload.edge_seq) == cell for t in out) >= 12  # the table dominates
    lp = gen.sequence_log_prob(out[0].payload.edge_seq)
    assert math.isfinite(lp) and lp == sim.log_prob(params, out[0].payload.edge_seq)


# === Module C1: behavioural moments ===========================================================

C1_FAST = {"module": "c1", "moment_trips": 40, "band_origins": 20, "gate_draws": 2000}


@pytest.fixture(scope="module")
def gen1(fixture_network: RoadNetwork) -> UldpSynthGenerator:
    return UldpSynthGenerator(fixture_network, epsilon=2.0, **C1_FAST)  # type: ignore[arg-type]


def _c1_key(report: UserReport) -> tuple[int, int]:
    """Bin a continuous HM report by question and public gate bin."""
    return report.question, c1_bin(report.answer[0], report.epsilon)


def _hm_reports(
    xs: list[float], question: int, eps: float, rng: np.random.Generator
) -> list[UserReport]:
    return [UserReport("c1", question, (hm_perturb(x, eps, rng),), eps) for x in xs]


@pytest.mark.parametrize("eps", [0.5, 2.0, 8.0])
def test_hm_is_unbiased_bounded_and_matches_its_bin_probabilities(eps: float) -> None:
    rng = np.random.default_rng(20)
    xs = np.array([-1.0, -0.3, 0.6, 1.0])
    probs = hm_bin_probs(xs, eps)
    assert np.allclose(probs.sum(axis=1), 1.0)
    for x, p in zip(xs, probs, strict=True):
        ys = np.array([hm_perturb(float(x), eps, rng) for _ in range(4000)])
        assert np.abs(ys).max() <= hm_bound(eps)
        assert abs(ys.mean() - x) < 4 * ys.std() / math.sqrt(len(ys))
        freq = np.bincount([c1_bin(float(y), eps) for y in ys], minlength=C1_BINS) / len(ys)
        assert np.abs(freq - p).max() < 0.03


def test_c1_moment_matching_recovers_parameters_from_synthetic_reports(
    gen1: UldpSynthGenerator,
) -> None:
    pub = gen1.public_params()
    # Exact inversion on the public samples, and clamping to the admissible set.
    assert solve_speed_level(pub, pub.speed_mean(0.5)) == pytest.approx(0.5, rel=1e-6)
    assert solve_decay(pub, pub.length.mean(0.005)) == pytest.approx(0.005, rel=1e-6)
    assert solve_decay(pub, 1.0) == 0.0 and solve_decay(pub, -1.0) == DECAY_MAX_PER_S
    # Reports drawn from the model at level 0.5 through HM: the unbiased mean recovers it.
    rng = np.random.default_rng(21)
    xs = []
    for _ in range(6000):
        r = int(rng.choice(len(pub.speed), p=np.asarray(pub.regime_weights)))
        m = pub.speed[r].moments(0.5)
        xs.append(float(m[int(rng.integers(len(m)))]))
    reports = _hm_reports(xs, 0, pub.epsilon, rng)
    mean = float(np.mean([r.answer[0] for r in reports]))
    assert abs(mean - pub.speed_mean(0.5)) < 0.04  # about three standard errors at eps = 2
    assert 0.35 < solve_speed_level(pub, mean) < 0.7


def test_c1_gate_keeps_prior_on_prior_reports_and_rejects_a_clear_shift(
    gen1: UldpSynthGenerator,
) -> None:
    pub = gen1.public_params()
    rng = np.random.default_rng(22)
    null = [
        *_hm_reports([pub.default_moment(0, rng) for _ in range(150)], 0, pub.epsilon, rng),
        *_hm_reports([pub.default_moment(1, rng) for _ in range(150)], 1, pub.epsilon, rng),
    ]
    kept = c1_server_fit(null, pub)
    assert not kept.gate_rejected and kept.gate_p_value > GATE_ALPHA
    assert (kept.speed_level, kept.decay_per_s) == (1.0, 0.0)
    fast = [*null[150:], *_hm_reports([0.6] * 100, 0, pub.epsilon, rng)]  # much faster trips
    fit = c1_server_fit(fast, pub)
    assert fit.gate_rejected and fit.speed_level > 1.0
    assert sum(fit.counts[0]) == 100 and sum(fit.counts[1]) == 150


def test_c1_privacy_tests_1_to_4(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    roster = ("u0", "u1", "u2", "u3")  # u3 never has a trip
    train_a = _users(sim, 3, [WALK, BIKE, CAR], seed=4)
    train_b = _users(sim, 3, [CAR, CAR, WALK], seed=5)
    probes = _trips(sim, 3, 6)

    def make() -> UldpSynthGenerator:
        return UldpSynthGenerator(fixture_network, epsilon=1.0, seed=3, **C1_FAST)  # type: ignore[arg-type]

    assert params_unchanged_under_view_swap(make, roster, train_a, train_b)
    assert log_prob_unchanged_under_view_swap(make, roster, train_a, train_b, probes)
    walker = [v for v in train_a if v.user_id == "u0"]
    ratio = randomiser_log_ratio(make(), (), walker, N_DRAWS, seed=7, key=_c1_key)
    assert 0.1 < ratio <= 1.0 + TOL
    long_seq = tuple(e for s in probes for e in s)
    canary = [_view("u3", 0, long_seq, 1e9), _view("u3", 1, probes[0], 1e-3)]
    ratio = canary_log_ratio(make, roster, train_a, canary, N_DRAWS, seed=8, key=_c1_key)
    assert ratio <= 1.0 + TOL


def test_c1_gate_that_keeps_the_prior_yields_the_shared_prior_arm(
    fixture_network: RoadNetwork,
) -> None:
    gen = UldpSynthGenerator(fixture_network, epsilon=2.0, seed=0, **C1_FAST)  # type: ignore[arg-type]
    gen.set_user_roster([f"u{u}" for u in range(40)])  # no trips: moments follow the prior
    gen.fit([])
    assert not gen.fitted.gate_rejected and sum(map(sum, gen.fitted.counts)) == 40
    assert gen.sim_params() == prior_params()
    prior = UldpPriorGenerator(fixture_network)
    prior.fit([])
    ph = simulator_params_hash(gen.sim, gen.sim_params(), zones_per_side=gen.zones_per_side)
    assert ph == prior.generate(1, seed=0)[0].params_hash


def test_c1_fit_generate_and_score_end_to_end(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    n_users = 80
    seqs = sorted(_trips(sim, 400, 23), key=sim.route_time_s)[:n_users]  # the shortest trips
    # Ten times slower than free flow (log ratio -2.3, scaled about -0.77).
    train = [_view(f"u{u}", 0, s, 10.0 * sim.route_time_s(s)) for u, s in enumerate(seqs)]
    gen = UldpSynthGenerator(fixture_network, epsilon=8.0, seed=1, **C1_FAST)  # type: ignore[arg-type]
    gen.set_user_roster([f"u{u}" for u in range(n_users + 5)])  # five users without trips
    gen.fit(train)
    fit = gen.fitted
    assert sum(map(sum, fit.counts)) == n_users + 5
    assert fit.gate_rejected and fit.speed_level < 1.0 and fit.decay_per_s > 0.0
    params = gen.sim_params()
    assert set(params.period_speed_factors) == {fit.speed_level}
    assert {r.distance_decay_per_s for r in params.regimes} == {fit.decay_per_s}
    assert params.regime_weights == prior_params().regime_weights  # C1 alone (finding F6)
    out = gen.generate(10, seed=11)
    assert len(out) == 10 and all(isinstance(t.payload, TimedRoute) for t in out)
    assert [t.payload for t in out] == [t.payload for t in gen.generate(10, seed=11)]
    lp = gen.sequence_log_prob(out[0].payload.edge_seq)
    assert math.isfinite(lp) and lp == sim.log_prob(params, out[0].payload.edge_seq)


# === Composite arm: the three modules on public thirds of the roster =========================

ALL_FAST = {
    "module": "all",
    "confusion_trips": 40,
    "moment_trips": 40,
    "band_origins": 20,
    "gate_draws": 2000,
}


def _make_all(network: RoadNetwork, epsilon: float, seed: int) -> UldpSynthGenerator:
    return UldpSynthGenerator(network, epsilon=epsilon, seed=seed, **ALL_FAST)  # type: ignore[arg-type]


def _assigned(
    gen: UldpSynthGenerator, roster: tuple[str, ...], train: list[TrajectoryView]
) -> dict[str, tuple[str, int]]:
    """(module, question) of every roster user's single report."""
    gen.set_user_roster(roster)
    reports = gen.collect_reports(train)
    assert len(reports) == len(roster)  # every user reports exactly once
    return {u: (r.module, r.question) for u, r in zip(roster, reports, strict=True)}


def _all_key(gen: UldpSynthGenerator):  # type: ignore[no-untyped-def]
    """Bin by module and question group; C1's continuous reports by public gate bin."""
    slots = gen.public_params().slots

    def key(r: UserReport) -> tuple[str, int, float]:
        module, local = slots[r.question]
        if module == "c1":
            return module, local, float(c1_bin(r.answer[0], r.epsilon))
        if module == "c2":
            return module, C2_QUESTION_GROUPS[local], r.answer[0]
        return module, 0, r.answer[0]

    return key


def test_composite_thirds_are_public_and_question_counts_follow_n_eps2(
    fixture_network: RoadNetwork,
) -> None:
    # Thirds of 7 and 17 users (n = 20, 50) at epsilon 0.5, 2, 8: reports x eps^2 / 16.
    counts = [question_count(n, e, 3) for n in (7, 17) for e in (0.5, 2.0, 8.0)]
    assert counts == [1, 1, 3, 1, 3, 3]
    assert composite_layout(20, 2.0)[:2] == ((7, 7, 6), (("speed",), ("od",), ("regime",)))
    full = (("speed", "length"), ("od", "band", "period"), ("regime",))
    assert composite_layout(50, 2.0)[1] == full
    sim = PublicSimulator(fixture_network)
    roster = tuple(f"u{u}" for u in range(30))
    train_a = _users(sim, 30, [WALK] * 30, seed=4)
    train_b = _users(sim, 30, [CAR] * 30, seed=5)
    a = _assigned(_make_all(fixture_network, 2.0, 3), roster, train_a)
    b = _assigned(_make_all(fixture_network, 2.0, 3), roster[::-1], train_b)
    c = _assigned(_make_all(fixture_network, 2.0, 4), roster, train_a)
    assert a == b  # other data, other roster order: same thirds, same questions
    thirds = {m: {u for u in roster if a[u][0] == m} for m in ("c1", "c2", "c3")}
    assert [len(s) for s in thirds.values()] == [10, 10, 10]
    assert thirds["c1"] != {u for u in roster if c[u][0] == "c1"}  # a new seed redraws


def test_composite_privacy_tests_1_to_4(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    roster = ("u0", "u1", "u2", "u3")  # u3 never has a trip
    train_a = _users(sim, 3, [WALK, BIKE, CAR], seed=4)
    train_b = _users(sim, 3, [CAR, CAR, WALK], seed=5)
    probes = _trips(sim, 3, 6)

    def make() -> UldpSynthGenerator:
        return _make_all(fixture_network, 1.0, 3)

    assert params_unchanged_under_view_swap(make, roster, train_a, train_b)
    assert log_prob_unchanged_under_view_swap(make, roster, train_a, train_b, probes)
    gen = make()
    gen.set_user_roster(roster)
    key = _all_key(gen)
    user = [v for v in train_a if v.user_id == "u2"]
    ratio = randomiser_log_ratio(gen, (), user, N_DRAWS, seed=7, key=key)
    assert 0.1 < ratio <= 1.0 + TOL
    long_seq = tuple(e for s in probes for e in s)
    canary = [_view("u3", 0, long_seq, 1e9), _view("u3", 1, probes[0], 1e-3)]
    assert canary_log_ratio(make, roster, train_a, canary, N_DRAWS, seed=8, key=key) <= 1.0 + TOL


def test_composite_gates_that_keep_the_prior_yield_the_shared_prior_arm(
    fixture_network: RoadNetwork,
) -> None:
    gen = _make_all(fixture_network, 2.0, 0)
    gen.set_user_roster([f"u{u}" for u in range(40)])  # no trips: every answer is the prior's
    gen.fit([])
    fit = gen.fitted
    assert not (fit.c1.gate_rejected or fit.c2.gate_rejected or fit.c3.gate_rejected)
    assert gen.sim_params() == prior_params()
    prior = UldpPriorGenerator(fixture_network)
    prior.fit([])
    ph = simulator_params_hash(gen.sim, gen.sim_params(), zones_per_side=gen.zones_per_side)
    assert ph == prior.generate(1, seed=0)[0].params_hash


def test_composite_fit_generate_and_facts_end_to_end(fixture_network: RoadNetwork) -> None:
    sim = PublicSimulator(fixture_network)
    n_users = 80
    seqs = sorted(_trips(sim, 400, 23), key=sim.route_time_s)[:n_users]  # the shortest trips
    train = [_view(f"u{u}", 0, s, 10.0 * sim.route_time_s(s)) for u, s in enumerate(seqs)]
    gen = _make_all(fixture_network, 8.0, 1)
    gen.set_user_roster([f"u{u}" for u in range(n_users + 5)])  # five users without trips
    gen.fit(train)
    fit, pub = gen.fitted, gen.public_params()
    assert fit.module_users == (29, 28, 28) and [len(q) for q in fit.questions] == [2, 3, 1]
    assert fit.c3.gate_rejected and fit.c1.gate_rejected
    assert fit.c3.regime_weights != prior_params().regime_weights
    # C1's moment matching runs on C3's fitted weights; its gate's null stays the prior's.
    target = min(max(fit.c1.means[0], -1.0), 1.0)
    on_c3 = replace(pub.c1, regime_weights=fit.c3.regime_weights)
    assert fit.c1.speed_level == solve_speed_level(on_c3, target)
    params = gen.sim_params()
    assert params.regime_weights == fit.c3.regime_weights
    assert params.departure_shares == fit.c2.departure_shares
    assert set(params.period_speed_factors) == {fit.c1.speed_level}
    assert {r.distance_decay_per_s for r in params.regimes} == {fit.c1.decay_per_s}
    out = gen.generate(10, seed=11)
    assert len(out) == 10 and all(isinstance(t.payload, TimedRoute) for t in out)
    assert [t.payload for t in out] == [t.payload for t in gen.generate(10, seed=11)]
    lp = gen.sequence_log_prob(out[0].payload.edge_seq)
    assert math.isfinite(lp) and lp == sim.log_prob(params, out[0].payload.edge_seq)
    facts = json.loads(json.dumps(_generator_facts(gen, 1)["uldp_fit"]))
    mods = facts["modules"]
    assert facts["roster_size"] == n_users + 5 and mods["c2"]["n_questions"] == 3
    assert [mods[m]["reports"] for m in ("c1", "c2", "c3")] == [29, 28, 28]
    assert mods["c3"]["histogram"]["regime"] == list(fit.c3.counts)
    assert sum(map(sum, mods["c1"]["histogram"].values())) == 29
    assert mods["c1"]["gate_rejected"] and mods["c1"]["gate_p_value"] < GATE_ALPHA


def test_composite_rule_n_fixes_the_questions_across_roster_sizes(
    fixture_network: RoadNetwork,
) -> None:
    # Target (20 users) and a shadow (50 users) under one rule_n ask the same questions.
    full = (("speed", "length"), ("od", "band", "period"), ("regime",))
    asked = {}
    for rule_n in (None, 50):
        for n in (20, 50):
            gen = UldpSynthGenerator(
                fixture_network,
                epsilon=2.0,
                seed=0,
                rule_n=rule_n,
                **ALL_FAST,  # type: ignore[arg-type]
            )
            gen.set_user_roster([f"u{u}" for u in range(n)])
            gen.fit([])
            facts = json.loads(json.dumps(gen.fit_facts()))
            assert facts["rule_n"] == rule_n and facts["roster_size"] == n
            assert facts["question_count_source"] == ("roster" if rule_n is None else "rule_n")
            assert facts["question_counts"] == {
                m: len(q) for m, q in zip(("c1", "c2", "c3"), gen.fitted.questions, strict=True)
            }
            asked[rule_n, n] = (gen.fitted.questions, gen.public_params().slots)
    assert asked[50, 20] == asked[50, 50] and asked[50, 20][0] == full
    assert asked[None, 20][0] != asked[None, 50][0]  # without rule_n the roster decides
    with pytest.raises(ValueError, match="rule_n"):
        UldpSynthGenerator(fixture_network, epsilon=2.0, rule_n=0)


# === Review notes E0: gate null, report ranges, HM ratio bound, empty destinations ============


def test_c3_gate_rarely_rejects_trips_of_the_prior_arm_itself(
    fixture_network: RoadNetwork,
) -> None:
    """Type-I rate: M is simulated under exactly prior_params(), the uldp_prior arm's law."""
    prior = UldpPriorGenerator(fixture_network)
    prior.fit([])
    n_users, reps = 60, 20
    roster = [f"u{u}" for u in range(n_users)]
    rejections = 0
    for rep in range(reps):
        trips = [t.payload for t in prior.generate(n_users, seed=100 + rep)]
        train = [
            _view(f"u{u}", 0, r.edge_seq, r.visits[-1].t_exit - r.visits[0].t_enter)
            for u, r in enumerate(trips)
        ]
        gen = UldpSynthGenerator(fixture_network, epsilon=2.0, seed=rep, **FAST)  # type: ignore[arg-type]
        gen.set_user_roster(roster)
        gen.fit(train)
        rejections += gen.fitted.gate_rejected
    assert rejections <= 4  # alpha = 0.05 expects 1 in 20; P(Binomial(20, 0.05) >= 5) < 0.003


def test_report_space_bounds_every_question_by_its_own_range(
    fixture_network: RoadNetwork,
) -> None:
    gen = _make_all(fixture_network, epsilon=1.0, seed=0)
    gen.set_user_roster([f"u{u}" for u in range(30)])
    pub = gen.public_params()
    space = gen.report_space(pub)
    b = hm_bound(1.0)
    assert space.high == 80.0 and b < 50.0  # the old shared range let 50 through on C1
    for q, (module, local) in enumerate(pub.slots):
        k = {"c1": None, "c2": pub.c2.k(C2_QUESTION_GROUPS[local]), "c3": 3}[module]
        lo, hi = (-b, b) if k is None else (0.0, float(k - 1))
        assert space.answer_range(q) == (lo, hi)
        validate_report(UserReport(module, q, (hi,), 1.0), space)
        for bad in (hi + 1.0, lo - 1.0):
            with pytest.raises(ValueError, match="outside"):
                validate_report(UserReport(module, q, (bad,), 1.0), space)
    c2 = UldpSynthGenerator(fixture_network, epsilon=1.0, **C2_FAST)  # type: ignore[arg-type]
    c2_space = c2.report_space(c2.public_params())
    assert [c2_space.answer_range(q)[1] for q in range(4)] == [80.0, 80.0, 5.0, 4.0]
    with pytest.raises(ValueError, match="entries"):
        ReportSpace(("x",), 2, 1, 0.0, 1.0, None, ((0.0, 1.0),))


@pytest.mark.parametrize("eps", [0.3, 1.0, 2.0, 8.0])
def test_hm_output_probabilities_obey_the_epsilon_ratio_bound(eps: float) -> None:
    dens_in, dens_out = pm_density(eps)
    c = (math.exp(eps / 2) + 1) / (math.exp(eps / 2) - 1)
    assert dens_in / dens_out == pytest.approx(math.exp(eps))  # PM density ratio
    assert dens_in * (c - 1) + dens_out * (c + 1) == pytest.approx(1.0)  # PM integrates to one
    edges = np.linspace(-hm_bound(eps), hm_bound(eps), 401)  # a fine partition of the output
    probs = hm_bin_probs(np.linspace(-1.0, 1.0, 41), eps, edges)
    assert np.allclose(probs.sum(axis=1), 1.0)
    positive = probs > 0
    assert (positive == positive[0]).all()  # every input reaches the same bins
    cols = probs[:, positive[0]]
    ratio = cols.max(axis=0) / cols.min(axis=0)  # worst pair of inputs, per bin
    assert ratio.max() <= math.exp(eps) * (1 + 1e-9)


def test_length_dest_weights_survive_an_origin_without_destinations() -> None:
    mass = np.array([1.0, 0.0, 0.0])
    costs = np.array([[0.0, np.inf, np.inf], [np.inf, 0.0, 30.0]], dtype=np.float32)
    moments = np.array([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float32)
    sample = LengthSample(np.array([0, 1]), costs, moments, mass)
    for decay in (0.0, 0.01):
        assert not sample.dest_weights(0, decay).any()  # the only massive node is the origin
    assert sample.dest_weights(1, 0.0) == pytest.approx([1.0, 0.0, 0.0])
    assert not sample.dest_weights(1, 0.01).any()  # with decay the massive node is unreachable
    assert list(sample.hosting()) == [1]
    assert sample.mean(0.0) == pytest.approx(0.5) and sample.mean(0.01) == 0.0
