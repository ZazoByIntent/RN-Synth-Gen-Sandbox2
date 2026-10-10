"""Public road-network simulator shared by the user-level LDP mechanisms (ULDP P3).

The simulator is built from the public map (the OSM ``RoadNetwork``) and cited
constants only; nothing in this module reads training data or is tuned on Geolife
(docs/NACRT_ULDP_SINTEZA.md §4.1, finding F8). It samples timed trips as
``TimedRoute`` payloads and scores edge sequences exactly (§4.7).

One trip, in sampling order:

1. a **regime** from the regime catalogue (module C3 calibrates the weights);
2. an **origin** node by public road-length mass and a **destination** node by a
   gravity model (mass times an exponential decay in free-flow cost), or, when an
   origin-destination zone table is set (module C2), a zone pair from that table and
   then both nodes by mass inside their zones;
3. a **departure** period from the period shares, uniform inside the period, on one
   public anchor day in local time (modules C1/C2);
4. a **route** by a Boltzmann walk towards the destination: at every node an outgoing
   link is chosen with probability falling exponentially in the cost it adds over the
   shortest remaining cost (cost-to-go from one reverse Dijkstra search per
   destination); after a public step bound the walk finishes on the shortest path, so
   every route is valid on the road network by construction;
5. **times**: free-flow link time (OSM ``maxspeed`` or the cited class speed) divided
   by the regime and period speed factors, times log-normal trip jitter and AR(1)
   log-normal link jitter, plus a delay on each turn (module C1 calibrates these).

The likelihood of an edge sequence is log P(O, D) plus the log probabilities of the
walk steps; a public floor on every term covers unreachable destinations, gaps
between links and the step bound. For a catalogue with several regimes it is the
weighted mixture over regimes. Times never enter it (the attack sees links only).

Expensive derived artefacts (the prepared graph and the shortest-path trees) live in
a process-wide cache keyed by a content hash of the map plus :data:`PUBLIC_SIM_VERSION`,
shared by every generator built on the same map.
"""

import hashlib
import heapq
import math
import re
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import networkx as nx
import numpy as np

from trajguard.datamodel import BEIJING_UTC_OFFSET_S, LinkVisit, TimedRoute
from trajguard.evaluation.timed_utility import DEPARTURE_PERIODS
from trajguard.maps.base import RoadNetwork
from trajguard.representation import Grid

#: Version of the prepared-graph layout and the cost model; part of every cache key, so
#: changing either invalidates every cached artefact.
PUBLIC_SIM_VERSION = "public_sim/1"

#: Free-flow speed (km/h) per OSM ``highway`` class, used when an edge carries no
#: numeric OSM ``maxspeed``. Urban classes take the middle design speed of their class
#: in the Chinese urban road design code CJJ 37-2012 (城市道路工程设计规范, §3.2):
#: expressway 100/80/60, arterial 60/50/40, secondary arterial 50/40/30, branch road
#: 40/30/20 km/h. Motorways take the middle freeway design speed of JTG B01-2014
#: (公路工程技术标准: 120/100/80 km/h). Verified (session 1) against the design-speed
#: table of https://wiki.openstreetmap.org/wiki/Key:highway:CN, which cites
#: GB 55011-2021 / CJJ 37-2012 (urban) and JTG B01-2014 (highways); the codes' own texts
#: are paywalled and were not opened. The OSM class mapping (trunk = urban expressway,
#: primary = arterial, secondary = secondary arterial, tertiary = branch road) follows
#: https://wiki.openstreetmap.org/wiki/China_tagging_guidelines (verified, session 1).
#: UNVERIFIED (session 1): a link (ramp) takes the lowest design speed of its parent
#: class; this is a conservative choice, no ramp rule of CJJ 37-2012 was checked.
#: Residential and unclassified roads take 30 km/h, the limit on an urban road without
#: a centre line and without a speed sign: Art. 45 of the Regulations for the
#: Implementation of the Road Traffic Safety Law of the PRC (2004), "没有道路中心线的
#: 道路，城市道路为每小时30公里" (verified, session 1, official text at
#: https://www.gov.cn/zhengce/content/2008-03/28/content_3745.htm). Living streets and
#: service roads take 20 km/h, the lowest branch-road design speed of CJJ 37-2012
#: (value verified as above; assigning it to these classes is a mapping choice).
CLASS_SPEED_KMH: dict[str, float] = {
    "motorway": 100.0,
    "motorway_link": 80.0,
    "trunk": 80.0,
    "trunk_link": 60.0,
    "primary": 50.0,
    "primary_link": 40.0,
    "secondary": 40.0,
    "secondary_link": 30.0,
    "tertiary": 30.0,
    "tertiary_link": 20.0,
    "unclassified": 30.0,
    "residential": 30.0,
    "living_street": 20.0,
    "service": 20.0,
}
#: Any other class: the Art. 45 urban limit without a centre line (verified, see above).
DEFAULT_SPEED_KMH = 30.0
_MPH_TO_KMH = 1.609344  # international mile, exact

