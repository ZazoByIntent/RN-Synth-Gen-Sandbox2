# Brainstorm A — LDP statistician lens

User-level pure local differential privacy (LDP) for timed road-network trajectory synthesis.
Four ideas built outward from standard LDP primitives. Section 0 holds the numbers and
protocol rules all four share, so each idea can stay within the word limit.

## 0. Shared numbers and protocol

**Glossary.** OD = origin–destination. GRR = generalized randomized response (true item with
probability e^ε/(e^ε+k−1), otherwise a random other item). OUE/OLH = optimized unary encoding /
optimized local hashing (frequency oracles whose error does not grow with the number of items).
HM = hybrid of Duchi's and the piecewise mechanism for one bounded number (Wang et al. 2019).
SW+EMS = square-wave mechanism plus EM-with-smoothing reconstruction of a one-dimensional
distribution (Li et al. 2020). PCKV = correlated key–value perturbation (Gu et al. 2020).
Recursive logit = route choice in which the next edge is drawn with probability
∝ exp(edge utility + value of continuing from it) (Fosgerau et al. 2013). MaxEnt = maximum
entropy (exponential family). MAP = maximum a posteriori. GLS = generalized least squares.
IPF = iterative proportional fitting (raking).

**n** = users in the train split, the only users a generator sees: ≈ 90 at the 182 rung (a shadow
sees ≈ 18 shadow users plus candidates), ≈ 5,000 if T-Drive's 10,000 taxis are added.

**Answer budget B.** n users answering one yes/no question by randomized response are worth
n·0.25/(0.25 + e^ε/(e^ε−1)²) error-free answers. With the best number of questions per user,
B ≈ n × 0.06 / 0.21 / 0.58 / 1.16 / 2.3 at ε = 0.5 / 1 / 2 / 4 / 8, i.e.
**B ≈ 5 / 19 / 52 / 104 / 210 at n≈90** and ≈ 300 / 1,070 / 2,900 / 5,800 / 11,600 at n≈5,000.
A parameter needs ≈ 10 answers for a standard error of ≈ 0.16 of its range, so each idea
activates about B/10 parameters and leaves the rest at the prior.

**Primitive errors** (unbiased unless noted). GRR: Var ≈ (e^ε+k−2)/(n(e^ε−1)²), best for
k < 3e^ε+2. OUE/OLH: Var ≈ 4e^ε/(n(e^ε−1)²) for any k (sd 0.14 at ε = 1, n = 182). HM on
[−1, 1]: Var ≤ 4.7/n at ε = 1, ≤ 1.7/n at ε = 2. Padding-and-sampling a multiset of ≤ K units:
variance × K². SW+EMS: smoothing bias, low Wasserstein error. Projections onto convex feasible
sets and ratio estimators add O(1/n) or boundary bias (upward on true zeros) and cut mean
squared error.

**Protocol rules used by every idea.**
- **P1** One question per user at ε ≤ 2; about ε/2 questions, each at ε/k, at ε ≥ 4 (sequential
  composition sums to ε). The question index comes from a public draw, independent of the data.
- **P2** Every per-user value is the average over the user's own trips of clipped per-trip
  values, so it lies in a public box whatever the trip count; estimands are user-weighted. For
  trip-weighted targets the user reports min(m_u, M)/M times the value and the server takes a
  ratio (bias O(1/n)).
- **P3** The server shrinks every estimate toward the map-only prior θ₀ (OD mass ∝ road length per
  zone with a fixed distance decay, fastest-path routing at OSM class speeds, uniform departure
  hour, free-flow speeds), with weights from the known noise variances.
- **P4** Timing: edge time = free-flow time × exp(fitted offsets + AR(1) noise along the path with
  public correlation and spread); timestamps = departure (Beijing local time, UTC+8) + cumulative
  edge times.
