# RN-LDP-Synth v1 — Design: private zone-walk synthesis

**Implementation:** `src/trajguard/synthesis/rn_ldp_synth.py` (`@register("generator", "rn_ldp_synth")`),
`src/trajguard/privacy/ldp.py` (GRR/OUE primitives), tests in `tests/test_rn_ldp_synth.py` and
`tests/test_ldp.py`. Literature context: `RESEARCH_SYNTHESIS.md` in the `RN-LDP-Synth` repo (37-paper
review; the gap this design targets is its §3).

## 1. Setting and threat model

Each user's device holds raw GPS trajectories, map-matched **on the device** against a public road
network (in the benchmark: `RoadNetwork` built by `OSMMapSource`; the mechanism consumes the matched
`edge_seq` view). The server is **untrusted**: it must never receive raw locations, raw edge sequences,
or any per-trajectory feature that is not ε-LDP-randomized. The server's legitimate output is a
*population* of synthetic trajectories, each a connected walk on the real road graph, statistically
similar to the real population.

Scoping (explicit, per the adversarial design review):

- The guarantee is **per-trajectory (event-level)** ε-LDP. The number of trajectories a user contributes,
  and participation itself, are assumed public in this threat model. A user contributing m trajectories
  spends m·ε of their own budget; a genuine *user-level* claim would require capping/padding every user
  to a public number of reports (documented extension, not implemented in v1).
- "Fixed shape" covers the message payload (four reports of fixed, data-independent size per trajectory).
  Timing and transport-layer metadata are outside the LDP model and must be handled by the transport
  (fixed reporting schedules, batching).
- The seeded `np.random.Generator` exists for experiment reproducibility (repo determinism rule) and
  **confers no privacy**: the ε-LDP property is a property of the mechanism's conditional output
  distribution. Deployment requires per-report randomness unknown to the server.
- The public structures (grid shape, `l_max`, budget split, zone partition, zone digraph) are derived from
  the public map and fixed configuration only. They must **never** be tuned on the private data — a
  data-dependent "public" structure would silently void the analysis below.

## 2. Public structures (zero privacy cost)

Built in `__init__` from `RoadNetwork` + constructor params, before any data is seen:

| Structure | Definition |
|---|---|
| Zone partition Z | `n_rows × n_cols` grid over the **projected** node-coordinate bbox (metres); cells containing ≥1 edge midpoint (midpoint of the edge's endpoint nodes) survive and are densely re-indexed. Every edge maps to exactly one zone. |
| Zone digraph A | Arc i→j (i≠j) iff some edge in zone i connects head-to-tail to some edge in zone j. The arc list `zone_arcs` (= F) is the LDP transition domain, \|F\| ≈ \|Z\|·avg-degree. |
| Hop table | All-pairs BFS distances on A (reachability guidance during synthesis). |
| Decode tables | Largest strongly-connected component of the road graph; per zone: length-weighted start edges and the entry map *tail node → best zone edge* (SCC-preferred); parallel (u,v) edges collapsed onto min `length_m` (mirrors `matching/leuven.py`). |
| Inflation factor c | Mean decode stretch measured on walks sampled from the **uniform** kernel with a fixed public seed (§7). Map+config-derived only. |

Key property used throughout: an edge sequence in which consecutive edges share a node projects onto a
zone sequence whose consecutive (deduplicated) zones are A-adjacent — the encoder never steps outside the
public domain F (tested invariant: `test_zone_sequences_follow_zone_arcs`).

## 3. On-device encoder and randomizers

Per trajectory (simulated per training view in `fit`; on a phone this is the entire privacy-critical
computation — table lookups, one uniform draw, four categorical randomizations):

1. Project `edge_seq` → zone sequence `zseq` (collapse consecutive duplicates). Empty trajectories are
   rejected before any budget is spent.
2. Features: start zone `s = zseq[0]`; end zone `e = zseq[-1]`; transition count `ℓ = min(len(zseq)−1,
   l_max)`; **one** transition `t` drawn uniformly from the trajectory's own transitions (uniform over all
   of F when ℓ = 0, so the report exists and is distribution-indistinguishable in shape).
