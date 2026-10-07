# R2-B ideas: whole synthetic users (brainstormer R2-B, 2026-10-07)

Terms as in `00_baseline.md`; EPR = exploration and preferential return (Song et al. 2010); "mode" = a
user's most frequent value (cell, corridor, daypart). All ideas reuse the plan §4.6 privacy argument,
the `encode_user`/`server_fit` split, the P3 public router and speeds, and the P4 privacy kit.

**Framing (read first).**
- Today's benchmark (P2 pooled trip metrics, per-trip MIA) sees a whole-user generator only through its
  single-trip marginal. Two kinds of user structure behave differently. Mixture latents (where or when a
  user is based: hub, corridor, habitual daypart) change that marginal, so a private estimate of them
  shows on unlinked metrics. Copy processes (how often a user repeats an earlier trip) leave it exactly
  equal to the base generator (proof in idea 3), so they are invisible to every unlinked metric and to
  the MIA.
- Mode principle (ideas 1 and 2). A habitual user puts a share h of its trip ends (or trips) on its
  mode. Under the same LDP noise, the user's mode carries about 1/h ≈ 2–3 times the signal of one
  sampled trip item for a place many users share (h ≈ 0.35–0.5 from the cited Zipf visitation law,
  González et al. 2008, Song et al. 2010), and the decoded trip-end share at that place has about h
  times the LDP SD, at the price of a public model for the other 1 − h. The estimand becomes "the
  distribution of habits plus one habit share", which is what a whole-user generator needs anyway.
- Noise (n = 91): OLH SD per value 0.41 / 0.089 / 0.0038 at ε 0.5 / 2 / 8 for any domain size;
  family-wise 5 % thresholds ≈ 3.0 SD over 36 values, 3.2 over 65, 3.7 over 400; HM and GRR from the
  baseline cheat sheet, scaled by √(91/n_group) under a user split.

## Idea 1. Habit modes: hub-and-return synthetic users ("report the habit, not a sample")
1. **Pitch.** Users report a habit (the modal cell of their trip ends, how strongly they return there,
   their modal departure daypart) instead of a sampled trip item; the server decodes habits into users
   who own a hub and return to it, and the sharper estimand shows on today's unlinked metrics.
2. **Report.** A public, data-independent draw picks one question; a frozen table in n·ε² sets the
   split (< 100: no question, prior arm; 100–2,000: all users on Q1 at 6×6; > 2,000: Q1 at 20×20, Q2,
   Q3 as 50/25/25). Q1: modal cell of the user's trip ends on a regular grid of the map's bounding box,
   OLH (safe fallback 3×3 by GRR; ablation: the land-use class holding most of its trip ends, 6 classes
   from a frozen OSM-tag table grouped as EULUC-China level I, GRR). Q2: habit share h_u = share of its
   trip ends in the modal cell, HM on [0, 1]. Q3: modal departure daypart, GRR over 6 Beijing-time
   dayparts. Ties use local randomness; a user without matched trips runs the same randomizer on a
   public default input. One value of ≤ 400 (plus the OLH seed) or one number.
3. **Privacy.** Plan §4.6 unchanged: public question draw; a standard ε-LDP primitive applied to a
   function of all the user's trips (local pre-processing and tie-breaking cannot break the e^ε ratio);
   one report, no composition, the rest post-processing. No ε split. Grid, class table, dayparts and
   the n·ε² table are frozen by commit hash before any Geolife run.
4. **Server.** π̂ = debiased OLH frequencies projected to the simplex; cells under the public
   family-wise threshold get public road-length mass instead (class ablation: π̂ = Σ_k ŝ_k μ_k with μ_k
   the road-length mass inside class-k OSM polygons); ĥ and daypart shares debiased and clipped.
   Public: kernel k_H for non-hub ends (road-length mass × exp(−distance/L), L from the cited
   radius-of-gyration law, González et al. 2008), prior h, diurnal prior, router, speeds. Synthetic
   user: hub cell H ~ π̂ (hub node by road-length mass); trip count from a public law or idea 3; each
   trip end is the hub with probability ĥ, else drawn from k_H; departure in the modal daypart with a
   public habit share, else from the diurnal prior; Boltzmann-walk route; per-segment times =
   free-flow × factor × jitter (P3).
5. **sequence_log_prob.** log P(O, D) + log P_route(seq | O, D) + public gap term, with
   P(O, D) = Σ_H π̂_H f_H(O) f_H(D), f_H = ĥ μ_H + (1 − ĥ) k_H (node distributions, no extra normaliser).
   The route term does not depend on H, so a query costs one cached walk plus a ≤ 400-term vector sum;
   no private factorization, no cache filled only for training destinations; time unused.
