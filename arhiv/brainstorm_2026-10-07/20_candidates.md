# Consolidated candidates: user-level pure LDP, timed road-network trajectory synthesis

Consolidation of the 20 ideas in `10_ideas_A..E` (7 Oct 2026), read against `01_task.md` and
`00_briefing.md`. Source ideas are cited as *lens.idea*: A.1 is idea 1 of lens A (LDP
statistician); B = transport scientist, C = machine learning / federated, D = privacy adversary,
E = wildcard. Candidates C1–C10 are ordered by my promise estimate (the "C" of a candidate has
nothing to do with lens C).

**Abbreviations.** LDP = local differential privacy (every user randomizes on the device).
OD = origin–destination. GRR / k-RR = generalized (k-ary) randomized response. OUE / OLH =
optimized unary encoding / optimized local hashing, frequency oracles for large domains. PM / HM =
piecewise / hybrid mechanism for one bounded number; Duchi = the one-bit mechanism for a bounded
number (or its ℓ₂-ball version for a vector); SW = square-wave mechanism for a numeric
distribution. PCKV = correlated key–value perturbation. PEM = prefix-extending heavy-hitter
method. RL = recursive logit, a route-choice model in which the next edge is drawn with
probability proportional to exp(edge utility + value of continuing); MaxEnt = maximum entropy
(exponential family). IPF / Furness = iterative proportional fitting. MIA = membership-inference
attack. JSD = Jensen–Shannon divergence. TPR / FPR = true / false positive rate.

## 0. Facts that apply to every candidate

1. **The real n is about half of what two authors used.** `fit` sees only the train split: about
   91 users at the 182 rung (only those with a trajectory that passes map-matching, so possibly
   fewer, with about 9 matched trips each on average), 25 at u50, 10 at u20, and about 5,000 if
   T-Drive is added. Authors A, C and most of D use n ≈ 91; B, E and D.4 computed with
   n ≈ 180–182, so their error bars are about √2 too small. All scale lines below are restated
   for n ≈ 91. A membership shadow sees about 18 shadow users plus candidate trajectories; whether
   candidates enter as one-trajectory users (E assumes so) or under their own `user_id` should be
   checked in the harness.
2. **The benchmark cannot rank these candidates on privacy.** User-level ε-LDP bounds every
   membership test by TPR ≤ e^ε · FPR, so the proposed pass mark (TPR ≤ 0.02 at FPR 0.01) is
   guaranteed only for ε ≤ ln 2 ≈ 0.69 (D §0.1). In practice one report among about 91 barely
   moves any estimate, so every candidate's MIA will sit at chance, as RN-LDP-Synth v1's already
   does (and even the non-private `markov` ceiling reaches only AUC 0.776, TPR 0.027 at FPR 0.01
   at u182). Useful privacy evidence is structural: a randomizer audit (empirical log-ratio of
   output frequencies ≤ ε), a canary user, and a test that `sequence_log_prob` reads only a small
   parameter vector and the map (D §0.1–0.2). Comparison plots need user-level ε: a user with 95
   trips under per-trajectory ε = 0.5 is at user-level ε ≈ 47 (D §0.3).
3. **Utility evidence does not exist yet.** Synthetic utility is not wired into the orchestrator;
   unpaired cell-JSD and length functions exist only in `rnldp_eval`, and departure-hour, duration
   and speed metrics do not exist at all. Every candidate needs them plus a "public prior only"
   arm, because the gain over the prior is the only proof that private data was used. A
   user-level average estimates the average *user*, while the raw references are trip-weighted
   and dominated by heavy Geolife users; compare with a user-weighted reference or use A's capped
   trip weighting (A §0, rule P2).
4. **What "public prior" can mean here.** The current `RoadNetwork` (OpenStreetMap, OSM) supplies
   topology, `length_m`, `highway` class, `oneway`, `maxspeed` (coverage undocumented, so
   configured class-default speeds fill the gaps) and node coordinates (turn angles, zones,
   road-length masses). Road names and refs (ring roads, corridors), land use and points of
   interest exist in OSM but not in the current tables: extracting them from the same OSM snapshot
   is allowed but is new work. Which highway classes the graph holds (drive-only, or also
   footways and cycleways) decides whether walking and cycling can be routed realistically.
   Diurnal departure profiles, route-choice coefficients, activity-motif shares, mode speeds and
   road capacities are not in OSM: they must be cited publications or plain configuration, frozen
   before the run. A prior tuned on Geolife is an unprotected release (B.4 and D.3 say so) — a
   live risk, because the designers already know Geolife's statistics from the S4 runs; only
   choices justified by the map or by public documentation are safe.
5. **Candidates compose without extra budget.** A public draw can assign each user to one
   question family, so every user still sends one report at full ε; combining families splits
   users, not ε (rankings of A, B and C; E's composition note). The likely final design is C1's
   route and time slots plus C2's (or C6's) spatial slots, possibly with C3's regime label.
6. **Route statistics are partly the map matcher's.** Detour, road-class and turn statistics are
   computed on map-matched edge sequences, and the matcher itself favours shortest paths between
   GPS fixes (B.1's risk), so a route-taste parameter learned at n ≈ 91 may describe the matcher
   rather than the users.

## 1. Dropped ideas: none

No idea meets a drop criterion. All 20 send exactly one report per user per window through a
standard ε-LDP primitive applied to a publicly bounded function of all the user's trips (or of one
trip chosen with data-independent local randomness); clip ranges, grids, catalogues and question
assignment are public; adaptivity happens only across disjoint user cohorts; no trusted party is
needed. All 20 route on the public graph (road-valid by construction) and model departure time and
per-segment timing. None is an exact re-publication. Closest to a drop, kept with a warning:

