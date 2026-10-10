"""User-level LDP plumbing: the phone/server split and its privacy audits (ULDP P4 + P5).

A user-level mechanism (docs/NACRT_ULDP_SINTEZA.md §4.2, §4.6, §6.2) is a
:class:`UldpGenerator`. Its ``fit`` is fixed here and never overridden:

1. ``public_params()`` builds everything public (map products, catalogue, number of
   questions, epsilon) from the map and the config only; it takes no view.
2. For every user of the training roster, in roster order, the **phone side**
   ``encode_user(user_views, public, rng)`` runs on that user's views alone (an empty
   tuple for a user without a matched trip, who must answer from a public default) with
   an independent per-user generator, and returns exactly one fixed-shape
   :class:`UserReport`. The report is checked against the public ``report_space`` and
   its epsilon is booked in a :class:`~trajguard.privacy.ldp.UserBudget`.
3. The **server side** ``server_fit(reports, public)`` turns the reports into fitted
   parameters; it never sees a view.

``encode_user`` and ``server_fit`` must be static methods (enforced when the subclass
is defined), so neither side can reach the other through instance state. A module of
block D implements: ``public_params``, ``report_space``, ``encode_user`` (static),
``server_fit`` (static), ``generate`` and ``sequence_log_prob`` (both reading only
``self.fitted`` and public objects), and sets ``self.epsilon`` and ``self.seed`` in its
constructor.

The four privacy tests of §6.2 are functions here, so every module runs them in its own
test file: :func:`params_unchanged_under_view_swap` (test 1),
:func:`randomiser_log_ratio` (test 2), :func:`canary_log_ratio` (test 3) and
:func:`log_prob_unchanged_under_view_swap` (test 4).
"""

import math
import pickle
from abc import abstractmethod
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

from trajguard.privacy.ldp import UserBudget
from trajguard.representation import TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator, views_by_user


def require_roster(gen: SyntheticGenerator) -> tuple[str, ...]:
    """The roster of a roster-opt-in generator; raise if ``set_user_roster`` was not called."""
    if gen.user_roster is None:
        raise RuntimeError(
            f"{type(gen).__name__} needs the training user roster (set_user_roster) before "
            "fit; without it users without a matched trip would silently drop out"
        )
    return gen.user_roster


@dataclass(frozen=True, slots=True)
class UserReport:
    """The one fixed-shape report a user's device sends (module, question, answer).

    A categorical answer is stored as its category index. ``epsilon`` is the budget the
    device spent producing it, booked against the user-level budget.
    """

    module: str
    question: int
    answer: tuple[float, ...]
    epsilon: float


@dataclass(frozen=True, slots=True)
class ReportSpace:
    """The public shape every report must have: modules, questions, answer length and range."""

    modules: tuple[str, ...]
    n_questions: int
    answer_len: int
    low: float
    high: float


def validate_report(report: UserReport, space: ReportSpace) -> None:
    """Raise ValueError unless ``report`` lies in the public report space."""
    if not isinstance(report, UserReport):
        raise ValueError(f"encode_user must return a UserReport, got {type(report).__name__}")
    if report.module not in space.modules:
        raise ValueError(f"report module {report.module!r} is not one of {space.modules}")
    if not 0 <= report.question < space.n_questions:
        raise ValueError(f"report question {report.question} outside [0, {space.n_questions})")
    if len(report.answer) != space.answer_len:
        raise ValueError(
            f"report answer has {len(report.answer)} values, the public size is {space.answer_len}"
        )
    for x in report.answer:
        if not (math.isfinite(x) and space.low <= x <= space.high):
            raise ValueError(f"report answer value {x} outside [{space.low}, {space.high}]")