#: Route-choice scale of the Boltzmann walk, seconds of added cost per unit of log
#: probability: the inverse of the travel-time coefficient -2.494 per minute of the
#: recursive logit (RL) route-choice model estimated on the Borlänge network, i.e.
#: 60 / 2.494 = 24.1 s. Source (verified, session 1): Mai, Fosgerau & Frejinger 2015,
#: "A nested recursive logit model for route choice analysis", Transportation Research
#: Part B 75:100-112, Table 4, column RL (working paper CIRRELT-2014-39,
#: https://www.cirrelt.ca/DocumentsTravail/CIRRELT-2014-39.pdf). The minute unit is that
#: of the shared specification in Fosgerau, Frejinger & Karlström 2013 (TR-B 56:70-80,
#: eq. 18), whose own Table 3 does NOT carry these values: it reports -2.45 and fixes the
#: U-turn coefficient at -20 (working paper https://mpra.ub.uni-muenchen.de/48707/).
DETOUR_SCALE_S = 60.0 / 2.494
#: Added cost of an immediate U-turn: the U-turn coefficient -4.459 of the same RL
#: estimate (Mai et al. 2015, Table 4, column RL; verified, session 1) expressed in
#: seconds of travel time, 60 * 4.459 / 2.494 = 107.3 s.
UTURN_PENALTY_S = 60.0 * 4.459 / 2.494

#: Public step bound of the walk: after STEP_BOUND_FACTOR times the free-flow shortest
#: path's link count plus STEP_BOUND_SLACK steps the route finishes on the shortest
#: path. Structural (it only guarantees termination), not fitted to any data.
STEP_BOUND_FACTOR = 2.0
STEP_BOUND_SLACK = 10

#: Public probability floor of every likelihood term (the value ``rn_ldp_synth`` uses).
PROB_FLOOR = 1e-12
_LOG_FLOOR = math.log(PROB_FLOOR)

#: A change of heading of at least this many degrees between consecutive links counts
#: as a turn for the turn delay (the usual split of straight on vs turning).
#: SESSION DECISION (session 1): no cited source; a structural threshold, frozen with the
#: catalogue (finding F8) and never tuned on Geolife.
TURN_ANGLE_DEG = 45.0

#: Local date of the public anchor day every synthetic trip departs on. Only the local
#: hour of day enters the timed metrics; the date is a fixed public choice.
ANCHOR_LOCAL_DATE = (2008, 1, 1)

#: Bound on the cached shortest-path trees per cost model and direction (least recently
#: used ones are dropped): about 1100 destinations per arm on the 35 764-node Beijing map
#: (§4.1) is about 0.3 GB of float64 trees.
MAX_CACHED_TREES = 1200

#: Departure-period names and boundaries, shared with the timed utility metrics.
PERIODS: tuple[tuple[str, float, float], ...] = DEPARTURE_PERIODS
N_PERIODS = len(PERIODS)


@dataclass(frozen=True)
class Regime:
    """One member of the regime catalogue (module C3): how a class of trips routes and moves.

    ``speed_factor`` scales the free-flow speed and ``speed_cap_mps`` caps it (a walking
    regime); both also shape route choice, since route cost is the regime's link time.
    ``class_cost`` multiplies the route cost of a road class (module C1).
    ``distance_decay_per_s`` is the gravity decay of destination choice in free-flow
    cost; it applies only while no origin-destination table is set.
    """

    name: str
    speed_factor: float = 1.0
    speed_cap_mps: float | None = None
    detour_scale_s: float = DETOUR_SCALE_S
    uturn_penalty_s: float = UTURN_PENALTY_S
    distance_decay_per_s: float = 0.0
    class_cost: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        """Reject non-positive speeds, scales and class costs and negative penalties."""
        if not self.speed_factor > 0:
            raise ValueError(f"Regime {self.name}: speed_factor must be > 0")
        if self.speed_cap_mps is not None and not self.speed_cap_mps > 0:
            raise ValueError(f"Regime {self.name}: speed_cap_mps must be > 0")
        if not self.detour_scale_s > 0:
            raise ValueError(f"Regime {self.name}: detour_scale_s must be > 0")
        if self.uturn_penalty_s < 0 or self.distance_decay_per_s < 0:
            raise ValueError(f"Regime {self.name}: penalties and decay must be >= 0")
        if any(not m > 0 for _, m in self.class_cost):
            raise ValueError(f"Regime {self.name}: class_cost multipliers must be > 0")


