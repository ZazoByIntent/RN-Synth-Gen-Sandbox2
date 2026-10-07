# Brainstorm D: privacy adversary / red-team lens

Four mechanism ideas for user-level pure local differential privacy (LDP: every user
randomizes on the device, the server is untrusted), designed backwards from the attacks in
`.brainstorm/00_briefing.md`. Section 0 holds the attack analysis, the budget arithmetic and
the protocol invariants that every idea relies on; each idea ends with a "subtle leaks" list
naming where a careless implementation would break the user-level guarantee. Sources read:
only `01_task.md` and `00_briefing.md`; the existing `rn_ldp_synth` code was not opened.

## 0. Attack analysis and shared constraints

### 0.1 What the membership attack exploits, and what it cannot see

The benchmark's membership inference is a likelihood-ratio attack (LiRA-lite). It calls
`fit` on shadow training sets that do or do not contain the candidate trajectory and
compares the candidate's `sequence_log_prob(edge_seq)` across the two groups. It wins
exactly when a fitted model assigns a sequence systematically higher probability because
that sequence, or its user's other sequences, were in the training set. In the non-private
`markov` ceiling the candidate's own transitions are literally in the count tables.

Under user-level ε-LDP the fitted model is a post-processing of n randomized reports, each a
function of one user's complete data. Replacing one user's whole data changes the
distribution of the fitted model by at most a factor e^ε, so any membership test obeys
TPR ≤ e^ε · FPR. At FPR 0.01 this gives 0.017 (ε 0.5), 0.027 (ε 1), 0.074 (ε 2), 0.55 (ε 4)
and nothing at ε 8. Two consequences. (a) The proposed pass mark "TPR ≤ 0.02 at FPR 0.01" is
guaranteed by the proof only for ε ≤ ln 2 ≈ 0.69; above that it is an empirical finding.
(b) The empirical attack will sit at chance for every idea below, because one report among n
moves a debiased average by about 1/n; that proves little (the briefing says the same about
RN-LDP-Synth v1). The informative checks are therefore: (i) an audit of the local
randomizer itself — draw 10^6 outputs for two different inputs; the largest log-ratio of
output frequencies must not exceed ε, because the whole guarantee lives in that one
function; (ii) a canary — fit once with and once without one synthetic user whose report is
extreme and unique, and measure the shift in `sequence_log_prob` of that user's trajectories;
(iii) a structural test that `sequence_log_prob` is a pure function of a small serialized
parameter vector θ and the public map, and that `fit` keeps no reference to `train`.

Blind spots of the attack that a mechanism must not exploit, and that the benchmark should
close once generators emit timestamps: candidates are edge sequences only, so time is
invisible — a timestamped generator could memorise departure times unpunished; extend the
score to `(edge_seq, times)`. `generate` is never called, so a generator could score with a
public model and sample from a private one; add a consistency test (mean log-prob of its own
samples versus held-out trajectories). The attack sees no metadata at all (0.2).

The reidentification attack is not run on synthetic data because synthetic trajectories
carry no user id. The adversary's analogue is distance-to-closest-record: given k points of a
target, is any synthetic trajectory unusually close to it? Under user-level LDP the
probability of emitting a trajectory within δ of the target's route is at most e^ε times its
value without the target, so this test has no more power than the bound above. Structurally,
all four ideas compute routes by public routing from sampled endpoints and never copy a
reported route, so near-duplicates arise only for routes that are typical anyway.

### 0.2 Metadata that leaks even when the main statistics are randomized

Each line: leak → structural fix. Every idea below assumes these fixes.

1. Number of trajectories per user. One report per trajectory (LDPTrace style) reveals the
   count exactly and costs m·ε. Fix: exactly one report per user per collection window, a
   function of all the user's data.
2. Participation. If only users with data report, "has trajectories in Beijing this month"
   is public. Fix: every enrolled device reports; "no data" is mapped to a public null input
   that is randomized like any other input (for a categorical question a draw from the public
   prior, for a numeric question the public prior mean).
3. Collection span and submission timing. A report sent right after a trip, or one carrying
   first/last timestamps, dates the user. Fix: submission at a public fixed time at the end of
   the window; no absolute timestamps in the report, only within-day phases or classes.
