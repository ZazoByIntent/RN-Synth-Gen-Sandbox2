"""User-level LDP synthesis on the public simulator (ULDP; docs/NACRT_ULDP_SINTEZA.md §4).

One generator, ``uldp_synth``, whose ``module`` config key selects the calibrating
module. Implemented so far: **C3, the regime vote** (§4.3, ``module: c3``), **C2, the
origin-destination shares** (§4.4, ``module: c2``) and **C1, the behavioural moments**
(§4.5, ``module: c1``), plus **the composite arm** (§4.2, ``module: all``).

Every module's phone answers from ONE usable trip drawn uniformly among the user's
trips (finding F2, a closed decision), not from all of the user's trips as plan §4.3-§4.5
describe: the report then has the law of a single trip, so the server's channels (C3's
confusion matrix, C2's and C1's prior predictions) need no public law of trips per user.

The composite, in one pass:

- **Public side.** A public draw (the generator's seed over the sorted roster, never the
  data; ``UldpGenerator.assign_questions``) cuts the roster into thirds for C1, C2 and
  C3. Each module asks as many of its questions as the public n·ε² rule allows on its
  third (:func:`question_count`, :data:`REPORT_INFO_PER_QUESTION`), at least one. The
  rule's n is the config's ``rule_n`` when given (plan §7.1 point 3: the target generator
  and every LiRA shadow then ask the same questions), otherwise the roster size.
- **Phone.** Every user answers only the assigned module's question, exactly as that
  module alone would, with the whole user-level epsilon (so epsilon per user is unchanged).
- **Server.** Each module's estimator and gate run on its own third. C3 gives the regime
  weights, C2 the OD and departure shares, C1 the speed level and decay, applied equally
  to every regime; C1's moment matching uses C3's fitted weights (its gate's null stays
  the prior's). Each part stays the prior's unless its own gate rejects.

C1, in one pass (Boltzmann-walk variant of §4.5; it runs on its own, finding F6):

- **Public side.** Two numeric questions (:data:`C1_QUESTIONS`): the speed moment, the
  log ratio of the trip's OSM free-flow time to its duration (within the public clip
  ``LOG_RATIO_CLIP``), and the length moment, the log free-flow cost between the trip's
  end nodes (on the frame :data:`LENGTH_FRAME_S`), both scaled to [-1, 1]. Their prior
  predictive distributions come from a public Monte Carlo (prior trips per regime; the
  band origins with their exact destination shares).
- **Phone.** For the publicly drawn question the phone draws ONE usable trip uniformly
  (finding F2; timed and on the map for speed, on the map for length), computes the moment and sends
  it by the hybrid mechanism HM (Wang et al., ICDE 2019) with the whole user-level
  epsilon. A user without a usable trip draws the moment from the prior predictive.
- **Server.** The report mean is unbiased per question. The gate (finding F7) bins the
  reports (:data:`C1_BINS` public bins) and compares them with the bins the prior
  predicts through HM (exact, up to the public Monte Carlo) by the shared Pearson gate.
  Only on rejection does moment matching move two numbers: the speed level (every
  ``SimParams.period_speed_factors`` entry) and the gravity decay
  (``Regime.distance_decay_per_s`` of every regime alike, on free-flow cost), each
  clamped to its admissible set; otherwise the parameters are exactly the prior.

C2, in one pass:

- **Public side.** The shared prior's answer shares for three questions: the OD cell
  (origin zone x destination zone on the 3 x 3 grid over the public map frame, the
  zones of the metric ``od3x3_jsd``; exact under the gravity prior,
  :func:`gravity_od_shares`), the free-flow cost band of the trip's origin-destination
  pair (six bands, :data:`COST_BAND_EDGES_S`; a public Monte Carlo over origins,
  :func:`gravity_band_shares`) and the departure period (the five periods of the timed
  utility metric; the prior's uniform-day shares).
- **Phone.** The public question slot (:data:`C2_QUESTION_GROUPS`, drawn by
  ``collect_reports``) names the question. The phone draws ONE usable trip uniformly
  (finding F2; on the map and timed), computes its answer and sends it by k-ary GRR (k = 81, 6 or
  5; finding F5: GRR, not OLH) with the whole user-level epsilon. A user without a
  usable trip draws the answer from the prior's shares (the public default).
- **Server.** Exact GRR debiasing per question. The gate (finding F7) sums the Pearson
  statistics of the three report histograms against the prior's predicted ones (exact
  for OD and period, up to the public Monte Carlo of the band shares) with the C3
  Monte Carlo p-value and level. Only on rejection does the server solve plan §4.4's
  estimator, T = argmin KL(T || Q) + 1/2 ||A T - t||^2 weighted by V^-1
  (:func:`kl_furness`): T and the gravity prior Q are tables over (OD cell, cost band)
  (:func:`gravity_band_given_od`), A maps T to its OD-cell and band marginals, t are the
  debiased frequencies and V their exact GRR noise covariance (:func:`grr_noise_cov`,
  at the prior's report shares). It is solved by Furness sweeps (iterative proportional
  scaling), one exact block per reported marginal. The OD-cell block scales rows and
  columns at once, because the full OD cell is reported (finding F5), so the plan's
  three-way scaling over rows, columns and bands runs as a two-way scaling over OD cells
  and bands. The band reports thus tilt the OD table; T's OD marginal becomes
  ``SimParams.od_shares``, and T's band marginal is recorded (the simulator has no band
  parameter, so the within-cell band tilt cannot reach it). The departure periods, an
  independent factor of the prior, get the same estimator with one block and become
  ``SimParams.departure_shares``.

C3, in one pass:

- **Public side.** The shared public prior (``public_sim.prior_params``): a catalogue
  of three regimes with cited speeds (``REGIME_CATALOGUE``: walk, bike, motorised) and
  its public prior weights (uniform, plan §4.3), the same one ``uldp_prior`` and
  ``uldp_oracle`` use, so a C3 arm whose gate keeps the prior IS the prior arm; a public
  time model (log-normal around each regime's jitter-free route time, spread
  :func:`time_log_sigma`, the phone's observation model) and the **confusion matrix** M,
  M[i, j] = expected posterior of regime j for a trip the public prior
  (``prior_params()``, jitter-free times) draws under regime i. M is simulated once on
  the public graph with a public seed (never from training trips, §6.3) and cached per map.
- **Phone.** Among the user's usable trips (edges known on the map, positive duration)
  the phone draws ONE uniformly (finding F2, so M needs no law of trips per user),
  computes the posterior over regimes of that trip under the public simulator's regimes
  and time model (the regime's jitter-free time on the trip's own route,
  ``PublicSimulator.route_time_s``) and draws one label from it. A user without a usable
  trip draws the label from the public prior predictive distribution M^T pi0 instead
  (the public default). The label goes out by k-ary GRR
  (k = 3) with the whole user-level epsilon; drawing it is local randomness and spends
  nothing. Only the GRR output is in the report.
- **Server.** Exact GRR debiasing gives the label frequencies. The gate (finding F7)
  compares the raw report histogram with the histogram the prior predicts through M and
  GRR. The null is the prior arm's own output: if every trip is drawn by exactly
  ``prior_params()`` (the ``uldp_prior`` arm), every user's label, trip or not, follows
  M^T pi0 (up to the public Monte Carlo of M). The test is a pre-registered Pearson
  chi-square whose p-value is a seeded Monte Carlo over the exact null multinomial
  (:data:`GATE_DRAWS`, :data:`GATE_ALPHA`). Only when it rejects are the regime weights
  refitted, by maximum likelihood (EM) of the
  report counts under the composed channel M times GRR; otherwise the prior weights stay.
  The fitted weights become ``SimParams.regime_weights`` for synthesis and scoring.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, ClassVar

import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.ldp import grr_perturb, grr_probabilities
from trajguard.representation import TrajectoryView
from trajguard.synthesis.public_sim import (
    BIKE_SPEED_KMH,
    DEFAULT_SPEED_KMH,
    FREE_FLOW_REGIME,
    PUBLIC_SIM_VERSION,
    REGIME_CATALOGUE,
    WALK_SPEED_KMH,
    PublicSimulator,
    Regime,
    SimParams,
    prior_params,
)
from trajguard.synthesis.uldp_arms import (
    LOG_RATIO_CLIP,
    simulate_trips,
    simulator_params_hash,
)
from trajguard.synthesis.uldp_base import (
    ReportSpace,
    UldpGenerator,
    UserReport,
    require_roster,
    split_sizes,
)

#: Reference speed of each catalogue member (in REGIME_CATALOGUE order) for the
#: time-model spread: the caps, and for the motorised regime the cited urban limit
#: without a sign (DEFAULT_SPEED_KMH).
_REFERENCE_KMH = (WALK_SPEED_KMH, BIKE_SPEED_KMH, DEFAULT_SPEED_KMH)
assert len(_REFERENCE_KMH) == len(REGIME_CATALOGUE)

#: Simulated trips per regime for the confusion matrix (public; Monte Carlo error of an
#: entry about 0.5 / sqrt(200) = 0.035). Production default; the constructor's
#: ``confusion_trips`` lowers it only for fast tests.
CONFUSION_TRIPS_PER_REGIME = 200
#: Public seed of the confusion-matrix simulation, shared by every arm on the same map.
CONFUSION_SEED = 20261010
#: Pre-registered gate: Pearson chi-square against the prior's predicted report
#: histogram, Monte Carlo p-value over GATE_DRAWS exact null draws, level GATE_ALPHA.
#: GATE_DRAWS is the production default; the constructor's ``gate_draws`` lowers it only
#: for fast tests.
GATE_ALPHA = 0.05
GATE_DRAWS = 100_000
GATE_SEED = 20261011
#: EM stopping rule for the regime weights (structural, not tuned).
EM_TOL = 1e-10
EM_MAX_ITER = 10_000

#: Module C2's public questions by slot. ``assign_questions`` draws a slot uniformly, so a
#: user is asked the OD cell with probability 0.5 and the cost band or the departure
#: period with 0.25 each: the plan's 0.4 : 0.2 : 0.2 for zone : band : period (§4.4),
#: renormalised after dropping the plan's regime question, which is C3's parameter.
C2_QUESTION_GROUPS = (0, 0, 1, 2)
C2_GROUP_NAMES = ("od", "band", "period")
#: Upper boundaries (s) of the six free-flow cost bands; the last band is open. They are
#: boundaries of the US Census Bureau American Community Survey "travel time to work"
#: tables (B08303 / B08603: ... 10-14, 15-19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-59,
#: 60-89, 90+ minutes, https://censusreporter.org/tables/B08603/), merged into six bands
#: at 10, 20, 30, 45 and 60 minutes; nothing is read from Geolife (finding F8).
COST_BAND_EDGES_S = (600.0, 1200.0, 1800.0, 2700.0, 3600.0)
N_COST_BANDS = len(COST_BAND_EDGES_S) + 1
#: The free-flow cost model of the bands: link length over OSM ``maxspeed`` or the cited
#: class speed (the regime with no factor, cap or class cost).
FREE_FLOW = FREE_FLOW_REGIME
#: Public Monte Carlo of the prior's band shares: origins drawn by mass, each giving the
#: exact band distribution over its destinations. Production default; the constructor's
#: ``band_origins`` lowers it only for fast tests.
BAND_ORIGINS = 200
BAND_SEED = 20261012

MODULES = ("c3", "c2", "c1", "all")


def time_log_sigma(reference_kmh: Sequence[float] = _REFERENCE_KMH) -> float:
    """Spread of the public time model: half the smallest log gap between adjacent regimes.

    SESSION DECISION: structural, read off the catalogue only (adjacent regimes' predicted
    times sit two spreads apart); no dispersion constant is cited or fitted.
    """
    logs = sorted(math.log(v) for v in reference_kmh)
    return min(b - a for a, b in zip(logs, logs[1:], strict=False)) / 2.0


def regime_posterior(
    sim: PublicSimulator,
    regimes: Sequence[Regime],
    prior_weights: Sequence[float],
    sigma: float,
    edge_seq: Sequence[int],
    duration_s: float,
) -> np.ndarray:
    """Posterior over regimes of one known trip: prior times the public time model.

    SESSION DECISION: the route term (``PublicSimulator.log_prob`` of each regime) is left
    out. The drive graph has no footways or cycleways (P9a), so the regimes differ by
    speed only; their route likelihoods differ only through the Boltzmann temperature,
    whose cited detour scale is in seconds of car time. On the fixture that term separates
    walk from motorised by 30-80 nats on a car route, against about 9 nats of time
    evidence, so a walking-speed trip would never be labelled walk (a misspecification
    artefact, not mode evidence).
    """
    logs = []
    for regime, w in zip(regimes, prior_weights, strict=True):
        ratio = math.log(duration_s / sim.route_time_s(edge_seq, regime))
        ratio = min(max(ratio, -LOG_RATIO_CLIP), LOG_RATIO_CLIP)
        logs.append(math.log(w) - 0.5 * (ratio / sigma) ** 2)
    arr = np.asarray(logs)
    post = np.exp(arr - arr.max())
    out: np.ndarray = post / post.sum()
    return out


def _trip_duration(view: TrajectoryView) -> float | None:
    """Duration of a view's clean GPS trip, None when it has no usable time."""
    if view.clean is None or len(view.clean.points) < 2:
        return None
    duration = view.clean.points[-1][2] - view.clean.points[0][2]
    return duration if duration > 0 else None