#: Walking speed: the middle of the 3-4 km/h walking speed the national guideline
#: assumes (住房城乡建设部, 城市步行和自行车交通系统规划设计导则, MOHURD, Dec 2013,
#: explanatory note on public-bicycle station spacing, "按照步行速度3～4km/h"; verified,
#: session D, https://www.gov.cn/gzdt/att/att/site1/20140114/001e3741a2cc143f348801.pdf).
WALK_SPEED_KMH = 3.5
#: Cycling speed: the same guideline, §3.1.8: an e-bike in a non-motorised lane rides
#: "at ordinary bicycle speed, at most 15 km/h" (应按人力自行车速度行驶，最高速度不得超过
#: 15公里/小时; verified, session D, same URL). SESSION DECISION: the bound is used as the
#: bicycle regime's speed cap.
BIKE_SPEED_KMH = 15.0

#: The shared regime catalogue (frozen, finding F8), part of the ONE public prior every
#: ULDP arm starts from (prior, oracle and every ``uldp_synth`` module). Walk and bike
#: cap the speed on every link; motorised is the free-flow regime (OSM ``maxspeed`` or
#: the cited class speed). The Beijing drive graph has no footways or cycleways (P9a),
#: so the regimes differ by speed only (route choice follows the regime's link times).
REGIME_CATALOGUE: tuple[Regime, ...] = (
    Regime("walk", speed_cap_mps=WALK_SPEED_KMH / 3.6),
    Regime("bike", speed_cap_mps=BIKE_SPEED_KMH / 3.6),
    Regime("motorised"),
)
#: The free-flow cost model (OSM ``maxspeed`` or the cited class speed, no factor, cap or
#: class cost): the cost the gravity decay of destination choice acts on.
FREE_FLOW_REGIME = Regime("free_flow")
#: Public prior weights of the catalogue: uniform. Source: the plan itself,
#: docs/NACRT_ULDP_SINTEZA.md §4.3 ("the arm with uniform weights is the baseline
#: 'public prior plus one label'"; shares are shrunk towards uniform). No mode share is
#: read from Geolife, and no published Beijing mode split is adopted, since the plan
#: names the uniform prior.
REGIME_PRIOR_WEIGHTS: tuple[float, ...] = (1.0 / 3.0,) * 3


def _uniform_period_shares() -> tuple[float, ...]:
    """Period shares of a departure time uniform over the 24-hour day."""
    return tuple((end - start) / 24.0 for _, start, end in PERIODS)


@dataclass(frozen=True)
class SimParams:
    """Every parameter the ULDP modules calibrate; :func:`prior_params` is the public prior.

    The defaults equal the prior except the regimes: one neutral free-flow regime, a
    building block for single-regime simulation (the prior sets the catalogue).

    - ``regimes`` / ``regime_weights``: the catalogue and its mixture weights (C3);
    - ``od_shares``: row-major Z x Z origin-destination zone shares, or None for the
      gravity prior (C2);
    - ``departure_shares``: shares of the five departure periods (C1/C2);
    - ``period_speed_factors``: speed level per departure period (C1);
    - ``trip_jitter_sigma``, ``link_jitter_sigma``, ``link_jitter_rho``: log-normal
      trip jitter and AR(1) log-normal link jitter of the link times (C1);
    - ``turn_delay_s``: delay added to a link that ends in a turn (C1).
    """

    regimes: tuple[Regime, ...] = (Regime("public"),)
    regime_weights: tuple[float, ...] = (1.0,)
    od_shares: tuple[float, ...] | None = None
    departure_shares: tuple[float, ...] = field(default_factory=_uniform_period_shares)
    period_speed_factors: tuple[float, ...] = (1.0,) * N_PERIODS
    # No cited dispersion or turn-delay constant is adopted: the prior is the
    # deterministic free-flow time and the modules calibrate these (SESSION DECISION).
    trip_jitter_sigma: float = 0.0
    link_jitter_sigma: float = 0.0
    link_jitter_rho: float = 0.0
    turn_delay_s: float = 0.0

    def __post_init__(self) -> None:
        """Reject shape mismatches, negative shares and out-of-range jitter."""
        if not self.regimes or len(self.regimes) != len(self.regime_weights):
            raise ValueError("SimParams: one weight per regime is required")
        for name, shares in (
            ("regime_weights", self.regime_weights),
            ("departure_shares", self.departure_shares),
            ("od_shares", self.od_shares or (1.0,)),
        ):
            if any(not (s >= 0) for s in shares) or not sum(shares) > 0:
                raise ValueError(f"SimParams: {name} must be >= 0 with a positive sum")
        if len(self.departure_shares) != N_PERIODS or len(self.period_speed_factors) != N_PERIODS:
            raise ValueError(f"SimParams: departure periods need {N_PERIODS} entries")
        if any(not f > 0 for f in self.period_speed_factors):
            raise ValueError("SimParams: period_speed_factors must be > 0")
        if self.trip_jitter_sigma < 0 or self.link_jitter_sigma < 0 or self.turn_delay_s < 0:
            raise ValueError("SimParams: jitter sigmas and turn delay must be >= 0")
        if not -1.0 < self.link_jitter_rho < 1.0:
            raise ValueError("SimParams: link_jitter_rho must lie in (-1, 1)")