4. Report size. Variable-length encodings leak content length. Fix: fixed-size encoding.
5. Hyperparameters chosen from the user's own data: grid size, clipping range, which question
   to answer, which model to vote for, a number of clusters picked by an elbow. Every such
   choice is either public (map, n, ε) or is itself the randomized value. Trajectory order and
   the user id must not seed any coin.
6. Deterministic "randomness". Seeding the randomized-response coin from a hash of the
   private value, to make reports reproducible, makes the mechanism a deterministic function
   of the data: ε = ∞. Coins come from the OS cryptographic generator; in the benchmark
   simulation from the seeded `np.random.Generator`, never from the data.
7. Per-user mechanism parameters. If the server can hand one user a different ε, codebook or
   question, it can isolate that user. Fix: one signed public configuration with a hash the
   device verifies and echoes in its report.
8. Longitudinal linkage. The task treats each window's submission as a new privacy unit; the
   realistic adversary links reports of the same device across T windows and holds T·ε
   against the same person. Fix: no stable device identifier in reports, and state the T·ε
   composition in the write-up.
9. Floating-point mechanisms. Laplace and piecewise mechanisms on floats admit the known
   Mironov-style attacks. Prefer discrete primitives; if a numeric mechanism is used, snap its
   output to a public grid.
10. Server-side shortcuts. The harness passes `train` to `fit`, so "fine-tune on the raw
    training set", "keep the training edge set as the support" or "fall back to training edge
    frequencies for unseen sequences" are one line away. The invariant "θ is small and public,
    `sequence_log_prob` reads only θ and the map", pinned by a test, is the defence.

### 0.3 Budget arithmetic at n = 182: what one report per user buys

Standard deviation of an estimated fraction of users, mechanism noise only, full budget ε on
one report per user, n = 182 (the population's own sampling noise, about 0.037 for a fraction
near 0.5, comes on top):

| primitive | ε = 0.5 | ε = 1 | ε = 2 | ε = 4 | ε = 8 |
|---|---|---|---|---|---|
| binary randomized response | 0.15 | 0.080 | 0.049 | 0.038 | 0.037 |
| GRR, K = 4 categories | 0.22 | 0.094 | 0.036 | 0.010 | 0.001 |
| GRR, K = 8 | 0.32 | 0.13 | 0.042 | 0.011 | 0.001 |
| GRR, K = 16 | 0.45 | 0.18 | 0.054 | 0.012 | 0.001 |
| OUE / OLH, any K | 0.29 | 0.14 | 0.063 | 0.020 | 0.003 |
| piecewise mechanism, mean of one value in [−1, 1] | 0.34 | 0.17 | 0.082 | 0.036 | 0.012 |

GRR is generalized randomized response (report the true category with probability
e^ε/(e^ε+K−1), otherwise a uniformly chosen other one). OUE / OLH are optimized unary
encoding / optimized local hashing (Wang et al., USENIX Security 2017), better than GRR once
K > 3e^ε + 2. The piecewise mechanism (Wang et al., ICDE 2019) handles bounded numbers;
reporting one of d coordinates chosen at random multiplies its standard deviation by √d.
At n = 10,000 every entry shrinks by a factor 7.4. Note that n inside `fit` is the number of
train users: about 91 at the 182-user rung, 25 at 50 and 10 at 20, so multiply the table by
1.4, 2.7 and 4.3 respectively; at the 20-user rung nothing private is estimable and every
mechanism below collapses to its public prior, which is the honest result.

Reading: at ε = 0.5 one binary question is the whole budget; at ε = 1 four categories; at
ε = 2 about eight; at ε = 4 a few dozen; ε = 8 estimates hundreds of categories but
e^8 ≈ 3,000 makes the guarantee nominal. Hence at n ≈ 180 the *spatial* distribution of trips
(hundreds of cells, thousands of origin–destination pairs) must come from public priors —
road graph, OpenStreetMap road classes, a gravity model — and the private bits buy a handful
of scalars: trip-length scale, departure-time phase, speed factor, at most a 4–8-way spatial
tilt. All four ideas are built so that this is their natural low-budget mode and so that they
grow in dimension with n·ε² without changing the proof.

Two evaluation notes. User-level mechanisms estimate user-weighted distributions (a user
with 300 trips counts once) while the benchmark's raw references are trajectory-weighted;
compare against a user-weighted raw reference or reweight publicly. The existing mechanisms
report per-trajectory ε; a user with 95 trajectories under per-trajectory ε = 0.5 has
user-level ε ≈ 47, so comparison plots should carry user-level ε on the axis.

