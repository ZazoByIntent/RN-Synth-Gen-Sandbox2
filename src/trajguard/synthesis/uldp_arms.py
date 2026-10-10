"""Control arms of the user-level LDP mechanisms: the public prior and the oracle (ULDP P3).

Both arms run the public simulator of :mod:`trajguard.synthesis.public_sim`
(docs/NACRT_ULDP_SINTEZA.md §4.1). The **prior** arm (``uldp_prior``) is the simulator
with its public defaults, the limit epsilon -> 0: it reads nothing from the training
data. The **oracle** arm (``uldp_oracle``) is the simulator with parameters estimated
**without noise** from the training users, each user weighing equally. The oracle is
NOT private and exists for evaluation only: it marks how far a perfect estimator of
the same parameters would get, and a mechanism arm's gain is the share of the
prior-to-oracle gap it closes (``evaluation.timed_utility.utility_gain``).

What the oracle estimates (everything else stays at the public prior):

- origin-destination zone shares (module C2), from the first and last link;
- departure-period shares (C1/C2), from the first GPS point in local time;
- regime weights over the shared catalogue of the prior (C3; walk, bike, motorised,
  ``public_sim.REGIME_CATALOGUE``): each trip goes to the regime whose jitter-free time
  on the trip's own route is closest, in log ratio, to the observed duration;
- the speed level of each departure period (C1): the mean log ratio of the chosen
  regime's time to the observed duration; and the trip jitter (C1): the spread around it.

Route-choice parameters (detour scale, U-turn penalty, class costs), the link jitter
and the turn delay stay at the prior (SESSION DECISION: at n of about 91 the plan
keeps route tastes at the prior and they partly describe the map matcher, §4.5).
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, replace
from typing import ClassVar

import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.privacy.base import params_hash
from trajguard.representation import TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator, views_by_user
from trajguard.synthesis.public_sim import (
    N_PERIODS,
    PUBLIC_SIM_VERSION,
    PublicSimulator,
    SimParams,
    prior_params,
)
from trajguard.synthesis.uldp_base import require_roster

#: Public clip of a trip's log speed ratio (regime time over observed duration): a
#: ratio below 1/20 or above 20 is a map-matching or timing artefact, not a speed.
LOG_RATIO_CLIP = math.log(20.0)


def simulator_params_hash(sim: PublicSimulator, params: SimParams, **extra: object) -> str:
    """Hash of everything a simulator arm's output depends on: map key, version, parameters."""
    return params_hash(
        {
            **extra,
            "map": sim.graph.key,
            "sim_version": PUBLIC_SIM_VERSION,
            "sim": asdict(params),
        }
    )


def simulate_trips(
    sim: PublicSimulator,
    params: SimParams,
    n: int,
    seed: int,
    generator_id: str,
    map_id: str,
    ph: str,
) -> list[SyntheticTrajectory]:
    """Sample n timed trips (``TimedRoute`` payloads) of one arm, deterministic in the seed."""
    routes = sim.simulate(params, n, np.random.default_rng(seed))
    return [
        SyntheticTrajectory(
            syn_id=f"{generator_id}/{seed}/{i}",
            generator_id=generator_id,
            params_hash=ph,
            payload=route,
            trained_on_split="train",
            map_id=map_id,
        )
        for i, route in enumerate(routes)
    ]


class _SimulatorArm(SyntheticGenerator):
    """A SyntheticGenerator that samples the public simulator under fixed parameters."""

    generator_id: ClassVar[str]
    #: True for an arm that reads training data without noise (evaluation only).
    non_private: ClassVar[bool]
    #: No epsilon: the prior spends none (epsilon -> 0), the oracle has no guarantee.
    epsilon: float | None = None

    def __init__(self, network: RoadNetwork, zones_per_side: int = 3, seed: int = 0) -> None:
        """Build the public simulator on the network; nothing here touches data."""
        self.sim = PublicSimulator(network, zones_per_side=zones_per_side)
        self.zones_per_side = zones_per_side
        self.seed = seed
        self.map_id = f"osm_{network.region}"
        self.params: SimParams = prior_params()
        self._fitted = False

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample n timed trips (``TimedRoute`` payloads), deterministic in the seed."""
        if not self._fitted:
            raise RuntimeError(f"{type(self).__name__}.generate called before fit()")
        ph = simulator_params_hash(self.sim, self.params, zones_per_side=self.zones_per_side)
        return simulate_trips(self.sim, self.params, n, seed, self.generator_id, self.map_id, ph)

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """Exact, floor-bounded log-likelihood of an edge sequence under the arm's parameters."""
        if not self._fitted:
            raise RuntimeError(f"{type(self).__name__}.sequence_log_prob called before fit()")
        return self.sim.log_prob(self.params, edge_seq)


