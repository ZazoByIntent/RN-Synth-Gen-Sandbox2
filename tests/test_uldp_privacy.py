"""ULDP P4 + P5: phone/server split, privacy tests 1-4 with positive controls, LiRA wiring.

Fixture-only. A toy user-level module (k = 4 randomized response on a clipped bucket)
passes the four tests of docs/NACRT_ULDP_SINTEZA.md §6.2; each test also runs against a
deliberately leaky module that it must catch.
"""

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import trajguard.experiments.orchestrator as orch
from test_orchestrator import base_config, beijing_maps_dir, mia_config, write_config
from trajguard.attacks.membership import MembershipInferenceAttack
from trajguard.datamodel import SyntheticTrajectory
from trajguard.privacy.ldp import (
    UserBudget,
    grr_estimate,
    grr_output_prob,
    grr_perturb,
    grr_probabilities,
)
from trajguard.representation import TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator
from trajguard.synthesis.uldp_arms import UldpOracleGenerator, UldpPriorGenerator
from trajguard.synthesis.uldp_base import (
    ReportSpace,
    UldpGenerator,
    UserReport,
    canary_log_ratio,
    log_prob_unchanged_under_view_swap,
    params_unchanged_under_view_swap,
    randomiser_log_ratio,
)

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here

K = 4
EPS = 1.0
TOL = 0.25  # about five standard errors of the log-ratio at 10 000 draws
N_DRAWS = 10_000