### 0.4 Protocol invariants and the shared public component

Invariants: exactly one fixed-size report per enrolled device per window, sent at a public
time; null users report; each device is assigned to at most one question or cohort by a
data-independent draw; grids, codebooks, clipping ranges, model zoos and budget splits derive
from the public map, n and ε and carry a hash; coins come from the OS generator; the server
discards raw reports after aggregation (defence in depth, not needed for ε); the fitted model
is a public parameter vector θ of a few dozen numbers; `sequence_log_prob` and `generate` read
only θ and the map and are consistent with each other.

Shared public component, used by Ideas 1, 2 and 4 and inside Idea 3's zoo: a
*destination-directed Boltzmann router*. Given origin and destination nodes it walks the road
graph edge by edge; at each node the next edge e′ is drawn with probability proportional to
exp(−β·c(e′) − θ·d(e′, dest)), where c is a public cost from length and OpenStreetMap class and
d(·, dest) is the shortest-path distance to the destination (one reverse Dijkstra per
destination, cached; networkx needs about 0.4 s per destination on 36k nodes, scipy's
`csgraph` about 40 ms — a one-line dependency justification). The walk stops at the
destination; a public step cap falls back to the shortest path. Every connected edge
sequence has a finite log-probability under it, which is what `sequence_log_prob` needs, and
routes are road-valid by construction. Per-segment times: free-flow speed from `maxspeed` or
a class default, times a per-trip speed factor and a public per-segment log-normal jitter,
plus a public turn delay by junction class. Departure time: a density on the 24-hour circle.
The ideas differ in which few parameters of this machinery are private and how they are
estimated.

## Idea 1: Public trip codebook, one-trip vote

- **One-sentence pitch:** The map alone defines a codebook of K road-valid "trip archetypes"
  (origin region × destination region × length class × daypart); each user reports the
  archetype of one randomly chosen own trip through randomized response, and the server
  reweights the public codebook.
- **What each user computes locally:** Draw one trip uniformly from all own trips in the
  window. Compute its public descriptor (origin x, y; destination x, y; log length; cos and
  sin of local departure time) and assign it to the nearest of K public centroids obtained
  by k-means on a public library of about 50,000 trips sampled from the map with a gravity
  origin–destination prior and the shared router (public seed). Private value: one integer in
  {1, …, K}. K is a public function of n and ε: 4 at (182, 1), 8 at (182, 2), 32 at
  (182, 4), 64 at (10,000, 2); beyond that a two-level codebook whose children are asked of
  later cohorts. Users without trips draw the integer from the library's own archetype
  frequencies.
- **What is randomized and how:** GRR over K symbols with the full ε (OLH once
  K > 3e^ε + 2). One report per user, fixed size. An optional second cohort — a
  data-independent split of users, each user still spends ε exactly once — answers a numeric
  speed-factor question through the piecewise mechanism; otherwise the speed factor is a
  public default.
- **What the server does:** Debias the K-histogram, clip negatives, zero cells below
  2σ(n, ε, K), renormalize, shrink toward the library's archetype frequencies with the public
  weight σ²/(σ² + 1/K²). θ = the K weights (plus one speed factor).
- **How a synthetic trajectory is generated:** Sample archetype k from θ; sample origin and
  destination from archetype k's public kernels (Gaussian around the cluster's endpoints,
  snapped to the nearest non-motorway node); route with the shared router; departure time
  from a von Mises density around the cluster's daypart centroid; per-segment times as in 0.4.
  `sequence_log_prob(seq)` = log Σ_k θ_k p_k(origin) p_k(destination) p_route(seq | origin,
  destination), finite for every sequence because the kernels have full support.
- **Why it is user-level pure LDP:** The private value is one symbol derived from the user's
  whole data; GRR is ε-LDP on that symbol domain, so two users with arbitrarily different data
  and trip counts have report distributions within e^ε (a mixture of e^ε-close distributions
  is e^ε-close). Easy part: one report, one primitive, no composition. Subtle part: codebook,
  K and the selection rule must be fixed before any data is seen, and the window is the unit.