6. **Estimable at n = 91.** ε 0.5: nothing (OLH SD 0.41) → prior arm. ε 2 (all on Q1, 6×6 cells of
   ≈ 5 km): SD 0.089 and threshold ≈ 0.27, so a cell holding ≥ ~35 % of users' modes is kept (power
   ≈ 0.8), while the same cell holds only ĥ·f + background ≈ 0.19 of randomly sampled trip ends (2.1 SD,
   dropped): that gap is what a coherent user buys today. Fallback 3×3: 9 shares ±0.062; class
   ablation: 6 shares ±0.055. ε 8: 20×20 at SD 0.0055 (45 users) keeps every cell holding ≥ 2 users'
   modes; ĥ ±0.045 and 6 daypart shares ±0.1, both sampling-limited. Only at n = 10,000: 20×20 hubs
   with ≥ 4–5 % of users at ε 2, the kernel scale L as a fourth question, and a joint (hub × trip-count
   class) item that trip-weights heavy users' hubs.
7. **Closest.** A mobile-crowd-coverage paper (AAAI; search snippet only) has each user upload one
   frequently visited location under geo-indistinguishability: metric DP, no generator, no habit share.
   Acharya, Liu, Sun (AISTATS 2023) and Kent et al. 2024: user-level LDP with m samples from one shared
   distribution; here users differ and the estimand is the habit distribution. DP-WHERE 2013, OnTheMap
   2008: central DP, home/work. §4: C2 asks one sampled trip end (signal diluted by h) and inverts
   gravity on 3×3 zones; Q1 could be bolted onto C2, but only a whole-user decoder turns modes into
   trips. C3 votes over generator settings. C4 (B.3 home x/y by PM, E.4 home-zone slot, D.4 relations
   on public land-use densities): no semantics or stay detection, defined for m ≥ 1, the land-use class
   is a private report not a prior, and the gain shows on unlinked metrics, so Cond-C4 is not needed.