def _bucket(views: Sequence[TrajectoryView], question: int) -> int:
    """The toy statistic, clipped to the public range; an empty user gets the default 0."""
    if not views:
        return 0
    if question == 0:
        return min(len(views), K - 1)
    return min(len(views[0].as_sequence()) // 3, K - 1)


class _Toy(UldpGenerator):
    """Honest toy module: a public draw picks one of two questions, GRR answers it."""

    def __init__(self, epsilon: float = EPS, seed: int = 0) -> None:
        self.epsilon = epsilon
        self.seed = seed

    def public_params(self) -> dict[str, float]:
        return {"epsilon": self.epsilon}

    def report_space(self, public: Any) -> ReportSpace:
        return ReportSpace(("toy",), 2, 1, 0.0, float(K - 1))

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        q = int(rng.integers(2))  # the public draw comes first and reads no data
        answer = grr_perturb(_bucket(user_views, q), K, public["epsilon"], rng)
        return UserReport("toy", q, (float(answer),), public["epsilon"])

    @staticmethod
    def server_fit(reports: Sequence[UserReport], public: Any) -> Any:
        out = []
        for q in range(2):
            counts = np.bincount(
                [int(r.answer[0]) for r in reports if r.question == q], minlength=K
            )
            n = int(counts.sum())
            est = grr_estimate(counts, n, public["epsilon"]) if n else np.ones(K)
            out.append(tuple(float(x) for x in est))
        return tuple(out)

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        freqs = self.fitted[1]
        b = min(len(edge_seq) // 3, K - 1)
        return math.log(max(freqs[b] / max(sum(freqs), 1e-9), 1e-9))

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        return []


# Side channels of the leaky controls: module-level, since both sides are static.
_STASHED_EDGES: list[int] = []
_SEEN_EDGES: set[int] = set()


class _LeakyServer(_Toy):
    """Control for test 1: the server adds a statistic the phones smuggled out of the views."""

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        _STASHED_EDGES.append(sum(len(v.as_sequence()) for v in user_views))
        return _Toy.encode_user(user_views, public, rng)

    @staticmethod
    def server_fit(reports: Sequence[UserReport], public: Any) -> Any:
        return (*_Toy.server_fit(reports, public), (float(sum(_STASHED_EDGES)),))


class _OverBudget(_Toy):
    """Control for test 2: answers at 3ε while declaring ε."""

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        q = int(rng.integers(2))
        answer = grr_perturb(_bucket(user_views, q), K, 3 * public["epsilon"], rng)
        return UserReport("toy", q, (float(answer),), public["epsilon"])


class _Unclipped(_Toy):
    """Control for test 3: sends the raw trip length, unbounded by the public range."""

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        raw = float(len(user_views[0].as_sequence())) if user_views else 0.0
        return UserReport("toy", 0, (raw,), public["epsilon"])


class _Familiar(_Toy):
    """Control for test 4: a "familiarity" bonus for links seen in the training views."""

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        _SEEN_EDGES.update(e for v in user_views for e in v.as_sequence())
        return _Toy.encode_user(user_views, public, rng)

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        familiar = sum(e in _SEEN_EDGES for e in edge_seq) / max(len(edge_seq), 1)
        return super().sequence_log_prob(edge_seq) + familiar


def _view(seq: Sequence[int], user: str) -> TrajectoryView:
    return TrajectoryView(sequence=tuple(seq), user_id=user)


ROSTER = ("a", "b", "c")  # c never has a trip and sends the public default
TRAIN_A = [_view((1, 2, 3), "a"), _view((4, 5, 6), "b")]
TRAIN_B = [
    _view(tuple(range(100, 112)), "a"),
    _view((200, 201), "a"),
    _view((300,), "b"),
]
PROBES = [(100, 101, 102), (1, 2, 3, 4, 5, 6), (300,)]


@pytest.fixture(autouse=True)
def _clear_side_channels() -> None:
    _STASHED_EDGES.clear()
    _SEEN_EDGES.clear()


# --- LDP building blocks ----------------------------------------------------------------


def test_grr_exact_probabilities() -> None:
    p, q = grr_probabilities(K, EPS)
    assert p + (K - 1) * q == pytest.approx(1.0)
    assert math.log(p / q) == pytest.approx(EPS)
    assert sum(grr_output_prob(o, 2, K, EPS) for o in range(K)) == pytest.approx(1.0)
    assert grr_output_prob(2, 2, K, EPS) == p and grr_output_prob(0, 2, K, EPS) == q
    with pytest.raises(ValueError):
        grr_output_prob(K, 0, K, EPS)


def test_user_budget_refuses_overspend() -> None:
    budget = UserBudget(1.0)
    for _ in range(3):
        budget.spend("u", 1.0 / 3)
    assert budget.spent("u") == pytest.approx(1.0) and budget.spent("v") == 0.0
    with pytest.raises(ValueError, match="user-level budget"):
        budget.spend("u", 0.01)
    assert budget.max_spent() == pytest.approx(1.0)


# --- P4: the phone/server contract ------------------------------------------------------


def test_fit_requires_roster_and_reports_once_per_user() -> None:
    gen = _Toy()
    with pytest.raises(RuntimeError, match="roster"):
        gen.fit(TRAIN_A)
    gen.set_user_roster(ROSTER)
    reports = gen.collect_reports(TRAIN_A)
    assert len(reports) == len(ROSTER)  # c, without trips, still reports
    assert reports == gen.collect_reports(TRAIN_A)  # deterministic in the seed
    gen.fit(TRAIN_A)
    assert gen.fitted is not None
    with pytest.raises(ValueError, match="not in the user roster"):
        gen.fit([*TRAIN_A, _view((7,), "stranger")])


def test_subclass_cannot_bypass_the_split() -> None:
    with pytest.raises(TypeError, match="must not override"):

        class _OwnFit(_Toy):
            def fit(self, train: Sequence[TrajectoryView]) -> None:
                pass

    with pytest.raises(TypeError, match="staticmethod"):

        class _InstanceEncoder(_Toy):
            def encode_user(  # type: ignore[override]
                self, user_views: Any, public: Any, rng: np.random.Generator
            ) -> UserReport:
                raise AssertionError


def test_overspending_report_is_refused() -> None:
    class _Greedy(_Toy):
        @staticmethod
        def encode_user(
            user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
        ) -> UserReport:
            return UserReport("toy", 0, (0.0,), 2 * public["epsilon"])

    gen = _Greedy()
    gen.set_user_roster(ROSTER)
    with pytest.raises(ValueError, match="user-level budget"):
        gen.fit(TRAIN_A)


# --- P5: the four privacy tests of §6.2, each with its positive control --------------------


def test_1_params_depend_on_reports_only() -> None:
    assert params_unchanged_under_view_swap(_Toy, ROSTER, TRAIN_A, TRAIN_B)
    assert not params_unchanged_under_view_swap(_LeakyServer, ROSTER, TRAIN_A, TRAIN_B)


def test_2_randomiser_audit_stays_within_epsilon() -> None:
    empty: list[TrajectoryView] = []
    extreme = [_view(tuple(range(30)), "u")] * 5  # bucket 3 in both questions
    honest = randomiser_log_ratio(_Toy(), empty, extreme, N_DRAWS, seed=1)
    assert EPS - TOL < honest <= EPS + TOL  # the GRR bound is tight on the extreme pair
    leaky = randomiser_log_ratio(_OverBudget(), empty, extreme, N_DRAWS, seed=1)
    assert leaky > EPS + TOL


def test_3_canary_with_extreme_trip() -> None:
    canary = [_view(tuple(range(5000)), "c")]  # c is enrolled and otherwise trip-less
    assert canary_log_ratio(_Toy, ROSTER, TRAIN_A, canary, N_DRAWS, seed=2) <= EPS + TOL
    with pytest.raises(ValueError, match="outside"):
        canary_log_ratio(_Unclipped, ROSTER, TRAIN_A, canary, N_DRAWS, seed=2)


def test_4_log_prob_reads_only_params() -> None:
    assert log_prob_unchanged_under_view_swap(_Toy, ROSTER, TRAIN_A, TRAIN_B, PROBES)
    assert not log_prob_unchanged_under_view_swap(_Familiar, ROSTER, TRAIN_A, TRAIN_B, PROBES)


# --- P5: LiRA shadows under the candidates' own user_id ------------------------------------


def _lira_inputs() -> tuple[list[tuple[int, ...]], list[tuple[int, bool]], list[str]]:
    pool = [(1, 2, 3), (4, 5, 6, 7), (8, 9), (1, 2, 3, 4, 5, 6), (10, 11, 12)]
    users = ["s1", "s2", "m1", "m1", "n1"]
    candidates = [(2, True), (3, True), (4, False)]
    return pool, candidates, users


def test_lira_shadows_of_a_user_level_generator_get_user_ids() -> None:
    pool, candidates, users = _lira_inputs()
    target = _Toy()
    target.set_user_roster(["m1"])
    target.fit([_view(pool[2], "m1"), _view(pool[3], "m1")])
    attack = MembershipInferenceAttack(n_shadow=4, shadow_factory=lambda k: _Toy(seed=k))
    result = attack.run(target, (pool, candidates, users))
    assert len(result.predictions) == len(candidates)
    with pytest.raises(ValueError, match="user roster"):
        attack.run(target, (pool, candidates))


def test_lira_input_of_other_generators_is_unchanged() -> None:
    pool, candidates, users = _lira_inputs()
    fits: list[list[TrajectoryView]] = []

    class _Spy(MarkovGenerator):
        def fit(self, train: Sequence[TrajectoryView]) -> None:
            fits.append(list(train))
            super().fit(train)

    target = MarkovGenerator()
    target.fit([TrajectoryView(sequence=pool[i]) for i in (2, 3)])
    scores = []
    for aux in ((pool, candidates), (pool, candidates, users)):
        attack = MembershipInferenceAttack(n_shadow=4, shadow_factory=lambda _k: _Spy())
        scores.append(attack.run(target, aux).scores)
    assert scores[0] == scores[1]
    assert all(v.user_id == "" and v.split is None for fit in fits for v in fit)


# --- run.json epsilon facts and the reused timed-utility target ---------------------------


def test_generator_facts_record_user_level_epsilon() -> None:
    gen = _Toy(epsilon=2.0)
    assert orch._generator_facts(gen, max_trips=5) == {"privacy_unit": "user", "user_epsilon": 2.0}

    class _PerTrip:
        epsilon = 0.5

    assert orch._generator_facts(_PerTrip(), max_trips=4) == {
        "privacy_unit": "trip",
        "trip_epsilon": 0.5,
        "max_trips_per_user": 4,
        "user_epsilon_bound": 2.0,
    }
    assert orch._generator_facts(UldpPriorGenerator.__new__(UldpPriorGenerator), 3) == {}


def _timed_rows(out: Path) -> list[tuple[str, str, str]]:
    rows = list(csv.DictReader((out / "results.csv").open()))
    return [
        (r["target_ref"], r["metric"], r["value"])
        for r in rows
        if r["family"] == "utility" and r["scope"] == "synthetic"
    ]


def test_timed_utility_reuses_the_membership_target(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With MIA on, the target is fitted once; the timed rows equal a timed-only run."""
    target_fits: list[str] = []
    fit = UldpOracleGenerator.fit

    def spy(self: UldpOracleGenerator, train: Sequence[TrajectoryView]) -> None:
        if all(v.clean is not None for v in train):  # shadows fit on bare sequences
            target_fits.append("target")
        fit(self, train)

    monkeypatch.setattr(UldpOracleGenerator, "fit", spy)
    outs = []
    for name, with_mia in (("mia", True), ("plain", False)):
        root = tmp_path / name
        root.mkdir()
        cfg = (
            mia_config(root, beijing_maps_dir) if with_mia else base_config(root, beijing_maps_dir)
        )
        cfg["synthetic_generators"] = [{"id": "uldp_prior"}, {"id": "uldp_oracle"}]
        cfg["split"]["fractions"] = {"train": 0.5, "test": 0.5}
        cfg["metrics"]["timed_utility"] = True
        target_fits.clear()
        orch.run(write_config(root, cfg))
        assert target_fits == ["target"]  # fitted once, by whichever path runs first
        outs.append(root / "out")
    assert _timed_rows(outs[0]) and _timed_rows(outs[0]) == _timed_rows(outs[1])
    arms = json.loads((outs[0] / "run.json").read_text())["arms"]
    assert arms["synthetic:uldp_oracle"]["timed_utility"]["n_synthetic"] > 0