- **Expected behaviour at n ≈ 180 vs 10,000:** At 182 and ε = 2, eight weights with standard
  deviation about 0.04 against a mean weight of 0.125: the coarse length / daypart / quadrant
  mix is learned; within-archetype geography is the public prior, so cell JSD barely improves
  over the prior while length and duration errors should fall clearly. At ε = 1, K = 4; at
  ε = 0.5, K = 2. At 10,000: K = 64–256, two-level codebooks, speed and daypart as extra
  cohorts.
- **Closest existing work and what differs:** LDPTrace and RN-LDP-Synth v1 quantize per
  trajectory to grid cells or zones and estimate transition tables; DP-Star and AdaTrace
  (central) use trip representatives and length distributions; DPT uses hierarchical
  reference systems. Here the quantization unit is the whole timed trip, the codebook comes
  from the map only, one symbol per user, and K is sized by (n, ε). I know of no published
  "public trip codebook + user-level frequency oracle"; the risk is that reviewers read it as
  a quantization of known pieces.
- **Implementation effort:** S–M. Library sampler and k-means codebook (public, cached by map
  hash), GRR/OLH with debiasing, shared router, mixture `sequence_log_prob`.
- **Main risk / failure mode:** Geolife's mass sits in a few square kilometres; with K ≤ 8 no
  archetype is that small, so the spatial gain over the public prior at n = 182 is nil, and the
  user-weighted mix differs from the trajectory-weighted raw reference.
- **Subtle leaks:** (1) Building the library or codebook from training endpoints puts the
  training support into the model; library from the map only, public seed, hash. (2) Choosing
  K by an elbow on the data; K comes from (n, ε). (3) Replacing "random trip" by "most frequent
  trip" is still ε-LDP, but choosing the rule after looking at the data is not. (4) OUE/OLH bit
  vectors need independent coins per bit; a vectorized implementation that reuses one draw per
  user correlates the bits and voids the proof. (5) Refining an archetype's endpoint kernel on
  the training trips assigned to it. (6) Letting users without trips skip the report instead
  of drawing from the public prior, which makes participation reveal activity.

## Idea 2: Behavioural moments and a moment-tilted router

- **One-sentence pitch:** Users never report where they go; each reports one clipped
  coordinate of a small vector describing *how* they travel (trip-length scale, detour,
  road-class shares, turn rate, speed factor, departure-time phase), and the server fits a
  maximum-entropy road-network generator — public origin–destination prior, Boltzmann router,
  circular time density — whose expected features match the estimated means.
- **What each user computes locally:** For each own map-matched trip: length in km (clipped
  to [0.5, 20]); detour ratio = route length / shortest-path length ([1, 2]); share of distance
  on motorway/trunk/primary ([0, 1]); share on residential/tertiary ([0, 1]); turns per km
  ([0, 5]); speed factor = mean speed / public free-flow speed of the route ([0.1, 1.5]); cos
  and sin of 2π·(local departure hour / 24). Average over own trips and rescale each coordinate
  to [−1, 1]: x ∈ [−1, 1]^d with d = 8 (d = 3 at small ε·√n; 20–40 at n = 10,000 with per-class
  speed factors, a second time harmonic, per-quadrant length means). Users without trips use
  the public prior mean.
- **What is randomized and how:** Choose a coordinate j uniformly and independently of the
  data; report d·PM(x_j) with the piecewise mechanism at the full ε (the multi-dimensional
  variant of Wang et al. 2019). One number per user, one message, no budget split.
- **What the server does:** Debias to μ̂ ∈ R^d, clip to the box, shrink toward the public prior
  mean with the public weight σ²_noise/(σ²_noise + σ²_prior). Fit by the generalized method
  of moments: the distance decay of the gravity prior from the length mean; router parameters
  (β per road class, θ) from detour, class shares and turn rate, using a *public* precomputed
  response surface E[features | β] simulated once per map and cached by map hash; von Mises
  mean and concentration from the circular moments; the speed-factor mean. θ holds about d
  numbers.
- **How a synthetic trajectory is generated:** Origin from the public density (residential
  road length per cell), destination from the fitted gravity kernel, route from the fitted
  router, departure time from the fitted von Mises density, per-segment times from free-flow
  speed times a log-normal speed factor around the fitted mean, plus public turn delays.
  `sequence_log_prob` is the exact sequential likelihood of the router (finite for any
  connected sequence; a public gap penalty otherwise).