_CONFUSION: dict[tuple[Any, ...], np.ndarray] = {}


def confusion_matrix(
    sim: PublicSimulator,
    regimes: Sequence[Regime],
    prior_weights: Sequence[float],
    sigma: float,
    n_per_regime: int = CONFUSION_TRIPS_PER_REGIME,
    seed: int = CONFUSION_SEED,
) -> np.ndarray:
    """M[i, j]: mean posterior of regime j over public trips simulated under regime i.

    Each regime's trips are drawn by exactly the public prior (``prior_params()`` with
    that one regime: jitter-free times), so the gate's null M^T pi0 is the label law of
    the prior arm's own output. ``sigma`` enters only the phone's posterior (its
    observation model), so M describes exactly the labelling rule the phones apply to
    such trips. Cached process-wide per map key, catalogue, prior, spread and seed.
    """
    key = (
        sim.graph.key,
        PUBLIC_SIM_VERSION,
        tuple(regimes),
        tuple(prior_weights),
        sigma,
        n_per_regime,
        seed,
    )
    hit = _CONFUSION.get(key)
    if hit is not None:
        return hit
    children = np.random.SeedSequence(seed).spawn(len(regimes))
    rows = []
    for regime, child in zip(regimes, children, strict=True):
        params = replace(prior_params(), regimes=(regime,), regime_weights=(1.0,))
        routes = sim.simulate(params, n_per_regime, np.random.default_rng(child))
        post = [
            regime_posterior(
                sim,
                regimes,
                prior_weights,
                sigma,
                r.edge_seq,
                r.visits[-1].t_exit - r.visits[0].t_enter,
            )
            for r in routes
        ]
        rows.append(np.mean(post, axis=0))
    m = np.asarray(rows)
    _CONFUSION[key] = m
    return m


def grr_frequencies(counts: np.ndarray, epsilon: float) -> np.ndarray:
    """Exact, unclipped GRR debiasing: unbiased input-category frequencies from output counts."""
    counts = np.asarray(counts, dtype=np.float64)
    n = float(counts.sum())
    if not n > 0:
        raise ValueError("no reports to debias")
    p, q = grr_probabilities(len(counts), epsilon)
    freqs: np.ndarray = (counts / n - q) / (p - q)
    return freqs


def grr_channel(k: int, epsilon: float) -> np.ndarray:
    """The k x k GRR channel: G[l, j] = P(report j | true label l)."""
    p, q = grr_probabilities(k, epsilon)
    g: np.ndarray = np.full((k, k), q) + (p - q) * np.eye(k)
    return g


def pearson_statistic(counts: np.ndarray, probs: np.ndarray) -> np.ndarray:
    """Pearson chi-square of count rows against expected shares ``probs`` (last axis).

    Bins with zero null share are left out of the sum: a row with no count there gets
    the statistic of the remaining bins, a row with any count there is impossible under
    the null and gets +inf (a certain rejection). Below HM's epsilon* the two middle C1
    gate bins are such bins, since Duchi's mechanism only outputs +-bound.
    """
    counts = np.asarray(counts, dtype=np.float64)
    probs = np.asarray(probs, dtype=np.float64)
    if np.isnan(counts).any() or np.isnan(probs).any() or (probs < 0).any():
        raise ValueError("gate counts and null shares must be non-negative numbers")
    support = probs > 0
    expected = counts.sum(axis=-1, keepdims=True) * probs
    safe = np.where(support, expected, 1.0)
    terms = np.where(support, (counts - expected) ** 2 / safe, 0.0)
    stat: np.ndarray = terms.sum(axis=-1)
    impossible = (np.where(support, 0.0, counts) > 0).any(axis=-1)
    stat = np.where(impossible, np.inf, stat)
    if np.isnan(stat).any():
        raise ValueError("Pearson gate statistic is NaN")
    return stat


def gate_test(
    counts: np.ndarray, null_probs: np.ndarray, draws: int = GATE_DRAWS, seed: int = GATE_SEED
) -> tuple[float, float]:
    """Pearson statistic and its Monte Carlo p-value under the exact null multinomial."""
    return grouped_gate_test([counts], [null_probs], draws=draws, seed=seed)


def grouped_gate_test(
    counts: Sequence[np.ndarray],
    null_probs: Sequence[np.ndarray],
    draws: int = GATE_DRAWS,
    seed: int = GATE_SEED,
) -> tuple[float, float]:
    """Sum of per-group Pearson statistics and its Monte Carlo p-value under the null.

    Every group (one public question) is an independent multinomial with its own
    report count (fixed by the public question draw) and null shares; groups without
    reports add nothing. With one group this is :func:`gate_test`, draw for draw.
    """
    rng = np.random.default_rng(seed)
    stat = 0.0
    null_stats = np.zeros(draws)
    for c, probs in zip(counts, null_probs, strict=True):
        c = np.asarray(c, dtype=np.int64)
        probs = np.asarray(probs, dtype=np.float64)
        n = int(c.sum())
        if n == 0:
            continue
        stat += float(pearson_statistic(c, probs))
        null_stats += pearson_statistic(rng.multinomial(n, probs, size=draws), probs)
    # A NaN must never compare False and turn into a silent p-value; +inf is a rejection.
    if math.isnan(stat) or np.isnan(null_stats).any():
        raise ValueError("gate statistic is NaN")
    exceed = int((null_stats >= stat - 1e-12).sum())
    return stat, (1.0 + exceed) / (1.0 + draws)