- **A.2** (→ C10): the zone-transition design of LDPTrace and RN-LDP-Synth v1 made user-level;
  kept because its conservation-exact walk removes the separate length model, but it is the public
  prior at every Geolife rung.
- **C.3** (→ C5): its author calls it "arguably an LDP port of PrE-Text"; kept because a pure-LDP,
  one-shot version over timed road trips is not obviously published.
- **E.2** (→ C9): an n-gram LDP model (Cunningham et al. is a listed neighbour) over a new,
  location-free alphabet; kept because the alphabet changes what is modelled.
- **B.2** (→ C2): LDP OD collection is published (L-SRR 2022; a hybrid local-DP OD paper in
  *Electronics* 2024, both found by author B); kept because the gravity-regularized inversion with
  timed road synthesis is not.

## 2. Candidates

### C1: Behavioural-moment router

**Provenance.** A.1 (centred-moment MaxEnt), B.1 (transfer-and-update RL with score reports), C.1
(one-shot score tilt), D.2 (behavioural moments, moment-tilted router), E.3 (revealed-preference
moments calibrate a simulator). The family appears in all five lens files, not four, and each
member is its author's top pick; "four" fits only the narrower wording "centred on a public
reference" (A.1 and E.3 centre on the same-endpoint fastest / shortest path, B.1 and C.1 on the
prior model's expected features, D.2 sends raw moments with only the detour ratio relative to the
shortest path).

**Mechanism.**
- *Local:* per own matched trip, a few clipped route and time statistics (road-class shares, turns
  per km, detour or length, speed ratio to the public free-flow speed overall / per class / per
  period, departure-hour harmonics), mostly as differences from a public reference, averaged over
  all the user's trips: x_u ∈ [−1, 1]^d, with d = 3–8 used at n ≈ 91 (16–25 defined in A.1 and
  C.1); d does not grow with the graph.
- *Randomization:* a public draw picks one coordinate or categorical slot; numeric slots by PM /
  HM / Duchi, categorical ones (period, speed regime, one trip's zone) by GRR / k-RR; full ε, no
  composition (A.1 sends about ε/2 questions at ε/k each when ε ≥ 4). Bound: the per-user average
  lies in a public box whatever the trip count.
- *Server:* unbiased means with known noise variance, projected onto the feasible set and shrunk
  toward the public prior θ₀; then a handful of parameters (class costs, turn penalty, detour
  temperature or distance decay, departure density, speed level or regime) is fitted so that the
  model's expected statistics match; the fit method differs by variant (table below).
- *Generation:* origin by public road-length mass, destination by gravity or a destination logit,
  path by an edge-by-edge destination-directed walk (road-valid; public step cap with a
  shortest-path finish), departure from the fitted circular density or period shares (UTC+8),
  per-edge time = free-flow time × fitted speed factor × AR(1) or log-normal jitter (+ public turn
  delay). `sequence_log_prob` = log P(O, D) + Σ log step probabilities + a public gap term: exact
  and finite.

**Variants — what exactly each author claims.**

| Variant | Statistics | Centred on | Randomizer | Server fit | Router |
|---|---|---|---|---|---|
| A.1 | 16: O and D macro-zone (3×3), log OD distance, metres per class group (3) and turns vs fastest path, 4 departure harmonics, weekday, 4 log speed ratios | same-endpoint fastest path | GRR / HM / SW, one question | projection (simplex, Toeplitz-PSD harmonics), then MAP exponential-family fit with exact log Z from sparse LU solves | exact RL toward zone sinks, θ private |
| B.1 | 3 likelihood-score coordinates (observed − expected features per OD free-flow minute; deterrence c_od − E[c given o]) + period or speed regime of one trip | prior model's expectation (score at θ₀) | PM / k-RR, 5 equiprobable questions | one Bayesian Newton step θ̂ = θ₀ + (Σ₀⁻¹ + JᵀV⁻¹J)⁻¹JᵀV⁻¹ĝ, Jacobian J simulated from prior trips | exact link RL, θ₀ from literature |
| C.1 | about 25: 5 departure, 4 length / radial, 8 route scores, 8 speed moments (road group × period) | prior model's expectation | PM (Duchi at small ε), sampling weighted to speed and length | Gaussian-posterior shrinkage; exact moment matching for departure, OD, speed; one Newton step for the route tilt | local logit on a public cost-to-go (cached reverse Dijkstra) |
| D.2 | 8 raw: length, detour ratio, two class shares, turns per km, speed factor, cos / sin departure hour (3 at small ε√n) | nothing (detour ratio only) | PM on one uniform coordinate | method of moments through a precomputed public response surface E[features given β]; von Mises departure | local Boltzmann walk on public distance-to-destination |
| E.3 | about 11 numeric (detour, class-share and turn-density differences, 4 period speed ratios, length) + O zone, D zone, period of one trip; 5 slots at small n | same-endpoint shortest path | PM / GRR (OUE at large n) | simulated method of moments (Mahalanobis + ridge) by coordinate search over ≤ 6 parameters; Furness OD; optional BPR congestion equilibrium at n ≈ 10,000 | local Boltzmann walk on public cost-to-go |

Two axes separate the variants: (i) exact RL with a private θ (A.1, B.1: a true maximum-entropy
model, but a new sparse factorization per generator) versus a local Boltzmann walk on a fixed
public cost-to-go (C.1, D.2, E.3: cacheable across the 17 generators of a membership arm, but only
loosely "maximum entropy"); (ii) centred residuals (narrower box, so less noise; A.1: a residual
three times narrower is worth nine times more users) versus raw moments.

**Public prior.** Graph, lengths, classes, oneway, turn angles, road-length zone masses: OSM,
available now. Class free-flow speeds: OSM `maxspeed` where present, configured defaults
elsewhere. Gravity decay and departure prior: configuration (uniform unless a published diurnal
profile is cited). θ₀: the fastest-path limit (OSM alone) or B.1's transferred literature
coefficients (public, foreign cities, not OSM); E.3's congestion extension also needs published
road capacities and a city-wide trip total. Verdict: available from OSM alone in its minimal form.

**Privacy argument.** Clean: one standard primitive on a publicly bounded average. Care points:
data-independent slot draw, public boxes and reference speeds, a null default for users without
trips, PM outputs snapped to a grid (floating-point attacks, D §0.2 item 9).

**Scale.** 182 rung (n ≈ 91): ε = 1 moves 1–2 numbers (speed level, mean length); ε = 2 moves 3–5
(plus detour or major-road preference, one departure harmonic pair) at about ±0.2–0.33 of the
half-range; ε = 8 all 16–25. n ≈ 5,000: 25–100+ (per-class speeds by period, zonal preferences,
turn penalties, taste variance; E.3's congestion timing). Degradation: shrinkage to θ₀ with known
variances, and a public n·ε² rule for how many coordinates are asked.

**Closest works named by the authors.** MaxEnt inverse reinforcement learning (Ziebart et al.
2008); recursive logit (Fosgerau, Frejinger, Karlström 2013); LDP mean estimation and risk
minimization (Duchi et al. 2018; Wang et al. 2019; Harmony); LDP learning from moments (Zheng et
al. 2017); LDP-SGD; transfer updating (Atherton and Ben-Akiva 1976); routing from DP-perturbed
trajectories (*Mathematics* 2024); non-private simulator calibration (arXiv 2501.10934); central
DP on traffic Markov chains (arXiv 2202.03325); PrivBayes, MWEM, PGM. Authors' guess: not found
(A, B, C, E); D expects the central-DP estimation of choice parameters to exist, not the local one.

**Effort / main risk.** M (C.1 is S–M on top of the prior; B.1 and E.3 are M–L). Risk:
misspecification and weak identification — a few averages cannot express idiosyncratic routes, and
Geolife's walking, cycling and motor trips share one cost model.

**Critique.** Five independent authors reaching the same design and all ranking it first suggests
it is the obvious construction — LDP estimation of an exponential family's sufficient statistics
followed by MaxEnt / recursive-logit fitting — so it is the candidate most likely to be published
already (centrally, or as generic LDP exponential-family learning) and must be searched hardest;
its contribution may have to rest on the user-level unit, the fastest-path centring and the timed
road-valid generator with an exact likelihood. In the benchmark it fails on space unless spatial
slots are included (cell JSD stays at the gravity prior while Geolife concentrates in north-west
Beijing), and the exact-RL variants risk the 300 s attack budget (17 private-θ factorizations plus
per-destination solves for every candidate sequence).

### C2: Gravity-regularized OD inversion from LDP margins or cordon counts

**Provenance.** B.2 (entropy-gravity demand from LDP margins), A.3 (private cordon counts and
dynamic OD inversion). A.1's macro-zone slots and E.3's Furness OD are the same idea used inside C1.

**Mechanism.**
- *Local:* B.2 — the user's shares of trip ends over Z public zones (9 at n ≈ 91, 36–144 at
  n ≥ 5,000) and of trips over six free-flow cost bands, five periods and three speed regimes
  (Z + 14 numbers). A.3 — for S public cordons × H hour bins, the per-trip indicators "crossed
  cordon c inbound / outbound in bin h", averaged, plus S − 1 log ring-to-ring time ratios (9
  numbers at S = H = 2). Neither grows with the graph.
