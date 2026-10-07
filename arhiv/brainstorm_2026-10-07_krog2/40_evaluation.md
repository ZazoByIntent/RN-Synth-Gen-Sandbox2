# Stage 4 evaluation with a red team: K1–K8 (evaluator, 2026-10-07)

Inputs: `01_task.md`, `04_evaluate_task.md`, `00_baseline.md`, `20_candidates.md` (K1–K8, X1–X14, dropped ideas),
`30_novelty_G1.md`–`G3.md`; repo code and `docs/NACRT_ULDP_SINTEZA.md` read-only. I wrote none of the inputs. Raw English
material; nothing here is decided. Marks: **V** verified here (algebra or code), **C** claim. A, B, C in §3–§4 are
combinations, not round-1 lenses.

## 0. Facts I checked myself
- **R-1 Geolife trajectories are unsplit recording sessions (V).** `datasets/geolife.py` yields one trajectory per `.plt`;
  `datasets/cleaning.py` only drops points above 200 km/h, thins to ≥ 5 s and applies the 20-point / 500 m minimums. Nothing
  in `src/` splits at stays or recording gaps, and `attacks/attribute.py` finds stay-points inside trajectories. Durations
  therefore contain dwells and gaps, and a home → shop → home session is a loop with D ≈ O. How common this is in the
  matched subset is unmeasured (C) and must not be measured on Geolife before the prior is frozen (lesson 7). It touches K1
  (*dur*), K2 (u), K3 (stop share), K4 (pieces, loops) and §4's C1–C3 (§5 F1).
- **R-2 `fit` receives only matched train trips (V, `experiments/orchestrator.py:1503`, `train_m`).** X6 holds; who reports
  then depends on private data (§5 F3).
- **R-3 Noise (V).** Exact debiased GRR at n = 91, shares at 1/k: ε 2: k = 3 / 4 / 9 → 0.073 / 0.074 / 0.079; ε 1: k = 3
  → 0.136, k = 9 → 0.206; ε 0.5, k = 3 → 0.28. X3 is right. A difference of two small shares (a sign balance) has
  SD ≈ 0.10 at ε 2.
- **R-4 EPR identifiability (V).** S(n) = (ρ(1+γ)n)^(1/(1+γ)), γ = 0.21: ρ = 0.6 vs 0.3 gives 2.4 vs 1.4 distinct places
  at 4 trip ends, 8.4 vs 4.7 at 18, 22.6 vs 12.8 at 60. With K6's bins (≤ 4, 5–7, 8–11, ≥ 12) only users with roughly
  4–25 matched trips separate the two values; K6's 5.4-SD figure assumes every user has exactly 9 trips.
- **R-5 K8's realistic effect (V arithmetic, C inputs).** A 0.2-nat peak slowdown against the prior's 0.42-nat jitter moves
  the share "peak trip > 10 of 29 ranks slower" from 0.22 to ≈ 0.36 and the opposite share to ≈ 0.12. With ≈ 40 of 91
  users eligible and every user on K8, the difference is ≈ 1.1 SD at ε 2 and ≈ 2.3 SD at ε 8.

## 1. Scoring
**Scales (1–5).** Novelty: 5 NOVEL; 4 NOVEL COMBINATION whose distinctive element is itself unpublished; 3 NOVEL COMBINATION
of published parts; 2 the element it sells is a CLOSE VARIANT, or low confidence; 1 EXISTS / CLOSE VARIANT. Privacy: 5
airtight, no non-public input; 4 airtight, but the estimator needs an input that is not S1-clean unless asked in the report,
or the ε 8 item is a near-identifier; ≤ 3 a leak. Fit: R1 plus an exact, affordable `sequence_log_prob`. Evidence at n = 91:
4 one quantity outside X10 moves reliably at ε 2; 3 one quantity plausibly ≥ 2 SD; 2 an item moves but saturates, is
confounded or has an ambiguous effect on the metrics; 1 nothing. Distinctness: 5 a separate contribution; 3 a new estimand
or generator inside §4's paradigm (private items calibrate a public simulator); 2 a module or question family of §4. Cost:
4 ≈ 2 sessions; 3 ≈ 3–4; 2 ≥ 5 or new prerequisites beyond P0–P5. Thesis: 5 the central user-level question; 3 a methods
or generator question; 2 incremental.

**Weights** (sum 20; total = Σ weight × score, max 100): Novelty 4, Distinctness 4, Evidence at n = 91 3, Thesis value 3,
Fit 2, Large-n 2, Privacy 1, Cost 1. Novelty is a gate (lesson 1) and the task is a *second* mechanism, so distinctness
weighs as much. Privacy weighs 1 because every candidate is one standard primitive at full ε through X1 and only its S1
inputs differ; a real privacy flaw would be a gate, not a score.

### K1 Twin-rank calibration
- Novelty 3: G1 NOVEL COMBINATION (medium); the sequential form is Joseph et al. 2019; Cormode & Markov 2023 plus Kuleshov et
  al. 2018 are two short steps away.
- Privacy 5: X1, twins simulated locally; the only estimator that needs no trips-per-user law (the PIT is uniform for any m_u).
- Fit 4: the host gives R1; at n = 91 the edge likelihood is the prior's (exact, cheap, MIA-blind); the *len* ablation needs a
  Monte-Carlo CDF.