- **P5** `sequence_log_prob` = log-probability of the edge sequence under the idea's own model
  (Ideas 1 and 3: OD term plus recursive-logit choice terms; Idea 2: zone walk plus a public
  within-zone logit; Idea 4: smoothed edge Markov chain of the weighted pool), mixed with a tiny
  public "teleport" term so it is finite for every sequence.
- Inside `fit`, views are grouped by `user_id` to simulate devices, each with a generator spawned
  from `seed`. Clips, zones, cordons, priors and candidate pools come from the map and fixed
  configuration only, and are cached across the 17 generators of a membership arm. Every model
  keeps ≤ B/10 private parameters, so membership AUC near 0.5 is expected and proves little;
  utility decides.

### Idea 1: Centred-moment MaxEnt route-and-time model
- **One-sentence pitch:** An exponential family over timed trips on the public graph, fitted by
  moment matching from one randomized, fastest-path-centred statistic per user.
- **What each user computes locally:** Sixteen clipped per-trip values, averaged (P2): origin and
  destination macro-zone (3×3), log OD distance, metres per class group (3) and turns minus those
  of the same-endpoint public fastest path, four departure-hour harmonics, weekday, log speed
  ratios (trip, per group).
- **What is randomized and how:** P1 with GRR, HM or SW. Centring narrows the clip and noise
  variance scales with its square, so a residual three times narrower is worth nine times more
  users; large detours are clipped (bias).
- **What the server does:** Projects moments onto the feasible set (simplex, Toeplitz-PSD
  harmonics), then a MAP fit, max θ·μ̂ − log Z(θ) − ½‖θ−θ₀‖²_Λ, with positive edge costs; log Z
  from sparse LU solves of the recursive logit toward zone sinks.
- **How a synthetic trajectory is generated:** Gravity OD; recursive-logit walk along out-edges
  to the destination zone's stop action (road-valid by construction); circular MaxEnt departure;
  P4 times with a trip speed regime drawn from the SW density.
- **Why it is user-level pure LDP:** One ε-LDP randomizer sees a bounded average of all the user's
  trips; centring uses only the map and the user's own endpoints. Subtle: an adaptive centre must
  be frozen before its batch reports.
- **Expected behaviour at n~180 vs n~10,000:** 182 rung (n≈90), ε = 1–2: 2–5 active values (OD
  distance, speed ratio, a harmonic pair), standard errors ≈ 0.15–0.2 of the clipped range;
  ε = 8: all 16. T-Drive (n≈5,000): 100–300 (zone masses, zonal class preferences, hourly
  profile). Degradation: public B/10 rule, rest at θ₀.
- **Closest existing work and what differs:** MaxEnt inverse reinforcement learning (Ziebart et
  al. 2008) and recursive logit need raw trips; LDP means give moments, not trips; LDP-SGD
  iterates gradients. Combined: timed trips from one-shot statistics; none found by my search.
- **Implementation effort:** M: cached fastest paths, randomizers, sparse recursive-logit solver,
  Fisher scoring, timed sampler.
- **Main risk / failure mode:** Sixteen features cannot express idiosyncratic routes (cell JSD
  stays near θ₀); 17 recursive-logit fits on 35,764 nodes may exceed 300 s.

### Idea 2: Kirchhoff flow oracle with flow-proportional synthesis
- **One-sentence pitch:** Estimate per-trip zone flows, project them onto the public graph's
  flow-conservation set, and synthesize with an absorbing walk that reproduces them exactly.
- **What each user computes locally:** Per public level (3×3, 6×6, 12×12 zones; arcs between
  road-connected zones) a trip is a unit flow: start (hour bin, origin), each zone crossing, end;
  trips over K units are scaled by K/units, keeping conservation. A time channel sums log
  travel-time ratios per arc. Dimension 69 at 3×3, ≈ 2,000 at 12×12.