- *Randomization:* B.2 answers one question about one locally sampled trip end or trip: zone by OLH
  (probability 0.4), band, period or regime by k-RR (0.2 each). A.3 picks one public cell, rounds
  the user's average unbiasedly to 0 or 1 and sends it by binary randomized response (speeds by
  HM). Full ε, one report; bound: one item from a finite public domain.
- *Server:* debias with the exactly known noise covariance. B.2: T = argmin KL(T ‖ Q) + ½‖AT − t̂‖²
  weighted by V⁻¹, with Q the public gravity prior on a 144-zone free-flow skim, solved by three-way
  Furness scaling (rows, columns, cost bands). A.3: generalized least squares through the public
  assignment map A (fastest routes timed by current speeds) plus λ·KL(p ‖ gravity), p ≥ 0, with
  ring identities, alternating OD and speeds.
- *Generation:* draw period (or hour bin) and zone pair, nodes inside zones by public mass, route
  by a public RL or time-dependent logit around the fastest path (literature coefficients, no
  budget spent on routes), timing by B's period × class speed module or A.3's ring-band × bin
  speed factors. `sequence_log_prob` = OD term + route term.

**Public prior.** Zone grid, free-flow skim and road-length masses: OSM, available. Gravity decay:
configuration. A.3's cordons: Beijing's ring roads are in OSM, but the current edge table has no
name/ref tags, so re-extract them or draw cordons as geometric rings around a public centre point;
check whether the 5th ring fits in the 30 × 33 km map. Route coefficients: literature. Verdict:
available from OSM alone, with that extraction caveat.

**Privacy argument.** Clean: one item or one bit through a standard primitive; optional
padding-and-sampling with a public cap for trip weighting. Care: zones, bands, cordons and prior
fixed in advance.