3. Four reports, nothing else:
   - `GRR(s; |Z|, ε_s)`, `GRR(e; |Z|, ε_e)`, `GRR(ℓ; l_max+1, ε_ℓ)` — k-ary randomized response:
     true category w.p. e^ε/(e^ε+k−1), each other w.p. 1/(e^ε+k−1);
   - `OUE(one-hot(t); |F|, ε_t)` — optimized unary encoding: true bit stays 1 w.p. 1/2, every other bit
     turns 1 w.p. 1/(e^ε_t+1).

`fit` accumulates only the report aggregates (`start_counts`, `end_counts`, `len_counts`, `bit_sums`);
raw features are dropped on the spot. The budget split is a public constant
(default weights 0.15/0.15/0.2/0.5 of ε for s/e/ℓ/t).

## 4. Formal guarantee and proof sketch

**Claim.** For any two trajectories τ, τ′ (any lengths, any shapes) and any output o of the per-trajectory
report pipeline M: `P[M(τ) = o] ≤ e^ε · P[M(τ′) = o]`, with ε = ε_s + ε_e + ε_ℓ + ε_t.

Proof sketch:

1. *Deterministic preprocessing.* Zone projection and clipping of ℓ at `l_max` are deterministic maps into
   public finite domains; applying an ε-LDP randomizer after deterministic preprocessing preserves ε-LDP.
2. *Per-report guarantees.* GRR's worst-case likelihood ratio is exactly e^ε (constants above). OUE with
   p = 1/2, q = 1/(e^ε+1) is ε-LDP over the **full bit-vector output space** {0,1}^|F| for one-hot inputs;
   every output has strictly positive probability under every input, so the ratio bound holds for all
   output vectors, not just single bits (worst case (p/q)·((1−q)/(1−p)) = e^ε).
3. *Sampled transition is a mixture.* The transition report first samples t from a τ-dependent
   distribution p_τ over F, then applies OUE. For any output y:
   P(y|τ) = Σ_t p_τ(t)·P_OUE(y|t) ≤ e^{ε_t}·P_OUE(y|t₀) for *every* fixed t₀ (step 2's uniform pairwise
   bound), hence P(y|τ) ≤ e^{ε_t}·Σ_{t₀} p_{τ′}(t₀)·P_OUE(y|t₀) = e^{ε_t}·P(y|τ′). The ℓ = 0 dummy case is
   the same bound with p_τ uniform.
4. *Composition.* The four randomizers run independently on (functions of) the same trajectory; the joint
   output factorizes, so the ratios multiply: e^{ε_s}·e^{ε_e}·e^{ε_ℓ}·e^{ε_t} = e^ε (sequential
   composition).
5. *Post-processing.* Debiasing, clipping at zero, normalisation, kernel construction, walk synthesis,
   decoding, inflation calibration (public inputs only) and `sequence_log_prob` consume only the joint
   LDP output and public structures — post-processing invariance applies.

The empirical check `tests/test_ldp.py::test_grr_empirical_frequency_ratio_bounded_by_exp_eps` (and the
OUE analogue) validates the randomizer ratio bound on a toy domain against exp(ε).

### ε accounting table

| Stage | Mechanism | Domain | Budget | Notes |
|---|---|---|---|---|
| Start zone | GRR | Z (\|Z\| categories) | ε_s = 0.15ε | one report |
| End zone | GRR | Z | ε_e = 0.15ε | one report |
| Transition count | GRR | {0..l_max} | ε_ℓ = 0.20ε | clipped deterministically first |
| One transition | OUE | F (feasible arcs) | ε_t = 0.50ε | sampled-then-randomized (mixture bound) |
| Aggregation, synthesis, decoding, calibration, log-prob | — | — | 0 | post-processing of the above |
| **Total per trajectory** | | | **ε** | sequential composition |

`spent_budget()` reports the per-trajectory ε; device budgets are parallel across users and do **not**
sum. There is no per-point term anywhere — the budget is independent of trajectory length, the failure
mode that dominates the per-point LDP literature (RESEARCH_SYNTHESIS.md §2.1).

## 5. Server aggregation (post-processing)

Standard frequency-oracle estimation over n reports: GRR debias `(count − n·q)/(p − q)` and OUE debias
`(bit_sum − n·q)/(1/2 − q)`, clipped at 0 and normalised → start distribution π̂, end distribution η̂,
length distribution λ̂, and arc frequencies → the zone-level Markov kernel P̂(j|i), row-normalised over
A's out-arcs with a uniform fallback for zero-mass rows.