- **What is randomized and how:** A public draw assigns level and channel; the P2 average, clipped
  to radius √K, goes through Duchi's ℓ2-ball mechanism, whose per-coordinate variance (≈ 7.4K/n at
  ε = 1) beats padding-and-sampling (3.7K²/n) below ε ≈ 4. Variant: send the residual against the
  fastest-path flow, a smaller circulation.
- **What the server does:** Weighted least squares across levels, shrunk to the map-only flow,
  under non-negativity, conservation at every zone (in + starts = out + ends), road-connected
  support and cross-level sums; Dykstra alternating projections.
- **How a synthetic trajectory is generated:** Start ∝ start flows; step z→z′ with probability
  f(z→z′)/outflow(z), or end: conservation makes expected arc visits equal the projected flows,
  so length needs no model. Public fastest paths join crossings (road-valid); P4 times from the
  time channel.
- **Why it is user-level pure LDP:** One ε-LDP report of a vector inside a public ball; the
  assignment ignores the data. Subtle: exact sphere sampling, public scaling rule and radius.
- **Expected behaviour at n~180 vs n~10,000:** n≈90: 3×3 per-arc sd ≈ 0.4 at ε = 2, 0.13 at
  ε = 4, 0.012 at ε = 8, for flows of 0.1–0.5. n≈5,000, ε = 1–2: 3×3 ≈ 0.06–0.09, 6×6 marginal.
  Degradation: users and shrinkage go to the finest level whose noise is below the prior's spread.
- **Closest existing work and what differs:** LDPTrace and RN-LDP-Synth v1 sample one
  length-normalized transition and model length separately; CDP-DTP (2025) enforces flow
  consistency under central DP. New: unbiased user-level flows, ℓ2 multiset oracle,
  conservation-exact walk.
- **Implementation effort:** M: zone/arc tables, ℓ2 mechanism, projection, walk sampler,
  within-zone router.
- **Main risk / failure mode:** A first-order zone walk ignores OD coupling (wandering trips);
  at benchmark n it is the prior unless ε = 8.

### Idea 3: Private cordon counts and dynamic OD inversion
- **One-sentence pitch:** Recover a time-dependent OD matrix from one binary cordon-crossing
  answer per user, by GLS through the public assignment map weighted by the exactly known noise.
- **What each user computes locally:** For S public cordons (3rd and 5th ring, radial cuts) and
  H hour bins: per-trip indicators "crossed c inbound/outbound in bin h" and log(time
  between consecutive ring crossings / free-flow time), averaged (P2). Dimension 2SH + S − 1
  (9 at S = H = 2).
- **What is randomized and how:** P1 over cells; each average is unbiasedly rounded to {0, 1} and
  sent by binary randomized response, the most efficient question; speeds by HM. At n≈5,000
  an ℓ2 report of all cells is better.
- **What the server does:** E[y] = A p, with p the OD × departure-bin distribution and A public
  (fastest routes timed by current speeds). Minimize (y−Ap)ᵀΣ⁻¹(y−Ap) + λ·KL(p ‖ gravity), p ≥ 0,
  Σ known exactly, with ring identities inbound − outbound = P(destination inside) −
  P(origin inside) (up to rare double crossings); alternate speeds and OD.
- **How a synthetic trajectory is generated:** Draw (origin zone, destination zone, bin) from p;
  route by the public time-dependent logit around the fastest path (road-valid by construction);
  P4 times from ring-band × bin speed factors.
- **Why it is user-level pure LDP:** One ε-LDP report on a bounded average; cordons, bins, A and
  the prior are public. Subtle: cordons must be fixed without looking at data.
- **Expected behaviour at n~180 vs n~10,000:** n≈90: 9 questions of ≈ 10 users, cell standard
  error ≈ 0.18 (ε = 2) or 0.09 (ε = 8), so only 2–4 radial parameters (centre attraction,
  morning-in/evening-out asymmetry, distance decay) leave the gravity prior. n≈5,000: ≈ 100 cells
  at 0.05–0.08, ring × sector dynamic OD. Degradation: fewer cordons, coarser bins.