- **Why it is user-level pure LDP:** The report is one piecewise-mechanism output of one
  coordinate of a vector in a public box; the mechanism is ε-LDP on that box, so two users
  with arbitrarily different data and trip counts have e^ε-close report distributions. Easy
  part: one standard primitive, no composition. Subtle part: box, d and the coordinate draw
  must not depend on the data; the free-flow reference must be public; moment matching is
  post-processing but must not peek at `train` to choose between fits.
- **Expected behaviour at n ≈ 180 vs 10,000:** At 182, ε = 2, d = 8: each mean has standard
  deviation about 0.23 on [−1, 1], i.e. ±2.2 km on mean trip length, ±0.16 on the speed
  factor, about ±20° on the departure phase before shrinkage. That moves the length, duration
  and speed distributions toward Geolife's and sets the daytime departure peak; geography
  stays the public prior. At ε ≤ 1 use d = 3 (length, speed factor, one time harmonic). At
  10,000 and ε = 2: d = 32 with standard deviation about 0.06, enough for per-class speeds by
  daypart, a bimodal time density and quadrant-level length tilts.
- **Closest existing work and what differs:** Recursive-logit route choice (Fosgerau,
  Frejinger, Karlström 2013) and logit traffic assignment are public, non-private estimators;
  LDP mean estimation (Duchi et al.; Wang et al. 2019; Harmony) is generic; central-DP
  synthesis from marginals (PrivBayes, MWEM, PGM) estimates tables, not moments of routes;
  AdaTrace and DP-Star estimate grids centrally. The combination solves what neither piece
  solves: at n ≈ 180 the only estimable private statistics are a few means, and a
  maximum-entropy router turns exactly those into a complete road-valid, timed generator with
  a proper likelihood. Central-DP estimation of discrete-choice parameters probably exists;
  the local, user-level, synthesis-oriented version I have not seen.
- **Implementation effort:** M. Feature extraction, piecewise mechanism, response-surface
  precomputation, router with cached reverse Dijkstra, von Mises time model, moment fit.
- **Main risk / failure mode:** Misspecification — one gravity prior and one router cannot
  express Geolife's campus-centred geography, so cell JSD may not beat the public prior; the
  response surface may be flat in some β directions (weak identification), which shrinkage
  masks but does not fix.
- **Subtle leaks:** (1) Picking the coordinate that "is most informative for me" instead of
  uniformly. (2) Clipping to the user's own range, or using the user's own top speed as the
  free-flow reference. (3) Letting ε or the box differ between users; the piecewise output
  range reveals ε. (4) Choosing between the fitted model and a public default by held-out
  likelihood on `train`. (5) Storing candidate sequences in the Dijkstra cache and reusing
  them anywhere in scoring. (6) Skipping users without trips instead of sending the prior mean.

## Idea 3: An electorate over a public generator zoo

- **One-sentence pitch:** The server publishes a factored zoo of complete road-valid timed
  generators built from the map alone; each user reports one randomized bit (or one of three
  levels) saying which zoo member fits their own trips better, and the fraction of users
  becomes the mixture weight — the data-dependent choice of model structure, which usually
  leaks silently, is made the only private value.
- **What each user computes locally:** The zoo is a product grid, e.g. origin–destination
  prior {road-density gravity, centre-biased gravity, uniform} × length scale {2, 5, 10 km} ×
  router temperature {greedy, mild, strong} × departure profile {flat, daytime peak, bimodal
  commute} × speed factor {0.4, 0.6, 0.8}: 243 public models, each with a likelihood the
  device evaluates with the public map (router term, circular density, log-normal speed). The
  device is assigned by a data-independent draw to one factor (or one duel A versus B); it
  computes the per-trip average log-likelihood of its own trips under each level of that
  factor, using only the likelihood terms that factor affects, and takes the argmax (or the
  sign of the difference). Private value: one symbol in {1, 2, 3} or one bit.
- **What is randomized and how:** Binary randomized response for duels, GRR with K = 3 for
  factor votes, full ε, one report. Users without trips send a uniform draw.
- **What the server does:** Debias per factor, clip, normalize, shrink toward uniform with the
  public noise weight; the product of per-factor weights is a mixture over the zoo
  (mean-field). Across windows each new cohort votes on the factor with the largest remaining
  uncertainty or duels the incumbent against a public challenger: coordinate ascent over
  months, which is the incremental update the task allows. θ = per-factor weight vectors.
