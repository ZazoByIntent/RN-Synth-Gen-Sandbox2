# R3-B Attack-first: ideas from the adversary's view (brainstormer R3-B, 2026-10-09)

Scope: `01_task.md` §1–§5, lens R3-B of §4; exclusions from `00_baseline.md` §3–§4, §9 (R3-B), §10.
Notation: P₀ = the public simulator P3 (Boltzmann router, gravity demand, public time law); twins = routes or
destinations drawn from P₀ with a seed hashed from (O, D, map, config), so they never depend on data; GRR
standard deviations (SD) from the baseline cheat sheet (§1); LiRA = the repo's membership attack.

**Three attack-driven design rules, used by every idea below (the "explicit rule" §9 calls untested).**
- AR1 Plaintext harmlessness. At ε 8 GRR is nearly truthful and the server reads the class; so the plaintext
  class must identify no one: equal prior mass (every class holds 1/k of the population under P₀ for every
  user, exact under the null for any trip count), and never a function of location or clock time.
- AR2 Many-hands release. The server releases only a clamped, shrunk tilt of P₀: g_c ∈ [1/G, G] and one report
  may move any released log-likelihood by at most log G / m (m public, e.g. 5), so a full tilt needs at least m
  users. Consequence: for every candidate route, the LiRA with/without difference of `sequence_log_prob` is
  bounded by log G / m, a non-vacuous membership bound where e^ε is vacuous (ε 8). Gate must be soft (a smooth
  weight in the test statistic) so that one report cannot flip prior ↔ fit.
- AR3 One leak channel. The only data-dependent factor in the likelihood of a (timed) trip is one monotone
  scalar function of the trip's typicality; geography stays prior at n = 91; time shares the same channel.
- Evaluation additions that are part of the story: a user-level MIA (sum of a user's per-trip LiRA scores; at
  u182 only 91 member vs ≈ 36 non-member users, so AUC only, the real evidence comes from the recovery
  simulation), a generate/likelihood consistency test (exact for rejection-sampling generators), the time-aware
  MIA P8 (idea 2), distance-to-closest-record parity on synthetic output (idea 3).

## Idea 1: TTR, twin-typicality router recalibration
1. **Pitch.** Each phone reports how typical one of its routes is under the public router, as a rank among
   public twin routes of the same endpoints; the server recalibrates the route-choice dispersion of P₀ by an
   exact, bounded tilt of the path likelihood itself, so the MIA sees a population-level change only.
2. **Report.** One uniformly drawn matched trip (⊥ if none; before P10, ⊥ also if O and D are within 500 m,
   because loop sessions are routes no router produces, F1). O, D = its end nodes; T = 30 twins from
   P₀(· | O, D); surprisal u(s) = −log P₀(s | O, D) with the public gap term; rank r = share of twins with
   lower surprisal; class c ∈ {typical, middle, atypical} by the twin terciles; GRR over 4 symbols (3 + ⊥) at
   full ε, 2 bits. R3-E variant: the median class over all the user's trips (lower variance, higher within-user
   coherence; this is the user-level-MIA ablation).
