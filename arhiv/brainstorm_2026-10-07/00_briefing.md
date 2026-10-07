# trajguard: briefing for designing a new protection mechanism

Facts from the repo docs and code, 7 Oct 2026. A "rung" is a population size: 20, 50 or 182 Geolife users.

## 1. Data representation and interfaces

- **Stages.** `CleanTrajectory`: `traj_id`, `user_id`, `points` = (lat, lon, t in unix s), `duration_s`, `length_m`, `mean_speed`, `split`. `MatchedTrajectory`: `edge_seq` (int edge ids), `matched_points` = (x, y, t, offset_m) in UTM metres, `match_score`. `fit` receives `TrajectoryView` objects wrapping both (`as_gps()`, `as_segments()`, `user_id`, `split`), so timestamps are available.
- **Map.** A `RoadNetwork` is passed in: a networkx `MultiDiGraph` plus node and edge tables (edges carry `length_m`, `highway`, `oneway`, `maxspeed`), EPSG:32650.
- **`SyntheticGenerator`:** `fit(train: Sequence[TrajectoryView]) -> None` on the train split; `generate(n, seed) -> Sequence[SyntheticTrajectory]`. Membership inference also needs `sequence_log_prob(edge_seq) -> float`, finite for every edge sequence.
- **`PrivacyMechanism`:** `apply(view) -> ProtectedTrajectory` per trajectory, payload (lat, lon, t); no `fit`.
- **Registration.** Subclass the ABC and add `@register("generator", "<name>")`. Constructor arguments are filled by name: `network` gets the map, `seed` gets `cfg.seed + offset` (0 target, 1000 + k shadow k); YAML parameters pass through, list values become separate arms.
- **Output.** `SyntheticTrajectory` = `syn_id`, `generator_id`, `params_hash`, untyped `payload`, `trained_on_split`, `map_id`. **No `user_id`, and no generator emits timestamps today** (`markov`, `rn_ldp_synth`: edge ids; `ldptrace`, `privtrace`: grid cells). The benchmark synthesizes unlinked trajectories, not users.

## 2. Datasets and maps

- **Geolife v1.3:** 182 users, one trajectory per `.plt` file, transport modes unused, GMT timestamps (Beijing is UTC+8). Cleaning removes points implying >200 km/h, keeps points ≥5 s apart, needs ≥20 points and ≥500 m. Per-user median/range and time span are not documented.
- **At 182 users:** 17,313 clean trajectories (about 95 per user); only 1,770 pass map-match score 0.3, so generators train on about 809.
- **Split** once, by user, seed 42: train 0.5, test 0.2, shadow 0.2, attack 0.1.
- **Beijing map:** OpenStreetMap, about 30 × 33 km, 35,764 nodes (edge count undocumented).
- **Porto** (LDPTrace `.dat`): 367,008 trajectories, one user each, no map or real timestamps; grid cells and membership inference only.

## 3. How a mechanism is measured

- **Membership inference (LiRA-lite), synthetic only.** A candidate is one trajectory: members are train trajectories, non-members test trajectories of other users. Sixteen same-class shadows each fit a random half of shadow split plus candidates; the score is a likelihood ratio of the candidate's `sequence_log_prob` under shadows that did versus did not see it. Reported: AUC and true-positive rate (TPR) at false-positive rate (FPR) 0.001/0.01/0.1. `generate` is never called. Members/non-members: 90/15 (u20), 130/33 (u50), 809/296 (u182); FPR 0.001 stays `NaN` below 1,000 non-members.
- **Reidentification, perturbation only** (by decision never on synthetic data). Knowing k = 3/5/10 evenly spaced points of a raw trajectory, the attacker names the user of the nearest other released trajectory under DTW (dynamic time warping), plain or length-normalised, over space only. Gallery `rematched` keeps releases that re-match to the map, so heavy noise empties it; `release` keeps all released points. Metrics: top-1/top-k accuracy, linkage rate; raw top-1 at u20 is 0.28/0.38/0.49.
- **Utility, raw versus its own release (perturbation only):** `cell_js_divergence` (Jensen-Shannon divergence of 20 × 20 cell visits); `length_dist_error`, `duration_dist_error`, `speed_dist_error` (Wasserstein-1 distance between trip-length, duration and mean-speed distributions). No mechanism alters time, so duration error is 0 everywhere. **Synthetic utility is not wired into the orchestrator**; unpaired cell-JSD and length functions exist, used only by the standalone `rnldp_eval` module (the LDPTrace/PrivTrace validations use the papers' metrics on Porto). A timestamped generator needs new unpaired duration/speed metrics.
- Proposed pass marks (awaiting supervisor): top-1 < 5 % at k ≤ 10; TPR at FPR 0.01 ≤ 0.02 with the AUC interval containing 0.5.

## 4. Existing mechanisms (ε units are not comparable)

| Name | Privacy unit | Representation |
|---|---|---|
| `geo_indistinguishability` (perturbation) | ε per 100 m, per point | GPS |
| `point_ldp` (perturbation) | local ε per point; randomized response over 20 × 20 cells, time kept | GPS → cells |
| `spatial_rounding`, `temporal_downsampling`, `gaussian_noise` | none | GPS |
| `ldptrace` (generator) | local ε per trajectory | 12 × 12 cells |
| `privtrace` (generator) | central DP per trajectory, trusted collector | adaptive 6 × 6 cells |
| `rn_ldp_synth` (generator) | local ε per trajectory | road zones → edges |
| `markov` (generator) | none; memorization ceiling | edges |

None protects whole users: m trajectories cost a user m·ε.

## 5. RN-LDP-Synth v1

The device maps its edge sequence to zones of a public 12 × 12 grid and sends four randomized reports: start zone, end zone, transition count (capped at 24) and **one** random zone transition (ε shares 0.15/0.15/0.2/0.5). The server removes the noise bias, estimating start, end and length distributions and a first-order zone transition matrix. Synthesis samples start, end and length, walks the zone graph toward the end, and routes onto connected real edges by shortest paths. **No timestamps.**

Membership inference is at chance (u182 AUC 0.513/0.517/0.472 at ε 0.5/2/8), but the non-private `markov` ceiling is weak too (u182 AUC 0.776, TPR at FPR 0.01 0.027; u50 AUC 0.542), so chance level proves little. On the 20-trajectory test data cell JSD is 0.31–0.37 bits versus Markov's 0.05, flat in ε because noise dominates at n = 10; length error is 230–452 m (Markov 1,536 m). Given up by design: time, within-zone routes, higher-order patterns, joint start–end, user-level protection.

## 6. Practical constraints

- Python 3.11+, numpy with seeded `np.random.Generator` only, Parquet + DuckDB, PyYAML, ruff, mypy. Justify every new dependency; deep (PyTorch/GPU) generators are out of scope.
- Tests: pytest on committed data only (20 synthetic Geolife-format trajectories from 5 users, a 183-node / 388-edge test map), offline, seconds.
- Time budget per attack call: 300 s at u20/u50, 1200 s at u182 (flagged, not fatal). A membership arm builds 17 generators, so cache public precomputation. The whole u182 membership run took 101–161 s per seed; per arm at u20, `rn_ldp_synth` took 20 s, `ldptrace` 10 s, `privtrace` 8 s.
- Grids, caps and budget splits come from the map and fixed configuration, never from private data.