- Evidence 2: against a car-speed prior, walks, buses and dwell-laden sessions (R-1) crowd the top tercile; three bins give at
  best a level and spread (a unimodal stand-in for a walk/vehicle mixture), a tercile reweighting keeps the prior's tail shape,
  and the quantity is X10's mode mix.
- Large-n 4: all question families, dithered bins, maps per period × length class, joint (Rosenblatt) PITs.
- Distinctness 2: same simulator and time parameters as C1; a reviewer reads a C1 question family with a better null.
- Cost 4: cheap twins for *dur*, a gate, a quantile map on P3; ≈ 2 sessions.
- Thesis 3: a pre-registered test-then-recalibrate step for public simulators under LDP; it serves §4 as much as a new mechanism.

### K2 Time-budget prisms
- Novelty 3: G2 NOVEL COMBINATION (medium); the generator side is prism destination choice (PCATS/FAMOS, MITO, Yoon et al.); the
  claim "no spatial quantity is released" is false, since τ = u·T is the OD's network distance in time units.
- Privacy 5: X1; cut points, congestion profile and dwell rule public; 'undefined' is a category.
- Fit 4: exact sums over daypart and cell; ≈ 300 s of shared public Dijkstras per arm at u182 (budget 1,200 s); FIFO times.
- Evidence 2: the u-shares (±0.073 at ε 2) will move, but u ≈ 0 for loops and dwell-laden sessions and the ring kernel then puts
  D next to O, so length and speed W1 can end up worse than the prior arm.
- Large-n 3: 48 OLH cells and family W; richer time histograms, no new structural object.
- Distinctness 2: one joint item of C1's speed ratio and duration, with τ playing C2's cost band; only the ring kernel is new.
- Cost 3: time-dependent costs, a cited congestion profile, ring normalisers; W adds POI and opening-hour exports.
- Thesis 3: "does space from time beat gravity?" is a generator question answerable without privacy.

### K3 Clock-sampled speed states
- Novelty 2: G2 NOVEL COMBINATION (narrow); time-weighted sampling is textbook, Markov speed synthesis and road-class stop events
  exist (BerlinMOD), and Google EIE releases time per mode under user-level (central) DP.
- Privacy 5: X1; thresholds public; the time-uniform draw is local randomness.
- Fit 4: exact forward algorithm, O(9L) per route; stop spells fill per-segment times; the walk state needs footways (P9).
- Evidence 3: four absolute time shares at ±0.074, no saturation; stop and walk shares plausibly ≥ 2 SD off a car-heavy prior;
  mean speed ±0.76 m/s; spatial metrics stay prior; X10.
- Large-n 3: state × class × daypart shares give time-weighted speed corrections; narrow.
- Distinctness 2: at n = 91 it re-measures C3's mode mix; G2 itself recommends it as a module.
- Cost 3: semi-Markov clock, state router, cited idle and spell constants.
- Thesis 2: adds stops to the time model; no question §4 cannot pose.

### K4 Via-point route structure
- Novelty 3: G2 NOVEL COMBINATION (medium); the statistic and its use for route generation are Knapen et al. 2016; the private
  law, the loop class and the exact-likelihood generator are new.
- Privacy 5: X1; decomposition rule, anchors and classes public; family C at ε 8 releases modal corridors (inside the vacuous
  bound), so it stays out of the core.
- Fit 4: exact via-DP (≤ 2 vias, ≤ 800 pairs) on lazily cached public anchors (≈ 40 s, 140 MB per 1,000); loops expressible.
- Evidence 3: one 4-way item at ±0.074; the loop or one-piece share moves if the prior misses by ≥ 0.15, plausible with
  unsplit sessions (R-1) but partly a pipeline effect (X13); the item lies outside X10.
- Large-n 4: class × offset × position, the window scale profile, period splits, corridor heavy hitters at 3–4 % of users.
- Distinctness 3: route structure and an anchored router lie outside C1–C3; still §4's paradigm.
- Cost 3: anchors derive from the existing `highway` column; decomposition on the device, via-DP, caches; ≈ 3–4 sessions.
- Thesis 3: can user-level LDP recover route structure, and does a structured router fix the walk's blind spots?

### K5 Habit-mode hubs
- Novelty 2: G3 NOVEL COMBINATION (narrow); its selling point "the mode, not a sample" is a CLOSE VARIANT of Wang et al. AAAI
  2018, and the decoder is DP-WHERE made local.
- Privacy 4: airtight, but ĥ needs the non-public trips-per-user law (X5), and the ε 8 20 × 20 item is a home-cell release
  (Maximum Amount rule; Golle & Partridge).
- Fit 4: exact, cheap hub mixture; but O and D are independent given the hub, so a share ĥ² of trips runs hub cell to hub
  cell, unlike home-based trips (fix: exactly one end at the hub).
- Evidence 3: a 5-km cell holding ≥ 35 % of users' modes is kept at ε 2 with power ≈ 0.78; whether one exists is unmeasured;
  C2's 3 × 3 shares see a coarse version.
- Large-n 3: 20 × 20 hubs at ≥ 4–5 % of users, the kernel scale, hub × trip count.
- Distinctness 2: the item "could be bolted onto C2" (consolidator); the decoder reads as home detection, a C4 revival.
- Cost 4: OLH, threshold, hub decoder, mixture likelihood; ≈ 2–3 sessions.
- Thesis 3: habit versus sampled item for heterogeneous users; unanalysed (G3) but small.