- **How a synthetic trajectory is generated:** Draw a level per factor from θ, then a trip
  from that zoo member (origin, destination, route via the shared router at that temperature,
  departure from that profile, per-segment times from that speed factor). `sequence_log_prob`
  = log of the mixture over the 27 combinations that affect edge sequences (origin–destination
  prior × length × router), sharing one Dijkstra per destination; time factors enter once the
  score takes timestamps.
- **Why it is user-level pure LDP:** One bit or one 3-way symbol per user, computed from all
  their trips, randomized with a standard primitive: the cleanest proof of the four. Subtle:
  the factor assignment must be data-independent; the zoo is frozen and hashed before the
  campaign; a reported *margin* instead of a sign would need public clipping; the same device
  must not be re-queried in the next window without charging T·ε.
- **Expected behaviour at n ≈ 180 vs 10,000:** At 182 and ε = 1 one duel per window (standard
  deviation 0.08) separates preferences above about 0.65 from indifference; at ε = 2 one
  3-way vote per window (0.034) resolves one factor, so five windows give one coordinate pass.
  Utility is bounded by the zoo: better length, duration and speed distributions and a correct
  daytime peak, geography at the level of the best public prior. At 10,000: all five factors in
  one window (2,000 users each, standard deviation 0.010), 5–7 levels per factor, finer zoos
  (quadrant-specific gravity priors) in later windows.
- **Closest existing work and what differs:** PATE-style noisy voting and
  exponential-mechanism model selection are central DP; Papernot and Steinke's private
  hyperparameter tuning is central; "Differentially Private Model Merging" (arXiv 2604.20985)
  certifies parameter mixtures centrally; DP-FedAvg trains parameters. A local, user-level
  electorate over public road-network generators with "fraction of users = mixture weight"
  and adaptive factor scheduling I have not seen. It is also the natural *null baseline*: any
  richer user-level mechanism must beat "public prior + one bit per user" or it adds nothing.
- **Implementation effort:** S. Zoo factory over the shared router and time models,
  device-side likelihood, binary RR / GRR, mixture scoring.
- **Main risk / failure mode:** If no zoo member is close to the data the votes pick the least
  bad one and the output is a lumpy mixture of a few prototypes; the adaptive story holds only
  under the new-user-per-window reading, which a realistic adversary rejects.
- **Subtle leaks:** (1) Adding a zoo member "that looks like the training set" after `fit`
  sees the data — the obvious cheat; freeze and hash the zoo. (2) Assigning factors or duels by
  how informative the user's data is. (3) Reporting an unclipped likelihood margin. (4)
  Re-querying the same device next window under a stable identifier. (5) Adding a "do you have
  any data" question to debias the null fraction without charging it. (6) Choosing the
  challenger from inspection of raw trajectories rather than from earlier cohorts' debiased
  estimates.

## Idea 4: Relations, not places — activity anchors from public land use

- **One-sentence pitch:** Synthesize a population of users who commute between a home and a
  work anchor drawn from public land-use proxies, where the only private inputs are
  *relations* (home–work road-distance class, commute daypart, chain type) estimated with one
  randomized answer per user — the mechanism cannot reveal home or work locations because it
  never transmits any location.
- **What each user computes locally:** Stay detection on own raw GPS with public parameters
  (200 m, 20 min); the two most-visited stays are anchors A (most time) and B (second).
  Private values: road-distance class of A–B in {< 2, 2–5, 5–10, > 10 km, none}; daypart of
  A→B departures by circular mean in {morning, midday, evening, night, none}; typical day
  chain in {A-B-A, A-B-C-A, A-C-A, other} (10,000-user rung only); a speed factor (numeric).
  The device is assigned by a data-independent draw to exactly one question. Dimension:
  K = 4–5 per question, independent of graph size.
- **What is randomized and how:** GRR with the full ε on the assigned question (piecewise
  mechanism for the speed factor). One report, fixed size; "none" is a real class for users
  without a second anchor; users with no data at all answer from the public prior.
- **What the server does:** Debias each small histogram, clip, shrink toward a public prior;
  θ = three 5-vectors and a scalar. Public inputs: home density = residential-road length per
  500 m cell, work density = primary/secondary/tertiary road length (plus office or
  commercial tags if present), both from OpenStreetMap only.