## 6. Synthesis

Per synthetic trajectory (`generate(n, seed)`, deterministic in `seed`):

1. Sample start z₀ ~ π̂, end target z_e ~ η̂, length target ℓ ~ λ̂; walk steps = max(1, round(ℓ / c))
   (§7's public inflation factor c).
2. **Reachability-guided walk on A:** at each step keep out-neighbours j with hop(j, z_e) ≤ remaining−1
   (precomputed hop table); if none survive, drop the guidance for that step; sample ∝ P̂ restricted to the
   kept arcs. The walk ends after the step budget (or at a sink zone). Guidance biases walks toward the
   sampled end zone without any hard endpoint constraint.
3. **Decode to real edges:** start from a length-weighted (SCC-preferred) edge of z₀; for each subsequent
   walk zone, route from the current head node to a **near entry** of that zone — exact reachability via
   Dijkstra, entry sampled among the 3 nearest reachable zone tails, then traverse that zone's entry
   edge. Unreachable zones truncate the walk (counted in `last_decode_truncations`; 0 on the fixture).
   Consecutive payload edges chain head-to-tail **by construction** — the road-network constraint is
   structural, not statistical (tested: `test_generated_paths_are_connected_road_walks`).

Payload = tuple of edge ids (the `MarkovGenerator` convention). `sequence_log_prob(edge_seq)` scores the
zone projection under π̂/η̂/λ̂/P̂ — the likelihood hook LiRA-style membership inference needs.

## 7. Decode-inflation calibration (public, zero budget)

Entering a zone lands away from the boundary to the next one, so a k-step zone walk decodes into more
than k projected zone transitions. The stretch factor is a property of the **public** structures and the
decoding procedure alone, so it is measured once at construction: walks sampled from the *uniform* kernel
with a fixed public seed are decoded and re-projected; c = mean(projected transitions / walk steps),
floored at 1. Sampled length targets are divided by c before walking.

Measured on `beijing_fixture` (183 nodes / 388 edges, 10×10 grid → 59 zones, 178 arcs): c = 2.15;
with calibration the synthetic population's mean zone-transition count tracks the training population at
ratio **1.03** (7.65 vs 7.45; mean edge counts 17.4 vs 14.6) at ε = 80, with 0 truncations.

## 8. Utility: preserved vs deliberately sacrificed

Preserved (population level, degrading gracefully with ε):
- **Spatial density** at zone granularity (π̂, η̂ and the stationary structure of P̂) — the benchmark's
  `cell_js_divergence` measures exactly this once synthetic pools are wired into the utility path.
- **Trip length distribution** (λ̂ at zone-hop granularity, decoded through real edge lengths with the
  calibration of §7) — the benchmark's `length_dist_error` analogue.
- **OD structure as marginals** (start and end zone distributions; coupled only through the
  reachability-guided walk, not jointly reported).
- **First-order flow structure** (feasibility-masked transition kernel).

Deliberately sacrificed for privacy (v1):
- **Timestamps / temporal patterns** — payloads carry no time; speeds/durations are not reported. (The
  benchmark's current re-identification attack and both utility metrics are time-free; edge `maxspeed`
  is available publicly if a later version wants synthetic timestamps.)
- **Within-zone micro-routes** — decoding picks plausible real-road connective tissue, not the user's
  actual streets; anything below zone granularity comes from the public map, not from data.
- **Higher-order and long-range correlations** — one sampled transition per trajectory feeds a
  first-order kernel; loops/detours/repeated visits are not representable.
- **Joint OD coupling** — P(start, end) is released only as two marginals.
- **User-level guarantee** — per-trajectory only (§1).
- **Small populations** — frequency-oracle noise scales as √n; with very few devices (the 20-trajectory
  fixture at ε ≈ 1) the estimates are near-uniform and utility comes mostly from the feasibility
  structure. This is inherent to honest LDP at small n, not a bug.

## 9. Novelty relative to the surveyed corpus

Framing (per the novelty review): **LDPTrace's collect–aggregate–synthesize paradigm made
road-network-native.** The specific combination is new in the surveyed corpus; the individual ingredients
are credited below.

| Prior work | What it shares | What v1 does differently |
|---|---|---|
| LDPTrace (PVLDB'23) | Per-trajectory budget split over features; OUE; server-side synthesis from aggregates; the paradigm | Domain = feasible arcs of a public road-zone digraph, not a free uniform grid; single-sampled-transition report (fixed shape, mixture-bound accounting) instead of multi-report transition encoding; decoding to connected real-road edge sequences; end-zone report + reachability-guided (not virtual-endpoint) termination |
| TPIS (IoT-J'25), BiPriv (SSRN) | Road-graph-native LDP domains; public-structure discipline | They release a 1:1 perturbed path per real trajectory (linkage surface remains); v1 releases population statistics and synthesizes decoupled trajectories |
| GG-I/GEM (arXiv'20) | Road network in the privacy machinery | GG-I is metric-DP (ε·d_s) for single points; v1 is plain ε-LDP on discrete public domains for whole-trajectory features — deliberately not an instance of GG-I |
| GeoPM-DMEIRL (FGCS'24) | LDP input + road-aware discretization + server generation | GeoPM composes per-point (budget linear in length) on a density grid and needs server IRL training; v1's budget is length-independent and synthesis is a Markov walk any device could run |
| NGRAM (PVLDB'21) / t-LDP (DASFAA'24) | Whole-sequence guarantees, plausibility constraints | They release per-user perturbed sequences without population aggregation and without a road graph; v1 aggregates and stays graph-native |
| MTNet / Diff-RNTraj / ControlTraj / STEGA | Topology-masked generation on road graphs | Masking is prior art, credited; those models are non-private (or central DP-SGD) and GPU-scale; v1 is LDP end-to-end and phone-scale |
| DPMM (ACSAC'22) | Density-aware noise on a road graph, DP synthesis | Central DP (trusted curator); v1 is local |

Not claimed: being the first road-network-constrained LDP mechanism; topology masking; superiority over
LDPTrace/TPIS/NGRAM on privacy-utility trade-offs (no comparable attack evaluation has been run yet —
§10). The sample-one-transition report is a design choice in the spirit of generic sample-then-report
budget conservation, not a claimed-first technique.

## 10. Limitations

1. **Attack evaluation is fixture-scale only (so far).** Honest LiRA now runs against this generator
   (same-class shadows via the shadow factory; §12) at the 20-trajectory fixture scale — single seed,
   coarse TPR granularity, no cross-seed error bars. Larger-scale MIA (Geolife-sized populations) and
   re-identification against synthetic pools (needs orchestrator `target_scope: synthetic` wiring)
   remain open.
2. **Zone granularity is a bias-variance knob.** Coarse grids lose spatial detail; fine grids blow up |Z|
   and |F| and hence GRR/OUE variance. Defaults (12×12) are untuned; tuning must use public data only.
3. **Decode truncations.** Zones unreachable from the current decode position truncate walks (0 on the
   fixture; expect >0 on large real graphs with one-way peripheries).
4. **Calibration approximation.** c is measured under the uniform kernel; the fitted kernel's inflation
   can differ modestly. Any refinement must remain data-independent.
5. **Small-n regime.** 182 Geolife users (and 20 fixture trajectories) is far below the populations LDP
   frequency oracles like to see; results at ε ≤ 1 will be noise-dominated. This is the honest cost of
   the local model and should be reported, not hidden.
6. **Sequence_log_prob approximates the generative process** (it scores the unguided kernel; guidance
   and decoding are not in the likelihood). Fine for LiRA ranking; not a true model likelihood.
7. **No timestamps** (§8). POI/attribute attacks that need dwell times cannot target v1 output
   meaningfully.

## 11. Integration and evaluation in trajguard

- **ABC/registration:** `SyntheticGenerator` subclass registered as `("generator", "rn_ldp_synth")`,
  imported in `experiments/builtins.py`. Constructor takes the `RoadNetwork` explicitly; the orchestrator
  run loop does not instantiate generators today (synthetic target scope is a later phase), so tests and
  scripts construct it directly. Future orchestrator wiring needs a network-injection path (e.g. via
  `_net_provider`) since the mechanism convention `cls(**yaml_params, seed=...)` has no `RoadNetwork` slot.
- **Datamodel:** consumes `TrajectoryView.as_segments()` (train split only, enforced); produces frozen
  `SyntheticTrajectory` records with edge-tuple payloads, `trained_on_split="train"`, `params_hash` over
  all constructor params + generate seed.
- **Determinism:** all randomness flows from the constructor seed (fit/device simulation) and the
  `generate` seed; two generators with equal seeds and inputs produce identical outputs (tested).
- **Region protocol:** verified end-to-end on `beijing_fixture` (committed test network). **Ljubljana**
  (EPSG:3794, `config/maps.yaml`) is the reserved region for real synthetic-population runs per the
  map/dataset consistency rule (T1: never paired with Geolife attacks); building it requires the OSM
  download CLI and is deliberately out of this slice.
- **Evaluation plan:** utility via the unpaired population metrics
  (`evaluation.utility.unpaired_cell_js_divergence` / `unpaired_length_w1`; the paired dispatch-table
  variants assume a raw↔released bijection population synthesis doesn't have); privacy via the empirical
  randomizer ratio test (in-tree) and LiRA with same-class shadows
  (`MembershipInferenceAttack(shadow_factory=...)`); re-identification once synthetic pools enter the
  run loop. First measured numbers: §12.

## 12. Measured evidence (fixture scale)

Produced by `python -m trajguard.experiments.rnldp_eval` (committed module; deterministic in its seed).
Protocol: 20 public shortest-path seed trajectories on `beijing_fixture`; 10 members fit the target,
all 20 are MIA candidates; LiRA with 16 same-class shadows (per-index seeds); utility = unpaired metrics
between the member population and an equal-sized synthetic release; Markov = non-private ceiling under
the identical protocol. Seed 20260706.

| Arm | MIA AUC | TPR@FPR=0.01 | TPR@FPR=0.1 | Cell JSD (bits) | Length W1 (m) |
|---|---|---|---|---|---|
| rn_ldp_synth @ ε=0.5 | 0.650 | 0.30 | 0.30 | 0.335 [0.289, 0.666] | 230 [167, 950] |
| rn_ldp_synth @ ε=2 | 0.460 | 0.00 | 0.30 | 0.314 [0.275, 0.618] | 316 [185, 1092] |
| rn_ldp_synth @ ε=8 | 0.470 | 0.10 | 0.20 | 0.374 [0.299, 0.633] | 452 [270, 1125] |
| rn_ldp_synth @ ε=80 | 1.000 | 1.00 | 1.00 | 0.341 [0.222, 0.773] | 271 [195, 719] |
| Markov (non-private ceiling) | 0.970 | 0.70 | 1.00 | 0.051 [0.057, 0.243] | 1536 [817, 2572] |

Reading (with the small-n caveats of §10.1 firmly attached):

- **Privacy at working budgets.** At ε ∈ {0.5, 2, 8} LiRA is at chance (AUC 0.46–0.65; with 10 members /
  10 non-members the null-AUC jitter is ≈±0.13, so 0.65 at ε=0.5 is within noise). TPR granularity is
  0.1 per member; FPR=0.01 is the zero-false-positive regime at this n.
- **The attack has teeth.** At ε=80 (a deliberately meaningless budget) the same attack achieves
  AUC 1.0 / TPR 1.0 — with near-noiseless aggregates over 10 members, each member visibly shifts
  π̂/λ̂/P̂. The chance-level results at working ε are therefore not an artefact of a weak attack.
- **The non-private ceiling is fully attackable** (Markov AUC 0.97), as expected for a memorizing model.
- **Utility price.** Spatial structure costs ≈0.3 bits of cell JSD vs the Markov ceiling's 0.05 at this
  population size — the honest LDP cost at n=10 reporting devices; the JSD is nearly flat in ε because
  frequency-oracle noise at this n dominates the budget effect. Trip-length fidelity is *better* than
  the non-private Markov (W1 230–452 m vs 1536 m): the mechanism spends budget on an explicit length
  distribution and calibrates decode inflation, whereas the Markov baseline has no length model at all.
- **CI reading note.** The bracketed intervals are percentile bootstraps under *independent* per-side
  resampling; for a non-negative statistic sitting near its zero boundary the replicates are
  systematically noisier than the point estimate, so an interval can sit entirely above it — the Markov
  cell-JSD row (0.051 [0.057, 0.243]) is exactly this artifact, not a precision interval around 0.051.
  It is the only such case in the table.