### K6 Mobility-signature users
- Novelty 3: G3 NOVEL COMBINATION (medium); descriptors (Kapp et al.), simulate–privatise–match (Sakong & Zentefis), EPR and urn
  copies are each published.
- Privacy 4: airtight, but the moment map needs the trips-per-user law (X5), and the bins were built around ≈ 9 matched trips
  per user, a Geolife figure (lesson 7).
- Fit 3: the EPR likelihood is a Monte-Carlo zone table per θ̂ plus public within-zone mass, not the law `generate` samples
  (X12); 17 simulations per arm, runtime unmeasured.
- Evidence 2: R-4: S separates ρ only for users with ≈ 4–25 trips, converting bin shares into ρ needs the unknown trips law, and
  whether ρ moves unlinked metrics is unverified (X11).
- Large-n 4: joint S × trip-count and (S, r_g) items identify ρ, γ and the trips law itself; whole users.
- Distinctness 3: another simulator family (individual mobility laws) and estimand (concentration); §4's architecture; C4 revival.
- Cost 2: EPR on OSM, SMM, copy layer, linked payload, coherence metrics (a new prerequisite), unmeasured runtime × 17.
- Thesis 4: user-level mobility structure (exploration vs return, whole users) under LDP, a question §4 cannot pose.

### K7 Proxy respondent
- Novelty 2: G1 NOVEL COMBINATION (low); both runnable forms are CLOSE VARIANTS (a threshold query on a local estimate; LDP
  private sampling).
- Privacy 4: airtight (the ε/2 exponential-mechanism proof is right), but the response surface needs the trips-per-user law and
  a θ_u population law, neither public.
- Fit 4: §4.7 likelihood at θ̂; the ε 8 option must put its released trips inside the likelihood (X12).
- Evidence 2: one designed threshold on the local speed ratio (3.4 SD is a design claim) is X10, and a D-optimal design under a
  wrong prior saturates like K1.
- Large-n 4: 10–25 structural parameters through designed multi-attribute scenarios.
- Distinctness 2: calibrates C1's parameters; server-designed query + RR answer + parametric surface is C7's rejected shape.
- Cost 2: on-device structural fits, simulated response surfaces, a D-optimal design, two population laws.
- Thesis 3: stated versus revealed information per LDP report; S2 only.

### K8 Within-user contrasts and couplings
- Novelty 4: G1 NOVEL COMBINATION (medium); the within-user estimand and its identification argument are unpublished under LDP
  (central analogue: Sopa et al. 2026); the GRR step itself is folklore.
- Privacy 5: X1; public eligibility rule with ⊥; pooled medians only from earlier disjoint cohorts or the prior.
- Fit 3: no generator of its own; on any host items a, c, d leave the edge likelihood unchanged; item b's clock router costs
  ≈ 220 s per arm at u182.
- Evidence 1: R-5: a realistic peak effect is ≈ 1 SD at ε 2 and ≈ 2.3 SD at ε 8 even with every user on K8; no P2 metric is
  conditional on period; MIA-blind.
- Large-n 4: period × class contrasts, weekday/weekend, a 3 × 3 copula, possibly an LDP fixed-effects estimator (G1).
- Distinctness 2: needs a host; on §4's simulator it is a question family for C1's time-of-day factor.
- Cost 3: pair rule, ordered probit, copula (twins shared with K1); a joint metric is a new prerequisite.
- Thesis 5: the thesis's central contrast: what user-level LDP learns that per-trajectory LDP cannot (within-person effects
  free of who travels when).

### Totals
| K | Nov ×4 | Priv ×1 | Fit ×2 | Evid ×3 | Large-n ×2 | Dist ×4 | Cost ×1 | Thesis ×3 | **Total /100** | Equal weights /40 |
|---|---|---|---|---|---|---|---|---|---|---|
| K4 | 3 | 5 | 4 | 3 | 4 | 3 | 3 | 3 | **66** | 28 |
| K8 | 4 | 5 | 3 | 1 | 4 | 2 | 3 | 5 | **64** | 27 |
| K6 | 3 | 4 | 3 | 2 | 4 | 3 | 2 | 4 | **62** | 25 |
| K1 | 3 | 5 | 4 | 2 | 4 | 2 | 4 | 3 | **60** | 27 |
| K2 | 3 | 5 | 4 | 2 | 3 | 2 | 3 | 3 | **57** | 25 |
| K5 | 2 | 4 | 4 | 3 | 3 | 2 | 4 | 3 | **56** | 25 |
| K3 | 2 | 5 | 4 | 3 | 3 | 2 | 3 | 2 | **53** | 24 |
| K7 | 2 | 4 | 4 | 2 | 4 | 2 | 2 | 3 | **53** | 23 |

Ranking: K4 66 > K8 64 > K6 62 > K1 60 > K2 57 > K5 56 > K3 53 = K7 53. With equal weights K4 still leads (28), K1 and K8
tie second (27) and K6 drops into a tie with K2 and K5 (25). My scoring noise is about ±3 points, so places 2–4 are not
separated. No single candidate passes 66 because each scores ≤ 3 on distinctness or on n = 91 evidence; §3 combines.