def em_mixture_weights(counts: np.ndarray, channel: np.ndarray, start: np.ndarray) -> np.ndarray:
    """Maximum-likelihood mixture weights of report counts under a known channel (EM).

    ``channel[i, j]`` is P(report j | regime i); the weights stay on the simplex.
    """
    counts = np.asarray(counts, dtype=np.float64)
    w = np.asarray(start, dtype=np.float64).copy()
    for _ in range(EM_MAX_ITER):
        joint = w[:, None] * channel  # regime x report
        resp = joint / joint.sum(axis=0, keepdims=True)
        new = (resp * counts[None, :]).sum(axis=1) / counts.sum()
        if np.abs(new - w).max() < EM_TOL:
            return np.asarray(new)
        w = new
    return np.asarray(w)


@dataclass(frozen=True, eq=False)
class C3Public:
    """Everything public C3 needs: simulator, catalogue, prior, time model, M, epsilon."""

    sim: PublicSimulator
    regimes: tuple[Regime, ...]
    prior_weights: tuple[float, ...]
    sigma: float
    confusion: np.ndarray
    epsilon: float
    gate_draws: int = GATE_DRAWS

    @property
    def k(self) -> int:
        """Number of regimes (= GRR categories)."""
        return len(self.regimes)

    @property
    def prior_labels(self) -> np.ndarray:
        """Label distribution the prior predicts (M^T pi0); also the public default."""
        lam: np.ndarray = self.confusion.T @ np.asarray(self.prior_weights)
        out: np.ndarray = lam / lam.sum()
        return out

    @property
    def prior_reports(self) -> np.ndarray:
        """Report histogram shares the prior predicts through GRR (the gate's null)."""
        rho: np.ndarray = self.prior_labels @ grr_channel(self.k, self.epsilon)
        return rho


@dataclass(frozen=True)
class C3Fit:
    """Server output of C3: report counts, debiased label shares, gate and regime weights."""

    counts: tuple[int, ...]
    label_frequencies: tuple[float, ...]
    gate_statistic: float
    gate_p_value: float
    gate_rejected: bool
    regime_weights: tuple[float, ...]


def c3_encode(
    user_views: Sequence[TrajectoryView], public: C3Public, rng: np.random.Generator
) -> int:
    """Phone side of C3: GRR output of one label from one uniformly drawn usable trip."""
    trips: list[tuple[Sequence[int], float]] = []
    for v in user_views:
        duration = _trip_duration(v)
        if duration is not None and public.sim.known(v.as_sequence()):
            trips.append((v.as_sequence(), duration))
    if trips:
        seq, duration = trips[int(rng.integers(len(trips)))]
        post = regime_posterior(
            public.sim, public.regimes, public.prior_weights, public.sigma, seq, duration
        )
    else:
        post = public.prior_labels
    label = int(rng.choice(public.k, p=post))
    return grr_perturb(label, public.k, public.epsilon, rng)


def c3_server_fit(reports: Sequence[UserReport], public: C3Public) -> C3Fit:
    """Server side of C3: debias, gate against the prior, refit the weights only on rejection."""
    answers = []
    for r in reports:
        a = r.answer[0]
        if a != int(a) or not 0 <= a < public.k:
            raise ValueError(f"C3 answer {a} is not a category index below {public.k}")
        answers.append(int(a))
    counts = np.bincount(answers, minlength=public.k)
    if not counts.sum():
        prior = tuple(float(x) for x in public.prior_weights)
        return C3Fit(tuple(int(c) for c in counts), prior, 0.0, 1.0, False, prior)
    freqs = grr_frequencies(counts, public.epsilon)
    stat, p_value = gate_test(counts, public.prior_reports, draws=public.gate_draws)
    rejected = p_value < GATE_ALPHA
    weights = np.asarray(public.prior_weights, dtype=np.float64)
    if rejected:
        channel = public.confusion @ grr_channel(public.k, public.epsilon)
        weights = em_mixture_weights(counts, channel, weights)
    return C3Fit(
        counts=tuple(int(c) for c in counts),
        label_frequencies=tuple(float(x) for x in freqs),
        gate_statistic=stat,
        gate_p_value=p_value,
        gate_rejected=bool(rejected),
        regime_weights=tuple(float(x) for x in weights),
    )


# --- Module C2: origin-destination shares ------------------------------------------------


def gravity_od_shares(sim: PublicSimulator, params: SimParams) -> np.ndarray:
    """Exact row-major Z x Z zone shares of the prior's (origin, destination) node pairs.

    Under the gravity prior without decay the origin is drawn by road-length mass and
    the destination by mass among the other nodes, so
    P(zo, zd) = sum over o in zo of m_o / M * (Z_zd - m_o [zd = zo]) / (M - m_o).
    """
    if params.od_shares is not None or any(r.distance_decay_per_s for r in params.regimes):
        raise ValueError("gravity_od_shares needs the gravity prior without distance decay")
    g = sim.graph
    nodes = np.flatnonzero(g.mass > 0)
    m, z = g.mass[nodes], g.zone[nodes]
    total = float(g.mass.sum())
    scale = m / total / (total - m)
    rows = scale[:, None] * g.zone_mass[None, :]
    rows[np.arange(len(nodes)), z] -= scale * m
    table = np.zeros((g.n_zones, g.n_zones))
    np.add.at(table, z, rows)
    flat = np.maximum(table, 0.0).ravel()
    out: np.ndarray = flat / flat.sum()
    return out


def cost_band(cost_s: float) -> int:
    """Index of the free-flow cost band of a cost in seconds (infinite: the open last band)."""
    return int(np.searchsorted(COST_BAND_EDGES_S, cost_s, side="right"))


_BANDS: dict[tuple[Any, ...], np.ndarray] = {}


def gravity_band_shares(
    sim: PublicSimulator, n_origins: int = BAND_ORIGINS, seed: int = BAND_SEED
) -> np.ndarray:
    """Prior shares of the free-flow cost bands of (origin, destination) node pairs.

    Public Monte Carlo over ``n_origins`` origins drawn by mass; each contributes the
    exact band distribution of its destinations by mass (one forward search), so the
    estimate is unbiased. Cached process-wide per map key, size and seed.
    """
    key = (sim.graph.key, PUBLIC_SIM_VERSION, COST_BAND_EDGES_S, n_origins, seed)
    hit = _BANDS.get(key)
    if hit is not None:
        return hit
    g = sim.graph
    router = sim.router(FREE_FLOW)
    origins = np.random.default_rng(seed).choice(
        len(g.mass), size=n_origins, p=g.mass / g.mass.sum()
    )
    acc = np.zeros(N_COST_BANDS)
    for o in origins:
        w = g.mass.copy()
        w[o] = 0.0
        bands = np.searchsorted(COST_BAND_EDGES_S, router.frm(int(o)), side="right")
        acc += np.bincount(bands, weights=w / w.sum(), minlength=N_COST_BANDS)
    out: np.ndarray = acc / acc.sum()
    _BANDS[key] = out
    return out


_BAND_GIVEN_OD: dict[tuple[Any, ...], np.ndarray] = {}


def gravity_band_given_od(
    sim: PublicSimulator, n_origins: int = BAND_ORIGINS, seed: int = BAND_SEED
) -> np.ndarray:
    """Prior band shares within every OD cell: row c is P(cost band | OD cell c), (Z^2, bands).

    The public Monte Carlo of :func:`gravity_band_shares` (same origins, same seed), with
    every origin's destinations split by zone as well as by band. SESSION DECISION: an OD
    cell no drawn origin reaches gets the overall band shares of the same Monte Carlo
    (the conservative fill: it adds no structure the sample did not see). Times the exact
    OD shares this is the gravity prior Q of plan §4.4. Cached per map key, size and seed.
    """
    key = (sim.graph.key, PUBLIC_SIM_VERSION, COST_BAND_EDGES_S, n_origins, seed)
    hit = _BAND_GIVEN_OD.get(key)
    if hit is not None:
        return hit
    g = sim.graph
    n_z = g.n_zones
    router = sim.router(FREE_FLOW)
    origins = np.random.default_rng(seed).choice(
        len(g.mass), size=n_origins, p=g.mass / g.mass.sum()
    )
    acc = np.zeros(n_z * n_z * N_COST_BANDS)
    for o in origins:
        w = g.mass.copy()
        w[o] = 0.0
        bands = np.searchsorted(COST_BAND_EDGES_S, router.frm(int(o)), side="right")
        cell = int(g.zone[o]) * n_z + g.zone
        acc += np.bincount(cell * N_COST_BANDS + bands, w / w.sum(), minlength=acc.size)
    table = acc.reshape(n_z * n_z, N_COST_BANDS)
    rows = table.sum(axis=1, keepdims=True)
    overall = table.sum(axis=0) / table.sum()
    out: np.ndarray = np.where(rows > 0, table / np.where(rows > 0, rows, 1.0), overall)
    _BAND_GIVEN_OD[key] = out
    return out


def grr_noise_cov(report_shares: np.ndarray, n: int, epsilon: float) -> np.ndarray:
    """Exact covariance of the GRR-debiased frequencies of n reports with these report shares.

    The counts are multinomial, so Cov = (diag(rho) - rho rho^T) / (n (p - q)^2); it is
    singular along the all-ones direction, along which the frequencies always sum to one.
    """
    rho = np.asarray(report_shares, dtype=np.float64)
    p, q = grr_probabilities(len(rho), epsilon)
    cov: np.ndarray = (np.diag(rho) - np.outer(rho, rho)) / (n * (p - q) ** 2)
    return cov