**Scale.** n ≈ 91, ε = 2: 9-zone margins about ±0.14 and band shares about ±0.13 (B's ±0.10 and
±0.09 assume n = 180), cordon cells ±0.18; two to four parameters leave the gravity prior (centre
attraction, morning-in / evening-out asymmetry, distance decay). n ≈ 5,000–10,000: 36-zone margins
±0.03 at ε = 1, per-period margins, free per-band deterrence, ring × sector dynamic OD (about 100
cells at 0.05–0.08). Degradation: coarser zones, fewer cordons and bins, KL pull to gravity.

**Closest works named by the authors.** Wilson (1967) entropy gravity; Evans and Kirby (1974)
tri-proportional fitting; Van Zuylen and Willumsen (1980), Cascetta (1984), Cascetta et al. (1993)
OD from counts; L-SRR (LDP OD collection, 2022); gravity from DP phone data (NBER chapter); hybrid
distributed/local DP OD estimation (*Electronics* 13(22):4545); central-DP OD with stops (arXiv
2202.12342). Authors' guess: B "moderate novelty"; A claims "LDP cordon answers as sole data, exact
noise covariance, ring identities" as new.

**Effort / main risk.** S–M. Risk: at n ≈ 91 the OD stays close to the road-length gravity prior,
and routes are never learned.

**Critique.** Its few private numbers go straight at the spatial metric and at the joint start–end
structure v1 lacked — if, as B and D state, Geolife's trip ends concentrate in the north-west, a
9-zone margin should detect that even at ±0.14 — but alone it learns no routes or speeds, and LDP
OD estimation is published, so it is best treated as C1's spatial slot family rather than as a
standalone contribution.

### C3: Label vote over a public behaviour catalogue

**Provenance.** B.4 (latent-class behavioural archetypes), C.2 (mixed-membership regimes from one
key–value report), D.3 (electorate over a public generator zoo).

**Mechanism.**
- *Local:* the device scores all its trips under K public complete generators that differ in
  behaviour. B.4: 6 named archetypes (walker, cyclist, peak commuter, off-peak driver,
  expressway-loyal driver, bus-like), each with route coefficients, speed regime, departure profile
  and deterrence. C.2: 2–3 variants of the prior (walking/cycling, urban motor, fast motor), with
  per-trip responsibilities averaged into weights w_u. D.3: a factored zoo of 3⁵ = 243 members (OD
  prior × length scale × router temperature × departure profile × speed factor); a public draw
  assigns the user to one factor or one pairwise duel. Private value: one label or one bit,
  independent of the graph.
- *Randomization:* the label is drawn from the user's posterior (B.4) or from w_u (C.2), or is the
  argmax or duel sign (D.3), then sent by GRR / k-RR (OLH when K > 3e^ε + 2) or binary randomized
  response with the full ε. C.2's large-n variant sends (label, one bit for a public residual
  coordinate) through one GRR over 2K values. Bound: finite public domain.
- *Server:* debiased label frequencies become mixture weights, shrunk to uniform. B.4 also removes
  the classification confusion (simulated once on the public graph under a public trips-per-user
  assumption) by expectation–maximization; C.2 estimates per-regime tilts from the key–value bits
  at large n; D.3 multiplies per-factor weights and, in later windows, lets new cohorts vote on the
  most uncertain factor or duel the incumbent against a public challenger.
- *Generation:* draw a regime (or one level per factor); origin by public mass, destination by the
  regime's deterrence, departure from its profile, route from its router (road-valid), per-edge
  times from its speed regime. `sequence_log_prob` = log Σ_k π̂_k P_k(seq) (D.3: over the 27
  combinations that affect edge sequences).

**Public prior.** The catalogue itself: per-archetype route coefficients, mode speeds (walking about
5 km/h, cycling, bus with stops, car), departure profiles and deterrence come from published
behavioural knowledge and designer configuration; OSM supplies only graph, classes and speeds.
Verdict: not from OSM alone; it needs cited behavioural constants (public, so allowed), frozen
before any Geolife result is seen.

**Privacy argument.** Clean: one label through one frequency oracle; posterior sampling is local
randomness. Care: catalogue, factor assignment and challengers public; reporting an unclipped
likelihood margin instead of a label would break the bound.

**Scale.** n ≈ 91, ε = 2: 6–8 shares at about ±0.06–0.07 before deconvolution, which inflates them
when the confusion matrix is nearly flat — enough for a slow-versus-motor split; ε = 1:
±0.11–0.16, so 2–3 regimes or one duel; D.3 resolves about one factor per window. n ≈
5,000–10,000: 24–48 classes (region, weekday), all five zoo factors with 5–7 levels at once,
per-regime corrections. Degradation: fewer classes, shrinkage to uniform.

**Closest works named by the authors.** Latent-class choice models (Greene and Hensher 2003);
labelled route choice (Ben-Akiva et al. 1984); LDP clustering and codebook quantization;
key–value LDP (PrivKV, Ye et al. 2019; PCKV, Gu et al. 2020); FedEM (Marfoq et al. 2021);
PATE-style voting, exponential-mechanism model selection, private hyperparameter tuning (Papernot
and Steinke), DP model merging (arXiv 2604.20985) — all central DP or non-private. Authors' guess:
new (B, C, D); D proposes D.3 as the mandatory null baseline.

**Effort / main risk.** S (D.3) to M (B.4, C.2). Risk: utility is capped by the hand-made
catalogue; misspecified regimes (a bus with stops resembles a bicycle) bias the shares; with about
9 trips per user the posterior labels are noisy.

**Critique.** It is the only family that represents Geolife's multimodal speed and duration mixture
instead of one speed scalar, so it should win on duration and speed metrics — which do not exist
yet — while its geography is the public prior; and because the catalogue is written by people who
have seen Geolife results, a reviewer can call the prior tuned. D.3 is worth building anyway as the
"public prior + one label per user" null baseline that every other candidate must beat.

### C4: Activity anchors and schedules