def prior_params() -> SimParams:
    """The one shared public prior: the regime catalogue under its prior weights, the rest default.

    Gravity OD without decay, uniform departures and free-flow times (the SimParams
    defaults). Every ULDP arm (``uldp_prior``, ``uldp_oracle``, every ``uldp_synth``
    module) starts from exactly these parameters.
    """
    return SimParams(regimes=REGIME_CATALOGUE, regime_weights=REGIME_PRIOR_WEIGHTS)


def parse_maxspeed_kmh(raw: object) -> float | None:
    """First numeric OSM ``maxspeed`` value in km/h (mph converted); None when absent."""
    text = str(raw)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match is None:
        return None
    value = float(match.group())
    if value <= 0:
        return None
    return value * _MPH_TO_KMH if "mph" in text.lower() else value


def primary_highway_class(raw: object) -> str:
    """The first OSM ``highway`` class of an edge (simplification can merge several)."""
    text = str(raw).strip("[]() ")
    first = text.split(",")[0].strip().strip("'\"")
    return first


def network_hash(network: RoadNetwork) -> str:
    """Content hash of what the simulator reads: map frame, nodes, edges, classes, speeds."""
    digest = hashlib.sha256(PUBLIC_SIM_VERSION.encode())
    digest.update(repr(map_frame(network)).encode())
    nodes = network.nodes[["node_id", "x", "y", "lon", "lat"]].sort_values("node_id")
    digest.update(nodes.to_numpy(dtype=np.float64).tobytes())
    edges = network.edges.sort_values("edge_id")
    digest.update(edges[["edge_id", "u", "v", "length_m"]].to_numpy(dtype=np.float64).tobytes())
    for col in ("highway", "maxspeed"):
        digest.update("\x1f".join(str(x) for x in edges[col]).encode())
    return digest.hexdigest()[:16]


def map_frame(network: RoadNetwork) -> tuple[float, float, float, float]:
    """The public map frame (meta.json ``bbox``) the origin-destination zones are cut on.

    It is the frame the timed utility metric ``od3x3_jsd`` cuts its zones on (the
    config's ``map.bbox``, equal to meta.json's), so simulator zones and metric zones are
    the same cells; a network without a frame is rejected rather than replaced by the
    node extent.
    """
    if network.bbox is None:
        raise ValueError(
            "the public simulator needs the map frame (RoadNetwork.bbox from meta.json); "
            "load the network through its MapSource"
        )
    min_lon, min_lat, max_lon, max_lat = (float(v) for v in network.bbox)
    return (min_lon, min_lat, max_lon, max_lat)