- **How a synthetic trajectory is generated:** Per synthetic user: home node proportional to
  home density; distance class from θ; work node proportional to work density restricted to
  that road-distance band (one bounded Dijkstra from home); commute daypart from θ, departure
  drawn inside it; return 8–10 h later with public jitter; optional third leg by chain type.
  Each leg is routed with the shared router and timed per segment as in 0.4; legs are emitted
  as unlinked `SyntheticTrajectory` objects (a linked variant is one flag).
  `sequence_log_prob(seq)` = Σ over leg types of P(leg) · P_home(origin) · P(destination |
  origin, distance class) · p_route(seq | origin, destination), with kernel-smoothed densities
  so every sequence scores finitely.
- **Why it is user-level pure LDP:** One GRR answer per user to one question whose value is a
  property of the whole user; ε-LDP on a 5-symbol domain, no composition. Easy: tiny domain,
  standard primitive. Subtle: stay-detection parameters, anchor ranking, class boundaries and
  question assignment are public; the per-synthetic-user trip count is a public constant, not
  a private estimate.
- **Expected behaviour at n ≈ 180 vs 10,000:** At 182, ε = 2, four questions: about 45 users
  per question, standard deviation about 0.075 against class means of 0.2–0.25, so the
  commute-distance and daypart mixes are recoverable; at ε = 1 two questions with three
  classes; at ε = 0.5 only the distance question. At 10,000: 8–10 distance classes,
  hour-level dayparts, chain types, and a coarse 4-zone home-region question charged like
  any other. Spatially the output is a city-wide commuting population; Geolife's campus
  concentration is not reproduced (cell JSD near the public prior), but durations, departure
  times and trip lengths follow the private relations.
- **Closest existing work and what differs:** Activity-based synthetic populations (MATSim,
  ActivitySim, iterative proportional fitting from census) are non-private; Berke et al. 2022
  generate stay trajectories from home/work inputs with an RNN under central DP; census-based
  DP population synthesis is central. Estimating only *relational* classes under user-level
  LDP and attaching them to public land-use anchors is, to my knowledge, new; it is also the
  only idea whose output naturally has user structure, matching the privacy unit.
- **Implementation effort:** M–L. Stay detection, anchor logic, land-use density rasters,
  banded destination sampling, chain generation, shared router; the linked-user variant and
  time-aware utility metrics are new benchmark work.
- **Main risk / failure mode:** Geolife is not a commuter population (students, logging hobby
  trips); anchors may be undefined for many users so the "none" class dominates, and the
  activity model misdescribes the data. The relation classes are themselves sensitive in a
  small population (one person with a > 10 km commute), which is exactly what ε bounds.
- **Subtle leaks:** (1) Transmitting any location-like value — a cell id, the distance to the
  nearest public anchor, even "my home cell is in the top 10 % density" — pins the home when
  combined with the public density map; transmit only the relation class. (2) Calibrating the
  home-density raster to training origins "to fix the Haidian problem"; spatial calibration
  must be its own randomized question. (3) Tuning stay-detection radius or dwell to the user's
  data. (4) Skipping users without a second anchor instead of answering "none". (5) Estimating
  the per-user trip count privately for the linked variant without charging it. (6) Using the
  user's anchors to decide which question to answer.

## Ranking

1. Idea 2 (behavioural moments, moment-tilted router) is best: one standard primitive, no composition, a proper sequential likelihood on the whole graph for `sequence_log_prob`, an explicit time model, graceful degradation to d = 3 at n ≈ 180 and growth to d ≈ 40 at 10,000; it is also the clearest contribution (maximum-entropy road-network synthesis from LDP moments).
2. Idea 1 (codebook vote) is the cheapest to build on the same router and the fairest successor to RN-LDP-Synth v1, but its novelty is thinner and its spatial gain at n ≈ 180 is nil.
3. Idea 3 (electorate over a zoo) has the cleanest proof and the best incremental-update story; keep it as the mandatory null baseline that Ideas 1, 2 and 4 must beat.
4. Idea 4 (anchor relations) is the strongest thesis narrative — user-level protection, user-level synthesis, no location ever transmitted — but needs the most new code and fits Geolife's population worst; build it after Idea 2, reusing its router and time model.
5. Whatever is chosen: ship the randomizer audit test, the canary test and the θ-only invariant with it, and put user-level ε on the comparison axis.