## 2. Red team: the top four
### K4 Via-point route structure
- **Strongest attack (statistics and visibility): "your route-structure law describes the pipeline, not behaviour."** Sessions
  are unsplit (R-1), so pieces and loops partly come from multi-stop sessions; the matcher fills GPS gaps with shortest paths
  (k pushed to 1) and turns jitter into short detours (spurious pieces); only ≈ 10 % of trajectories pass matching, probably
  the cleaner ones. **Survives for the benchmark** (test users carry the same artefacts, so P2 gains are real), **not for a
  behavioural claim** unless controlled. **Fix:** model the session structure instead of fighting it (a pause class from raw
  timestamps: combination A), a public minimum piece length (≈ 300 m) against jitter, a fixture check of piece counts on
  matched routes versus raw GPS, and K4 alone as the ablation that isolates the session effect.
- Statistics: raw class shares are confounded with the OD-length mix (longer trips have more pieces), so a wrong prior OD mix
  shows up as "route structure". Fix: the window item (vias per km), or class × two OD-distance bands at ε 8 (8 cells).
- Novelty: Knapen et al. 2016 publish the statistic and propose it for route generation; survives as NOVEL COMBINATION only if
  Knapen is named the closest work and the claim is the private law plus the exact-likelihood generator with loops; the window
  scale profile is the one estimand without precedent. Privacy: no attack on the core.

### K8 Within-user contrasts and couplings
- **Strongest attack (visibility): nothing shows on Geolife and nothing the benchmark can see.** R-5; items a, c, d leave the
  edge likelihood unchanged; P2 has no period-conditional or joint metric. **Does not survive as a standalone mechanism;
  survives as a module and as an S2 and theory result.** **Fix:** host it on K1's twins (combination B), add one cheap metric
  (duration W1 within departure period), and give S2 a population where who travels when is confounded, so within-user and
  pooled estimates visibly differ.
- Novelty: a sign test on an RR-protected paired difference is folklore and the central analogue exists; survives only through
  the identification argument plus a variance comparison with the pooled estimator.
- Statistics: eligibility selects users with both peak and off-peak trips (commuter-like), so the estimand is the effect among
  eligible users; the ⊥ share reports its size.

### K6 Mobility-signature users
- **Strongest attack (statistics): ρ is not identified at n = 91.** R-4: only users with ≈ 4–25 matched trips separate ρ = 0.6
  from 0.3, and translating bin shares into ρ needs the trips-per-user law, which is not public (X5); the estimate is then
  either biased (guessed law) or an S1 violation (Geolife law). **Does not survive at n = 91; survives at large n** with a
  joint S × trip-count item (16 cells, too thin at n = 91: ≈ ±0.08 per cell at ε 2). **Fix:** the joint item; bins frozen
  from a public EPR simulation under a public trips law; and the one-hour public check (does ρ move length W1 and 3 × 3 OD JSD
  at all?) as a go/no-go before any code.
- Visibility: the coherence metrics rest on ≈ 36 test users at u182 and are useless at u20/u50. Fit: Monte-Carlo likelihood
  (X12), deterministic at least with common random numbers across the 17 generators.

### K1 Twin-rank calibration
- **Strongest attack (statistics): saturation plus redundancy.** Against a car-speed prior with 0.42-nat jitter, walks, buses
  and dwell-laden sessions (R-1) fall in the top tercile; a location-scale fit of three bins then yields a level and a spread
  at best and no bimodality. Every remedy re-runs §4: a public mode-mixture prior turns the PIT into a mode classifier (C3), a
  re-centring cohort costs √2 and is Joseph et al. 2019. **Survives only as an estimator layer**, not as a second mechanism.
  **Fix:** a public mode-mixture prior or unequal prior-quantile bins with a tail bin (e.g. at PIT 0.5 / 0.95 / 0.999, exact
  null kept), and pairing with K8 (combination B) so that it carries an estimand §4 lacks.
- Visibility: time is not in the edge likelihood, so the MIA sees the prior (AUC 0.5 by construction); gains only on duration
  and speed W1. Privacy: no attack; its m-invariance is the cleanest answer to X5 (§5 F2, F7).

## 3. Combinations
A combination counts only if its parts share one report (one public question draw, one primitive at full ε), one privacy
argument (X1), and do not re-tell §4.