#: Stopping rules of :func:`kl_furness` (structural, not tuned): the largest change of a
#: scaling exponent over one sweep, and the largest gradient entry of a block solve.
FURNESS_TOL = 1e-9
FURNESS_MAX_SWEEPS = 1_000
NEWTON_TOL = 1e-12
NEWTON_MAX_ITER = 200


def _logsumexp(x: np.ndarray) -> float:
    top = float(np.max(x))
    return top + math.log(float(np.exp(x - top).sum()))


def _block_solve(
    log_base: np.ndarray, target: np.ndarray, cov: np.ndarray, lam: np.ndarray
) -> np.ndarray:
    """One block's exact scaling exponents (Newton with backtracking, warm start ``lam``).

    Maximises the block's dual -logsumexp(log_base - lam) - lam . target - lam.cov.lam / 2,
    whose stationarity condition is m(lam) = target + cov lam: the block marginal m of the
    scaled table equals the reported frequencies up to the noise allowance cov lam.
    """

    def value(x: np.ndarray) -> float:
        return -_logsumexp(log_base - x) - float(x @ target) - 0.5 * float(x @ cov @ x)

    k = len(target)
    pin = np.full((k, k), 1.0 / k)  # fixes the flat all-ones direction of the dual
    f = value(lam)
    for _ in range(NEWTON_MAX_ITER):
        m = np.exp(log_base - lam - _logsumexp(log_base - lam))
        grad = m - target - cov @ lam
        if np.abs(grad).max() < NEWTON_TOL:
            break
        step = np.linalg.solve(np.diag(m) - np.outer(m, m) + cov + pin, grad)
        t, improved = 1.0, False
        while t > 1e-12:
            new = lam + t * step
            f_new = value(new)
            if f_new >= f:
                lam, f, improved = new, f_new, True
                break
            t *= 0.5
        if not improved:
            break  # no ascent left at machine precision
    return lam


def kl_furness(
    prior: np.ndarray, blocks: Sequence[tuple[np.ndarray, np.ndarray, np.ndarray]]
) -> np.ndarray:
    """T = argmin KL(T || Q) + 1/2 sum_b ||A_b T - t_b||^2 weighted by V_b^-1 (plan §4.4).

    ``prior`` is Q over cells (>= 0, summing to one). Each block is (category of every
    cell, reported frequencies t_b, their noise covariance V_b); A_b T sums T per
    category. The minimiser has the Furness form T ~ Q x prod_b exp(-lam_b[category]),
    so it is found by Furness sweeps (iterative proportional scaling): each block in
    turn rescales its categories, exactly solving its own condition
    A_b T = t_b + V_b lam_b with the other blocks' factors held. With V_b -> 0 this is
    classical Furness / IPF onto the reported marginals; a finite V_b stops short of
    them by the reports' noise. Cells where Q is zero stay zero.
    """
    q = np.asarray(prior, dtype=np.float64)
    with np.errstate(divide="ignore"):
        log_q = np.log(q)
    cats = [np.asarray(c, dtype=np.int64) for c, _, _ in blocks]
    lams = [np.zeros(len(t)) for _, t, _ in blocks]
    for _ in range(FURNESS_MAX_SWEEPS):
        moved = 0.0
        for b, (_, target, cov) in enumerate(blocks):
            rest = log_q.copy()
            for o in range(len(blocks)):
                if o != b:
                    rest -= lams[o][cats[o]]
            top = float(rest[np.isfinite(rest)].max())
            base = np.bincount(cats[b], np.exp(rest - top), minlength=len(target))
            with np.errstate(divide="ignore"):
                log_base = np.log(base) + top
            new = _block_solve(
                log_base, np.asarray(target, np.float64), np.asarray(cov, np.float64), lams[b]
            )
            moved = max(moved, float(np.abs(new - lams[b]).max()))
            lams[b] = new
        if moved < FURNESS_TOL:
            break
    log_t = log_q.copy()
    for lam, c in zip(lams, cats, strict=True):
        log_t -= lam[c]
    out: np.ndarray = np.exp(log_t - _logsumexp(log_t))
    return out