**Provenance.** B.3 (anchor-and-tour activity synthesis), D.4 (relations, not places, on public
land use), E.4 (compiled mobility programs).

**Mechanism.**
- *Local:* public rules turn the user's trips into an activity summary. B.3: home (most frequent
  first origin or last destination of a local day), main anchor, median leave and return times →
  7 items (home x and y, log commute distance, commute direction toward the centre, two times,
  speed regime). D.4: stay detection (200 m, 20 min), two most-visited stays → relation classes
  only (home–work road-distance class of 5, commute daypart of 5, day-chain type of 4 at large n,
  speed factor). E.4: a fixed-shape program in a public grammar — home zone (16), work offset (5
  distance bins × 8 sectors), commute days / leave hour / away time, errand rate / radius / time,
  routing style (3), speed class (3): 11 slots, 4 of them used at n ≈ 91.
- *Randomization:* one publicly assigned slot per user; PM for numeric items (B.3), GRR / k-RR for
  classes and program slots; E.4's large-n mode uses PEM prefix heavy hitters over four disjoint
  groups with OLH. Full ε; "none" is a real class for users without a second anchor. Bound: finite
  domain or public interval.
- *Server:* debiased slot marginals shrunk to public priors. B.3: a Gaussian home envelope on
  residential-road mass and a two-parameter work-choice logit P(w | h) ∝ A_w·exp(−β·c_hw +
  κ·cos θ_hw) fitted to the LDP means. D.4: classes attached to public home and work densities
  (residential vs primary–tertiary road length per 500 m cell). E.4 at large n: frequent complete
  programs plus pairwise tables, the rest by Gibbs sampling.
