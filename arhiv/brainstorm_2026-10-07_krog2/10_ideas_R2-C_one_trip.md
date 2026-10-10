# R2-C ideas: one sampled trip (or pair, or sub-path) per user, lifted to user-level ε-LDP

Brainstormer R2-C, 2026-10-07. Inputs: `01_task.md`, `00_baseline.md`, three web queries (no LDP calibration of traffic
simulators found; DPMM's per-trip waypoints found; only central-DP recalibration of classifiers found). Terms as in
`00_baseline.md`. New terms: PIT = probability integral transform (a model's CDF evaluated at the observation; uniform
when the model is right); twin = a trip the public simulator draws for the same context as a real trip; rank histogram =
distribution of a real trip's rank among its twins.

## 0. Shared notes for all ideas below
- **Lift lemma (privacy).** Let R be ε-LDP on a public finite domain X. For any selection map f from the user's whole data
  D into X (uniform trip, matched pair, sub-path window, a rank against device-simulated twins, a public default when
  nothing qualifies; deterministic or randomized, even data-dependent), R(f(D)) is ε-LDP at user level, because
  P(y | D) ≤ max_x P(R(x) = y) ≤ e^ε min_x P(R(x) = y) ≤ e^ε P(y | D'). Data-independent sampling matters for the estimand
  only, never for privacy, so the selection rule is free for estimator design. X, R and every threshold, window, bin and
  default must be public.
- **One trip or a user average?** For a binary item, "sample one trip, then binary RR" has exactly the output law of
  Duchi's one-bit mechanism on the user's share (P(1) = q + f_u(p − q)). For scalar moments, averaging all trips plus PM/HM
  wins when a user's own trips differ (about 2.7× lower variance at ε 2, 40–150× at ε 8) and loses nothing to one trip
  when they are alike. A single trip is the natural carrier for categorical, structural and joint items (GRR needs one
  category; a user's histogram can only be sampled), so the ideas below carry those and leave moments to C1.
- **Heavy vs light users (weighting menu).** w_u = min(m_u, M)/M with a public cap M. (a) M = 1, uniform trip:
  user-weighted estimand, no extra variance (default at n ≈ 91). (b) Padding-and-sampling: send ⊥ with probability
  1 − w_u, GRR over k + 1, ratio estimator ŝ_j/(1 − ŝ_⊥): capped trip-weighted estimand, SD × 1/ρ with ρ = mean(w_u).
  (c) Weight-class tag: GRR over k × C with C = 2–3 public m-classes and public class weights: SD × √(1 + CV²(w)) × the
  cost of the larger domain; beats (b) when ρ is small, biased by the weight spread inside a class. Kish's bound
  n_eff = n/(1 + CV²(w)) caps every scheme: uncapped trip weighting with CV(m) ≈ 2 leaves about 18 of 91 users.
  Proposal: user-weighted estimand with P2's user-weighted reference; (b) with M = 4 as a sensitivity arm; trip weighting
  only in the recovery simulation.
- **Noise used below** (exact SD of a debiased GRR share at n = 91, shares near uniform; ε 0.5 / 2 / 8): k = 2:
  0.21 / 0.069 / 0.052; k = 3: 0.28 / 0.073 / 0.049; k = 4: 0.33 / 0.074 / 0.045; k = 9: 0.49 / 0.079 / 0.033. The cheat
  sheet's ±0.048 for 3 shares at ε 2 is the limit of a vanishing true share; with shares near 1/3 the sampling term adds
  about 50 %.
- **Control arm every idea must beat:** `ldptrace` lifted to user level (one uniformly sampled matched trip per user at
  full user ε, its grid walk snapped to OSM by the public router). A re-telling, not an idea, but the comparison a
  CLOSE-VARIANT reviewer will ask for.
- **Considered and dropped.** (i) One synthetic trip per user by the exponential mechanism with the public simulator as
  base measure (exact rejection sampler on the device, road-valid timed output): less informative than one 27-way GRR item
  at n ≈ 91 and C5/D.1 in disguise (Cond-C5 not met). (ii) Public stratum plus presence plus value: PrivKV on a trip
  alphabet. (iii) "Any of my trips touched cell c" reach bits: about 10 users per cell at n ≈ 91. (iv) Day sampling: a
  Geolife recording session is not a full day, and per-day quantities (trip count, dwell, time budget) are invisible to
  unlinked-trip metrics and belong to R2-A/R2-B.

## R2-C.1 Twin-rank vote: one trip ranked among public twins recalibrates the simulator
1. **Pitch.** The device ranks one of its trips among K twins that the public simulator draws for that trip's own
   context and sends only the coarse rank; the server learns which conditional law of the simulator is miscalibrated,
   corrects it by a monotone map, and keeps the prior wherever an exact uniform null is not rejected.
2. **Report.** A public draw (seeded by the user index) picks one question of the simulator's chain: *dur* = travel time
   given the trip's own route and departure; *route* = surprise log P_router(route | O, D); *len* = OD road distance given
   O; *dep* = departure clock time. The device samples one matched trip uniformly, simulates K = 29 twins with its context
   (dur: jitter draws of the public time model on the real route and departure; route: Boltzmann walks O → D; len: gravity
   destinations from O; dep: exact PIT, no twins), ranks the real statistic among them (random tie-break) and sends GRR_ε
   over 3 prior-equal bins (rank 0–9, 10–19, 20–29): 1.6 bits. At ε 8 the joint of one trip: the 3 × 3 cell of its
   (dep, dur) ranks, uniform under the null by the Rosenblatt property (9-way GRR). Large n: 5–10 bins with public
   per-user dithered edges, so the server fits a smooth map. **Heavy vs light users:** under a correct prior each user's
   rank is exactly uniform whatever m_u and context mix, so the imbalance cannot fake a miscalibration; only the signal is
   user-weighted. ε 8 variant: rank the user's whole trip set among 29 twin sets with the same contexts; still uniform for
   every m_u, more power for heavy users, but sizing a correction needs the m-law (weight-class tag, §0).
3. **Privacy.** Question, dither and twin seeds are public or local randomness; trip choice, twins, rank and bin are a
   randomized function of the user's data into the public domain {1, 2, 3}; GRR at full ε; lift lemma. Users are split
   across questions, ε is not; twins never leave the device.
4. **Server.** Debias to rank-bin shares. A public gate (debiased chi-square against uniform, critical value simulated in
   advance) decides per question whether to move at all. Time questions: quantile mapping, G = monotone piecewise-linear
   PIT law through the shares; corrected density = prior density × g(F_prior(x | context)), exactly normalised since
   E_prior[g(U)] = 1 (3 bins: a shift and a spread of log-duration). Route and len: simulated moments; the expected rank
   histogram as a function of router temperature β or gravity decay γ is computed publicly once; θ̂ minimises the
   GRR-covariance-weighted distance. Synthesis: O from the prior (or C2), D by gravity at γ̂, route by the Boltzmann walk at
   β̂ (road-valid), departure from the mapped diurnal prior, per-segment times = free-flow × public factor × jitter with the
   total quantile-mapped and every segment scaled by the same ratio.
5. **`sequence_log_prob`.** Time does not enter: log P(O, D; γ̂) + Σ log step probabilities at β̂ + public floor, the §4
   code with at most two corrected numbers (at n ≈ 91, ε 2 only *dur* is asked, so routes stay prior). Ablation:
   log p_prior + log g(F_ℓ(ℓ(seq) | O, D)), F_ℓ from public twins per queried (O, D) seeded by a hash of (O, D, map,
   config), identical for members and non-members, cached across the 17 generators.
6. **Estimable.** ε 0.5: ±0.28 per share; the gate keeps the prior (honest no-gain arm). ε 2: one question for all users
   (*dur*, lesson 10), ±0.073 per share: the log-duration shift to about ±0.2σ (σ = prior spread) while it stays within
   one σ, plus one coarse spread factor. ε 8: ±0.05 per share (sampling); two questions at about 45 users each (±0.07),
   or the (dep, dur) copula for all (±0.033 per cell). n = 10,000: all four questions, 8 dithered bins, G split by
   period × length tertile, two or three copulas, prior-equal-mass origin and destination cells.
7. **Closest work.** Non-private: rank histograms (Talagrand et al. 1997; Hamill 2001), PIT calibration (Dawid 1984;
   Gneiting et al. 2007), simulation-based calibration (Talts et al. 2018), quantile mapping. DP: privacy-preserving
   recalibration (Luo et al. 2020, arXiv 2008.09643; central, classifier confidences). LDP: Calibrate (prior in the
   estimator, not the report); LDP goodness-of-fit tests (Berrett & Butucea 2020; Lam-Weil et al. 2022; raw data against
   a fixed law, no context, no correction); Xiong et al. 2023 (simulator inference from central DP). **New vs
   per-trajectory LDP** (LDPTrace, RetraSyn, PrivTrace, L-SRR, Cunningham et al., TraCS, DPMM, GeoPM-DMEIRL): all
   randomize geography; none sends a statistic relative to a public generator conditioned on the trip's own context,
   calibrates time, or has an exact null telling the server when to keep its prior. **vs §4, C4–C10:** C1 (A.1, C.1, D.2,
   E.3) sends clipped trip-averaged moments; C.1 ("centred on the prior's expectation") is nearest but sends a mean, needs
   clipping and features, has no null. C3 (B.4, C.2, D.3) is a posterior label over K generators (mixture weights), not
   calibration within one. C5 (D.1, C.3) votes for the nearest library member; twins are exchangeable with the real trip,
   not a library. C7 (C.4) searches knobs with likelihood-gain bits. Watch R2-E ("latent codes by inverting a public
   simulator"): a PIT is that latent for one conditional.
8. **Main risk.** Saturation: a narrow car-speed prior puts every walk or bus trip in the top bin (resolution collapses
   beyond about 2σ); the remedy, a diffuse mode-mixture prior from cited speeds, makes *dur* partly re-estimate C3's
   regime shares, so the distinct gain rests on route, dep and copula questions. One map per question assumes
   context-free miscalibration (short walks, long drives break it). Geolife durations include stops and GPS gaps.

## R2-C.2 Piece-count router: one trip's route structure (via points and loops)
1. **Pitch.** One sampled trip carries its route's structure (how many near-shortest pieces it splits into, or whether it
   is a loop), and the server fits a via-point router whose routes concatenate near-shortest walks through public anchor
   nodes, which also produces the loops a walk toward the destination cannot.
2. **Report.** The device samples one matched trip uniformly and splits its edge sequence greedily into maximal pieces
   whose free-flow cost is at most (1 + τ) times the shortest cost between the piece's ends (τ = 0.05 public, absorbs
   matcher wiggles). Class ∈ {1 piece, 2 pieces, ≥ 3 pieces, loop} (loop: OD road distance below 0.25 × route length);
   GRR over 4: 2 bits. ε 8 or large n: add the main via's lateral offset class (offset/OD distance below or above 0.15)
   and position along the OD axis (early/middle/late), 6–20 categories. **Sub-path variant:** a public log-uniform window
   length ℓ_u in [0.5, 8] km; the device places a window of that length uniformly on its sampled route and sends one RR
   bit, "this window is near-shortest"; the server fits S(ℓ) = exp(−λℓ), λ = via points per km. **Heavy vs light
   users:** uniform trip, user-weighted law. The piece count grows with trip length, so users with many short trips and
   users with few long ones differ in length, not behaviour; the generator therefore draws k given OD distance
   (Poisson(λ̂ · d_OD), or class shares per OD-distance tertile at large n). Padding with M = 4 as a sensitivity arm.
3. **Privacy.** Decomposition and class are deterministic functions of the trip and the public map (τ, cost metric,
   anchors, loop threshold frozen before any Geolife run); GRR or RR at full ε; lift lemma; one report.
4. **Server.** Debias; shrink to a public prior from cited shares of shortest-path-consistent and anchor-based routes
   (Zhu & Levinson 2015; Lima et al. 2016; Manley et al. 2015; constants to extract and freeze) and a cited leisure-loop
   share. Generator: (O, D) from the prior or C2 (loop: D within a public radius of O); k from the shares (or
   Poisson(λ̂ d_OD)); k − 1 vias from a public anchor set A (about 500–3,000 junctions of secondary-or-higher roads) under
   a public offset kernel around the OD axis (loop: one via at a public radius); pieces = high-β Boltzmann walks toward
   the next via (road-valid, exact step probabilities); departure and per-segment times from the public time model (or
   R2-C.1's corrections).
5. **`sequence_log_prob`.** Sum over classes of π_class × Σ over via positions on the sequence of P(vias | O, D) ×
   Π P_walk(piece | next via), plus the public floor. Vias must be anchors on the queried sequence (≤ 2 vias, about 40
   anchor positions, ≤ 800 pairs), so a dynamic programme with prefix sums of log step probabilities toward each
   candidate via is exact and cheap; the k = 1 term is the §4 walk. Needs one reverse Dijkstra per anchor (≈ 40 ms with
   scipy csgraph), cached once per map and shared by all 17 generators: ≈ 140 MB for 1,000 anchors, or lazily for
   anchors on queried routes.
6. **Estimable.** ε 0.5: ±0.33 per share, prior kept. ε 2: ±0.074 per share: moves the loop share (the §4 walk gives
   loops almost no mass, so a loop share of 0.15 or more is a 2-SD gain) and the single-piece share; or λ to about ±25 %
   (window variant, λ ≈ 0.2 per km). ε 8: ±0.045 per share plus the offset class of two-piece trips, or λ to about
   ±18 %. n = 10,000: class × offset × position (about 20 cells) and splits by period (do peak trips detour more?).
7. **Closest work.** DPMM (Haydari et al., ACSAC 2022) samples waypoints and picks candidate paths between them by the
   exponential mechanism, per trajectory: it releases each user's perturbed path, with no population estimand, generator
   likelihood or time. Via-node alternative routes (Abraham et al. 2013), PRESS shortest-path compression (Song et al.
   2014) and anchor-based route choice (Manley et al. 2015) are non-private. **New vs per-trajectory LDP:** LDPTrace,
   RetraSyn and PrivTrace learn grid transitions (randomness at every step, no route structure, no loops); L-SRR,
   Cunningham et al. and TraCS perturb places or points. Here the private object is the route's global structure, the
   server output is a population via-point law, and the likelihood is exact. **vs §4, C4–C10:** C1 (A.1, B.1, C.1, D.2,
   E.3) tilts a one-piece walk by route moments (detour, class shares, turns/km), randomness at every step; the via-point
   law puts it into a few global decisions, and the piece count does not depend on class mix or turn density. None of C9
   (E.2 tokens), C8 (A.4 corridors), C5 (D.1, C.3 libraries) or C10 (A.2 flows) counts pieces or loops.
8. **Main risk.** GPS gaps make the matcher fill straight shortest paths (k biased to 1) and GPS noise creates spurious
   pieces; τ and the cost metric decide k and must be frozen on OSM and the fixture, and lesson 4 applies to the
   1-versus-2-piece split. Hiking and sport loops may be off-graph and fail the 0.3 match score (P9: are footways in the
   graph?), so the matched set may hold few loops. At n ≈ 91 the via-location law stays prior; anchor caching must fit
   the 300 s budget at u20/u50.

## R2-C.3 Paired twin-rank contrast: within-user, prior-relative time effects
1. **Pitch.** User-level LDP can compare two trips of the same person, which no per-trajectory mechanism can: the device
   picks a public-rule matched pair (a peak and an off-peak trip of comparable free-flow length) and sends the coarse
   sign of the difference of their twin-ranks, giving the error of the prior's time-of-day factor free of who travels
   when (walkers at midday, drivers at peak).
2. **Report.** Public windows (peak 7–9 h and 17–19 h Beijing time, off-peak the rest of 6–22 h) and comparability
   (free-flow route times within a factor 1.5). If eligible pairs exist, pick one uniformly; rank each trip's duration
   among 29 *personalised* twins (the public time model shifted by the user's own mean log-speed ratio over all its
   trips, computed locally, which removes saturation and the user's level); d = rank_peak − rank_offpeak;
   class ∈ {d < −10, |d| ≤ 10, d > 10}, otherwise ⊥; GRR over 4: 2 bits. Variants by public draw: weekday versus
   weekend; same-OD-cell pair "same route?" (large n only). **Heavy vs light users:** eligibility needs two suitable
   trips, so heavy users answer more often; the estimand is the mean within-user effect among eligible users, the ⊥
   share estimates eligibility, and a homogeneous effect needs no reweighting (checkable at large n with the
   weight-class tag).
3. **Privacy.** Pair selection (data-dependent), personalised twins, ranks and class are a randomized function of the
   user's data into a public 4-value domain; GRR at full ε; lift lemma. Both trips feed one report, so nothing composes.
4. **Server.** Debias; class shares among eligible users = ŝ_c/(1 − ŝ_⊥). With a correct period factor and equal user
   effects in both periods, d is symmetric, so the sign balance is an exact test; an ordered-probit fit with the public
   jitter scale sizes it as one number, the log-speed error μ̂ of the peak factor. Time model: free-flow × prior period
   factor × exp(μ̂ · 1[peak]) × jitter, combined with the regime level of C3 or R2-C.1 without double-counting the mode
   mix. R2-C.1's (dep, dur) copula measures the same dependence across users (confounded); this measures it within
   users. Routes and OD come from the host mechanism.
5. **`sequence_log_prob`.** Unchanged from the host route model (prior walk, C1/C2 or R2-C.2): a time module, invisible
   to the membership attack.
6. **Estimable.** Eligibility ρ unknown (guess 0.3–0.6 at u182). ε 0.5: nothing. ε 2: ±0.074 per share, ±0.15 per class
   among eligible users (ρ ≈ 0.5), ±0.23 on the sign balance: only a very large prior error shows. ε 8: ±0.14 on the
   sign balance, moderate effects. n = 10,000: period × road-class contrasts, weekday/weekend, route repetition.
7. **Closest work.** Central user-level DP averages per user (Rameshwar et al. 2024; Levy et al. 2021); MTNet and PUTS
   model travel times under central DP; Kent, Berrett & Yu 2024 give rates for user-level LDP with many observations per
   user, not within-user contrasts. **New vs per-trajectory LDP:** LDPTrace and its relatives randomize each trajectory
   separately, so two trips of one person can never be linked; a within-person contrast is impossible there by
   construction. **vs §4, C4–C10:** C1 (C.1, E.3) estimates period × road-class speed factors across users, confounded
   with the mode mix; C3 gives regime shares only. C4's D.4 ("relations, not places") relates anchors to build tours;
   here two trips' prior-relative times identify one effect for an unlinked-trip time model, so Cond-C4 is not needed.
8. **Main risk.** Low eligibility (about 9 matched trips per user, often all in one period) leaves n_eff ≈ 30–45; the
   effect may be small next to within-user noise (different purposes and modes on different days); duration and speed W1
   do not reward de-confounding, so the gain is mostly scientific (a clean congestion effect).

## Self-ranking
1. R2-C.1 Twin-rank vote: most novel (a model-relative rank with an exact null as the LDP payload), moves the two numbers ε 2 can move, keeps the prior honestly at ε 0.5, plugs into the §4 simulator; risk: a diffuse prior makes it partly re-learn C3's regime mix.
2. R2-C.2 Piece-count router: a new route law (via points, loops) with an exact likelihood that fills the §4 router's loop gap; risk: matcher artefacts and few loops among matched trips.
3. R2-C.3 Paired twin-rank contrast: the only idea per-trajectory LDP cannot imitate even in principle, but a time-only module whose gain the benchmark barely sees.