@dataclass(frozen=True, eq=False)
class C2Public:
    """Everything public C2 needs: simulator, epsilon and the prior's shares per question."""

    sim: PublicSimulator
    epsilon: float
    od_prior: np.ndarray
    band_prior: np.ndarray
    period_prior: np.ndarray
    #: The gravity prior Q over (OD cell, cost band), shape (Z^2, bands); its OD marginal
    #: is exactly ``od_prior`` (:func:`gravity_band_given_od`).
    od_band_prior: np.ndarray
    gate_draws: int = GATE_DRAWS

    @property
    def priors(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prior answer shares per question group (od, band, period); also the public default."""
        return self.od_prior, self.band_prior, self.period_prior

    @property
    def od_support(self) -> np.ndarray:
        """OD cells the map can host a trip in (the gravity prior's support)."""
        support: np.ndarray = self.od_prior > 0
        return support

    def k(self, group: int) -> int:
        """Number of GRR categories of a question group."""
        return len(self.priors[group])

    def prior_reports(self, group: int) -> np.ndarray:
        """Report shares the prior predicts for a question group through GRR (the gate's null)."""
        rho: np.ndarray = self.priors[group] @ grr_channel(self.k(group), self.epsilon)
        return rho


@dataclass(frozen=True)
class C2Fit:
    """Server output of C2: per-group counts and debiased shares, gate, fitted shares.

    Groups are (od, band, period); a group without reports has empty frequencies.
    ``band_shares`` is the band marginal of the fitted (OD cell, band) table, recorded
    only: the band reports reach the simulator through the OD shares they tilt.
    """

    counts: tuple[tuple[int, ...], ...]
    frequencies: tuple[tuple[float, ...], ...]
    gate_statistic: float
    gate_p_value: float
    gate_rejected: bool
    od_shares: tuple[float, ...] | None
    departure_shares: tuple[float, ...]
    band_shares: tuple[float, ...]


def _c2_trips(
    user_views: Sequence[TrajectoryView], sim: PublicSimulator
) -> list[tuple[Sequence[int], float]]:
    """(edge sequence, departure instant) of every usable trip: known on the map, timed."""
    trips: list[tuple[Sequence[int], float]] = []
    for v in user_views:
        seq = v.as_sequence()
        if v.clean is not None and len(v.clean.points) >= 2 and sim.known(seq):
            trips.append((seq, float(v.clean.points[0][2])))
    return trips


def c2_category(sim: PublicSimulator, group: int, edge_seq: Sequence[int], t0: float) -> int:
    """The true answer of one trip to a C2 question group (OD cell, cost band or period)."""
    if group == 0:
        zo, zd = sim.od_zones(edge_seq)
        return zo * sim.n_zones + zd
    if group == 1:
        g = sim.graph
        origin = int(g.tail[g.edge_index[int(edge_seq[0])]])
        dest = int(g.head[g.edge_index[int(edge_seq[-1])]])
        return cost_band(float(sim.router(FREE_FLOW).frm(origin)[dest]))
    return sim.departure_period(t0)


def _c2_range(public: C2Public, question: int) -> tuple[float, float]:
    """Answer range of a C2 question slot: category indices 0 to k - 1 of its group."""
    return 0.0, float(public.k(C2_QUESTION_GROUPS[question]) - 1)


def c2_encode(
    user_views: Sequence[TrajectoryView], public: C2Public, question: int, rng: np.random.Generator
) -> int:
    """Phone side of C2: GRR output of one trip's answer to the public question."""
    group = C2_QUESTION_GROUPS[question]
    k = public.k(group)
    trips = _c2_trips(user_views, public.sim)
    if trips:
        seq, t0 = trips[int(rng.integers(len(trips)))]
        category = c2_category(public.sim, group, seq, t0)
    else:
        category = int(rng.choice(k, p=public.priors[group]))
    return grr_perturb(category, k, public.epsilon, rng)


def c2_server_fit(reports: Sequence[UserReport], public: C2Public) -> C2Fit:
    """Server side of C2: debias, gate against the prior, KL-Furness fit only on rejection."""
    answers: list[list[int]] = [[] for _ in C2_GROUP_NAMES]
    for r in reports:
        group = C2_QUESTION_GROUPS[r.question]
        a = r.answer[0]
        if a != int(a) or not 0 <= a < public.k(group):
            raise ValueError(f"C2 answer {a} is not a category index below {public.k(group)}")
        answers[group].append(int(a))
    counts = [np.bincount(a, minlength=public.k(g)).astype(np.int64) for g, a in enumerate(answers)]
    freqs = [grr_frequencies(c, public.epsilon) if c.sum() else np.zeros(0) for c in counts]
    nulls = [public.prior_reports(g) for g in range(len(counts))]
    stat, p_value = grouped_gate_test(counts, nulls, draws=public.gate_draws)
    rejected = p_value < GATE_ALPHA
    od: tuple[float, ...] | None = None
    period = tuple(float(x) for x in public.period_prior)
    band = tuple(float(x) for x in public.band_prior)
    if rejected:
        q = public.od_band_prior
        cells = np.arange(q.size)
        cats = (cells // N_COST_BANDS, cells % N_COST_BANDS)  # OD cell, cost band
        blocks = [
            (cats[g], freqs[g], grr_noise_cov(nulls[g], int(counts[g].sum()), public.epsilon))
            for g in (0, 1)
            if len(freqs[g])
        ]
        if blocks:
            table = kl_furness(q.ravel(), blocks).reshape(q.shape)
            od = tuple(float(x) for x in table.sum(axis=1))
            band = tuple(float(x) for x in table.sum(axis=0))
        if len(freqs[2]):
            cov = grr_noise_cov(nulls[2], int(counts[2].sum()), public.epsilon)
            idx = np.arange(len(public.period_prior))
            fitted = kl_furness(public.period_prior, [(idx, freqs[2], cov)])
            period = tuple(float(x) for x in fitted)
    return C2Fit(
        counts=tuple(tuple(int(x) for x in c) for c in counts),
        frequencies=tuple(tuple(float(x) for x in f) for f in freqs),
        gate_statistic=stat,
        gate_p_value=p_value,
        gate_rejected=bool(rejected),
        od_shares=od,
        departure_shares=period,
        band_shares=band,
    )


# --- Module C1: behavioural moments ------------------------------------------------------

#: Module C1's public questions, one numeric moment each; ``assign_questions`` draws a
#: slot uniformly. SESSION DECISION: d = 2, the two numbers plan §4.5 expects to move at
#: n ≈ 91 and epsilon = 2 (the speed ratio to OSM and the length scale), asked at every
#: epsilon; route-choice tastes (class costs, turn penalty, detour temperature) stay on
#: the prior, as §4.5 expects at epsilon <= 2, and no question count is derived from data.
C1_QUESTIONS = ("speed", "length")
#: Public frame of the length moment: the log free-flow cost between a trip's end nodes,
#: clipped to 1 to 90 minutes (90 minutes is the last boundary of the ACS travel-time
#: bands behind :data:`COST_BAND_EDGES_S`; SESSION DECISION: 1 minute is a structural
#: floor, nothing is read from Geolife).
LENGTH_FRAME_S = (60.0, 5400.0)
#: Gate bins per question: equal-width bins over the randomiser's public output range.
#: SESSION DECISION: few bins keep the Pearson gate sensitive to a location shift at about
#: 45 reports per question.
C1_BINS = 4
#: Simulated public prior trips per regime for the speed moment's prior predictive.
#: Production default; the constructor's ``moment_trips`` lowers it only for fast tests.
C1_TRIPS_PER_REGIME = 200
C1_SEED = 20261013
#: Admissible set of the fitted parameters: the speed level within the public speed clip
#: (``exp(+-LOG_RATIO_CLIP)``), the decay from 0 (the gravity prior) to one per minute of
#: free-flow cost (SESSION DECISION: structural bound).
DECAY_MAX_PER_S = 1.0 / 60.0
#: The hybrid mechanism HM mixes PM and Duchi's mechanism only above this epsilon and is
#: Duchi's mechanism alone below it (Wang et al., ICDE 2019, §III-C: epsilon* = 0.61).
HM_EPSILON_STAR = 0.61
#: Bisection steps of the moment matching (structural, not tuned).
BISECT_ITER = 60


def pm_bound(epsilon: float) -> float:
    """Output bound C of the Piecewise Mechanism (Wang et al., ICDE 2019, Alg. 2)."""
    a = math.exp(epsilon / 2.0)
    return (a + 1.0) / (a - 1.0)


def duchi_bound(epsilon: float) -> float:
    """Output magnitude of Duchi et al.'s one-bit mechanism for one number in [-1, 1]."""
    e = math.exp(epsilon)
    return (e + 1.0) / (e - 1.0)


def hm_pm_share(epsilon: float) -> float:
    """Probability that HM uses PM (1 - exp(-epsilon/2) above epsilon*, else 0)."""
    return 1.0 - math.exp(-epsilon / 2.0) if epsilon > HM_EPSILON_STAR else 0.0


def hm_bound(epsilon: float) -> float:
    """Public bound of every HM output (PM's C whenever PM is used; it exceeds Duchi's)."""
    return pm_bound(epsilon) if hm_pm_share(epsilon) > 0 else duchi_bound(epsilon)


def hm_perturb(x: float, epsilon: float, rng: np.random.Generator) -> float:
    """Hybrid mechanism (Wang et al., ICDE 2019): an unbiased epsilon-LDP report of x in [-1, 1]."""
    if not -1.0 <= x <= 1.0:
        raise ValueError(f"HM input {x} outside [-1, 1]")
    if rng.random() < hm_pm_share(epsilon):
        c = pm_bound(epsilon)
        a = math.exp(epsilon / 2.0)
        lo = (c + 1.0) / 2.0 * x - (c - 1.0) / 2.0
        hi = lo + c - 1.0
        if rng.random() < a / (a + 1.0):
            y = float(rng.uniform(lo, hi))
        else:
            u = float(rng.uniform(0.0, c + 1.0))
            y = -c + u if u < lo + c else hi + (u - (lo + c))
        return min(max(y, -c), c)
    d = duchi_bound(epsilon)
    e = math.exp(epsilon)
    p_plus = 0.5 + x * (e - 1.0) / (2.0 * (e + 1.0))
    return d if rng.random() < p_plus else -d


def c1_edges(epsilon: float) -> np.ndarray:
    """Public gate-bin edges: C1_BINS equal-width bins over [-hm_bound, hm_bound]."""
    b = hm_bound(epsilon)
    edges: np.ndarray = np.linspace(-b, b, C1_BINS + 1)
    return edges


def c1_bin(y: float, epsilon: float) -> int:
    """Gate bin of one report (half-open bins, the last one closed)."""
    idx = int(np.searchsorted(c1_edges(epsilon), y, side="right")) - 1
    return min(max(idx, 0), C1_BINS - 1)


def pm_density(epsilon: float) -> tuple[float, float]:
    """PM's output density inside and outside the input's high-probability window [l, r].

    Wang et al., ICDE 2019, Alg. 2: the window [l, r] has width C - 1 and the output
    lands in it with probability exp(eps/2) / (exp(eps/2) + 1); their ratio is exp(eps).
    """
    a = math.exp(epsilon / 2.0)
    dens_in = (math.exp(epsilon) - a) / (2.0 * a + 2.0)
    return dens_in, dens_in / math.exp(epsilon)


def hm_bin_probs(x: np.ndarray, epsilon: float, edges: np.ndarray | None = None) -> np.ndarray:
    """Exact P(report in bin | input x) under HM, one row per input value.

    The bins are the public gate bins (:func:`c1_edges`) unless ``edges`` (increasing,
    spanning [-hm_bound, hm_bound]) are given; the last bin is closed.
    """
    xc = np.asarray(x, dtype=np.float64)[:, None]
    edges = c1_edges(epsilon) if edges is None else np.asarray(edges, dtype=np.float64)
    n_bins = len(edges) - 1
    left, right = edges[:-1][None, :], edges[1:][None, :]
    out = np.zeros((xc.shape[0], n_bins))
    beta = hm_pm_share(epsilon)
    if beta > 0:
        c = pm_bound(epsilon)
        lo = (c + 1.0) / 2.0 * xc - (c - 1.0) / 2.0
        hi = lo + c - 1.0
        dens_in, dens_out = pm_density(epsilon)
        inside = np.maximum(np.minimum(right, hi) - np.maximum(left, lo), 0.0)
        total = np.maximum(np.minimum(right, c) - np.maximum(left, -c), 0.0)
        out += beta * (dens_in * inside + dens_out * (total - inside))
    d = duchi_bound(epsilon)
    e = math.exp(epsilon)
    p_plus = 0.5 + xc[:, 0] * (e - 1.0) / (2.0 * (e + 1.0))
    for y, share in ((d, p_plus), (-d, 1.0 - p_plus)):
        idx = min(max(int(np.searchsorted(edges, y, side="right")) - 1, 0), n_bins - 1)
        out[:, idx] += (1.0 - beta) * share
    return out


def speed_moment(t_free_s: Any, duration_s: Any) -> Any:
    """Speed moment in [-1, 1]: log(free-flow time / duration) within the public speed clip."""
    ratio = np.log(np.asarray(t_free_s, dtype=np.float64) / np.asarray(duration_s))
    return np.clip(ratio, -LOG_RATIO_CLIP, LOG_RATIO_CLIP) / LOG_RATIO_CLIP


def length_moment(cost_s: Any) -> Any:
    """Length moment in [-1, 1]: log free-flow cost between end nodes on the public frame."""
    lo, hi = (math.log(v) for v in LENGTH_FRAME_S)
    c = np.clip(np.asarray(cost_s, dtype=np.float64), *LENGTH_FRAME_S)
    return 2.0 * (np.log(c) - lo) / (hi - lo) - 1.0


@dataclass(frozen=True, eq=False)
class SpeedSample:
    """Links of public prior trips simulated under one regime (speed moment's prior predictive)."""

    regime: Regime
    link_len: np.ndarray
    link_ff: np.ndarray
    link_trip: np.ndarray
    t_free: np.ndarray

    def moments(self, level: float) -> np.ndarray:
        """Each trip's speed moment when every period speed factor is ``level``."""
        speed = self.link_ff * self.regime.speed_factor * level
        if self.regime.speed_cap_mps is not None:
            speed = np.minimum(speed, self.regime.speed_cap_mps)
        t = np.bincount(self.link_trip, self.link_len / speed, minlength=len(self.t_free))
        out: np.ndarray = speed_moment(self.t_free, t)
        return out


@dataclass(frozen=True, eq=False)
class LengthSample:
    """Free-flow costs from public origins drawn by mass (length moment's prior predictive)."""

    origins: np.ndarray
    costs: np.ndarray  # (origins, nodes) free-flow cost, float32
    moments: np.ndarray  # length_moment of costs, float32
    mass: np.ndarray

    def dest_weights(self, i: int, decay: float) -> np.ndarray:
        """Destination shares from origin i under the gravity model with this decay.

        All zeros when origin i has no destination of positive weight (no other node
        with mass, or with decay none reachable): such an origin hosts no trip.
        """
        w = self.mass.copy()
        w[int(self.origins[i])] = 0.0
        if decay > 0:
            c = self.costs[i].astype(np.float64)
            reachable = np.isfinite(c) & (w > 0)
            if not reachable.any():
                return np.zeros(len(w))
            shift = float(c[reachable].min())
            w = w * np.exp(-decay * (c - shift))  # unreachable (inf) -> 0
        total = float(w.sum())
        if not total > 0:
            return np.zeros(len(w))
        out: np.ndarray = w / total
        return out

    def hosting(self) -> np.ndarray:
        """Indices of the origins with another node of positive mass (they host a trip)."""
        out: np.ndarray = np.flatnonzero(self.mass.sum() - self.mass[self.origins] > 0)
        return out

    def mean(self, decay: float) -> float:
        """Expected length moment under the gravity model with this decay.

        The average runs over the origins that host a trip; 0 (the frame's centre) if none.
        """
        values = []
        for i in range(len(self.origins)):
            w = self.dest_weights(i, decay)
            if w.any():
                values.append(float(w @ self.moments[i].astype(np.float64)))
        return float(np.mean(values)) if values else 0.0


_C1_SAMPLES: dict[tuple[Any, ...], tuple[tuple[SpeedSample, ...], LengthSample]] = {}


def c1_samples(
    sim: PublicSimulator,
    regimes: Sequence[Regime],
    n_per_regime: int = C1_TRIPS_PER_REGIME,
    n_origins: int = BAND_ORIGINS,
) -> tuple[tuple[SpeedSample, ...], LengthSample]:
    """Public Monte Carlo samples of both C1 moments under the prior; cached per map.

    Speed: trips simulated per regime under the prior (seed :data:`C1_SEED`). Length:
    the origins of :func:`gravity_band_shares` (same seed and draw, so their free-flow
    trees are shared), each with the exact cost to every node.
    """
    key = (sim.graph.key, PUBLIC_SIM_VERSION, tuple(regimes), n_per_regime, n_origins)
    hit = _C1_SAMPLES.get(key)
    if hit is not None:
        return hit
    g = sim.graph
    speed = []
    children = np.random.SeedSequence(C1_SEED).spawn(len(regimes))
    for regime, child in zip(regimes, children, strict=True):
        params = SimParams(regimes=(regime,))
        routes = sim.simulate(params, n_per_regime, np.random.default_rng(child))
        idx = [np.array([g.edge_index[int(e)] for e in r.edge_seq]) for r in routes]
        link = np.concatenate(idx)
        trip = np.concatenate([np.full(len(ix), i) for i, ix in enumerate(idx)])
        ff = g.free_flow_mps[link]
        t_free = np.bincount(trip, g.length[link] / ff, minlength=len(idx))
        speed.append(SpeedSample(regime, g.length[link], ff, trip, t_free))
    origins = np.random.default_rng(BAND_SEED).choice(
        len(g.mass), size=n_origins, p=g.mass / g.mass.sum()
    )
    router = sim.router(FREE_FLOW)
    costs = np.stack([router.frm(int(o)) for o in origins]).astype(np.float32)
    length = LengthSample(origins, costs, length_moment(costs).astype(np.float32), g.mass)
    out = (tuple(speed), length)
    _C1_SAMPLES[key] = out
    return out


@dataclass(frozen=True, eq=False)
class C1Public:
    """Everything public C1 needs: simulator, epsilon, prior weights, moment samples, null."""

    sim: PublicSimulator
    epsilon: float
    regime_weights: tuple[float, ...]
    speed: tuple[SpeedSample, ...]
    length: LengthSample
    speed_null: np.ndarray
    length_null: np.ndarray
    gate_draws: int = GATE_DRAWS

    def speed_mean(self, level: float) -> float:
        """Expected speed moment of the prior mixture with every period factor at ``level``."""
        pairs = zip(self.regime_weights, self.speed, strict=True)
        return float(sum(w * float(s.moments(level).mean()) for w, s in pairs))

    def default_moment(self, question: int, rng: np.random.Generator) -> float:
        """A draw from the prior predictive of a question's moment (the public default)."""
        if question == 0:
            r = int(rng.choice(len(self.speed), p=np.asarray(self.regime_weights)))
            prior = self.speed[r].moments(1.0)
            return float(prior[int(rng.integers(len(prior)))])
        hosts = self.length.hosting()
        i = int(hosts[int(rng.integers(len(hosts)))])
        w = self.length.dest_weights(i, 0.0)
        return float(self.length.moments[i, int(rng.choice(len(w), p=w))])


def c1_public(
    sim: PublicSimulator,
    epsilon: float,
    prior: SimParams,
    n_per_regime: int = C1_TRIPS_PER_REGIME,
    n_origins: int = BAND_ORIGINS,
    gate_draws: int = GATE_DRAWS,
) -> C1Public:
    """Build C1's public objects, including the gate's null bin shares under the prior."""
    speed, length = c1_samples(sim, prior.regimes, n_per_regime, n_origins)
    total = float(sum(prior.regime_weights))
    weights = tuple(float(w) / total for w in prior.regime_weights)
    speed_null = np.zeros(C1_BINS)
    for w, s in zip(weights, speed, strict=True):
        speed_null += w * hm_bin_probs(s.moments(1.0), epsilon).mean(axis=0)
    length_null = np.mean(
        [
            length.dest_weights(int(i), 0.0) @ hm_bin_probs(length.moments[i], epsilon)
            for i in length.hosting()
        ],
        axis=0,
    )
    return C1Public(sim, epsilon, weights, speed, length, speed_null, length_null, gate_draws)


@dataclass(frozen=True)
class C1Fit:
    """Server output of C1: per-question bin counts and unbiased means, gate, fitted values.

    Questions are (speed, length); a question without reports has mean None. Without a
    rejection the speed level is 1 and the decay 0, the prior's values.
    """

    counts: tuple[tuple[int, ...], ...]
    means: tuple[float | None, ...]
    gate_statistic: float
    gate_p_value: float
    gate_rejected: bool
    speed_level: float
    decay_per_s: float


def c1_moment(
    user_views: Sequence[TrajectoryView], public: C1Public, question: int, rng: np.random.Generator
) -> float:
    """The moment of one uniformly drawn usable trip, or the public default without one."""
    sim = public.sim
    if question == 0:
        timed = []
        for v in user_views:
            duration = _trip_duration(v)
            if duration is not None and sim.known(v.as_sequence()):
                timed.append((v.as_sequence(), duration))
        if timed:
            seq, duration = timed[int(rng.integers(len(timed)))]
            return float(speed_moment(sim.route_time_s(seq), duration))
    else:
        known = [v.as_sequence() for v in user_views if sim.known(v.as_sequence())]
        if known:
            seq = known[int(rng.integers(len(known)))]
            g = sim.graph
            origin = int(g.tail[g.edge_index[int(seq[0])]])
            dest = int(g.head[g.edge_index[int(seq[-1])]])
            return float(length_moment(sim.router(FREE_FLOW).frm(origin)[dest]))
    return public.default_moment(question, rng)


def c1_encode(
    user_views: Sequence[TrajectoryView], public: C1Public, question: int, rng: np.random.Generator
) -> float:
    """Phone side of C1: HM report of one trip's moment for the public question."""
    return hm_perturb(c1_moment(user_views, public, question, rng), public.epsilon, rng)


def _bisect(f: Callable[[float], float], lo: float, hi: float, target: float, up: bool) -> float:
    """Solve f(u) = target on [lo, hi] for a monotone f, clamped to the interval's ends."""
    sign = 1.0 if up else -1.0
    if sign * (target - f(lo)) <= 0:
        return lo
    if sign * (target - f(hi)) >= 0:
        return hi
    for _ in range(BISECT_ITER):
        mid = 0.5 * (lo + hi)
        if sign * (f(mid) - target) < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def solve_speed_level(public: C1Public, target: float) -> float:
    """Speed level whose expected speed moment matches ``target`` (clamped to the clip)."""
    u = _bisect(
        lambda v: public.speed_mean(math.exp(v)), -LOG_RATIO_CLIP, LOG_RATIO_CLIP, target, True
    )
    return math.exp(u)


def solve_decay(public: C1Public, target: float) -> float:
    """Gravity decay whose expected length moment matches ``target`` (clamped to [0, max])."""
    return _bisect(public.length.mean, 0.0, DECAY_MAX_PER_S, target, False)


def c1_server_fit(reports: Sequence[UserReport], public: C1Public) -> C1Fit:
    """Server side of C1: unbiased means, gate against the prior, moment matching on rejection."""
    answers: list[list[float]] = [[] for _ in C1_QUESTIONS]
    for r in reports:
        answers[r.question].append(float(r.answer[0]))
    counts = [
        np.bincount([c1_bin(y, public.epsilon) for y in a], minlength=C1_BINS).astype(np.int64)
        for a in answers
    ]
    means = [float(np.mean(a)) if a else None for a in answers]
    nulls = [public.speed_null, public.length_null]
    stat, p_value = grouped_gate_test(counts, nulls, draws=public.gate_draws)
    rejected = p_value < GATE_ALPHA
    level, decay = 1.0, 0.0
    if rejected:
        if means[0] is not None:
            level = solve_speed_level(public, min(max(means[0], -1.0), 1.0))
        if means[1] is not None:
            decay = solve_decay(public, min(max(means[1], -1.0), 1.0))
    return C1Fit(
        counts=tuple(tuple(int(x) for x in c) for c in counts),
        means=tuple(means),
        gate_statistic=stat,
        gate_p_value=p_value,
        gate_rejected=bool(rejected),
        speed_level=level,
        decay_per_s=decay,
    )


# --- Composite arm: the three modules on public thirds of the roster ----------------------

#: Order of the composite's modules; the public draw gives the i-th third to the i-th.
COMPOSITE_MODULES = ("c1", "c2", "c3")
#: Public n·ε² rule (plan §4.2): a module asks as many of its questions as keep
#: reports x epsilon^2 per question at or above this, and at least one. SESSION DECISION:
#: one HM or Duchi report of a mean in [-1, 1] has variance about 4 / epsilon^2 at small
#: epsilon, so m reports with m·ε² >= 16 put the mean's SD at or below 0.5, half the
#: range's half-width; read off the randomiser, nothing from Geolife.
REPORT_INFO_PER_QUESTION = 16.0
#: Order in which a module's questions are kept as n·ε² grows. C1: speed, then length.
#: C2: OD cell, then departure period, then cost band (SESSION DECISION: the band shares
#: reach the simulator only indirectly, by tilting the OD shares, so they go last).
C1_PRIORITY = (0, 1)
C2_PRIORITY = (0, 2, 1)


def question_count(n_reports: int, epsilon: float, n_max: int) -> int:
    """Questions a module asks under the public n·ε² rule (at least one, at most n_max)."""
    return max(1, min(n_max, int(n_reports * epsilon**2 / REPORT_INFO_PER_QUESTION + 1e-9)))


def composite_layout(
    roster_size: int, epsilon: float, rule_n: int | None = None
) -> tuple[tuple[int, ...], tuple[tuple[str, ...], ...], tuple[tuple[str, int], ...]]:
    """Public plan of the composite: users per module, asked question names, question slots.

    The users per module are thirds of the roster; the question counts are the n·ε² rule
    on thirds of ``rule_n`` when given (same questions for any roster), else of the roster.
    The slots are (module, local question) pairs in global question order; C2 keeps the
    slots of :data:`C2_QUESTION_GROUPS` whose group is asked, so the asked groups keep the
    plan's relative weights.
    """
    sizes = split_sizes(roster_size, len(COMPOSITE_MODULES))
    rule = sizes if rule_n is None else split_sizes(rule_n, len(COMPOSITE_MODULES))
    d1 = question_count(rule[0], epsilon, len(C1_PRIORITY))
    d2 = question_count(rule[1], epsilon, len(C2_PRIORITY))
    c1_kept = sorted(C1_PRIORITY[:d1])
    c2_kept = set(C2_PRIORITY[:d2])
    slots: list[tuple[str, int]] = [("c1", q) for q in c1_kept]
    slots += [("c2", s) for s, g in enumerate(C2_QUESTION_GROUPS) if g in c2_kept]
    slots.append(("c3", 0))
    names = (
        tuple(C1_QUESTIONS[q] for q in c1_kept),
        tuple(C2_GROUP_NAMES[g] for g in sorted(c2_kept)),
        ("regime",),
    )
    return sizes, names, tuple(slots)


@dataclass(frozen=True, eq=False)
class CompositePublic:
    """Everything public the composite needs: the three modules' objects and the public plan."""

    c1: C1Public
    c2: C2Public
    c3: C3Public
    epsilon: float
    roster_size: int
    module_users: tuple[int, ...]
    questions: tuple[tuple[str, ...], ...]
    slots: tuple[tuple[str, int], ...]
    rule_n: int | None = None


@dataclass(frozen=True)
class CompositeFit:
    """Server output of the composite: the public plan and each module's own fit and gate."""

    roster_size: int
    module_users: tuple[int, ...]
    questions: tuple[tuple[str, ...], ...]
    c1: C1Fit
    c2: C2Fit
    c3: C3Fit
    rule_n: int | None = None


def composite_encode(
    user_views: Sequence[TrajectoryView],
    public: CompositePublic,
    question: int,
    rng: np.random.Generator,
) -> UserReport:
    """Phone side of the composite: the assigned module's answer with the whole epsilon."""
    module, local = public.slots[question]
    if module == "c1":
        answer = c1_encode(user_views, public.c1, local, rng)
    elif module == "c2":
        answer = float(c2_encode(user_views, public.c2, local, rng))
    else:
        answer = float(c3_encode(user_views, public.c3, rng))
    return UserReport(module, question, (answer,), public.epsilon)


def composite_server_fit(reports: Sequence[UserReport], public: CompositePublic) -> CompositeFit:
    """Server side: each module's estimator and gate on its third; C1 matches on C3's weights."""
    by_module: dict[str, list[UserReport]] = {m: [] for m in COMPOSITE_MODULES}
    bound = hm_bound(public.epsilon)
    for r in reports:
        module, local = public.slots[r.question]
        if r.module != module:
            raise ValueError(f"question {r.question} belongs to {module!r}, not {r.module!r}")
        if module == "c1" and not abs(r.answer[0]) <= bound:
            raise ValueError(f"C1 answer {r.answer[0]} outside the HM bound {bound}")
        by_module[module].append(UserReport(module, local, r.answer, r.epsilon))
    c3 = c3_server_fit(by_module["c3"], public.c3)
    c2 = c2_server_fit(by_module["c2"], public.c2)
    # The gate's null stays the prior's; only the moment matching sees C3's fitted weights.
    c1 = c1_server_fit(by_module["c1"], replace(public.c1, regime_weights=c3.regime_weights))
    return CompositeFit(
        public.roster_size, public.module_users, public.questions, c1, c2, c3, public.rule_n
    )


def _gate_facts(fit: C1Fit | C2Fit | C3Fit) -> dict[str, Any]:
    return {
        "gate_statistic": float(fit.gate_statistic),
        "gate_p_value": float(fit.gate_p_value),
        "gate_rejected": bool(fit.gate_rejected),
    }


def module_facts(fit: C1Fit | C2Fit | C3Fit) -> dict[str, Any]:
    """JSON-ready record of one module's fit: report histograms, gate and fitted values.

    C3 counts reports per answer (label); C2 per answer of each question group; C1's
    answers are continuous, so it counts reports per public gate bin of each question.
    """
    if isinstance(fit, C3Fit):
        return {
            "reports": int(sum(fit.counts)),
            "histogram": {"regime": list(fit.counts)},
            **_gate_facts(fit),
            "regime_weights": list(fit.regime_weights),
        }
    if isinstance(fit, C2Fit):
        return {
            "reports": int(sum(map(sum, fit.counts))),
            "histogram": {n: list(c) for n, c in zip(C2_GROUP_NAMES, fit.counts, strict=True)},
            **_gate_facts(fit),
            "od_shares": None if fit.od_shares is None else list(fit.od_shares),
            "departure_shares": list(fit.departure_shares),
        }
    return {
        "reports": int(sum(map(sum, fit.counts))),
        "histogram": {n: list(c) for n, c in zip(C1_QUESTIONS, fit.counts, strict=True)},
        "means": list(fit.means),
        **_gate_facts(fit),
        "speed_level": float(fit.speed_level),
        "decay_per_s": float(fit.decay_per_s),
    }


@register("generator", "uldp_synth")
class UldpSynthGenerator(UldpGenerator):
    """User-level pure-epsilon-LDP synthesis: one module calibrates the public simulator."""

    generator_id: ClassVar[str] = "uldp_synth"

    def __init__(
        self,
        network: RoadNetwork,
        epsilon: float,
        module: str = "c3",
        zones_per_side: int = 3,
        seed: int = 0,
        confusion_trips: int = CONFUSION_TRIPS_PER_REGIME,
        gate_draws: int = GATE_DRAWS,
        band_origins: int = BAND_ORIGINS,
        moment_trips: int = C1_TRIPS_PER_REGIME,
        rule_n: int | None = None,
    ) -> None:
        """Build the public simulator; ``module`` picks ``c3``, ``c2``, ``c1`` or ``all``.

        ``all`` is the composite arm: a public draw gives each module a third of the
        roster, and every user answers only their module's question with the whole epsilon.

        ``confusion_trips`` (C3), ``band_origins`` (C2 and C1's length origins),
        ``moment_trips`` (C1's prior trips per regime) and ``gate_draws`` are Monte Carlo
        sizes of public objects and of the gate's p-value; keep the defaults outside tests.

        ``rule_n`` (composite only) fixes the n of the public n·ε² rule, so the question
        counts no longer follow the roster: the target generator and every LiRA shadow,
        whose rosters differ, ask the same questions (plan §7.1 point 3). Without it the
        counts follow the roster size, and ``fit_facts`` says so.
        """
        if module not in MODULES:
            raise ValueError(f"uldp_synth: module {module!r} is not one of {MODULES}")
        if not epsilon > 0:
            raise ValueError(f"uldp_synth: epsilon must be > 0, got {epsilon}")
        if min(confusion_trips, gate_draws, band_origins, moment_trips) < 1:
            raise ValueError(
                "uldp_synth: confusion_trips, gate_draws, band_origins and moment_trips "
                "must be >= 1"
            )
        if rule_n is not None and (isinstance(rule_n, bool) or int(rule_n) != rule_n):
            raise ValueError(f"uldp_synth: rule_n must be an integer, got {rule_n!r}")
        if rule_n is not None and rule_n < 1:
            raise ValueError(f"uldp_synth: rule_n must be >= 1, got {rule_n}")
        self.rule_n = None if rule_n is None else int(rule_n)
        self.moment_trips = int(moment_trips)
        self.confusion_trips = int(confusion_trips)
        self.band_origins = int(band_origins)
        self.gate_draws = int(gate_draws)
        self.epsilon = float(epsilon)
        self.seed = seed
        self.module = module
        self.zones_per_side = zones_per_side
        self.sim = PublicSimulator(network, zones_per_side=zones_per_side)
        self.map_id = f"osm_{network.region}"
        self._public: C3Public | C2Public | C1Public | CompositePublic | None = None

    def prior_sim_params(self) -> SimParams:
        """The one shared public prior (``public_sim.prior_params``); no per-module prior."""
        return prior_params()

    def public_params(self) -> Any:
        """The module's public objects (C3: catalogue, M; C2: prior shares; C1: moment samples).

        The composite's plan (users and questions per module) also depends on the roster
        size, so it needs the roster and is rebuilt when the roster size changes.
        """
        if self.module == "all":
            n = len(require_roster(self))
            if not (isinstance(self._public, CompositePublic) and self._public.roster_size == n):
                sizes, names, slots = composite_layout(n, self.epsilon, self.rule_n)
                self._public = CompositePublic(
                    self._c1_public(),
                    self._c2_public(),
                    self._c3_public(),
                    self.epsilon,
                    n,
                    sizes,
                    names,
                    slots,
                    self.rule_n,
                )
            return self._public
        if self._public is None and self.module == "c1":
            self._public = self._c1_public()
        if self._public is None and self.module == "c2":
            self._public = self._c2_public()
        if self._public is None:
            self._public = self._c3_public()
        return self._public

    def _c1_public(self) -> C1Public:
        return c1_public(
            self.sim,
            self.epsilon,
            self.prior_sim_params(),
            self.moment_trips,
            self.band_origins,
            self.gate_draws,
        )

    def _c2_public(self) -> C2Public:
        prior = self.prior_sim_params()
        od = gravity_od_shares(self.sim, prior)
        return C2Public(
            self.sim,
            self.epsilon,
            od,
            gravity_band_shares(self.sim, self.band_origins),
            np.asarray(prior.departure_shares, dtype=np.float64),
            od[:, None] * gravity_band_given_od(self.sim, self.band_origins),
            self.gate_draws,
        )

    def _c3_public(self) -> C3Public:
        prior = self.prior_sim_params()
        sigma = time_log_sigma()
        m = confusion_matrix(
            self.sim, prior.regimes, prior.regime_weights, sigma, self.confusion_trips
        )
        return C3Public(
            self.sim,
            prior.regimes,
            prior.regime_weights,
            sigma,
            m,
            self.epsilon,
            self.gate_draws,
        )

    def report_space(self, public: Any) -> ReportSpace:
        """C3: one label; C2: four slots (OD cell, OD cell, band, period); C1: two moments.

        The composite's questions are its public slots, each owned by one module. Every
        question has its own range: a C1 answer lies within the HM output bound, a C2 or
        C3 answer is a category index in [0, k - 1] for that question's k.
        """
        if isinstance(public, CompositePublic):
            b = hm_bound(public.epsilon)
            ranges = tuple(
                (-b, b)
                if m == "c1"
                else _c2_range(public.c2, local)
                if m == "c2"
                else (0.0, float(public.c3.k - 1))
                for m, local in public.slots
            )
            owner = tuple(COMPOSITE_MODULES.index(m) for m, _ in public.slots)
            high = max(hi for _, hi in ranges)
            return ReportSpace(COMPOSITE_MODULES, len(public.slots), 1, -b, high, owner, ranges)
        if isinstance(public, C1Public):
            b = hm_bound(public.epsilon)
            ranges = tuple((-b, b) for _ in C1_QUESTIONS)
            return ReportSpace(("c1",), len(C1_QUESTIONS), 1, -b, b, None, ranges)
        if isinstance(public, C2Public):
            ranges = tuple(_c2_range(public, q) for q in range(len(C2_QUESTION_GROUPS)))
            high = max(hi for _, hi in ranges)
            return ReportSpace(("c2",), len(C2_QUESTION_GROUPS), 1, 0.0, high, None, ranges)
        k1 = float(public.k - 1)
        return ReportSpace((self.module,), 1, 1, 0.0, k1, None, ((0.0, k1),))

    @staticmethod
    def encode_user(
        user_views: Sequence[TrajectoryView], public: Any, question: int, rng: np.random.Generator
    ) -> UserReport:
        """Phone side: the module's single randomised answer to the public question."""
        if isinstance(public, CompositePublic):
            return composite_encode(user_views, public, question, rng)
        if isinstance(public, C1Public):
            y = c1_encode(user_views, public, question, rng)
            return UserReport("c1", question, (y,), public.epsilon)
        if isinstance(public, C2Public):
            answer = c2_encode(user_views, public, question, rng)
            return UserReport("c2", question, (float(answer),), public.epsilon)
        label = c3_encode(user_views, public, rng)
        return UserReport("c3", question, (float(label),), public.epsilon)

    @staticmethod
    def server_fit(reports: Sequence[UserReport], public: Any) -> Any:
        """Server side: the module's fit from the reports alone."""
        if isinstance(public, CompositePublic):
            return composite_server_fit(reports, public)
        if isinstance(public, C1Public):
            return c1_server_fit(reports, public)
        if isinstance(public, C2Public):
            return c2_server_fit(reports, public)
        return c3_server_fit(reports, public)

    def sim_params(self) -> SimParams:
        """Simulator parameters of the fitted module (C3 weights; C2 OD, periods; C1 speed, decay).

        The composite sets all three; each module's part stays the prior's unless its own
        gate rejected.

        C1's speed level scales every period factor and its decay is set on every
        regime alike (closed decision: C1 corrections apply equally to all C3 regimes).
        """
        if self.fitted is None:
            raise RuntimeError("uldp_synth used before fit()")
        if isinstance(self.fitted, CompositeFit):
            c1, c2, c3 = self.fitted.c1, self.fitted.c2, self.fitted.c3
            params = replace(
                self.prior_sim_params(),
                regime_weights=c3.regime_weights,
                od_shares=c2.od_shares,
                departure_shares=c2.departure_shares,
            )
            if not c1.gate_rejected:
                return params
            return replace(
                params,
                regimes=tuple(
                    replace(r, distance_decay_per_s=c1.decay_per_s) for r in params.regimes
                ),
                period_speed_factors=tuple(c1.speed_level * f for f in params.period_speed_factors),
            )
        if isinstance(self.fitted, C1Fit):
            prior = self.prior_sim_params()
            if not self.fitted.gate_rejected:
                return prior
            level, decay = self.fitted.speed_level, self.fitted.decay_per_s
            return replace(
                prior,
                regimes=tuple(replace(r, distance_decay_per_s=decay) for r in prior.regimes),
                period_speed_factors=tuple(level * f for f in prior.period_speed_factors),
            )
        if isinstance(self.fitted, C2Fit):
            return replace(
                self.prior_sim_params(),
                od_shares=self.fitted.od_shares,
                departure_shares=self.fitted.departure_shares,
            )
        return replace(self.prior_sim_params(), regime_weights=self.fitted.regime_weights)

    def fit_facts(self) -> dict[str, Any]:
        """JSON-ready record of the fit for ``run.json``: per module reports, gate, fitted values.

        The composite adds the roster size, the rule's ``rule_n`` and where the question
        counts came from (``rule_n`` or ``roster``), the counts per module and, per module,
        its users and asked questions (the public n·ε² rule).
        """
        if self.fitted is None:
            raise RuntimeError("uldp_synth used before fit()")
        if not isinstance(self.fitted, CompositeFit):
            return {"module": self.module, "modules": {self.module: module_facts(self.fitted)}}
        fit = self.fitted
        fits: dict[str, C1Fit | C2Fit | C3Fit] = {"c1": fit.c1, "c2": fit.c2, "c3": fit.c3}
        counts = {m: len(q) for m, q in zip(COMPOSITE_MODULES, fit.questions, strict=True)}
        modules = {}
        for m, users, names in zip(COMPOSITE_MODULES, fit.module_users, fit.questions, strict=True):
            modules[m] = {
                "users": int(users),
                "n_questions": len(names),
                "questions": list(names),
                **module_facts(fits[m]),
            }
        return {
            "module": self.module,
            "roster_size": fit.roster_size,
            "rule_n": fit.rule_n,
            "question_count_source": "roster" if fit.rule_n is None else "rule_n",
            "question_counts": counts,
            "modules": modules,
        }

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n timed trips (``TimedRoute`` payloads), deterministic in the seed."""
        params = self.sim_params()
        ph = simulator_params_hash(
            self.sim,
            params,
            module=self.module,
            epsilon=self.epsilon,
            zones_per_side=self.zones_per_side,
        )
        return simulate_trips(self.sim, params, n, seed, self.generator_id, self.map_id, ph)

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """Exact, floor-bounded log-likelihood under the fitted mixture (public caches only)."""
        return self.sim.log_prob(self.sim_params(), edge_seq)