8. **Risk.** Geolife modes may not concentrate (no 5-km cell with ≥ 35 % of users, a hub split by a
   cell boundary, land-use classes unclustered or badly tagged in Beijing's OSM): then ε 2 equals the
   prior arm. ĥ is biased upward for users with 1–3 trips (corrected by simulation under the public
   trips-per-user law, as C3 does). k_H misplaces the 1 − h mass of users with a distant second place.
   At ε 8 single users' hubs are released, so the MIA may rise above chance (inside a vacuous e^8 bound).

## Idea 2. Corridor-loyal users: the modal named road as a route habit
1. **Pitch.** Users report the named OSM corridor their trips ride most (mode principle on routes) or
   how loyal they are to it; synthetic users inherit one habitual corridor and route through it with a
   loyalty share, so the private signal sits in the route likelihood that the MIA reads.
2. **Report.** Q1: modal corridor among a frozen list of 64 named corridors (OSM ways grouped by
   `ref`/`name`, highway ≥ secondary, longest first) plus "none" (no trip rides a listed corridor for
   ≥ 500 m), OLH over 65 values. Q2: loyalty λ_u = share of the user's trips riding its modal corridor
   for ≥ 500 m, HM. Public draw between Q1 and Q2 by a frozen table in n·ε².
3. **Privacy.** As idea 1; the list and the 500 m threshold are OSM plus a constant.
4. **Server.** π̂ over corridors (debias, threshold, the rest to "none"); λ̂ (public prior until
   estimated). Synthetic user: corridor c ~ π̂ or none; OD from the public demand or idea 1's hubs; with
   probability λ̂ a trip routes via one of c's ≤ 5 public waypoints w as two Boltzmann walks O→w and
   w→D, else the plain walk; times as in P3 with OSM maxspeed.
5. **sequence_log_prob.** log P(O, D) + log[(1 − λ̂ Σ_c π̂_c) P_walk(seq) + λ̂ Σ_c π̂_c |W_c|⁻¹
   Σ_{w ∈ W_c ∩ seq} P_walk(seq up to w) · P_walk(seq from w)] + gap term. The 320 waypoint cost-to-go
   vectors (≈ 15 s, ≈ 50 MB) are public, built once per map and config hash and shared by the 17
   generators; the sum runs over detected corridors only.
6. **Estimable at n = 91.** ε 0.5: nothing. ε 2 (all on Q1): SD 0.089, threshold ≈ 0.28 over 65
   values, so a corridor must be the mode of ≥ ~37 % of users; probably nothing → prior arm. ε 8
   (60/40): SD 0.005 releases essentially every training user's modal corridor; λ̂ ±0.045. Only at
   n = 10,000: corridors shared by ≥ 3–4 % of users at ε 2, λ per road class.
7. **Closest.** C8 (A.4: length-sampled road-hierarchy node + speed bit by PCKV, adaptive descent, pool
   raking without a finite likelihood) shares only the corridor target; here one batch, a user's mode
   instead of a length-sampled point, a loyalty share and an exact via-waypoint likelihood; Cond-C8 is
   not claimed. Yang et al. 2020 (hot paths, LDP + secret sharing, prefix trie), AHEAD 2021. §4: C1
   fits generic route tastes, never a named road. C4 has no route habits.
8. **Risk.** Map matching snaps to arterials, so modal corridors partly describe the matcher (lesson 4).
   At n = 91 the gain appears only at ε 8, where the MIA can also see members' corridors. Needs a new
   OSM name/ref export. "Via one waypoint" is a crude model of riding a road.

## Idea 3. Copy-process users: linked habits with an invariant single-trip marginal
1. **Pitch.** Synthetic users repeat earlier trips through a content-independent copy process
   (exploration–return over whole trips) calibrated by user-level reports on repetition and trip
   counts; each trip's marginal stays exactly the base generator, so the MIA and pooled metrics see no
   change, and the value is measured by user-level coherence metrics shipped with the idea. It meets
   Cond-C4 by supplying the metric, and it needs no anchors.
2. **Report.** Q1: repeat share r_u = 1 − (distinct OD cell pairs on the public 20×20 grid)/m_u, HM.
   Q2: trip-count class of m_u in {1, 2–4, 5–12, ≥ 13}, GRR. At ε 8 or large n also Q3 route loyalty
   (share of same-OD trip pairs with edge Jaccard ≥ 0.8) and Q4 time loyalty (share of same-OD pairs
   departing within ±1 h), HM; a user without a repeat sends a public default input.
3. **Privacy.** As idea 1; every statistic is a function of the user's whole trip set.
4. **Server.** Copy law: trip 1 is new; trip j starts a new habit with probability ρ·D^(−γ) (D = habits
   so far; prior ρ = 0.6, γ = 0.21, Song et al. 2010), else copies a habit chosen in proportion to its
   count. ρ is matched to the debiased mean of r by simulation on the public map under the base
   generator G and the estimated trip-count law (absorbs chance zone collisions and small m); λ and κ
   likewise. Synthetic user: m from the count law; each new habit is a fresh draw from G (public
   simulator, idea 1, or any trip generator including the §4 composite); a copy keeps O and D, keeps the
   route with probability λ else redraws it from G given the OD, keeps the departure hour with
   probability κ else redraws it from G; per-segment times are always redrawn (P3).
5. **sequence_log_prob.** Exactly log G(seq). Proof sketch: copy decisions depend on indices and counts
   only, never on trip content, so each trip equals the root of its copy chain, a draw from G, and
   partial redraws use G's own conditionals. Copy parameters never enter the per-trip likelihood: no
   new MIA surface, and pooled metrics equal the base's in expectation.
6. **Estimable at n = 91** (standalone on the public prior, split 60/40). ε 0.5: nothing → EPR
   constants and a public trips-per-user law. ε 2: mean r ±0.08, four trip-count shares ±0.11 → one
   copy parameter and a coarse count law. ε 8: r ±0.036, count shares ±0.08, plus λ. Only at
   n = 10,000: r per count class, λ per road class, κ.
   **Shipped metrics** (a P2 add-on plus a `syn_user_id` payload field): W1 of per-user repeat share,
   distinct-cell ratio, log trip count and radius of gyration, and the reach-to-volume ratio per 20×20
   cell (distinct users ÷ trips), synthetic users vs held-out test users with a user-level bootstrap.
   Unlinked releases are scored as "every trip its own user", so the metric prices unlinking.
7. **Closest.** EPR (Song et al. 2010), DITRAS (Pappalardo & Simini 2018), TimeGeo 2016, ASTRA
   (agenda-based EPR, search snippet): non-private. DP-WHERE 2013: central. Berke et al. 2022: no DP.
   The searches found no LDP-calibrated copy process. Per-zone "ever visited" bits resemble the
   presence-style reports of user-level LDP distribution estimation (Acharya et al. 2023, not re-read),
   so reach stays a metric. C4 (B.3, D.4, E.4): no anchors, stays or commute semantics; defined for
   m ≥ 2 (m = 1 gives r = 0); taxis give r ≈ 0 and the layer reduces to G. §4 releases unlinked trips.
8. **Risk.** Invisible on every current metric by construction, so worthless unless the coherence
   metrics are adopted; ≈ 36 held-out test users at u182 make per-user W1 noisy (useless at u20/u50).
   Copies cut the effective synthetic sample, inflating the finite-sample bias of pooled JSD unless many
   synthetic users are generated. Map matching inflates route loyalty. Users given to Q1–Q2 are lost to
   the base module (its SD × √(n/n_base)).

**Considered and dropped.** Private twins (each user releases one whole synthetic user drawn from
exp(ε/2 · clipped log-likelihood) × a public prior over user parameters): at ε 2 the tilt is at most e^1
across hundreds of parameter cells, so the true cell gets < 1 % of the mass; one GRR per coordinate
dominates it, and a GRR over a joint user template is D.3/C3. Reach-set users (one "ever visited zone z"
bit per user): ≈ 10 users per zone at n = 91, ±0.14 at ε 2, weaker than modes; kept only as a metric.

**Self-ranking.**
1. Idea 1: the only design here whose user structure shows on today's unlinked metrics (ε 2 if a shared hub exists, ε 8 surely); build it with idea 3 as its second module.
2. Idea 3: cheap, exact, zero MIA surface, meets Cond-C4; no gain at all without the shipped metric.
3. Idea 2: new route-level habit with an exact likelihood, but at n = 91 it shows only at ε 8 and partly measures the map matcher.