class UldpGenerator(SyntheticGenerator):
    """A user-level pure-ε-LDP generator: one report per training user, server sees reports only."""

    needs_user_roster: ClassVar[bool] = True
    #: The unit epsilon protects; run.json records it as the user-level epsilon.
    privacy_unit: ClassVar[str] = "user"

    epsilon: float
    seed: int
    #: Whatever ``server_fit`` returned; None before fit.
    fitted: Any = None

    _SEALED: ClassVar[tuple[str, ...]] = ("fit", "collect_reports", "fit_from_reports")
    _STATIC: ClassVar[tuple[str, ...]] = ("encode_user", "server_fit")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Refuse a subclass that overrides the fixed fit or makes a side non-static."""
        super().__init_subclass__(**kwargs)
        for name in cls._SEALED:
            if name in cls.__dict__:
                raise TypeError(f"{cls.__name__} must not override UldpGenerator.{name}")
        for name in cls._STATIC:
            if name in cls.__dict__ and not isinstance(cls.__dict__[name], staticmethod):
                raise TypeError(f"{cls.__name__}.{name} must be a staticmethod")

    @abstractmethod
    def public_params(self) -> Any:
        """Everything public, built from the map and config only (never from a view)."""

    @abstractmethod
    def report_space(self, public: Any) -> ReportSpace:
        """The public shape of every report under ``public``."""

    @staticmethod
    @abstractmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, rng: np.random.Generator
    ) -> UserReport:
        """Phone side: one randomised report from one user's views (empty: public default)."""

    @staticmethod
    @abstractmethod
    def server_fit(reports: Sequence[UserReport], public: Any) -> Any:
        """Server side: fitted parameters from the reports alone."""

    @abstractmethod
    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """Log-likelihood of a sequence from ``self.fitted`` and public objects only."""

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Encode every roster user on their own views, then fit the server on the reports."""
        self.fit_from_reports(self.collect_reports(train))

    def collect_reports(self, train: Sequence[TrajectoryView]) -> tuple[UserReport, ...]:
        """Run the phone side once per roster user (independent per-user generators)."""
        roster = require_roster(self)
        public = self.public_params()
        space = self.report_space(public)
        grouped = views_by_user(train, roster)
        budget = UserBudget(self.epsilon)
        children = np.random.SeedSequence(self.seed).spawn(len(roster))
        reports: list[UserReport] = []
        for user, child in zip(roster, children, strict=True):
            report = self.encode_user(tuple(grouped[user]), public, np.random.default_rng(child))
            validate_report(report, space)
            budget.spend(user, report.epsilon)
            reports.append(report)
        return tuple(reports)

    def fit_from_reports(self, reports: Sequence[UserReport]) -> None:
        """Server side only: validate the reports and fit the parameters from them."""
        public = self.public_params()
        space = self.report_space(public)
        for report in reports:
            validate_report(report, space)
            if report.epsilon > self.epsilon + UserBudget.TOLERANCE:
                raise ValueError(f"report spent {report.epsilon:g} > epsilon {self.epsilon:g}")
        self.fitted = self.server_fit(tuple(reports), public)


# --- Privacy tests 1-4 of docs/NACRT_ULDP_SINTEZA.md §6.2 -----------------------------


def _same(a: Any, b: Any) -> bool:
    """Byte-identical pickles: exact equality that also works for numpy contents."""
    return pickle.dumps(a) == pickle.dumps(b)


def _enrolled(make: Callable[[], UldpGenerator], roster: Sequence[str]) -> UldpGenerator:
    gen = make()
    gen.set_user_roster(roster)
    return gen


def params_unchanged_under_view_swap(
    make: Callable[[], UldpGenerator],
    roster: Sequence[str],
    train_a: Sequence[TrajectoryView],
    train_b: Sequence[TrajectoryView],
) -> bool:
    """Test 1: the server's parameters stay the same when the views change but the reports don't.

    Instance A encodes ``train_a`` and fits on its reports; instance B encodes
    ``train_b`` (so any side channel now holds B's views) and fits on A's reports.
    """
    ref = _enrolled(make, roster)
    reports = ref.collect_reports(train_a)
    ref.fit_from_reports(reports)
    expected = pickle.dumps(ref.fitted)
    other = _enrolled(make, roster)
    other.collect_reports(train_b)
    other.fit_from_reports(reports)
    return pickle.dumps(other.fitted) == expected


def log_prob_unchanged_under_view_swap(
    make: Callable[[], UldpGenerator],
    roster: Sequence[str],
    train_a: Sequence[TrajectoryView],
    train_b: Sequence[TrajectoryView],
    probes: Sequence[Sequence[int]],
) -> bool:
    """Test 4: ``sequence_log_prob`` reads only the parameters and public, map-keyed caches.

    The log-probabilities of ``probes`` under the instance fitted on ``train_a`` are
    recorded at once; they must be reproduced by an instance that encoded ``train_b``
    but fitted on A's reports, and by a fresh instance that only saw A's reports.
    """
    ref = _enrolled(make, roster)
    reports = ref.collect_reports(train_a)
    ref.fit_from_reports(reports)
    expected = [ref.sequence_log_prob(p) for p in probes]
    other = _enrolled(make, roster)
    other.collect_reports(train_b)
    other.fit_from_reports(reports)
    swapped = [other.sequence_log_prob(p) for p in probes]
    fresh = _enrolled(make, roster)
    fresh.fit_from_reports(reports)
    blind = [fresh.sequence_log_prob(p) for p in probes]
    return _same(expected, swapped) and _same(expected, blind)


def _report_key(report: UserReport) -> Hashable:
    return (report.module, report.question, report.answer)


def randomiser_log_ratio(
    gen: UldpGenerator,
    views_a: Sequence[TrajectoryView],
    views_b: Sequence[TrajectoryView],
    n_draws: int,
    seed: int,
    key: Callable[[UserReport], Hashable] = _report_key,
    min_count: int = 50,
) -> float:
    """Test 2: largest empirical |log ratio| of report frequencies between two users.

    Each user is encoded ``n_draws`` times with independent generators; outputs are
    binned by ``key`` (identity on the report by default; continuous answers need a
    coarser key). Bins with fewer than ``min_count`` reports over both users are skipped;
    a bin one user never produces while the other produces at least ``min_count`` gives
    ``inf``. A pure ε-LDP encoder stays at or below ε within sampling tolerance.
    """
    public = gen.public_params()
    space = gen.report_space(public)
    counts: list[Counter[Hashable]] = []
    for user_seed, views in enumerate((views_a, views_b)):
        children = np.random.SeedSequence([seed, user_seed]).spawn(n_draws)
        tally: Counter[Hashable] = Counter()
        for child in children:
            report = gen.encode_user(tuple(views), public, np.random.default_rng(child))
            validate_report(report, space)
            tally[key(report)] += 1
        counts.append(tally)
    worst = 0.0
    for b in set(counts[0]) | set(counts[1]):
        ca, cb = counts[0][b], counts[1][b]
        if ca + cb < min_count:
            continue
        if ca == 0 or cb == 0:
            return math.inf
        worst = max(worst, abs(math.log(ca / n_draws) - math.log(cb / n_draws)))
    return worst


def canary_log_ratio(
    make: Callable[[], UldpGenerator],
    roster: Sequence[str],
    train: Sequence[TrajectoryView],
    canary_views: Sequence[TrajectoryView],
    n_draws: int,
    seed: int,
    key: Callable[[UserReport], Hashable] = _report_key,
) -> float:
    """Test 3: a canary user with an extreme trip stays inside the public report space and ε.

    ``canary_views`` (carrying a user of ``roster``) join ``train``; the full fit must
    accept the canary's report (out-of-space answers raise ValueError), and the canary's
    report distribution is compared with that of a user without a trip (the public
    default). Returns the largest empirical |log ratio|, as in test 2.
    """
    gen = _enrolled(make, roster)
    gen.fit([*train, *canary_views])
    return randomiser_log_ratio(gen, canary_views, (), n_draws, seed, key=key)