- *Generation:* per synthetic person, a home node by public residential density (inside B.3's
  envelope or E.4's zone), a work node in the drawn distance band or offset, home→work at the drawn
  leave time and back after the away time, optional third leg or errands; each leg is routed on
  the graph and timed per segment, and legs are emitted unlinked. `sequence_log_prob`: closed-form
  mixture over leg types (B.3, D.4) or a documented surrogate (E.4).

**Public prior.** Home and work density from OSM road classes (available now) or from OSM land-use
and office / commercial tags (in OSM, partial in Beijing, not in the current tables: new
extraction); activity-motif shares (Schneider et al. 2013) and schedule spreads from literature
(public, not OSM, not Beijing-specific). Verdict: partly OSM.

**Privacy argument.** Clean: one slot per user. D.4 never transmits a location; B.3 sends home
coordinates through PM, protected but the most identifying quantity at large ε; E.4's prefix mode
needs strictly disjoint groups.

**Scale.** n ≈ 91, ε = 2: about four questions of about 23 users each — class shares ±0.1, home
centre ±3–5 km, two departure means; ε = 1: two 3-class questions; ε = 0.5: commute distance only.
n ≈ 10,000: home-zone histograms, regional deterrence, chain types, complete-program archetypes
above about 5 % frequency at ε = 2. Degradation: fewer slots, public spreads and motif shares.

**Closest works named by the authors.** Activity-based models (Bowman and Ben-Akiva 2001; MATSim;
ActivitySim); IPF / Gibbs population synthesis (Beckman et al. 1996; Farooq et al. 2013);
central-DP activity diaries (Badu-Marfo, Farooq and Patterson 2020); OnTheMap central-DP commute
flows (Machanavajjhala et al. 2008); Berke et al. 2022 (central-DP stay trajectories); PEM (Wang et
al. 2018); Apple's sequence-fragment puzzle; Bayesian program learning. Authors' guess: not found
under LDP (B, D, E); E calls E.4 its most original idea.

**Effort / main risk.** M (B.3, E.4) to M–L (D.4). Risk: Geolife is not a commuter population, so
anchors are noisy or undefined; T-Drive taxis have no home–work anchors.

**Critique.** Its main asset — coherent synthetic users that match the user-level privacy unit — is
invisible to a benchmark that scores unlinked single trajectories, and its core assumption fits
neither Geolife (about 9 matched train trips per user, many of them not commutes) nor T-Drive
(taxi shifts): the strongest thesis story and the weakest benchmark bet.

### C5: Vote over a public trip library

**Provenance.** D.1 (public trip codebook, one-trip vote), C.3 (hierarchical vote distillation onto
a public trip library). A.4's pool raking (C8) is a related generation step.

**Mechanism.**
- *Local:* a library of 20,000–50,000 timed trips is generated from the map alone (gravity OD on
  road-length masses, shared router, public departure prior) and clustered by k-means on public
  descriptors (endpoints, log length, departure-hour cos / sin, duration) into K archetypes (D.1:
  K = 4 / 8 / 32 at ε = 1 / 2 / 4 for n = 182, fewer at n ≈ 91, 64–256 at n ≈ 10,000) or into a
  tree of branching 4–6 and depth ≤ 4 (C.3, ≤ 1,296 leaves). D.1: the device draws one own trip
  uniformly and maps it to the nearest centroid; C.3: it soft-assigns all its trips to leaves with
  a public kernel, averages them, and samples one node at a public random level.
- *Randomization:* GRR over K symbols (OLH when K > 3e^ε + 2), full ε; D.1 optionally lets a public
  second cohort send a speed factor by PM instead. Bound: finite public domain.
- *Server:* debias, clip negatives, zero cells below 2σ, renormalize, shrink toward the library's
  own archetype masses (D.1); per-level frequencies with top-down shrinkage of P(child | parent)
  (C.3); at large n later disjoint cohorts vote on refined libraries.
- *Generation:* sample an archetype or leaf; D.1 draws origin and destination from the archetype's
  Gaussian kernels, routes with the shared router and draws departure from a von Mises density
  around its daypart; C.3 re-routes one of the leaf's library trips over the same OD and jitters
  departure and speeds within the leaf's bands. `sequence_log_prob`: exact mixture (D.1) or the
  prior's log-probability plus a log mass ratio (C.3, coarse).

**Public prior.** The library: OSM graph, road-length masses, router at public parameters, public
departure prior — OSM plus configuration, available now; its coverage of Geolife-like trips depends
on how wide that prior is.

**Privacy argument.** Clean: one symbol per user; codebook frozen and hashed before data;
independent coins for every OUE bit (D.1's leak 4).

**Scale.** n ≈ 91, ε = 2: about 8 weights at ±0.06 against a mean weight of 0.125; ε = 1: 4
weights; C.3's level 1 (4–6 types) at ±0.15–0.18 (ε = 1) or ±0.08 (ε = 2). n ≈ 10,000: 64–256
archetypes, or about 36 tree nodes, deeper only under heavy nodes. Degradation: K is a public
function of (n, ε).

**Closest works named by the authors.** LDPTrace, RN-LDP-Synth v1, DP-Star, AdaTrace, DPT;
Federated Private Evolution / PrE-Text (Hou et al. 2024; user-level central DP, several rounds);
LDP hierarchical histograms (Cormode et al. 2019). Authors' guess: D "not published, but may read
as a quantization of known pieces"; C "arguably an LDP port of PrE-Text".

**Effort / main risk.** S–M (D.1) to M–L (C.3). Risk: with K ≤ 8 no archetype is as small as
Geolife's spatial concentration, so the spatial gain is nil; the library limits what can be
selected.

**Critique.** At n ≈ 91 it reweights four to eight coarse trip types, which can fix the length and
daypart mix but not geography or routes, and "each user votes for the nearest public sample" is
Private Evolution's core step with local instead of central noise, so its novelty is the thinnest
of the top half — a cheap, honest successor to v1 rather than a contribution.

### C6: Graph-spectral low-pass field

**Provenance.** E.1.

**Mechanism.**
- *Local:* the distribution of the user's matched edge endpoints over the about 35,800 nodes,
  projected on the first K eigenvectors of the normalized Laplacian of the undirected road graph
  (public, cached), each coefficient bounded by b_k = max_i |U_k(i)|; plus three departure-hour
  harmonics (6 values), mean capped length and a speed ratio: d = K + 8 (K ≈ 8 at n ≈ 91, about
  200 at n ≈ 10,000).
- *Randomization:* a public slot draw (weights may favour low modes); rescale to [−1, 1]; PM with
  the full ε. Bound: b_k computed from the public eigenvectors.
- *Server:* unbiased slot means; shrinkage ĉ_k ← ĉ_k·max(0, 1 − σ_k²/ĉ_k²) with σ_k² known from the
  mechanism, so modes below the noise vanish; density f = Σ ĉ_k U_k, clipped and renormalized; the
  same for the 24-hour density; gravity scale from the mean length.
- *Generation:* origin from f; destination ∝ f(j)·exp(−d_sp(O, j)/λ̂); shared router with length
  cost; departure from the harmonic density; edge time = length / (ρ̂·maxspeed) + public turn delay.
  `sequence_log_prob` = log f(O) + log P(D given O) + route term.

**Public prior.** Laplacian eigenvectors of the OSM graph (computable, cached by map hash): OSM
alone; fallback 2-D cosine modes on node coordinates.

**Privacy argument.** Clean.

**Scale.** n ≈ 91, ε = 2: per-coordinate standard deviation about 0.34 of the half-range at d = 16
(E's 0.24 is for n = 182), so roughly 2–6 low modes, one harmonic and one speed scalar; ε = 1: the
first mode only. n ≈ 10,000: a few dozen modes. Degradation: automatic, through shrinkage over a
nested basis.

**Closest works named by the author.** Graph signal processing (Shuman et al. 2013); central-DP
wavelet and Fourier histograms; grid histograms in LDPTrace and RetraSyn. Author's guess: the
parametrization is new, the primitive is not.

**Effort / main risk.** M. Risk: it says only where trips are; routes are generic.

**Critique.** Low Laplacian eigenvectors of large real road graphs tend to concentrate on weakly
connected fringes (dead-end clusters, bridges), which would make b_k large and the first modes
useless at city scale — check this on the Beijing graph before anything else; the 2-D cosine
fallback turns the idea into a cosine-basis LDP histogram, which is known. If the modes are
city-scale, it is a good spatial slot family for C1, competing with C2.

### C7: One-bit likelihood-gain regression over prior knobs

**Provenance.** C.4.

**Mechanism.**
- *Local:* a public draw gives the user a setting θ_u of k knobs of the public prior model (speed
  multiplier, peak hour, length scale, weight on major roads; k ≈ 2 at n ≈ 91); the device computes
  the per-edge average log-likelihood gain of its trips under the prior at θ_u over the prior at
  θ₀, clipped to [−c, c]: one scalar for any map.
- *Randomization:* Duchi's one-bit mechanism (PM at larger ε), full ε. Bound: public clip c.
- *Server:* debiased reports observe L(θ_u) − L(θ₀); Bayesian least squares fits a quadratic surface
  (2k coefficients, diagonal curvature); θ̂ is its maximizer, with a Gaussian (Laplace) posterior;
  later disjoint cohorts get settings near θ̂.
- *Generation:* the prior model at θ̂ (or a few posterior draws): knob-shaped departure profile,
  fitted length scale, road-valid link-logit route, speeds scaled by the multiplier with AR(1)
  noise; `sequence_log_prob` is exact under that model.

**Public prior.** The prior model on the OSM graph, with Dijkstra fields cached on a public knob
grid; the diurnal profile shape from configuration or literature. Verdict: OSM plus configuration.

**Privacy argument.** Clean.

**Scale.** n ≈ 91: one knob (ε = 1) or two (ε = 2); n ≈ 5,000: 6–8 knobs with full curvature at
ε ≥ 2. Degradation: fewer knobs.

**Closest works named by the author.** POPri (Hou et al. 2025; federated, aggregate DP, iterative);
DPZero-style zeroth-order methods (central); Zheng et al. 2017. Author's guess: no LDP analogue
found; "the most novel" idea of lens C.

**Effort / main risk.** M. Risk: user cost grows with the number of surface coefficients; a small c
turns reports into signs (a median-type optimum, wrong for mixture-share knobs), a large c adds
noise.

**Critique.** For knobs that are exponential-family parameters, C1's moment matching uses the same
users far more efficiently, so this pays only for knobs that enter non-linearly (major-road weight,
peak hour); at n ≈ 91 it estimates one or two numbers from noisy one-bit observations of a surface
of unknown curvature, so θ̂ will often land on the edge of the design.

### C8: Adaptive road-corridor sieve with key–value reports

**Provenance.** A.4.

**Mechanism.**
- *Local:* a public road hierarchy — level 1: 3×3 macro-zones × 3 class groups (27 nodes); level 2:
  named arterial corridors plus one local-roads node per zone (a few hundred); level 3: pieces of
  about 1 km. The device picks one own trip and one point on it uniformly by length; key = the
  active hierarchy node containing it (else "elsewhere"), value = its log speed ratio rounded to
  ±1; a public 20 % of users send a departure hour instead.
- *Randomization:* PCKV for the (key, value) pair; circular square-wave mechanism for the hour; one
  report per user. Bound: finite key domain, binary value.
- *Server:* users are split into batches by a public random permutation; batch b expands the
  children of nodes above 3σ in batch b − 1; then tree-consistent constrained least squares,
  non-negativity, parent-shrunk speeds, and an EM-smoothed departure density.
- *Generation:* a cached pool of about 10⁵ public candidate trips (gravity OD, randomized fastest
  paths: road-valid) is raked by IPF to the resolved shares and resampled; departure from the
  square-wave density; per-edge times from node speeds.

**Public prior.** Hierarchy and pool from OSM; level-2 corridors need OSM name/ref tags, which are
not in the current edge table (re-extract). Verdict: OSM alone, with that extraction.

**Privacy argument.** Clean in principle, needs care in implementation: PCKV's internal split
between key and value budgets, and batches that are disjoint and fixed before they report.

**Scale.** n ≈ 91: a single batch; level-1 standard deviation about 0.094 at ε = 2 against shares of
about 0.04, so 2–3 nodes resolve; ε = 8: corridors above about 1 %. n ≈ 5,000: corridors above
about 5 % (ε = 2) or 2 % (ε = 4). Degradation: unresolved nodes keep the prior split.

**Closest works named by the author.** PEM, TreeHist, AHEAD (Du et al. 2021), PCKV; central-DP
PMW^Pub; PrivTrace's adaptive grid. Author's guess: new road-class/corridor hierarchy, joint
location and speed at one resolution, pool raking.

**Effort / main risk.** M–L. Risk: shares fix where traffic is, not OD coupling or route continuity;
the pool may lack the demanded routes.

**Critique.** At n ≈ 91 there is one batch, so the adaptive descent that defines the idea never runs
and what remains is a 27-cell key–value histogram; raking a public pool to marginal volume shares
cannot restore OD pairs or routes, so this is a T-Drive-only arm.

### C9: Manoeuvre × road-class token n-grams

**Provenance.** E.2.

**Mechanism.**
- *Local:* every move gets a public "part of speech": the manoeuvre from the bearing change
  (straight, slight, left, right, U-turn) × the class group of the entered edge (5), plus begin and
  end tokens: 27 tokens. The user holds a token-bigram distribution (27² pairs), departure-period
  shares (24), origin-zone shares (144) and per-class speed ratios; at n ≈ 91 the alphabet shrinks
  to the class unigram (5), the manoeuvre unigram (3), an end hazard, one speed ratio and four
  periods.
- *Randomization:* public slot draw (0.4 / 0.3 / 0.2 / 0.1); one sampled move's token pair by OUE
  (GRR on the reduced alphabet), one sampled trip's origin or period by OUE / GRR, speed by PM;
  full ε. Bound: one item from a finite domain.
- *Server:* debias, clip, renormalize; back-off smoothing toward the public "graph language" (the
  token bigram of a uniform random walk on the graph); keep the tilt r(tag′ given tag) = estimated
  over prior.
- *Generation:* origin edge from the origin histogram (public density at small n); at each node,
  tag the out-edges and draw one ∝ r(tag′ given previous tag) × an optional pull toward a
  gravity-drawn destination; stop by the end hazard; departure from the period histogram; edge
  time = length / (ρ̂_class·maxspeed) + public manoeuvre delay.

**Public prior.** Bearings from OSM node coordinates, classes and the random-walk bigram: OSM alone;
manoeuvre delays from literature constants.

**Privacy argument.** Clean.

**Scale.** n ≈ 91: about 14 numbers over four slots, GRR-5 standard deviation about 0.11 at ε = 2
(E's 0.08 assumes n = 182). n ≈ 10,000: the frequent bigram pairs (OUE about 0.03), 144-zone
origins, 24 periods, five class speeds. Degradation: unigrams and the public random-walk back-off.

**Closest works named by the author.** Cunningham et al. (spatial n-grams with reachability
pruning); TrajLDP direction perturbation; road-type transition priors in map-matching hidden Markov
models; driver identification from manoeuvres. Author's guess: the alphabet is new; "a non-private
road-class Markov generator may exist".

**Effort / main risk.** S–M. Risk: without the pull, walks wander and lengths are unrealistic; with
it, the n-gram adds little beyond the router.

**Critique.** At n ≈ 91 it estimates the same few class and turn shares that C1 already collects,
with a weaker generator; it becomes distinct only at T-Drive scale, where its novelty over
Cunningham et al. rests on the alphabet alone — best used as C1's route-style module, as its
author suggests.

### C10: Conservation-consistent zone-flow oracle

**Provenance.** A.2.

**Mechanism.**
- *Local:* at public levels (3×3, 6×6, 12×12 zones; arcs between road-connected zones) each trip is
  a unit flow (start with hour bin and origin, every zone crossing, end), long trips scaled to K
  units; the user averages these and adds a time channel (summed log travel-time ratios per arc).
  Dimension 69 at 3×3, about 2,000 at 12×12.
- *Randomization:* a public draw assigns level and channel; the average, clipped to ℓ₂ radius √K,
  goes through Duchi's ℓ₂-ball mechanism (better than padding-and-sampling below ε ≈ 4); variant:
  send the residual against the fastest-path flow. Bound: public ℓ₂ radius.
- *Server:* weighted least squares across levels, shrunk to the map-only flow, under
  non-negativity, flow conservation at every zone, road-connected support and cross-level sums
  (Dykstra alternating projections).
- *Generation:* start ∝ start flows; step z → z′ with probability f(z → z′) / outflow(z) or stop, so
  expected arc visits equal the projected flows and trip length needs no separate model; public
  fastest paths join the zone crossings; per-edge times from the time channel.

**Public prior.** Zone adjacency and map-only flows from OSM: available.

**Privacy argument.** Clean in principle, needs care: exact sphere sampling in Duchi's
multidimensional mechanism, public radius and scaling rule.

**Scale.** n ≈ 91: 3×3 per-arc standard deviation about 0.4 at ε = 2, 0.13 at ε = 4, 0.012 at ε = 8,
for flows of 0.1–0.5. n ≈ 5,000: 3×3 at 0.06–0.09 (ε = 1–2), 6×6 marginal. Degradation: users go to
the finest level whose noise is below the prior's spread.

**Closest works named by the author.** LDPTrace and RN-LDP-Synth v1 (one length-normalized
transition, separate length model); CDP-DTP (2025; flow consistency under central DP). Author's
guess: new user-level flows, ℓ₂ multiset oracle, conservation-exact walk.

**Effort / main risk.** M. Risk: a first-order zone walk ignores OD coupling (wandering trips); it is
the prior unless ε = 8.

**Critique.** It is the v1 / LDPTrace zone-transition design made user-level, and its own numbers
(per-arc 0.4 at ε = 2) confirm the briefing's verdict on transition matrices at this scale: at
every Geolife rung it is the public prior, so it is at most a T-Drive arm.

## 3. Summary table

"n needed" gives what the 182 rung (n ≈ 91 train users) buys at ε = 2, then what a large
population buys. "Novelty guess" gives the authors' guess, then mine. The last column answers
whether the public prior can be built for Beijing from OSM alone.

| Candidate | Privacy argument | n needed (n ≈ 91 → large n) | Effort | Novelty guess (authors / mine) | Promise 1–5 | Prior from OSM alone? |
|---|---|---|---|---|---|---|
| C1 Behavioural-moment router | clean | 3–5 numbers → 25–100 at 5k | M | not found / high risk: obvious, five-way convergence | 4 | yes (minimal); B.1 adds literature coefficients |
| C2 Gravity-regularized OD inversion | clean | 2–4 OD parameters → 36–144 zones at 5–10k | S–M | moderate / thin: LDP OD is published | 3 | yes; cordons need a name/ref re-extraction |
| C3 Label vote over a behaviour catalogue | clean | 2–8 shares → 24–48 classes at 5–10k | S–M | new / moderate | 3 | no: catalogue from cited behavioural constants |
| C4 Activity anchors and schedules | clean (E.4 prefix mode: care) | 4 slot marginals → program archetypes at 10k | M–L | new / plausible, highest of the set | 3 | partly: road proxies yes, land use is a new extraction, motifs from literature |
| C5 Vote over a public trip library | clean | 4–8 weights → 64–256 at 10k | S–M (D.1), M–L (C.3) | thin / thin: Private Evolution step with local noise | 2 | yes |
| C6 Graph-spectral field | clean | 2–6 modes → dozens at 10k | M | new parametrization / plausible if modes are city-scale | 2 | yes |
| C7 Likelihood-gain regression | clean | 1–2 knobs → 6–8 at 5k | M | none found / plausible | 2 | yes, plus configuration |
| C8 Adaptive corridor sieve | needs care (PCKV, batches) | 2–3 cells → corridors above 2–5 % at 5k | M–L | new / moderate | 2 | yes, with a name/ref re-extraction |
| C9 Token n-grams | clean | unigrams only → bigrams at 10k | S–M | new alphabet / thin | 1 | yes |
| C10 Zone-flow oracle | needs care (ℓ₂ mechanism) | nothing at Geolife scale → 3×3 zones at 5k | M | new / thin: v1 made user-level | 1 | yes |

**Main warning for the evaluator.** At the benchmark's real scale (about 91 train users at the 182
rung and 10 at the 20 rung, while authors B and E computed with 180) every candidate releases
little more than its OpenStreetMap-only prior and every membership attack will sit at chance, so
rank candidates by novelty, proof cleanliness and measured gain over a "public prior only" arm on
time-aware metrics that still have to be built, not by attack numbers or the authors' error bars.
