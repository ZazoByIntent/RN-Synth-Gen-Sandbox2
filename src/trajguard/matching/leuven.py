"""HMM map matcher built on leuvenmapmatching (design §2.2, module 3)."""

import math

from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher
from pyproj import Transformer

from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.experiments.registry import register
from trajguard.maps.base import RoadNetwork
from trajguard.matching.base import MapMatcher


@register("matcher", "leuven")
class LeuvenMapMatcher(MapMatcher):
    """DistanceMatcher-based HMM matching in the network's projected CRS.

    Parameter names follow the design §8 ``map_matching:`` block and map onto
    leuvenmapmatching as: radius_m -> max_dist, gps_error_m -> obs_noise,
    k_candidates -> max_lattice_width. ``match_score`` is matcher-agnostic:
    ``frac_matched * exp(-mean_offset_m / (2 * gps_error_m))`` in [0, 1], so a
    future fmm matcher produces comparable scores.
    """

    def __init__(
        self, radius_m: float = 50.0, gps_error_m: float = 20.0, k_candidates: int = 8
    ) -> None:
        self.radius_m = radius_m
        self.gps_error_m = gps_error_m
        self.k_candidates = k_candidates
        # per-RoadNetwork caches, keyed by id(net): (InMemMap, edge lookup, transformer)
        self._cache: dict[int, tuple[InMemMap, dict[tuple[int, int], int], Transformer]] = {}

    def match(self, traj: CleanTrajectory, net: RoadNetwork) -> MatchedTrajectory:
        """Return the trajectory mapped to an edge sequence with a match score.

        A trajectory that cannot be matched at all yields an empty edge_seq with
        frac_matched = match_score = 0.0 (filtering happens in match_many).
        """
        map_con, edge_lookup, transformer = self._network_ctx(net)
        # leuvenmapmatching's documented coordinate order is (y, x); t is ignored.
        path = [(y, x) for x, y in (transformer.transform(lon, lat) for lat, lon, _ in traj.points)]
        matcher = DistanceMatcher(
            map_con,
            max_dist=self.radius_m,
            obs_noise=self.gps_error_m,
            max_lattice_width=self.k_candidates,
            non_emitting_states=True,
        )
        matcher.match(path)
        # lattice_best mixes emitting and non-emitting states; only emitting ones
        # (obs_ne == 0) correspond to observations, one per matched input point.
        seen: set[int] = set()
        states = []
        for m in matcher.lattice_best:
            if m.obs_ne == 0 and m.obs not in seen:
                seen.add(m.obs)
                states.append(m)

        matched_points = tuple(
            (m.edge_m.pi[1], m.edge_m.pi[0], traj.points[m.obs][2], float(m.dist_obs))
            for m in states
        )
        node_path = matcher.path_pred_onlynodes
        pairs = list(zip(node_path, node_path[1:], strict=False))
        # Trailing/leading non-emitting lattice states can extend the node path
        # past the observations; keep only the span supported by emitting states
        # (interior bridge edges between observations stay).
        observed = {(m.edge_m.l1, m.edge_m.l2) for m in states}
        while pairs and pairs[0] not in observed:
            pairs.pop(0)
        while pairs and pairs[-1] not in observed:
            pairs.pop()
        edge_seq = tuple(edge_lookup[pair] for pair in pairs)
        frac_matched = len(states) / len(traj.points) if traj.points else 0.0
        if matched_points:
            mean_offset = sum(p[3] for p in matched_points) / len(matched_points)
            score = frac_matched * math.exp(-mean_offset / (2 * self.gps_error_m))
        else:
            score = 0.0
        return MatchedTrajectory(
            traj_id=traj.traj_id,
            user_id=traj.user_id,
            map_id=f"osm_{net.region}",
            edge_seq=edge_seq,
            matched_points=matched_points,
            match_score=score,
            frac_matched=frac_matched,
        )

    def quality(self, matched: MatchedTrajectory) -> dict[str, float]:
        """Quality summary: mean/max GPS->road offset (m), frac_matched, edge count."""
        offsets = [p[3] for p in matched.matched_points]
        return {
            "mean_offset_m": sum(offsets) / len(offsets) if offsets else float("nan"),
            "max_offset_m": max(offsets) if offsets else float("nan"),
            "frac_matched": matched.frac_matched,
            "match_score": matched.match_score,
            "n_edges": float(len(matched.edge_seq)),
        }

    def _network_ctx(
        self, net: RoadNetwork
    ) -> tuple[InMemMap, dict[tuple[int, int], int], Transformer]:
        """Build (once per RoadNetwork) the leuven map, edge lookup, and transformer."""
        ctx = self._cache.get(id(net))
        if ctx is not None:
            return ctx
        map_con = InMemMap(f"osm_{net.region}", use_latlon=False, use_rtree=False)
        for node, data in net.graph.nodes(data=True):
            map_con.add_node(node, (data["y"], data["x"]))  # (y, x) per documented contract
        for u, v in net.graph.edges(keys=False):
            map_con.add_edge(u, v)
        # leuven's map is simple adjacency (no multigraph): parallel (u, v) edges
        # collapse onto the shortest one.
        edge_lookup: dict[tuple[int, int], int] = {}
        best_len: dict[tuple[int, int], float] = {}
        for row in net.edges.itertuples(index=False):
            key = (int(row.u), int(row.v))
            length = float(row.length_m)
            if key not in edge_lookup or length < best_len[key]:
                edge_lookup[key] = int(row.edge_id)
                best_len[key] = length
        transformer = Transformer.from_crs("EPSG:4326", net.crs, always_xy=True)
        ctx = (map_con, edge_lookup, transformer)
        self._cache[id(net)] = ctx
        return ctx