- **Closest existing work and what differs:** OD estimation from counts (Van Zuylen & Willumsen
  1980; Cascetta 1984; dynamic: Cascetta et al. 1993) uses sensor counts with guessed errors; DP
  OD publication is central. New: LDP cordon answers as sole data, exact noise covariance,
  ring identities.
- **Implementation effort:** S–M: cordon edge sets, crossing extractor, randomizers, assignment
  map, regularized GLS, sampler.
- **Main risk / failure mode:** Routes stay the public prior; rings suit radial Beijing, not every
  city.

### Idea 4: Adaptive corridor sieve with key–value reports and pool raking
- **One-sentence pitch:** Descend a public road hierarchy in user batches, each user sending one
  length-sampled (road node, speed) pair, and rake a road-valid candidate pool to the shares.
- **What each user computes locally:** Tree: 3×3 macro-zones × 3 class groups (27 nodes), then
  named arterial corridors plus a local-roads node per zone (a few hundred), then ≈ 1 km pieces.
  Per user: length shares on the active nodes (a probability vector, so no padding blow-up) and
  per-node log speed ratios.
- **What is randomized and how:** One own trip, one point uniform by length; key = its active node
  (else "elsewhere"), value = log speed ratio rounded to ±1, sent by PCKV. A public 20 % send a
  departure hour by circular SW instead.
- **What the server does:** Batch b expands the children of nodes above three standard deviations
  in batch b − 1; unexpanded mass follows the prior. Then tree-consistent constrained least
  squares, non-negativity, parent-shrunk speeds, EMS departures.
- **How a synthetic trajectory is generated:** A cached pool of ≈ 10⁵ public candidates (gravity
  OD, randomized fastest paths: road-valid by construction) is raked by IPF to the resolved shares
  and resampled; SW departure; P4 times from node speeds.
- **Why it is user-level pure LDP:** One ε-LDP report per user; a batch's active nodes depend only
  on earlier batches and are fixed before it reports; batches follow a public random permutation.
- **Expected behaviour at n~180 vs n~10,000:** n≈90: one batch; level-1 sd ≈ 0.094 at ε = 2
  (shares ≈ 0.04, so 2–3 nodes resolve) and ≈ 0.002 at ε = 8, where a second batch reaches
  corridors above ≈ 1 %. n≈5,000: corridors above ≈ 5 % (ε = 2) or ≈ 2 % (ε = 4). Degradation:
  unresolved nodes keep the prior split.
- **Closest existing work and what differs:** Heavy-hitter prefix trees (PEM, TreeHist), AHEAD (Du
  et al. 2021), PCKV; central-DP PMW^Pub and PrivTrace's adaptive grid. New: a road-class/corridor
  hierarchy, location and speed at one resolution, pool raking; the descent itself is incremental.
- **Implementation effort:** M–L: corridor extraction, batch simulation, PCKV, circular SW, tree
  projection, pool and IPF.
- **Main risk / failure mode:** Shares fix where traffic is, not OD coupling or route continuity;
  the pool may lack demanded routes.

## Ranking
1. Idea 1 is best: it spends the 19–210-answer budget at n≈90 on the few numbers the length, duration and speed metrics depend on, has an exact likelihood for membership inference, and grows by adding parameters at n≈5,000.
2. Idea 3 is the best complement: binary cordon questions are the cheapest LDP questions that carry OD-joint and timing information, its inversion uses the exactly known noise, and it can supply Idea 1's OD block.
3. Idea 4 pays off at T-Drive scale or ε = 8, where adaptive descent finds the corridors actually used; at n≈90 and ε ≤ 2 it is the map-only model.
4. Idea 2 has the most novel post-processing (synthesis exactly consistent with conserving flows) but needs thousands of users even at 3×3; keep it as a large-n arm.
5. Top pick: Idea 1, with Idea 3's cordon indicators added as extra centred features once B allows.