3. **Privacy.** Lift lemma (RANGI §5.5): everything the device computes is a path to one of 4 public values and
   only the GRR output leaves, so P(y | D) ≤ e^ε P(y | D'). Twins, T, class rule, G, m, gate constants are public
   and frozen by hash; one report, no split; every train user reports (P11).
4. **Server and synthesis.** Debias ŝ_c; soft gate against uniform (exact null whatever the trip count);
   g_c = 3 ŝ_c shrunk by w(n, ε, m) = min(1, (log G / m)·n(p − q)/3) and clamped to [1/G, G], renormalised
   so Σ g_c / 3 = 1. Release: P₁(s | O, D) = P₀(s | O, D)·g(c(s)), c(s) ranked against the same hashed twins;
   normalised up to a public O(T^−1/2) factor per (O, D), exact in expectation. Reading: a non-parametric
   temperature recalibration of route choice. Origin and destination from the prior demand (geography stays
   prior), departure from the public profile, route by rejection sampling (draw s ~ P₀, accept with g_c / G),
   so generate and likelihood are the same model by construction (X12); segment times = free-flow × public
   factor × jitter (P3). At ε 8 or large n: class × departure period (9 cells) gives period-specific
   dispersion; a road-class-group split is a further ablation.
5. **`sequence_log_prob(seq)`** = log P₀(O, D) + log P₀(seq | O, D) + log g_{c(seq)} + gap term. Reverse
   Dijkstra per destination cached (≈ 40 ms), 30 twin walks per (O, D) hashed and cached once for all 17
   generators (≈ 1,100 destinations, 1–2 min); finite through the public floor; reads only parameters and
   map/config-keyed caches (P4).
6. **n = 91.** ε 0.5: share SD 0.28–0.41, the gate keeps the prior. ε 2: 3 shares ± 0.073, the gate rejects
   when one tercile is off by ≥ 0.15 (0.48 instead of 0.33), i.e. a dispersion error of about one tercile,
   plausible because the prior temperature is a guessed constant and the matcher's gap fill makes matched
   routes over-direct; log g has SD ≈ 0.22 nats against a clamp of 0.5; the gain shows in length W1 and cell
   JSD through route directness, never in geography. ε 8: ± 0.05, so 5 classes or the 9-cell period joint
   (± 0.05 per cell). n = 10,000: ε 2 ± 0.007, a 10-step recalibration curve by period and road-class group
   (≈ 30 cells); ε 0.5 ± 0.03, the 3-class item.
7. **Closest work and differences.** K1 / R2-C.1 (twin rank, exact null, quantile map): TTR ranks the model's
   own log-likelihood, so it recalibrates the path distribution itself, not a one-dimensional duration
   density; the estimand (route-choice dispersion) was measured by no round (C1 = taste direction by moments,
   K4 = pieces, K1's large-n *len* ablation = one feature, whereas surprisal is the sufficient statistic for the
   temperature); the tilt sits inside `sequence_log_prob` (K1's dur is invisible, X11); rejection sampling
   makes X12 exact; AR1–AR3 and the user-level MIA are new. Published: temperature scaling (Guo et al. 2017),
   CDF recalibration (Kuleshov 2018), typicality tests (Nalisnick et al. 2019), LDP goodness-of-fit (Acharya
   2019): none under LDP, none on path distributions, none with one report per user. Not C3/C5 (votes over
   catalogues or libraries), not C9 (tokens), not K7 (self-fit).
8. **Main risk.** It may measure the matcher (shortest-path gap fill, X13) and unsplit sessions (F1) rather than
   behaviour, so P10 is needed and the recovery simulation must include a misspecified run with matcher-like
   fill; at ε 2 the number may converge with the walk/vehicle mix (X10); an evaluator may call it "K1 on routes"
   (rebuttal: estimand and likelihood visibility); rank discreteness with T = 30.

## Idea 2: JTT, joint timed-typicality tilt (time and route share one leak channel)
1. **Pitch.** The phone ranks the joint typicality of one trip's route and travel time among timed twins; one
   3-class item tilts the joint law of (route, times) by one bounded factor, so the time-aware MIA (P8) gets
   exactly the same bounded log-ratio as the route-only MIA: adding time to the attack cannot add advantage.
2. **Report.** One uniformly drawn matched trip with its departure and duration from the raw timestamps on
   the device (⊥ rules as in idea 1). Timed twins: T = 30 pairs (s, τ) from P₀(· | O, D, dep), τ = the sum of
   public edge times (free-flow × factor(dep) × jitter). Joint surprisal u(s, τ) = −log P₀(s | O, D)
   − log f₀(τ | s, dep); rank among the twins; 3 classes + ⊥ by GRR at full ε (2 bits). At ε 8 or large n a
   9-cell item: route-rank tercile (given O, D) × duration-rank tercile (given the route), GRR over 10.
3. **Privacy.** Lift lemma as in idea 1; departure enters only the device-side twin simulation through the
   public factor profile; the plaintext is a typicality class, no location, no clock time (AR1); one report.
4. **Server and synthesis.** Debias, soft gate, tilt g under AR2. Release P₁(s, τ | O, D, dep)
   = P₀(s | O, D)·f₀(τ | s, dep)·g(c(s, τ)). O, D and dep from the prior; (s, τ) by rejection sampling of
   timed prior draws (accept with g_c / G), and the accepted draw's segment times are released as they are,
   so per-segment times carry the tilt consistently (a trip accepted as "atypical" keeps its slow or
   roundabout segments). The 9-cell g at ε 8 is not separable: it carries the coupling "are atypical routes
   also slow?", a joint query no marginal design reaches (R3-C open list).
5. **`sequence_log_prob(seq)`** = log P₀(O, D) + log P₀(seq | O, D) + log ḡ(seq) + gap term, where
   ḡ(seq) = E[g(c(seq, τ))] over 30 hashed draws of (dep, τ) from the public profile and f₀(· | seq, dep),
   ranked against the (O, D) twins: the exact marginal of the tilted joint, in [1/G, G], so the AR2 bound
   holds. The timed likelihood for P8 adds log f₀(τ | seq, dep) + log g(c(seq, τ)) + log profile(dep). Cost:
   30 edge-time vectors per candidate, negligible next to the cached Dijkstra and twins of idea 1.
6. **n = 91.** ε 0.5 nothing. ε 2: one 3-class share ± 0.073, one number that blends route directness with the
   speed level against the prior (lesson 2 convergence: it cannot say which); it moves duration W1 within
   period (P12) and length W1 after a ≥ 0.15 tercile shift. ε 8: the 9-cell joint, GRR over 10, SD ≈ 0.035
   per cell after the F4 correction: separates dispersion from time level and measures their coupling, 2–3
   numbers. n = 10,000: 9 cells × 3 periods at ε 2 (± 0.02 per cell), the coupling by period.
7. **Closest work and differences.** K1 *dur* ranks duration only and is invisible to the MIA; K1's ε 8
   joint is dep × dur (clock × time), JTT's is route × time, proposed by no round; K8 item c is a within-user
   coupling across trips, JTT's coupling is within one trip across the two channels and enters the
   likelihood. Idea 1 is its route-only marginal. RATR 2025 and Brauer 2024 release each user's own timed
   trajectory (per-user objects, no synthesis); PUTS and MTNet are central DP. Conformal and multivariate
   typicality (Nalisnick 2019) give the statistic, never under LDP with one report per user.
8. **Main risk.** Needs P1 (timed payload) and P8 (time-aware MIA), neither built; before P10 the duration
   holds stops, so stop-laden sessions saturate the atypical class (lesson 4) and the ⊥ loop rule costs a ⊥
   share; at ε 2 the one number is a blend; at ε 8 the ⊥ share plus 10 symbols make GRR marginal (k < 3e^ε + 2
   still holds).

## Idea 3: GCC, gallery-coverage calibration (the linkage attacker's statistic as the report)
1. **Pitch.** The phone runs the reidentification attacker on itself: the distance from one of its trips to the
   nearest route of a fixed public city-wide gallery, ranked against the same distance for prior-drawn trips.
   The server calibrates one concentration parameter of demand and routing so that the released routes are
   population-calibrated in the attacker's own metric, and distance-to-closest-record parity becomes a
   controlled quantity instead of an afterthought.
2. **Report.** Public gallery 𝒢: 5,000 routes from P₀ (hashed), resampled to 20 points in UTM, published.
   Device: one uniformly drawn matched trip (⊥ rules as before), resampled to 20 points; d = min over the
   gallery of `dtw_norm` with a bounding-box prefilter (≈ 2·10⁶ operations). The server publishes the
   reference distribution of d for 10,000 fresh prior trips; class c = tercile of d in it, {near, mid, far}
   + ⊥, GRR at full ε (2 bits). Under a correct prior every trip's d is a draw from the reference, so the null
   is exact for any trip count. Variant (R3-E): the median d over all the user's trips.
3. **Privacy.** Lift lemma; gallery, reference terciles and the κ path are public and hashed; one report.
   AR1: equal mass, no coordinates leave; at ε 8 a truthful "far" still says "I travel where the prior puts
   little mass", a weak location signal with anonymity set n/3, to be stated, not hidden.
4. **Server and synthesis.** Debias, soft gate. Estimand: one concentration parameter κ along a public path
   through the simulator, temperature β(κ), gravity decay λ(κ), origin-mass exponent α(κ) (κ > 0 concentrates
   demand and routes on the prior's main mass, κ < 0 spreads them). A public response surface κ → expected
   class shares (simulated once on 20 κ values) and weighted least squares on the 3 debiased shares give κ̂,
   shrunk to 0 and clamped so that the origin-destination log-ratio against P₀ stays ≤ 0.5 on 3 × 3 macro
   zones (AR2 analogue). Release = the simulator at κ̂: origin by mass^α, destination by gravity with decay
   λ, route by the Boltzmann walk at β, departure and segment times from the public law. Coverage guard: an
   over-represented "far" class vetoes any sharpening by idea 1 when both run (a combination arm).
5. **`sequence_log_prob(seq)`** = log P_κ̂(O) + log P_κ̂(D | O) + log P_κ̂(seq | O, D) + gap term: the prior's
   exact form with re-parametrised constants, cached Dijkstra, no twins needed; the demand change moves
   P(O, D) for every route, so the MIA sees the release.
6. **n = 91.** ε 0.5 nothing. ε 2: 3 shares ± 0.073, a tercile shift ≥ 0.15 is detectable and plausible on
   Geolife (trip ends concentrated at a few campuses while the prior spreads them by road length), but κ̂ is
   one number: it moves length W1 and cell JSD through concentration only and cannot move mass to where the
   users are (AR3: geography stays prior). ε 8: ± 0.05, 5 distance classes, κ plus a spread (2 numbers).
   n = 10,000: class × period and class × public length band, coverage by trip length, 6–9 numbers.
7. **Closest work and differences.** Distance to closest record and "density and coverage" (Park et al.
   2018; Naeem et al. 2020) are evaluation metrics for synthetic data; here the attacker's metric is the LDP
   report and a calibration target. C5, D.1 and Private Evolution report which public sample is nearest (a
   frequency oracle over a gallery); GCC reports only a distance class, so no gallery frequencies and no
   private sampling. K1 ranks against twins of the trip's own context; GCC ranks a distance to a global
   gallery (geography and shape jointly). The estimation step is "simulate, perturb, match" (taken; novelty
   is claimed only for the statistic and the attack-side target). Not C2 (zone shares), K6 (signature bins),
   K2 (time-budget ring).
8. **Main risk.** A one-dimensional estimand with a possibly flat response surface (the class shares may
   barely depend on κ), so it may equal its prior arm at every Geolife rung (lesson 3); its lasting value may
   be the coverage guard and the parity metric rather than the generator; the gallery is one more public
   artefact to freeze.

## Idea 4: DRT, destination-rank tilt (no location parameter ever)
1. **Pitch.** Zone shares (C2) at ε 8 pass a rare origin-destination cell into the likelihood: a cell with
   prior mass 0.005 that one user fills in a shadow of 18 users gets a likelihood ratio near 3 for every route
   of that user. DRT replaces every location parameter by a per-origin rank: the phone ranks its trip's
   destination among 30 destinations the gravity prior draws for the same origin, and the server tilts the
   distance-decay law exactly, with equal prior mass and a bounded tilt.
2. **Report.** One uniformly drawn matched trip (⊥ rules as before); origin node O; 30 twin destinations
   D_j ~ P₀(D | O) (gravity on the free-flow skim, hashed); statistic = free-flow cost of (O, D); rank among
   the twins' costs; terciles {nearer, middle, farther} + ⊥; GRR at full ε (2 bits). At ε 8 or large n:
   tercile × departure period, 9 cells.
3. **Privacy.** Lift lemma; no coordinate leaves; the plaintext "my destination is farther than two thirds of
   the gravity draws for my origin" has anonymity set n/3 (AR1); the rank is exact under the null for every
   origin and every trip count (a conditional probability integral transform per origin); one report.
4. **Server and synthesis.** Debias, soft gate, tilt g under AR2. Release P₁(D | O) = P₀(D | O)·g(c(D | O)),
   c ranked against the hashed twins of O, normalised up to a public O(T^−1/2) factor per origin. Origin from
   the prior mass; destination by rejection sampling from gravity (accept with g_c / G); route and times from
   P₀, or from idea 1's tilt in a combination arm: two levels of one typicality principle, users split by
   the public draw, never ε.
5. **`sequence_log_prob(seq)`** = log P₀(O) + log P₀(D | O) + log g_{c(D | O)} + log P₀(seq | O, D) + gap
   term. The twin destinations need one forward Dijkstra per origin (≈ 40 ms, cached, ≈ 1,100 origins per
   arm, shared by the 17 generators); finite through the floor.
6. **n = 91.** ε 0.5 nothing. ε 2: ± 0.073 per share; a decay error that shifts a tercile by 0.15 (trips
   systematically shorter or longer than gravity says) is plausible for Geolife's short campus trips against
   a city-wide decay; it moves length W1, duration W1 and the 3 × 3 OD JSD radially (how far), never where.
   ε 8: 9 cells ± 0.035, decay by period (2–3 numbers). n = 10,000: tercile × period × a 3 × 3 public
   mass-balanced macro zone of the origin, 81 cells at ε 2 ± 0.02, the first point where geography moves.
7. **Closest work and differences.** C2 / B.2 (absolute cost bands plus zone shares, minimum KL to gravity,
   L-SRR): DRT has no zone item, a per-origin conditional rank with an exact null and a bounded tilt, and is
   motivated by the rare-cell leak. K2 / R2-A.1 reaches destinations through the time budget's ring, DRT
   ranks the actual destination's cost. Yoon et al. 2012 (potential path areas) and DP gravity calibration
   from central OD tables (Boninsegna & Silvestri 2025) are the published neighbours. Destination-level
   sibling of idea 1; not K5 (modal cell), not K4 (via points), not K6 (radius of gyration bins).
8. **Main risk.** Thin novelty if read as "C2's cost band as a rank" (rebuttal: the exact per-origin null, no
   location parameter, the ε 8 leak argument); the cost tercile is radial only; before P10 loop sessions fall
   into "nearer" and bias toward short trips (⊥ loop rule); at ε 2 the number may again be the walk/vehicle
   mix (short walks), X10.

## Self-ranking
1. **TTR (idea 1)** is the one to carry: visible to today's MIA, exact likelihood with generation consistent by
   construction, rules AR1–AR2 with a quantitative ε 8 bound, and one plausible number at ε 2.
2. **JTT (idea 2)** is TTR's timed extension and the most attack-first statement of the set ("time adds no
   advantage"), but it waits on P1 and P8 and blends two quantities at ε 2.
3. **DRT (idea 4)** before **GCC (idea 3)**: DRT is a modest sibling that removes C2's rare-cell leak; GCC is
   the purest adversary's-view report but will likely equal its prior arm at n = 91.