@register("generator", "uldp_prior")
class UldpPriorGenerator(_SimulatorArm):
    """Prior arm: the public simulator with public defaults (epsilon -> 0); ignores the data."""

    generator_id = "uldp_prior"
    non_private = False

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Keep the public prior; the training data is deliberately not read."""
        self.params = prior_params()
        self._fitted = True


@register("generator", "uldp_oracle")
class UldpOracleGenerator(_SimulatorArm):
    """Oracle arm: simulator parameters estimated without noise, per user. NOT private."""

    generator_id = "uldp_oracle"
    non_private = True
    needs_user_roster = True

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Estimate the calibratable parameters from the training users without noise.

        Raises RuntimeError without a roster: shadow fits hand the roster over too (P5),
        with every candidate under its own user_id.
        """
        grouped = views_by_user(train, require_roster(self))
        users = [g for g in grouped.values() if g]
        self.params = oracle_params(self.sim, users, prior_params())
        self._fitted = True


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    """Weighted mean of a non-empty sample."""
    return float(np.average(values, weights=weights))


def oracle_params(
    sim: PublicSimulator, users: Sequence[Sequence[TrajectoryView]], prior: SimParams
) -> SimParams:
    """Noise-free, user-weighted estimates of the calibratable parameters (non-private).

    Each user (group of views) with at least one usable trip weighs one, split evenly
    over its trips; in a per-period estimate each user with trips in that period weighs
    one. A view needs a known edge sequence for the OD shares and, in addition, a clean
    GPS trip with a positive duration for every time estimate. A parameter with no
    usable trip keeps its prior value.
    """
    n_z = sim.n_zones
    od = np.zeros(n_z * n_z)
    dep = np.zeros(N_PERIODS)
    regime_w = np.zeros(len(prior.regimes))
    # Per period: (user index, log ratio of the chosen regime) of every timed trip.
    timed: list[list[tuple[int, float]]] = [[] for _ in range(N_PERIODS)]
    n_od_users = n_time_users = 0
    for u, views in enumerate(users):
        seqs = [(v, v.as_sequence()) for v in views]
        seqs = [(v, s) for v, s in seqs if sim.known(s)]
        if seqs:
            n_od_users += 1
            for _, s in seqs:
                zo, zd = sim.od_zones(s)
                od[zo * n_z + zd] += 1.0 / len(seqs)
        trips = []
        for v, s in seqs:
            if v.clean is None or len(v.clean.points) < 2:
                continue
            t0, t1 = v.clean.points[0][2], v.clean.points[-1][2]
            if t1 > t0:
                trips.append((s, t0, t1 - t0))
        if not trips:
            continue
        n_time_users += 1
        for s, t0, duration in trips:
            ratios = [
                float(
                    np.clip(
                        math.log(sim.route_time_s(s, r) / duration), -LOG_RATIO_CLIP, LOG_RATIO_CLIP
                    )
                )
                for r in prior.regimes
            ]
            k = int(np.argmin(np.abs(ratios)))
            regime_w[k] += 1.0 / len(trips)
            period = sim.departure_period(t0)
            dep[period] += 1.0 / len(trips)
            timed[period].append((u, ratios[k]))

    params = prior
    if n_od_users:
        params = replace(params, od_shares=tuple(float(x) for x in od / od.sum()))
    if not n_time_users:
        return params
    factors = list(prior.period_speed_factors)
    residuals: list[float] = []
    residual_w: list[float] = []
    for p, rows in enumerate(timed):
        if not rows:
            continue
        per_user: dict[int, int] = {}
        for u, _ in rows:
            per_user[u] = per_user.get(u, 0) + 1
        w = [1.0 / per_user[u] for u, _ in rows]
        level = _weighted_mean([r for _, r in rows], w)
        factors[p] = math.exp(level)
        residuals.extend(r - level for _, r in rows)
        residual_w.extend(w)
    sigma = math.sqrt(_weighted_mean([r * r for r in residuals], residual_w))
    return replace(
        params,
        regime_weights=tuple(float(x) for x in regime_w / regime_w.sum()),
        departure_shares=tuple(float(x) for x in dep / dep.sum()),
        period_speed_factors=tuple(factors),
        trip_jitter_sigma=sigma,
    )