### A Legs, pieces and loops (K4 + K3's stop spells + K2-W's dwell; K1's gate optional): beats every single candidate
- **Report.** The device draws one matched trajectory uniformly, cuts it into legs at pauses by a public rule (e.g. ≥ 3 min
  within 150 m, or a recording gap ≥ 3 min with < 300 m displacement), splits each leg into maximal near-shortest pieces
  (K4's greedy rule, τ = 0.05, e.g. minimum piece 300 m) and flags a loop (OD road distance < 0.25 × route length). Below a
  public n·ε² threshold (n = 91, ε ≤ 2): one class of {one leg and one piece; one leg, ≥ 2 pieces; ≥ 2 legs; loop} by GRR
  over 4. At ε 8 or large n: legs {1, 2, ≥ 3} × max pieces per leg {1, ≥ 2} × loop (12 cells), or, on a public user split,
  K3's speed state at a time-uniform second, K2-W's dwell class of one pause, or K4's window bit.
- **Privacy.** X1 for every family; rules frozen by hash; users, never ε, are split; one report.
- **Server and generator.** Debias, project, shrink to a cited prior (Knapen et al. 2016 decomposition sizes; Zhu & Levinson
  2015 shortest-path shares; a cited share of tours with intermediate stops; a cited leisure-loop share; a cited activity-
  duration law for dwells). Departure from the public profile, O by road-length mass, class from π̂, D by the prior or C2 (near
  O for a loop), vias and pause points at public anchors under K4's offset kernel, pieces as high-β Boltzmann walks, segment
  times = free-flow × factor × jitter plus a dwell at each pause. Road-valid and timed.
- **Likelihood.** K4's exact via-DP. In an edge sequence a pause at an anchor is a via (time is summed out), so legs add no
  likelihood cost; pauses must stay at anchors so that `generate` and the likelihood are one model (X12).
- **Checks.** One report, one argument: yes. Re-tells §4: no; none of C1–C3 models legs, pieces, loops or pauses, and the §4
  walk gives loops almost no mass. n = 91: the paused share (perhaps the loop share) is the likely mover at ±0.074, visible on
  duration, mean-speed and length W1 and on the OD diagonal. Scores: Nov 3, Priv 5, Fit 4, Evid 3, Large-n 4, Dist 4, Cost 2,
  Thesis 4 → **72** (equal weights 29).

### B Rank calibration across and within users (K1 + K8 items a, c): beats every single candidate, partly re-tells §4
- One report: a public draw picks a single-trip PIT bin (K1), a paired twin-rank class of one eligible peak/off-peak pair
  (K8a) or a within-user rank-correlation sign (K8c); GRR at full ε; X1. Exact nulls throughout: single-trip ranks are uniform
  under a correct prior, and paired PIT differences are symmetric when a user effect shifts both trips alike (V: the two PITs
  are exchangeable).
- K8 gets a host and K1 gets an estimand §4 lacks. But generator and parameters are §4's time model, so it reads as §4's
  estimator layer, and at n = 91 the n·ε² rule puts every user on K1's *dur*: on Geolife, B = K1. Scores: Nov 4, Priv 5,
  Fit 4, Evid 2, Large-n 4, Dist 2, Cost 3, Thesis 5 → **69** (equal 29).

### C Hubs and exploration (K6 + K5): does not beat K4
- One report among the modal cell (K5 Q1, the n = 91 item), habit share (HM), S × trip count (GRR over 16), r_g bins; X1. EPR's
  top-ranked location is the hub, so all items describe one d-EPR population with a home. Revives C4 (Cond-C4: coherence
  metrics must ship); n = 91 evidence is K5's hub cell; Monte-Carlo likelihood; ≥ 5 sessions. Scores: Nov 3, Priv 4, Fit 3,
  Evid 3, Large-n 4, Dist 3, Cost 2, Thesis 4 → **65** (equal 26).

### Rejected pairings
- K2 + K3 (time first with a speed clock): both n = 91 items are X10's mode mix and K2's loop failure remains.
- K7 + anything: its runnable forms are CLOSE VARIANTS and it needs two non-public population laws.
- K1 + K4 (rank of the piece count among twin routes for the trip's own OD): removes OD confounding for the ordinal part, but
  adds device twins for a 4-way item; kept as an optional large-n estimator inside A.
- The consolidator's four drops stand; R2-E.3 is now known to be LDP private sampling (G1), which strengthens its drop.

**Answer.** Yes: A is one mechanism with modules, one report and one privacy argument, outside §4, and it beats every single
candidate under both weightings. B also beats them on the weighted total, but only as a calibration layer for §4's simulator.

## 4. Final picks for the author
### Pick 1: A, Legs, pieces and loops
**In plain words.** Real GPS trajectories are rarely one straight trip from A to B: people stop on the way, follow routes made
of a few near-shortest stretches joined at turning points, and often come back to where they started. Each phone picks one of
its user's trajectories at random, works out which of four structure types it is (one direct stretch; several stretches; with
a stop; a round trip) and sends that type through randomized response. The server learns how common each type is and generates
synthetic trajectories of the same types on the OpenStreetMap graph: stretches between public junctions, stops with durations
from published time-use constants, round trips that return near the start, all with departure and per-segment times.
**Caveats.** The Geolife signal will partly come from how the data were cut (R-1, matcher; X13). The core statistic is Knapen
et al. 2016's; the novelty is the private law plus an exact-likelihood generator with loops and pauses (NOVEL COMBINATION,
medium). Pauses only at public anchors (cost). OD-mix confounding of raw class shares. P1 must represent a dwell, not only
per-edge entry times. ≈ 5–6 sessions beyond P0–P5.
**Geolife at n = 91.** ε 0.5: the prior arm. ε 2: one 4-way item at ±0.074; the share of trajectories with a pause moves if
the prior misses it by ≥ 0.15–0.25; gains on duration, mean-speed and length W1 and the OD diagonal, against A's prior arm and
against §4's walk on the same OD; K4 alone as the session ablation. ε 8: the 12-cell joint at ≈ ±0.03–0.05.
**Only the simulation.** Pieces per km by OD band, via offsets and positions, the dwell law by daypart, corridor heavy hitters;
recovery curves; the misspecified run (simulate a one-piece walk population; the gate must keep the prior).
**Open decisions.** (1) Trips or sessions: a public stay split for all arms (consistent with §4's trip model, but it changes
the S4 data and removes most of A's pause and loop signal) or sessions modelled by A. (2) The pause rule and minimum piece
length. (3) The cited constants of the prior. (4) Pauses only at anchors, or anywhere at a higher likelihood cost. (5) A
standalone mechanism, or a router option of §4. (6) User-weighted estimand (one trajectory per user) or capped trip weighting (X4).

### Pick 2: B, Rank calibration across and within users
**In plain words.** Each phone compares one of its own trips, or one rush-hour trip with one off-peak trip, against "twins" that
the public simulator produces for exactly the same route and time, and sends only a coarse rank (faster than most twins, in the
middle, slower). If the public simulator is right, these ranks are perfectly balanced for every user, whatever their mode or
number of trips, so the server tests the simulator with a pre-registered threshold, keeps it unless the test fails, and
otherwise recalibrates its travel times. The paired form measures the rush-hour effect within the same person, free of who
travels when, which per-trajectory LDP cannot do by construction.
**Caveats.** It calibrates §4's own simulator and time parameters, so a reviewer may read it as §4's estimator layer; time is
not in the edge likelihood (MIA-blind); single-trip ranks saturate against a car prior unless the prior is a public mode mixture
or the bins include a tail bin.
**Geolife at n = 91.** Only the duration rank (n·ε² rule): a level shift or a "much slower" share at ε 2, the same mode-mix
quantity C1 and C3 move (X10); nothing at ε 0.5; at ε 8 HM ranks (±0.045 nats) on two questions.
**Only the simulation.** The gate's exact level under any trips-per-user law; within-user versus pooled rush-hour effect under
confounding; per-context maps; joint PITs.
**Open decisions.** Host (§4's P3 or A's router); mode-mixture prior or tail bins; ship as a mechanism or fold into §4 as C1's
time questions; a period-conditional duration metric in P2; the eligible-pair rule.

### Pick 3: C, Hubs and exploration (whole users)
**In plain words.** Synthetic people instead of synthetic trips. At Geolife size each user reports only the 5-km square where most
of their trips start or end; with many users they also report how many distinct places they visit for their number of trips and
how strongly they return to the main place. The server fits a published exploration-and-return model of individual mobility on
the OSM graph, gives each synthetic user a main place and emits their trips, unlinked for today's metrics and linked for new
user-level metrics.
**Caveats.** Cond-C4: coherence metrics must ship and rest on ≈ 36 test users at u182; the modal cell reads as a home report and
at ε 8 releases near-home cells; X5 and R-4 leave the exploration constants unidentified at n = 91; Monte-Carlo likelihood; the
hub generator must put the hub at exactly one trip end; ≥ 5 sessions.
**Geolife at n = 91.** One hub cell at ε 2, only if ≥ 35 % of users share a modal 5-km cell (unmeasured).
**Only the simulation.** Recovery of ρ and γ with the joint item; whether ρ changes unlinked metrics; coherence metrics versus n.
**Open decisions.** Linked output and coherence metrics; S1-clean handling of the trips law; grid size; the one-hour public EPR
check as a go/no-go.

Not picked: K1 and K8 alone (an estimator layer and an invisible estimand, both better inside B), K2 (loop failure, overlaps C1
and C2), K3 (a module), K5 and K6 alone (inside C), K7 (CLOSE VARIANT forms).

## 5. Findings for the chosen §4 design
- **F1 Sessions, not trips (V, new).** By R-1 §4's trip model is misspecified on Geolife: C1's speed ratio and departure moments
  include dwells and gaps; a round-trip session has D ≈ O, which C2's gravity and the Boltzmann walk barely produce; C3 may label
  a car session with a long stop as walk or cycle. Decide before the prior is frozen: a public stay split as a dataset option
  (changes every arm and the S4 numbers) or session-aware modelling (pick A's pause and loop classes as a §4 router option).
  Either way P1's timed payload needs a dwell (entry and exit time per edge), or a pause becomes an absurdly slow edge.
- **F2 X5 confirmed (V by reasoning).** Plan §4.3 simulates C3's confusion matrix "under a public number of trips per user",
  which no cited constant gives (it is set by cleaning and the ≈ 10 % match rate). Cheapest remedy: draw C3's label from the
  posterior of ONE uniformly sampled trip, so the confusion matrix is public by construction (cost: a flatter matrix, small when
  regimes differ in speed by a factor of 3 or more). Alternatives: a trip-count class inside the label item; an m-invariant rank
  form (K1); a sensitivity sweep in S2. C1's user means and C2's sampled trip end are unbiased for the user-weighted estimand
  without the law.
- **F3 Who reports must not depend on the data (V for the harness, new).** `fit` sees only matched train trips (R-2), so a train
  user without a matched trip sends no report, and the n of the n·ε² rule counts users with matched trips. Both are functions of
  private data: R2 compares any two possible users, and "no report" versus a GRR output differs without bound, while n couples
  every other user's question to user i. Tiny in practice at n = 91 (n·ε² is far from the thresholds), but the guarantee stated
  in §4.2 ("every enrolled user sends one report") does not hold as implemented. Fix: pass every train user to `fit` (for
  instance with clean views for unmatched trajectories, as X6 proposes), let users without a matched trip send the public default,
  read n from the train split; add a P4 test that a user whose trips stop matching still sends exactly one report.
- **F4 Plan noise values (V).** §4.3 (C3: 0.12 at ε 1, 0.05 at ε 2), §4.4 (C2: 0.06 if all answer, 0.10 at 40 %, 0.19 at ε 1)
  and §5.1 (3 shares 0.05, 9 shares 0.06; a third of users 0.08 / 0.11) are vanishing-share values. Exact at shares near 1/k:
  3 shares 0.136 (ε 1), 0.073 (ε 2); 9 shares 0.206 (ε 1), 0.079 (ε 2), 0.11 for a share near 0.5; at 40 % of users 0.125; with
  a third of users 0.126 / 0.137. With OLH, as §4.4 specifies for zones, ≈ 0.095 (all) and ≈ 0.15 (40 %). No module verdict
  flips; detection margins shrink by 15–40 %.
- **F5 Primitive choice (V).** For C2's 3 × 3 zones at ε ≥ 1 GRR beats OLH (k = 9 < 3e^ε + 2 = 10.2 at ε 1, 24 at ε 2; ≈ 0.079
  vs ≈ 0.095 at ε 2); OLH only from 36 zones up.
- **F6 Expect C1 to duplicate C3 on Geolife (C, X10).** At n = 91 the speed ratio and the regime vote measure the same mode mix;
  report the C1-only arm at ε 2 as a check, not as a separate gain (the plan already expects most evidence from C3 and C2).
- **F7 A do-no-harm gate per module (suggestion).** Compare each module's raw report histogram with the histogram the prior
  predicts through the known randomizer (exact under the null, no extra users); keep the prior unless a pre-registered test
  rejects. K1's twin ranks extend this to continuous items without any trips-per-user law. It gives §4 an evidence statement even
  where nothing moves.
- **F8 Freeze candidate design constants too (lesson 7).** Bin edges and eligibility rules built around ≈ 9 matched trips per user
  (K6's bins, R2-D's cohorts, K8's eligibility guesses) use a Geolife figure; the freeze-by-hash rule must cover them, as it
  covers §4's zones and catalogue.
- **F9 Works §4 should cite (from G1–G3).** Private calibration of a shared model or simulator: Cormode & Markov, PVLDB 2023 (LDP);
  Chopra et al., AAMAS 2024 (MPC). Simulate–privatise–match, not to be claimed as new: Sakong & Zentefis (NBER 2024), Xiong et
  al. 2023, Wang, Chang & Awan 2025. Mode, distance and duration under user-level (central) DP: Bian et al. 2024 (Google EIE), for
  C3's mode mix. User-level LDP with m samples per user: Acharya, Liu & Sun 2023; Kent, Berrett & Yu 2024 (C2's one sampled item
  is their baseline). Whole-user DP generators: PateGail (AAAI 2023), PateGAIL++ (ICLR 2026); never claim "the first user-level
  LDP trajectory generator". LDP private sampling: Husain et al. 2020, Park et al. 2024, Zamanlooy et al. 2025; C3's "posterior
  draw, then GRR" is a locally private sampler, and Park et al.'s optimal sampler deserves a comparison. Adaptive cohorts (§4.8):
  Joseph et al. 2019, Aamand et al. 2025, Penso et al. 2025, Wang et al. AAAI 2018 (disjoint groups, each uploading once). Route
  structure constants usable as an S1-clean prior for C1's router: Knapen et al. 2016, Zhu & Levinson 2015. Stops by road class
  on OSM: BerlinMOD.

## 6. Pushback round (one round, 2026-10-07)
This section supersedes the scores, ranking and picks of §1–§4 where they differ. The re-scores assume the stay split, which I now
recommend as a shared prerequisite for the new campaign and for §4 (F1); without it, A's extra signal would describe how volunteers
switched logging on and off, not travel. One web check (Zhu & Levinson 2015, PMC full text); Knapen et al. 2016 stayed paywalled.

- **P1 (a)** The split removes pauses and splits round trips, leaving pieces and stop-free leisure loops. Cited car data put 30–55 % of
  trips within 5 % of the shortest time (Zhu & Levinson 2015, 25,157 GPS trips; Knapen et al.'s tables are paywalled; no cited loop
  share), so the multi-piece share is ≈ 0.45–0.7, itself a ±0.12 range. A 2-SD move needs ≥ 0.15 (exact SD 0.074–0.077 near 0.5, ε 2),
  and its likely causes are the mode mix (walkers' routes judged by car costs) and matcher gap filling: Evidence 3 → 2. **(b)** No (56/95).
- **P2** A never led on novelty (A 3, B 4); its lead came from distinctness and evidence, which P1 removes. I still lower A and K4 to 2:
  Knapen et al. 2016 publish the statistic and its use for route generation, and the rest (a frequency oracle on it, a loop class, an
  exact via likelihood) is lesson 1's "one detail". One rule for all: frequency oracle on a published statistic + published generator
  = 2 (K2 also 3 → 2); an estimation step with its own identification argument = 3 (K1, K6); a new estimand = 4 (K8).
- **P3** Changing only the weights (privacy a gate; large-n 3, evidence 2, the rest as before; max 95) keeps the top three: A 68, B 66,
  C 62; singles K4 = K8 = 62. All candidates pass the gate on two conditions: the F3 reporting fix (all), and a trips-per-user law asked
  inside the report, never fitted on Geolife (K5, K6, K7, C). The order changes only through P1, P2 and P4 (table); moving the spare
  weight point to cost or to fit changes no place among the options.
- **P4** Yes, B passes. P3 is a prerequisite that K2–K5 reuse too, not a §4 module, and B's report (a rank against device-simulated
  twins, exactly uniform under a correct prior for any trip count) and its within-person estimand appear nowhere in C1–C3. Condition,
  not a redesign: no moment or vote questions, and the n = 91 duration level is shown head-to-head with C1 on the same users and
  simulator, not as a new finding. "Estimator layer" overstated it: Distinctness 2 → 3 (K1 alone stays 2: its estimand is C1's).
- **P5** C is S1-viable: at n = 91 only the modal-cell item runs, and unlinked output needs no trips law (a fixed trip count per synthetic
  user gives the user-weighted estimand, X4); at large n the law is measured inside the report. Cond-C4 is a benchmark prerequisite, not
  S1. Time-first T = K2 + K3 (one duration × tightness or speed-state item; isochrone destinations; speed-state clock router; exact
  likelihood) scores 54/95 against C's 62: its Geolife item is C3's mode mix and both parts are frequency oracles. Keep C; T runner-up.
- **P6** B: departure from the public diurnal profile (the *dep* rank recalibrates it only at ε 8 or large n); segment times = public
  free-flow × factor × jitter, the trip total quantile-mapped from the duration ranks (reports, n = 91) and the rush-hour factor from
  within-person pairs (large n), every segment scaled alike. C: departure and segment times public (a modal-daypart item only at ε 8).
  A′: all public (K3's speed states as a large-n module). Only B estimates time at Geolife size; T would make time its whole estimand.
- **P7** Yes, all three: every train user sends one report, and a "no matched trip" category ⊥ joins each domain (B's rank bins + 1,
  C 36 + 1 cells, A′ 4 + 1 classes). n becomes the public train-split count (≈ 91 / 25 / 10); the ⊥ share d is estimated privately, and
  shares among users with data get SD × 1/(1 − d) against an all-informative population, × 1/√(1 − d) against today's leaky harness
  (× 1.05 at d = 0.1, × 1.2 at d = 0.3). The gates stay exact, since ⊥ is outside the null.

### Re-score (privacy a pass/fail gate; weights Novelty 4, Distinctness 4, Thesis 3, Large-n 3, Evidence 2, Fit 2, Cost 1; max 95)
| Option | Nov | Dist | Thesis | Large-n | Evid | Fit | Cost | **/95** | Change and reason |
|---|---|---|---|---|---|---|---|---|---|
| **B** K1 + K8 | 4 | 3 | 5 | 4 | 2 | 4 | 3 | **70** | Dist 2 → 3 (P4) |
| K8 | 4 | 2 | 5 | 4 | 1 | 3 | 3 | 62 | part of B |
| **C** K6 + K5 | 3 | 3 | 4 | 4 | 3 | 3 | 2 | **62** | S1-viable with P5's conditions |
| A, sessions kept | 2 | 4 | 3 | 4 | 3 | 4 | 2 | 61 | Nov 3 → 2 (P2), Thesis 4 → 3: its extra signal is logging behaviour; not recommended |
| K6 | 3 | 3 | 4 | 4 | 2 | 3 | 2 | 60 | part of C |
| K1 | 3 | 2 | 3 | 4 | 2 | 4 | 4 | 57 | part of B |
| **A′** = K4 after the split | 2 | 3 | 3 | 4 | 2 | 4 | 3 | **56** | Nov 3 → 2 (P2), Evid 3 → 2 (P1) |
| T K2 + K3 | 2 | 3 | 3 | 3 | 3 | 4 | 2 | 54 | new (P5) |
| K5 | 2 | 2 | 3 | 3 | 3 | 4 | 4 | 52 | – |
| K2 | 2 | 2 | 3 | 3 | 3 | 4 | 3 | 51 | Nov 3 → 2 (P2); Evid 2 → 3 (the split removes its loop failure) |
| K7 | 2 | 2 | 3 | 4 | 2 | 4 | 2 | 51 | – |
| K3 | 2 | 2 | 2 | 3 | 3 | 4 | 3 | 48 | – |

Ranking of options: **B 70 > C 62 > A′ 56 > T 54**; the singles K8 62, K6 60 and K1 57 are parts of B and C. Equal weights (privacy a
gate, max 35) give B 25, C 22, A′ 21, T 20; the spare weight point on cost (B 73, C 64, A′ 59, T 56) or on fit (B 74, C 65, A′ 60,
T 58) keeps the order.

### Updated picks
1. **B Rank calibration across and within users** (K1 + K8), with P4's condition and a public mode-mixture prior (or an extra
   "much slower" bin) against saturation. Weakest point: at Geolife size it shows only the duration level, the mode mix that C1 and C3
   also show; its distinctive results (the exact-null test, the within-person rush-hour effect) appear only in the simulation.
2. **C Hubs and exploration** (K6 + K5), under P5's S1 conditions and Cond-C4.
3. **A′ Route structure** (K4 with the loop class; pauses dropped after the split; K3's speed states as a large-n module). T (K2 + K3)
   is within noise of it and is the better choice if time itself must be what users report.