def _dijkstra(
    ptr: list[int], adj: list[int], far: list[int], cost: list[float], src: int
) -> np.ndarray:
    """Single-source shortest costs over a CSR adjacency (``adj`` holds edge indices)."""
    dist = [math.inf] * (len(ptr) - 1)
    dist[src] = 0.0
    done = bytearray(len(ptr) - 1)
    heap = [(0.0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if done[u]:
            continue
        done[u] = 1
        for k in range(ptr[u], ptr[u + 1]):
            e = adj[k]
            v = far[e]
            nd = d + cost[e]
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return np.asarray(dist, dtype=np.float64)


def _csr(n: int, keys: np.ndarray, edges: np.ndarray) -> tuple[list[int], list[int]]:
    """CSR pointers and edge lists grouping ``edges`` by node ``keys``."""
    order = np.argsort(keys, kind="stable")
    counts = np.bincount(keys, minlength=n)
    ptr = np.concatenate(([0], np.cumsum(counts)))
    return [int(x) for x in ptr], [int(x) for x in edges[order]]


class PreparedGraph:
    """Public arrays derived from one road network: links, speeds, masses, zones, CSR.

    The origin-destination zones are a ``zones_per_side`` square grid over the public map
    frame (:func:`map_frame`); with 3 per side they are exactly the metric's 3 x 3 zones.

    Only links with both ends in the largest strongly connected component are usable,
    so every usable node reaches every other one and a walk never gets stuck.
    """

    def __init__(self, network: RoadNetwork, zones_per_side: int, key: str) -> None:
        self.key = key
        nodes = network.nodes.sort_values("node_id")
        edges = network.edges.sort_values("edge_id")
        self.node_ids = nodes["node_id"].to_numpy()
        self.node_index = {int(n): i for i, n in enumerate(self.node_ids)}
        n_nodes = len(self.node_ids)
        self.x = nodes["x"].to_numpy(dtype=np.float64)
        self.y = nodes["y"].to_numpy(dtype=np.float64)
        lon = nodes["lon"].to_numpy(dtype=np.float64)
        lat = nodes["lat"].to_numpy(dtype=np.float64)

        self.edge_ids = edges["edge_id"].to_numpy(dtype=np.int64)
        self.edge_index = {int(e): i for i, e in enumerate(self.edge_ids)}
        self.tail = np.array([self.node_index[int(u)] for u in edges["u"]], dtype=np.int64)
        self.head = np.array([self.node_index[int(v)] for v in edges["v"]], dtype=np.int64)
        # A zero-length link would make the cost-to-go non-decreasing along a step.
        self.length = np.maximum(edges["length_m"].to_numpy(dtype=np.float64), 0.1)
        self.highway = [primary_highway_class(h) for h in edges["highway"]]
        speeds = []
        for hw, raw in zip(self.highway, edges["maxspeed"], strict=True):
            kmh = parse_maxspeed_kmh(raw)
            speeds.append(kmh if kmh is not None else CLASS_SPEED_KMH.get(hw, DEFAULT_SPEED_KMH))
        self.free_flow_mps = np.asarray(speeds, dtype=np.float64) / 3.6
        self.bearing = np.arctan2(
            self.y[self.head] - self.y[self.tail], self.x[self.head] - self.x[self.tail]
        )

        digraph = nx.DiGraph()
        digraph.add_nodes_from(range(n_nodes))
        digraph.add_edges_from(zip(self.tail.tolist(), self.head.tolist(), strict=True))
        scc = max(nx.strongly_connected_components(digraph), key=len)
        self.in_scc = np.zeros(n_nodes, dtype=bool)
        self.in_scc[list(scc)] = True
        self.usable = self.in_scc[self.tail] & self.in_scc[self.head]
        use = np.flatnonzero(self.usable)
        self.out_ptr, self.out_adj = _csr(n_nodes, self.tail[use], use)
        self.in_ptr, self.in_adj = _csr(n_nodes, self.head[use], use)
        self.head_l = [int(h) for h in self.head]
        self.tail_l = [int(t) for t in self.tail]

        # Public road-length mass: half of every usable incident link's length.
        mass = np.zeros(n_nodes)
        np.add.at(mass, self.tail[use], self.length[use] / 2.0)
        np.add.at(mass, self.head[use], self.length[use] / 2.0)
        self.mass = mass

        # Zones are cut on the public map frame, the same cells as the metric's zones.
        self.bbox = map_frame(network)
        self.zones = Grid(bbox=self.bbox, n_rows=zones_per_side, n_cols=zones_per_side)
        self.n_zones = self.zones.n_cells
        self.zone = np.array([self.zones.cell_of(a, o) for a, o in zip(lat, lon, strict=True)])
        self.zone_mass = np.bincount(self.zone, weights=mass, minlength=self.n_zones)
        massive = np.bincount(self.zone, weights=(mass > 0).astype(float), minlength=self.n_zones)
        self.zone_massive_nodes = massive.astype(int)
        self._trees: dict[tuple[str, str], OrderedDict[int, np.ndarray]] = {}

    def tree(self, cost_key: str, cost: list[float], node: int, reverse: bool) -> np.ndarray:
        """Shortest costs to ``node`` (reverse) or from it (forward), LRU-cached per cost model."""
        cache = self._trees.setdefault((cost_key, "to" if reverse else "from"), OrderedDict())
        hit = cache.get(node)
        if hit is not None:
            cache.move_to_end(node)
            return hit
        if reverse:
            dist = _dijkstra(self.in_ptr, self.in_adj, self.tail_l, cost, node)
        else:
            dist = _dijkstra(self.out_ptr, self.out_adj, self.head_l, cost, node)
        cache[node] = dist
        if len(cache) > MAX_CACHED_TREES:
            cache.popitem(last=False)
        return dist


_PREPARED: dict[str, PreparedGraph] = {}


def prepared_graph(network: RoadNetwork, zones_per_side: int) -> PreparedGraph:
    """The process-wide cached prepared graph of a network, keyed by version and content."""
    key = f"{network_hash(network)}:z{zones_per_side}"
    hit = _PREPARED.get(key)
    if hit is None:
        hit = PreparedGraph(network, zones_per_side, key)
        _PREPARED[key] = hit
    return hit


class _Router:
    """Route cost, cost-to-go and Boltzmann step probabilities of one regime."""

    def __init__(self, g: PreparedGraph, regime: Regime) -> None:
        self.g = g
        self.regime = regime
        speed = g.free_flow_mps * regime.speed_factor
        if regime.speed_cap_mps is not None:
            speed = np.minimum(speed, regime.speed_cap_mps)
        mult = dict(regime.class_cost)
        factor = np.array([mult.get(h, 1.0) for h in g.highway])
        cost = g.length / speed * factor
        self.cost = [float(c) for c in cost]
        digest = hashlib.sha256(cost.tobytes()).hexdigest()[:16]
        self.key = f"{g.key}:{digest}"

    def to(self, dest: int) -> np.ndarray:
        """Cost-to-go of every node towards ``dest``."""
        return self.g.tree(self.key, self.cost, dest, reverse=True)

    def frm(self, origin: int) -> np.ndarray:
        """Shortest cost from ``origin`` to every node."""
        return self.g.tree(self.key, self.cost, origin, reverse=False)

    def sp_next(self, node: int, h: np.ndarray) -> int:
        """The shortest-path link out of ``node`` (lowest link cost plus cost-to-go)."""
        g = self.g
        best, best_v = -1, math.inf
        for k in range(g.out_ptr[node], g.out_ptr[node + 1]):
            e = g.out_adj[k]
            v = self.cost[e] + h[g.head_l[e]]
            if v < best_v:
                best, best_v = e, v
        return best

    def step_bound(self, origin: int, dest: int, h: np.ndarray) -> int:
        """Public step bound: a multiple of the shortest path's link count plus slack."""
        hops, node = 0, origin
        while node != dest:
            node = self.g.head_l[self.sp_next(node, h)]
            hops += 1
        return int(math.ceil(STEP_BOUND_FACTOR * hops)) + STEP_BOUND_SLACK

    def step(self, node: int, prev: int, h: np.ndarray) -> tuple[list[int], np.ndarray]:
        """Candidate links out of ``node`` and their Boltzmann probabilities."""
        g, r = self.g, self.regime
        cand = g.out_adj[g.out_ptr[node] : g.out_ptr[node + 1]]
        added = np.empty(len(cand))
        for i, e in enumerate(cand):
            a = self.cost[e] + h[g.head_l[e]] - h[node]
            if prev >= 0 and g.head_l[e] == g.tail_l[prev] and g.tail_l[e] == g.head_l[prev]:
                a += r.uturn_penalty_s
            added[i] = max(a, 0.0)
        w = np.exp(-(added - added.min()) / r.detour_scale_s)
        return cand, w / w.sum()


def _period_of_hour(hour: float) -> int:
    """Index of the departure period containing a local hour of day."""
    for i, (_, start, end) in enumerate(PERIODS):
        if start <= hour < end:
            return i
    return N_PERIODS - 1


class PublicSimulator:
    """The public road-network trip simulator: samples timed trips and scores edge sequences."""

    def __init__(
        self,
        network: RoadNetwork,
        zones_per_side: int = 3,
        utc_offset_s: int = BEIJING_UTC_OFFSET_S,
    ) -> None:
        """Prepare (or fetch from the cache) the public graph; nothing here touches data."""
        if zones_per_side < 1:
            raise ValueError(f"zones_per_side must be >= 1, got {zones_per_side}")
        self.graph = prepared_graph(network, zones_per_side)
        self.utc_offset_s = int(utc_offset_s)
        local = datetime(*ANCHOR_LOCAL_DATE, tzinfo=timezone(timedelta(seconds=self.utc_offset_s)))
        self.anchor_utc_s = local.timestamp()
        self._routers: dict[Regime, _Router] = {}

    @property
    def n_zones(self) -> int:
        """Number of origin-destination zones (zones_per_side squared)."""
        return self.graph.n_zones

    def router(self, regime: Regime) -> _Router:
        """The (memoized) router of one regime."""
        r = self._routers.get(regime)
        if r is None:
            r = _Router(self.graph, regime)
            self._routers[regime] = r
        return r

    def known(self, edge_seq: Sequence[int]) -> bool:
        """True when every link of a non-empty sequence exists on the map."""
        return bool(edge_seq) and all(int(e) in self.graph.edge_index for e in edge_seq)

    def od_zones(self, edge_seq: Sequence[int]) -> tuple[int, int]:
        """Origin and destination zone of a known edge sequence."""
        g = self.graph
        first, last = g.edge_index[int(edge_seq[0])], g.edge_index[int(edge_seq[-1])]
        return int(g.zone[g.tail[first]]), int(g.zone[g.head[last]])

    def route_time_s(self, edge_seq: Sequence[int], regime: Regime | None = None) -> float:
        """Jitter-free time of a known edge sequence under a regime (free flow when None)."""
        g = self.graph
        idx = np.array([g.edge_index[int(e)] for e in edge_seq])
        speed = g.free_flow_mps[idx]
        if regime is not None:
            speed = speed * regime.speed_factor
            if regime.speed_cap_mps is not None:
                speed = np.minimum(speed, regime.speed_cap_mps)
        return float((g.length[idx] / speed).sum())

    def departure_period(self, t_utc: float) -> int:
        """Departure-period index of a Unix-seconds UTC instant in this simulator's local time."""
        return _period_of_hour(((t_utc + self.utc_offset_s) % 86400.0) / 3600.0)

    # ------------------------------------------------------------------ sampling

    def simulate(self, params: SimParams, n: int, rng: np.random.Generator) -> list[TimedRoute]:
        """Sample n timed trips under the given parameters, deterministic in ``rng``."""
        self._check(params)
        weights = np.asarray(params.regime_weights, dtype=np.float64)
        weights = weights / weights.sum()
        dep = np.asarray(params.departure_shares, dtype=np.float64)
        dep = dep / dep.sum()
        od = self._od_table(params)
        out: list[TimedRoute] = []
        for _ in range(n):
            regime = params.regimes[int(rng.choice(len(weights), p=weights))]
            router = self.router(regime)
            origin, dest = self._sample_od(router, od, rng)
            period = int(rng.choice(N_PERIODS, p=dep))
            _, start, end = PERIODS[period]
            t0 = self.anchor_utc_s + 3600.0 * float(rng.uniform(start, end))
            route = self._walk(router, origin, dest, rng)
            out.append(self._timed(route, regime, params, period, t0, rng))
        return out

    def _check(self, params: SimParams) -> None:
        """Reject an origin-destination table of the wrong size for this map's zones."""
        if params.od_shares is not None and len(params.od_shares) != self.n_zones**2:
            raise ValueError(f"od_shares needs {self.n_zones**2} entries (zones squared)")

    def _od_table(self, params: SimParams) -> np.ndarray | None:
        """The OD table restricted to zone pairs that can host a trip, normalized; None if unset."""
        if params.od_shares is None:
            return None
        g = self.graph
        table = np.asarray(params.od_shares, dtype=np.float64).reshape(self.n_zones, self.n_zones)
        ok = np.outer(g.zone_mass > 0, g.zone_mass > 0)
        ok[np.diag_indices(self.n_zones)] &= g.zone_massive_nodes >= 2
        table = np.where(ok, table, 0.0)
        if not table.sum() > 0:
            raise ValueError("od_shares put no mass on any zone pair this map can host")
        normalized: np.ndarray = table / table.sum()
        return normalized

    def _sample_od(
        self, router: _Router, od: np.ndarray | None, rng: np.random.Generator
    ) -> tuple[int, int]:
        """Origin and destination nodes: by OD zone table and mass, or by mass and gravity."""
        g = self.graph
        if od is not None:
            pair = int(rng.choice(od.size, p=od.ravel()))
            zo, zd = divmod(pair, self.n_zones)
            w_o = np.where(g.zone == zo, g.mass, 0.0)
            origin = int(rng.choice(len(w_o), p=w_o / w_o.sum()))
            w_d = np.where(g.zone == zd, g.mass, 0.0)
        else:
            origin = int(rng.choice(len(g.mass), p=g.mass / g.mass.sum()))
            w_d = self._gravity(router, origin)
        w_d = w_d.copy()
        w_d[origin] = 0.0
        dest = int(rng.choice(len(w_d), p=w_d / w_d.sum()))
        return origin, dest

    def _gravity(self, router: _Router, origin: int) -> np.ndarray:
        """Unnormalized gravity weights of every destination from ``origin``.

        The decay acts on the free-flow cost (:data:`FREE_FLOW_REGIME`), not on the
        regime's own route cost, so one decay value means the same trip-length scale in
        every regime (module C1 sets it equally on all of them).
        """
        g = self.graph
        decay = router.regime.distance_decay_per_s
        if decay == 0.0:
            return g.mass
        cost = self.router(FREE_FLOW_REGIME).frm(origin)
        weights: np.ndarray = g.mass * np.exp(-decay * cost)  # inf cost -> 0
        return weights

    def _walk(self, router: _Router, origin: int, dest: int, rng: np.random.Generator) -> list[int]:
        """Boltzmann walk from origin to dest, finished on the shortest path after the bound."""
        g = self.graph
        h = router.to(dest)
        bound = router.step_bound(origin, dest, h)
        route: list[int] = []
        node, prev = origin, -1
        while node != dest:
            if len(route) < bound:
                cand, probs = router.step(node, prev, h)
                e = cand[int(rng.choice(len(cand), p=probs))]
            else:
                e = router.sp_next(node, h)
            route.append(e)
            prev, node = e, g.head_l[e]
        return route

    def _timed(
        self,
        route: list[int],
        regime: Regime,
        params: SimParams,
        period: int,
        t0: float,
        rng: np.random.Generator,
    ) -> TimedRoute:
        """Link visits of a route: free-flow time over speed factors, jitter and turn delays."""
        g = self.graph
        idx = np.asarray(route)
        speed = g.free_flow_mps[idx] * regime.speed_factor * params.period_speed_factors[period]
        if regime.speed_cap_mps is not None:
            speed = np.minimum(speed, regime.speed_cap_mps)
        base = g.length[idx] / speed
        log_jitter = np.full(len(route), rng.normal(0.0, params.trip_jitter_sigma))
        rho, sig = params.link_jitter_rho, params.link_jitter_sigma
        eps = rng.normal(0.0, sig)  # stationary start of the AR(1) link noise
        for i in range(len(route)):
            if i:
                eps = rho * eps + math.sqrt(1.0 - rho * rho) * rng.normal(0.0, sig)
            log_jitter[i] += eps
        times = base * np.exp(log_jitter)
        visits = []
        t = t0
        for i, e in enumerate(route):
            dwell = 0.0
            if i + 1 < len(route) and params.turn_delay_s > 0:
                turn = abs(math.remainder(g.bearing[route[i + 1]] - g.bearing[e], 2 * math.pi))
                if math.degrees(turn) >= TURN_ANGLE_DEG:
                    dwell = params.turn_delay_s
            t_exit = t + float(times[i]) + dwell
            visits.append(
                LinkVisit(edge_id=int(g.edge_ids[e]), t_enter=t, t_exit=t_exit, dwell_s=dwell)
            )
            t = t_exit
        return TimedRoute(visits=tuple(visits), utc_offset_s=self.utc_offset_s)

    # ---------------------------------------------------------------- likelihood

    def log_prob(self, params: SimParams, edge_seq: Sequence[int]) -> float:
        """Exact, floor-bounded log-likelihood of an edge sequence (times do not enter, §4.7)."""
        if not edge_seq:
            raise ValueError("cannot score an empty edge sequence")
        self._check(params)
        g = self.graph
        idx = [g.edge_index.get(int(e), -1) for e in edge_seq]
        od = self._od_table(params)
        weights = np.asarray(params.regime_weights, dtype=np.float64)
        weights = weights / weights.sum()
        terms = [
            math.log(w) + self._regime_log_prob(self.router(r), od, idx)
            for r, w in zip(params.regimes, weights, strict=True)
            if w > 0
        ]
        top = max(terms)
        return top + math.log(sum(math.exp(t - top) for t in terms))

    def _regime_log_prob(self, router: _Router, od: np.ndarray | None, idx: list[int]) -> float:
        """log P(O, D) plus the walk-step log probabilities of one regime."""
        g = self.graph
        if idx[0] < 0 or idx[-1] < 0:
            return _LOG_FLOOR * (len(idx) + 2)
        origin, dest = int(g.tail[idx[0]]), int(g.head[idx[-1]])
        lp = self._od_log_prob(router, od, origin, dest)
        if not (g.in_scc[origin] and g.in_scc[dest]) or origin == dest:
            return lp + _LOG_FLOOR * len(idx)
        h = router.to(dest)
        bound = router.step_bound(origin, dest, h)
        node, prev = origin, -1
        for step, e in enumerate(idx):
            if e < 0 or not g.usable[e]:
                lp += _LOG_FLOOR
                node, prev = (g.head_l[e], -1) if e >= 0 else (node, -1)
                continue
            if g.tail_l[e] != node:  # a gap between links
                lp += _LOG_FLOOR
                node, prev = g.tail_l[e], -1
            if node == dest:  # the walk would already have stopped
                p = 0.0
            elif step < bound:
                cand, probs = router.step(node, prev, h)
                p = float(probs[cand.index(e)])
            else:
                p = 1.0 if e == router.sp_next(node, h) else 0.0
            lp += math.log(max(p, PROB_FLOOR))
            node, prev = g.head_l[e], e
        return lp

    def _od_log_prob(self, router: _Router, od: np.ndarray | None, origin: int, dest: int) -> float:
        """log P(origin, dest) under the OD table or the gravity prior, floor-bounded."""
        g = self.graph
        m_o, m_d = float(g.mass[origin]), float(g.mass[dest])
        if m_o <= 0 or m_d <= 0 or origin == dest:
            return 2 * _LOG_FLOOR
        if od is not None:
            zo, zd = int(g.zone[origin]), int(g.zone[dest])
            rest = float(g.zone_mass[zd]) - (m_o if zo == zd else 0.0)
            p = float(od[zo, zd]) * m_o / float(g.zone_mass[zo]) * m_d / rest
            return math.log(max(p, PROB_FLOOR))
        p_o = m_o / float(g.mass.sum())
        w = self._gravity(router, origin)
        total = float(w.sum()) - float(w[origin])
        p_d = float(w[dest]) / total if total > 0 else 0.0
        return math.log(max(p_o, PROB_FLOOR)) + math.log(max(p_d, PROB_FLOOR))
