# Evaluation of candidates C1–C10

Sceptical evaluator, 7 Oct 2026. Read once each, and nothing else in the repo: `01_task.md`,
`00_briefing.md`, `20_candidates.md`, `30_novelty_C1.md`, `30_novelty_C2_C3_C4.md`,
`30_novelty_C5_to_C10.md`.

**Abbreviations.** LDP = local differential privacy: each user randomizes on the device and the
server is not trusted. ε = the privacy budget of one user for the whole collection window.
OD = origin–destination. GRR = generalized randomized response (send one of k categories). PM and
Duchi = standard mechanisms for one bounded number. MIA = membership-inference attack; LiRA = the
likelihood-ratio form the benchmark runs. JSD = Jensen–Shannon divergence. W1 = Wasserstein-1
distance between two one-dimensional distributions. RL = recursive logit, a route-choice model.
TPR / FPR = true / false positive rate. **Prior arm** = the same generator with no private reports
(ε → 0), built only from the map and cited constants. **Oracle arm** = the same estimator applied
to the users' exact statistics without noise (ε = ∞): a non-private ceiling for that model family.

## 0. What I checked before scoring

### 0.1 Novelty verdicts

The three reports confirm the summary I was given: NOVEL COMBINATION (medium confidence) for C1,
C2, C3, C4, C6 and C8, and CLOSE VARIANT (medium) for C5, C7, C9 and C10. Four qualifications in
the reports change the scores:

- **C1 rests on an unread paper.** GeoPM-DMEIRL (Huang et al., *FGCS* 2024: LDP perturbation
  followed by maximum-entropy inverse reinforcement learning) is paywalled, so it was judged from
  search snippets. If it randomizes per-user features rather than locations, C1 becomes a CLOSE
  VARIANT.
- **C2's estimation layer, taken alone, is a close variant of L-SRR** (CCS 2022). Only the
  gravity-coupled inversion combined with timed routing is new, and the report calls the
  contribution thin. The cordon variant (A.3) may overlap published ε-DP point-to-point traffic
  measurement.
- **C3 is novel only in its mixture-weight form** (B.4, C.2). The duel form (D.3) is a close
  variant of locally private hypothesis selection (Gopi et al., COLT 2020).
- **C6 and C8 are novel in a fragile place.** C6's novelty is a change of basis, and whether that
  basis is useful depends on an unchecked property of the Beijing graph. C8's novelty is an
  adaptive step that never runs at n ≈ 91.

### 0.2 Noise at the benchmark's real scale (recomputed)

The table gives the standard deviation of the debiased estimate. For a number (Duchi's mechanism)
it is a fraction of the half-width of the reporting range; for categories (GRR) it is in absolute
share units. n is the number of reporting train users.

| What is estimated | n = 10 (20-user rung) | n = 91 (182-user rung) | n = 5,000 (T-Drive train) |
|---|---|---|---|
| one number, every user answers it, ε = 1 / ε = 2 | 0.68 / 0.42 | 0.23 / 0.14 | 0.031 / 0.019 |
| one number, users split over 4 questions, ε = 1 / 2 | 1.37 / 0.83 | 0.45 / 0.28 | 0.062 / 0.038 |
| 3 shares, every user answers, ε = 1 / 2 | 0.36 / 0.14 | 0.12 / 0.048 | 0.016 / 0.006 |
| 9 shares (3 × 3 zones), every user answers, ε = 1 / 2 | 0.57 / 0.19 | 0.19 / 0.062 | 0.026 / 0.008 |

Three consequences:

1. **At the 20-user rung every candidate is its prior.** That rung is a smoke test, not evidence.
2. **At n ≈ 91, one or two numbers or one categorical question move at ε = 2, up to about eight
   numbers at ε = 8, and nothing at ε = 0.5** (corrected in the pushback round, point 1).
   The consolidator's warning holds for routes, turns, transitions and OD pairs. It does not hold
   in the few directions where the public prior is badly wrong:
   - the speed level and mode mix (free-flow car speeds from OpenStreetMap, OSM, against a
     Geolife population that also walks, cycles and takes buses);
   - the trip-length scale (a gravity prior on a 30 × 33 km map);
   - where trips start and end, at 3 × 3 resolution;
   - possibly the departure-hour profile.

   A number every user answers at ε = 1 has a standard deviation of 0.23 of its half-range, so it
   detects a prior error of about half the half-range or more. That is plausible for the speed
   level and unknown for the others. Criterion 3 therefore asks two things of each candidate: does
   it spend its users on those directions, and which metric would register the gain?
3. **At n ≈ 5,000 the budget buys about 10–25 numbers at ε = 1–2, not the "100+" some authors
   state.** 100 questions at ε = 2 give 0.19 per number, the precision of two questions at n = 91.
   T-Drive also records a fix only about every 3 minutes (from the dataset's own description, not
   the briefing). Its route statistics are therefore largely the map matcher's shortest-path
   interpolation between fixes. Large-n claims should rest on timing, OD and lengths, not on route
   tastes.

## 1. Scoring table

Each criterion is scored 1–5, higher is better. On criterion 5, 5 means small effort and low risk.
Totals are unweighted. `01_task.md` makes novelty a requirement, so I treat novelty ≥ 3 as a gate:
a CLOSE VARIANT cannot be picked, whatever its total.

| Candidate | 1 Novelty | 2 Privacy | 3 Gain over prior | 4 Fit | 5 Effort, risk | 6 Story | Total |
|---|---|---|---|---|---|---|---|
| C1 Behavioural-moment router | 4 | 5 | 4 | 4 | 3 (M) | 5 | **25** |
| C2 Gravity-regularized OD | 3 | 5 | 4 | 5 | 4 (S–M) | 3 | **24** |
| C3 Label vote over a catalogue | 3 | 4 | 3 | 5 | 4 (S–M) | 4 | **23** |
| C6 Graph-spectral field | 3 | 5 | 2 | 4 | 3 (M) | 3 | 20 |
| C5 Vote over a trip library | 2 | 5 | 3 | 4 | 4 (S–M) | 2 | 20 |
| C4 Activity anchors | 4 | 4 | 2 | 3 | 2 (M–L) | 4 | 19 |
| C9 Token n-grams | 2 | 5 | 2 | 4 | 3 (S–M) | 1 | 17 |
| C7 Likelihood-gain regression | 2 | 5 | 2 | 3 | 2 (M) | 2 | 16 |
| C8 Adaptive corridor sieve | 3 | 4 | 2 | 2 | 2 (M–L) | 2 | 15 |
| C10 Zone-flow oracle | 2 | 4 | 1 | 3 | 2 (M) | 1 | 13 |

Privacy hardly separates the candidates, because every one sends a single report through a
standard primitive. A privacy score below 5 marks a residual risk: a model structure written by
people who have seen Geolife, or a primitive that is easy to implement wrongly. It does not mean
the proof is broken.

### 1.1 Justifications

**C1 Behavioural-moment router**
- *Novelty 4.* An unpublished combination that solves the stated gap. The report's size does not
  grow with the graph, and the mechanism is user-level, timed and road-valid, with an exact
  likelihood. The score falls to 2 if GeoPM-DMEIRL randomizes per-user features.
- *Privacy 5.* Each user sends one publicly drawn coordinate of a per-user average clipped to a
  public box, through PM or Duchi at full ε. The proof is three lines and there is nothing to
  compose.
- *Gain 4.*
  - At n ≈ 91, two numbers are measurable at ε = 2, and more at ε = 8 (pushback round, point 1):
    the speed ratio to the OSM free-flow speed and the trip-length scale. The metrics are duration W1, mean-speed W1 and length W1.
  - Route tastes (detour temperature, road-class preference, turn penalty) stay at the prior for
    ε ≤ 2 and partly describe the matcher.
  - There is no spatial gain without C2's questions.
  - At T-Drive scale it can estimate speed factors per road class and period. Metrics: duration W1
    by departure hour, and per-class travel-time error.
- *Fit 4.* The Boltzmann-walk variant routes on a public reverse-Dijkstra cost-to-go (the remaining
  travel cost to the destination, computed by one shortest-path search back from it). That cost is
  cached once per map and shared by the 17 generators of an arm. The likelihood is finite only
  with a public floor probability at each step, which covers unreachable destinations, gaps
  between edges and the step cap. The exact-RL variants (A.1, B.1) need 17 sparse factorizations
  with private parameters per arm.
- *Effort M, 3–4 sessions.* Most likely failure: at n ≈ 91 only the speed and length numbers move,
  so the novel route-moment part shows nothing on Geolife.
- *Story 5.* The anchor contribution. It is the only candidate that addresses complete paths, time
  and the user-level unit at once.

**C2 Gravity-regularized OD inversion**
- *Novelty 3.* Novel as a combination, thin as a contribution because of L-SRR. Claim only the
  gravity-coupled inversion of user-level margins and its use as the demand side of a timed
  generator.
- *Privacy 5.* One item from a finite public domain (zone, cost band or period) through GRR or OLH
  (optimized local hashing).
- *Gain 4.*
  - At n ≈ 91 and ε = 2, it estimates 3 × 3 trip-end shares at ±0.06 if every user answers and
    ±0.10 if 40 % do, plus the distance decay.
  - The metrics are cell JSD (the only synthetic utility metric that already exists), length W1
    and a 3 × 3 OD JSD.
  - The gain shows only if Geolife's trip ends are concentrated inside the map relative to
    road-length mass. Nobody has checked this, and the map extent may already be cropped to
    Geolife.
  - At ε = 1 the nine shares are ±0.19, which is marginal.
  - At T-Drive it gives 36-zone margins at about ±0.03–0.04 (ε = 1) and per-period OD, the
    classic taxi application.
- *Fit 5.* The route term is public and identical across the 17 generators, so it is computed
  once. Only an OD table of at most 144 cells differs between them, and the gravity prior has full
  support.
- *Effort S–M, 2 sessions.* Most likely failure: trip ends are not concentrated enough, so there is
  no cell-JSD gain at ε ≤ 2.
- *Story 3.* It supplies the demand side the others lack, but it shares C1's estimator template:
  LDP margins or moments, then a maximum-entropy fit shrunk toward a public prior.

**C3 Label vote over a public behaviour catalogue**
- *Novelty 3.* Mixture weights over complete public generators, estimated from one user-level
  label, are unpublished. The duel form is published and must not be claimed.
- *Privacy 4.* The proof is one line: one label goes through GRR, and drawing that label from the
  user's posterior is local randomness. But people who have seen Geolife results write the whole
  model structure. "No data-dependent model structure" holds only if every catalogue constant is
  cited and frozen.
- *Gain 3.*
  - At n ≈ 91 it estimates three regime shares at ±0.12 (ε = 1) or ±0.05 (ε = 2), before
    deconvolution.
  - The gain shows in the shape of the duration and mean-speed distributions: a walk-versus-vehicle
    bimodality that no single speed number can fit.
  - Geography stays at the prior.
  - At T-Drive the story is weak: taxis are one mode, so the catalogue would have to be rewritten.
- *Fit 5.* Each catalogue member's probability of a candidate sequence is public. It is computed
  once (K times about 1,100 shortest-path trees per arm) and reused by all 17 generators; only the
  K weights differ.
- *Effort S–M, 2 sessions.* Most likely failure: misspecified regimes (a bus with stops resembles a
  bicycle) make the confusion matrix nearly flat, and deconvolution then amplifies the noise.
- *Story 4.* Structurally different from C1 and C2: it chooses within a model space instead of
  estimating moments. It is strongest where they are weakest, at small n and with multimodal
  travel.

**C6 Graph-spectral field**
- *Novelty 3.* The novelty is narrow: the change of basis and its per-mode bound.
- *Privacy 5.* The bound b_k comes from the public eigenvectors, and one PM slot is sent.
- *Gain 2.* Two to six modes at ε = 2, measured on cell JSD, but only if the low Laplacian modes of
  the Beijing graph cover the city. In real road graphs the low modes usually concentrate on
  dangling fringes, and the cosine fallback is Duchi's known estimator.
- *Fit 4.* Eigenvectors are cached by map hash.
- *Effort M.* Most likely failure: the modes are localized on fringes.
- *Story 3.* An alternative spatial question family to C2's zones, not a new axis.

**C5 Vote over a public trip library**
- *Novelty 2.* Private Evolution / PrE-Text with the noise moved onto the device.
- *Privacy 5.* One symbol from a frozen, hashed codebook.
- *Gain 3.* Four to eight archetype weights at n ≈ 91, on length W1 and departure-hour W1, with no
  geography at K ≤ 8. At T-Drive, 64–256 archetypes.
- *Fit 4.*
- *Effort S–M.* Low technical risk.
- *Story 2.*

**C4 Activity anchors and schedules**
- *Novelty 4.* The relation-only reports (D.4) were found nowhere.
- *Privacy 4.* One slot per user, but the long local pipeline of stay-detection thresholds invites
  tuning on Geolife, and B.3's home coordinate is the most identifying quantity in the whole set.
- *Gain 2.* About four slot marginals at n ≈ 91: the home centre at ±3–5 km (cell JSD) and
  departure means (departure-hour W1). A benchmark of unlinked trips cannot see coherent synthetic
  users, and T-Drive taxis have no home–work anchors.
- *Fit 3.* A closed-form mixture over legs for B.3 and D.4, only a surrogate for E.4.
- *Effort M–L.* Most likely failure: anchors are undefined with about nine matched trips per user.
- *Story 4.*

**C9 Token n-grams**
- *Novelty 2.* Only the alphabet is new.
- *Privacy 5.* One item from a 27-token domain.
- *Gain 2.* Road-class and manoeuvre unigrams plus one speed ratio: the same numbers C1 collects,
  with a weaker generator.
- *Fit 4.*
- *Effort S–M.* Most likely failure: without a destination pull the walks wander.
- *Story 1.* It is C1's route-style question family with a weaker generator, not a new axis.

**C7 Likelihood-gain regression**
- *Novelty 2.* A close variant of LDP Bayesian optimization (Zhou and Tan 2021).
- *Privacy 5.* One clipped number through Duchi's one-bit mechanism.
- *Gain 2.* One or two knobs, estimated from one-bit readings of a surface whose curvature is
  unknown. The estimate often lands on the edge of the design.
- *Fit 3.* Every device must evaluate likelihoods at its assigned setting, and the cache grows with
  the knob grid.
- *Effort M.*
- *Story 2.*

**C8 Adaptive corridor sieve**
- *Novelty 3.* The novelty is in the adaptive descent.
- *Privacy 4.* PCKV's split of the budget between key and value, and the batch rule, need care.
- *Gain 2.* There is only one batch at n ≈ 91, so it reduces to a 27-cell key–value histogram in
  which two or three nodes resolve; beyond that it cannot be told apart from the prior. At T-Drive
  it resolves corridors above 2–5 % with their speeds, so it is a T-Drive-only arm.
- *Fit 2.* Resampling a finite pool gives no natural finite likelihood for an arbitrary sequence.
- *Effort M–L,* plus a re-extraction of road names and refs.
- *Story 2.*

**C10 Zone-flow oracle**
- *Novelty 2.*
- *Privacy 4.* Exact sphere sampling in Duchi's ℓ₂-ball mechanism at dimension 69–2,000 is easy to
  get wrong.
- *Gain 1.* The per-arc standard deviation is 0.4 at ε = 2 against flows of 0.1–0.5, so below
  ε ≈ 4 it is provably the prior at every Geolife rung.
- *Fit 3.*
- *Effort M.*
- *Story 1.* The v1 / LDPTrace design made user-level, not a new axis.

## 2. Red team: C1, C2, C3, C6

C6 and C5 tie at 20. C6 takes the fourth slot because C5 fails the novelty gate.

### 2.1 Leaks common to all four, and one shared fix

- **Participation.** `fit` sees only users with at least one matched trajectory. In a real
  deployment, "sent a report" would therefore reveal "has a matchable trip". Every enrolled user
  must send exactly one fixed-size report, with a public default when they have no trips.
- **Device randomness.** Each user's random stream must not depend on their data (no seeding from
  `traj_id` or from trip content). Server code must never see it or be able to re-derive it.
- **Values before noise.** A user's statistic before randomization must never reach a log,
  `run.json` or a cache.
- **Floating point.** PM and Laplace outputs are snapped to a public grid; otherwise the low bits
  of the floating-point output can reveal the true value.
- **Time is never attacked.** The benchmark's MIA calls only `sequence_log_prob(edge_seq)`, which
  sees no timestamps. A departure density or speed model fitted on raw timestamps would be an
  unprotected release that no number in the benchmark would reveal.
- **The fix, one kit for every candidate.** Split each generator into two functions:
  `encode_user(views, public, rng) -> Report`, which returns a fixed-size, typed report, and
  `server_fit(reports, public) -> params`, which never receives views. Then add four tests:
  1. The fitted parameters stay identical when the raw views change but the reports are held
     fixed.
  2. A randomizer audit: the empirical log-ratio of output frequencies between two extreme users
     stays at most ε, within sampling tolerance.
  3. A canary user with an extreme trip.
  4. `sequence_log_prob` reads only the fitted parameters and caches keyed by map and
     configuration.

### 2.2 C1
- **(a) Where the budget leaks.**
  - Skipping a user on a question whose statistic is undefined for them, for example a user with no
    trip on that road class or in that period. Answering then reveals the class or the period.
    Undefined values must map to a public default inside the box.
  - Taking the speed reference or the clipping box from the training data, for example the train
    median speed instead of OSM `maxspeed` and configured class defaults.
  - In the multi-question mode at ε ≥ 4, sending k answers at ε each instead of ε/k each.
  - Letting users with more trips answer more questions.
  - Computing the public rule for the number of questions from the count of users who happen to
    have matched trips.
- **(b) Attack.** A "familiarity" or path-size term in the edge costs, computed from the training
  trips, is a standard route-choice device. It raises the step probability of members' own rare
  edges, and LiRA then separates members at low FPR, as it does for `markov`. A subtler version
  fills the cost-to-go cache only for destinations that occur in training. Non-member destinations
  then go through a fallback and get systematically different log-probabilities, so the set of
  cached destinations alone carries a membership signal.
- **(c) Closing it.** Edge costs come from map attributes and the fitted parameters only. The
  cost-to-go is computed lazily for any queried destination by one public function, on the same
  code path for members and non-members. Apply tests 1 and 4.

### 2.3 C2
- **(a) Where the budget leaks.**
  - Sending both ends of every trip costs m·ε for a user with m trips.
  - Placing zones, cost bands or periods at quantiles of the data.
  - Choosing the padding-and-sampling cap from the distribution of trips per user.
  - Using a gravity-decay "prior" fitted on Geolife.
  - In the cordon variant, sending a crossing count instead of the user's average rounded without
    bias to 0 or 1.
- **(b) Attack.** Choosing the node inside a zone by the empirical endpoint mass of the training
  trips instead of the public road-length mass. The node-given-zone term then spikes on members'
  exact start and end nodes, and `generate` re-emits trips that start at members' homes. This is
  memorization through the one non-public factor of an otherwise public likelihood.
- **(c) Closing it.** Within-zone mass, zones, bands, periods, the decay and the KL weight (the
  strength of the pull toward the gravity prior) all come from the map and the configuration, and
  are hashed into `params_hash`. The KL weight is never tuned by cross-validation on training data.
  Apply tests 1–4.

### 2.4 C3
- **(a) Where the budget leaks.**
  - Reporting the likelihood margin or the whole posterior vector instead of one label.
  - Setting catalogue constants (mode speeds, departure profiles, distance deterrence) or the number
    of regimes from the S4 Geolife statistics, or after looking at fits.
  - Building the deconvolution confusion matrix by classifying the actual training trips, instead
    of simulating it from the public members under a public trips-per-user law.
  - Choosing the D.3 challengers with the votes of the same cohort that then votes on them.
- **(b) Attack.** Adding a "realistic" catalogue member fitted on training trips, for example a
  Markov model over edges. The mixture log-likelihood then contains a memorizing component, and
  LiRA reads it directly.
- **(c) Closing it.** The catalogue holds only public models. Every constant is cited, and the
  catalogue is frozen by commit hash before any 182-user run. The confusion matrix is simulated,
  and reports carry only a label. Apply tests 1–4.

### 2.5 C6
- **(a) Where the budget leaks.**
  - Projecting node visit counts instead of the user's normalized distribution, so that the
    sensitivity grows with the number of trips.
  - Choosing the bound b_k, the number of modes or the question weights by looking at which modes
    fit Geolife.
  - Computing the eigenvectors on a subgraph pruned to the visited nodes.
- **(b) Attack.** Clipping the density to zero, or to a floor set from the data, on nodes that no
  training trip visits. Non-members who start elsewhere fall to the floor and members do not, so
  the support alone is a membership signal.
- **(c) Closing it.** The basis, the support (the largest connected component) and the floor come
  from the map. The number of modes and the question weights are a public function of n and ε.
  Apply tests 1–4.

## 3. Recommendation: C1, C3, C2

They are listed in priority order; the order of implementation is in §5.

### 3.1 C1, behavioural-moment router (start with the cacheable Boltzmann-walk variant)

- **Why.** It is the only candidate aimed at the whole research gap: complete paths with time,
  under a user-level unit. Its report size does not grow with the map, the privacy proof is three
  lines, the likelihood is exact, and the cache survives all 17 generators of an arm.
- **What it can defend.** The randomized object, a per-user average of route and timing statistics
  measured against a per-trip map reference, and the LDP moment-matching fit with known noise.
- **Its honest limitation.** At n ≈ 91 the measured gain will come from its simplest coordinates
  (speed level, trip length), so route tastes must be shown at large n.
- **Decide first:** the statistic list, and the public rule for how many questions are asked at
  each combination of n and ε. **Check first:** read GeoPM-DMEIRL in full.
- **In a paper:** "Moment-calibrated route-choice synthesis: each user sends one randomized
  coordinate of their map-centred route and timing averages, and the server fits a
  maximum-entropy road-network trip model with timed edges and an exact sequence likelihood."

### 3.2 C3, label vote over a public behaviour catalogue (mixture-weight form)

- **Why.** It is the only family that represents Geolife's mix of walking and vehicle trips, which
  no single speed number fits. That makes it the most likely to show a gain on duration and speed
  at n ≈ 91. It also has the cheapest benchmark fit, the lowest risk and a mechanism type different
  from C1's. Its uniform-weight form is the "public prior plus one label" baseline that every other
  arm must beat.
- **Its weaknesses.** T-Drive (taxis are one mode) and the objection that the catalogue is tuned. A
  cited, frozen catalogue answers the second, together with measuring the gain against C3's own
  uniform-weight arm.
- **Decide first:** the catalogue (three regimes at n ≈ 91) and its cited constants. **Check
  first:** whether the Beijing graph holds footways and cycleways. That decides whether the regimes
  differ in routes or only in speed.
- **In a paper:** "Locally private mixture voting: each user sends one randomized label over a
  frozen public catalogue of complete behavioural trip generators, and the server deconvolves the
  votes into mixture weights."

### 3.3 C2, gravity-regularized OD inversion (zone-margin form, no cordons)

- **Why.** Without it, no new arm moves cell JSD, the only synthetic utility metric that exists,
  and the joint start–end structure that v1 lacked stays at the prior. It is S–M, has the best
  benchmark fit and the strongest T-Drive story (taxi OD).
- **How to build it.** Its novelty is thin, so build it on C1's code path as the demand-side
  question family. Users are split publicly between the families, and every user still reports at
  full ε. Claim only the gravity-coupled inversion of user-level margins.
- **Decide first:** the zone grid (3 × 3 over the public map box), the cost bands and the periods.
  Drop the cordon variant because it overlaps ε-DP traffic measurement.
- **In a paper:** "Gravity-regularized origin–destination inversion: user-level LDP margins of trip
  ends and travel-cost bands, inverted through a road-network gravity prior, drive timed road-valid
  synthesis."

### 3.4 How the three read together

- **Complementary contributions.** The portfolio is behavioural (how people move: route and speed,
  C1), demand-side (where they go: OD, C2) and structural (which kind of traveller: regime mixture,
  C3).
- **Risk spread.** Low for C3, low to medium for C2, medium for C1.
- **One scale story for all three.** At small n the server can only choose among public hypotheses
  and correct a few first moments. The public rule for the number of questions then lets the same
  reports resolve more as n grows.
- **The honest weak spot.** C1 and C2 share one estimator template. Present the template once, and
  present the two as instantiations with different priors (fastest path versus gravity) and
  different metrics.
- **The likely final mechanism.** A composite arm that splits users across all three families
  costs no extra budget. The packaging was revised in the pushback round (point 3): one mechanism
  with three modules.
- **What is missing.** No pick is high-risk and high-novelty. C4 would be, but it cannot be
  measured in this benchmark (§6).

## 4. Open decisions, in the order they block work

1. **The public prior and its freeze.** Decide which sources count as public: OSM only, or OSM plus
   cited constants (speeds, departure profile, gravity decay, C3's catalogue). Freeze everything by
   commit hash before any 182-user run, because the designers have already seen Geolife numbers.
   Also decide on two kinds of prior arm: one common prior arm for comparing candidates, and each
   candidate's own ε → 0 arm for the claim that private data was used.
2. **The utility evidence.**
   - The reference is the held-out test users, not the train users.
   - Choose user-weighted or trip-weighted references. User-level estimators target the average
     user, while trip-weighted references are dominated by heavy users, so the wrong choice can
     make a working estimator look worse than its prior.
   - Pre-register the primary metrics.
   - Define the gain as the share of the prior-to-oracle gap recovered, with intervals over seeds
     and test users.
   - Drop, rather than report as failures, the metrics on which even the oracle does not beat the
     prior.
3. **The privacy unit inside the harness.**
   - Do all train users report, with a default for users who have no matched trip?
   - Do membership candidates enter the shadow fits as one-trajectory users or under their own
     `user_id`?
   - Is the number of questions fixed by configuration, so that target and shadows have the same
     model structure?
4. **Whether the MIA becomes time-aware.** The time model is the largest new private release, and
   today no attack touches it.
5. **ε grid and user allocation.** The public rule for the number of questions per family, the
   split of users between the C1, C2 and C3 families, and whether to build the composite arm.
6. **The route to large-n evidence.** A T-Drive loader (large, risky), a parameter-recovery
   simulation (small to medium), or both in that order. Without one, C1 and C2 cannot show anything
   beyond two to four numbers.
7. **Pass marks for utility,** agreed with the supervisor, and how existing per-trajectory
   mechanisms are converted to user-level ε (m·ε) in comparison plots.

## 5. Benchmark prerequisites

Effort per item; a session is one working block with the AI assistant.

| # | Prerequisite | Effort | Blocks |
|---|---|---|---|
| P0 | Verify the user plumbing. Check that every view passed to `fit` (target and shadows) carries a populated `user_id`, which ids membership candidates carry inside shadow fits, and whether unmatched trajectories reach `fit`. Check: a fixture test that asserts `all(v.user_id for v in train_views)` and that grouping by `user_id` gives the fixture's train users, and logs the candidates' `user_id`s inside one shadow fit | S (under 1 hour) | everything user-level |
| P1 | Timed synthetic payload: edge ids plus departure time and per-edge entry times, in local time UTC+8 (stated explicitly), serialized to Parquet | S | all three |
| P2 | Unpaired synthetic utility metrics in the orchestrator. Move cell JSD and length W1 out of `rnldp_eval`; add duration W1, mean-speed W1, circular departure-hour W1 and a 3 × 3 OD JSD; add a user-weighted option, the held-out reference and bootstrap intervals; update the results schema and its pinned doc | M (1–2 sessions) | all three |
| P3 | Shared public prior model: a probabilistic router with an exact, floored likelihood (a Boltzmann walk on a reverse-Dijkstra cost-to-go, which needs a compiled shortest-path routine for about 1,100 candidate destinations per arm); gravity OD on road-length masses; a departure prior; free-flow speeds per class times a public factor, with jitter; a cache keyed by map and configuration hash and shared by the 17 generators. With ε = 0 it is the prior arm; with the same estimator on statistics without noise it is the oracle arm. It is also the base of C3's catalogue | M (1–2 sessions) | all three |
| P4 | Privacy kit: the `encode_user` / `server_fit` split and tests 1–4 of §2.1 | S–M (1 session) | all three |
| P5 | Harness checks from decision 3, and the user-level ε recorded in `run.json` for every arm | S | membership runs |
| P6 | Parameter-recovery simulation: a synthetic population drawn from the prior at known parameters, n = 91 to 10,000, to show the large-n curve without new data | S–M | the scale claims of C1 and C2 |
| P7 | T-Drive loader: split week-long taxi traces into trips by public stop and gap rules, clip to the map box, match at about 3-minute sampling, split by taxi | L (2–4 sessions); risk: the matcher fails on sparse fixes | real-data large-n evidence |
| P8 | Optional time-aware MIA, with a likelihood that includes timestamps | M | decision 4 |
| P9 | Two one-hour checks: which highway classes the Beijing graph holds (C3), and the full text of GeoPM-DMEIRL (C1) | S | C1, C3 |

P0–P5 come before the first mechanism and cost about as much as one mechanism (4–6 sessions).
After them: C3 (2 sessions), C2 (2), C1 (3–4) and the composite arm (1).

## 6. What I would not do, and why

- **C10.** It is provably its prior at every Geolife rung: per-arc noise is 0.4 at ε = 2 against
  flows of 0.1–0.5. It is also a close variant of LDPTrace.
- **C9.** A close variant whose only novelty is the alphabet. At n ≈ 91 it duplicates C1's
  road-class and turn questions with a weaker generator. Keep the alphabet as a possible C1
  question family at T-Drive scale.
- **C5.** A close variant of Private Evolution. C3's uniform-weight arm already serves as the
  "public prior plus one vote" baseline.
- **C7.** A close variant of LDP Bayesian optimization, and less efficient than C1's moment
  matching for knobs that are exponential-family parameters.
- **C8, for now.** Its novelty sits in an adaptive descent that never runs at n ≈ 91. Resampling a
  pool gives no natural finite likelihood, and the corridors need a re-extraction of road names and
  refs. Revisit it only with T-Drive.
- **C4, for now.** It is novel, but a benchmark of unlinked trips cannot see coherent synthetic
  users. Anchors are undefined with about nine matched trips per user, and taxis have no home–work
  anchors. Keep D.4's relation-only reports as future work or a discussion item.
- **C6, unless checked first.** Run one eigenvector computation on the Beijing graph. If the low
  modes sit on fringes, C6 collapses to Duchi's cosine-basis estimator. If they cover the city, it
  may replace C2's zones as the spatial question family.
- **C1's exact recursive-logit variants as the first build.** Seventeen factorizations with private
  parameters per arm put the 300 s budget at risk; start with the cacheable walk.
- **Ranking by MIA numbers.** Every user-level arm sits at chance by construction
  (TPR ≤ e^ε · FPR). Even the non-private `markov` ceiling is weak: AUC 0.542 at u50, and TPR
  0.027 at FPR 0.01 at u182.
- **Overclaiming or tuning.** Do not claim route-taste learning at Geolife scale, do not tune any
  constant on Geolife, and do not treat the 20-user rung as evidence.
- **Reusing the `rn_ldp_synth` code as a template.** `01_task.md` excludes it.

## Pushback round

7 Oct 2026, answers to the coordinator's seven points. The picks stay C1, C3 and C2. The packaging
changes to one mechanism with three modules (point 3). §0.2, C1's gain line, §3.4 and §5 (new P0)
were corrected to match.

### 1. Variance accounting

You are right about my headline. The table in §0.2 did include the split penalty (d = 4 gives
0.45 / 0.28 with Duchi's mechanism), but the "2–4 numbers" I stated used d = 1. Below is the
standard deviation per coordinate at n = 91, as a fraction of the half-range. It uses the hybrid
mechanism (HM), which is better than Duchi's above ε ≈ 0.6. The first value is noise only; the
second adds a between-user spread of 0.4 of the half-range, which matters only at ε = 8.

| d (questions) | ε = 0.5 | ε = 2 | ε = 8 |
|---|---|---|---|
| 1 | 0.43 | 0.11 / 0.12 | 0.017 / 0.045 |
| 2 | 0.61 | 0.15 / 0.16 | 0.023 / 0.064 |
| 4 | 0.86 | 0.21 / 0.23 | 0.033 / 0.090 |
| 8 | 1.21 | 0.30 / 0.33 | 0.047 / 0.13 |

A gain needs a prior error of about two standard deviations.
- **ε = 0.5:** a 91-user run shows nothing.
- **ε = 2:** a gain shows only for d ≤ 2, with prior errors of about 0.3 of the half-range or
  more. d = 4 works only for a single error near 0.45. One categorical question also works: three
  shares at ±0.05 or nine at ±0.06 if every user answers, ±0.08 or ±0.11 if a third do.
- **ε = 8:** d ≤ 8 works for errors from 0.1 to 0.25.

So the honest answer is "ε = 8 for a small model, ε = 2 for one question family, never ε = 0.5".
It changes the thesis story in four ways:
- The Geolife evidence is a three-point curve. At ε = 0.5 the output equals the prior, which is
  the negative result LDP theory predicts. At ε = 2 one family is asked, so the C1-only, C2-only
  and C3-only arms form the ablation. At ε = 8 the small composite is asked.
- The public allocation rule must give all users to one module when n·ε² is small.
- User-level ε = 8 should be framed against the 4.5–18 that the per-trajectory arms (ε = 0.5–2)
  give a user with nine matched trips.
- C1's route moments become a large-n claim only (point 6).

No pick changes, but most of the measured Geolife evidence will come from C3 and C2 at ε = 2.

### 2. C2 versus C6

No swap.
- **(a) What each can estimate.** At n = 91, C2's single GRR question estimates all nine 3 × 3
  trip-end shares at once (±0.06 at ε = 2). A frequency oracle pays much less for more categories
  than coordinate sampling pays for more coordinates. C6 must send continuous coefficients one slot
  at a time, so at ε = 2 it resolves 1–2 coefficients at ±0.11–0.15 of their bound b_k, and only if
  the low modes span the city. At n = 10,000, C2 gives 36-zone margins and per-period OD with
  origin–destination coupling (for example morning-inbound versus evening-outbound asymmetry). C6
  gives 25–50 road-smooth modes of a single trip-end density, with only distance-decay coupling.
- **(b) Implementation risk.** C2 is GRR plus iterative proportional fitting, and its only risk is
  in the data. C6 risks eigenvectors that localize on fringes and truncated expansions that ring
  into negative densities. That risk can be decided in an hour from the public graph, so it is
  cheap to settle.
- **(c) Thesis diversity.** C6 is more diverse in method. C2 covers the demand-side axis: pairs of
  places, not just places.

If the eigenvector check passes, add "spectral modes versus zones" as a one-session ablation of
C2's spatial question.

### 3. Packaging

I now recommend one mechanism with three modules and one report schema, (module id, answer). A
public draw picks the module, and the user answers it at full ε. Splitting ε inside one report
would be worse: splitting it three ways costs about 3× the variance of splitting users at ε ≤ 2,
and 7.5× (numbers) to 85× (a three-way label) at ε = 8.
- **Privacy accounting.** One three-line proof and ε per user, with no composition. Three
  independent mechanisms run on the same users would cost 3ε by basic composition. They have
  "independent budgets" only if they are alternatives that are never released together.
- **Effort.** About the same as three separate mechanisms, because P3 already holds the composed
  trip model: C3's members are settings of C1's model, and C2 supplies the OD. Add one session for
  the allocation rule and the composite generator.
- **How a reviewer reads it.** One system with a public allocation rule and per-module ablations
  reads as a design. Three mechanisms that share a prior, a router and an estimator read as three
  flavours of one idea.
- **Measurement.** The registry still exposes C1-only, C2-only, C3-only and composite presets as
  separate arms.
- **Risks.** Coupling (one bug breaks every arm) and fewer countable contributions. Mitigate by
  shipping each module as its own arm before composing, and by claiming the evaluation method
  (prior and oracle arms, structural privacy audit) as a separate contribution.

### 4. Input plumbing

The briefing (§1) states that `fit` receives `TrajectoryView` objects exposing `user_id`. I did not
verify this in code. Three things remain unverified:
- whether `user_id` is populated for every view in both target and shadow fits;
- which `user_id` membership candidates carry inside shadow fits;
- whether trajectories that failed map matching reach `fit` at all.

These are now prerequisite P0. The check is a fixture test that asserts
`all(v.user_id for v in train_views)`, asserts that grouping by `user_id` gives the fixture's
train users, and logs the `user_id`s of the candidates inside one shadow fit.

### 5. GeoPM-DMEIRL fallback

If GeoPM-DMEIRL randomizes per-user features, three things remain:
- **The map-centred statistic.** Each trip is measured against the fastest path and the free-flow
  speed between its own endpoints, which narrows the public box: a box three times narrower needs
  nine times fewer users.
- **The time model,** which comes from the same single report.
- **The exact, floored sequence likelihood with road validity by construction,** which a deep
  reward with a policy network does not give.

The user-level unit also remains, if GeoPM works per trajectory. That is enough to lead only as the
behavioural module of the one-mechanism framework (point 3). As a standalone mechanism it would
read as "GeoPM-DMEIRL plus time" and should not lead. Title features: user-level, timed
road-network trips, map-centred moments — for example "User-level locally private synthesis of
timed road-network trips from map-centred moments".

### 6. Large-n evidence: the recovery simulation

- **Truth.** θ* is the oracle arm's fit on the u182 train users. It is used only to generate data,
  never as a prior or in a released model. Two public offsets of θ₀ are added, so the result does
  not depend on where Geolife happens to sit.
- **Synthetic users.** Each user's parameters θ_u are θ* plus the oracle-estimated between-user
  spread. Trips per user are resampled from the u182 distribution. Trips are generated by the
  shared model on the Beijing graph, road-valid and timed. The same `encode_user` and `server_fit`
  code runs as on real data.
- **Grid.** n = 10, 25, 91, 300, 1,000, 3,000 and 10,000; ε in {0.5, 2, 8}; at least 20 seeds per
  cell.
- **Measured.** Per-parameter error and the coverage of the reported intervals; the number of
  parameters whose interval excludes the prior; and the share of the prior-to-oracle gap recovered
  on the five utility metrics, against held-out simulated users.
- **Presentation.** One panel per metric, with n on a log axis and simulated bands per ε. The real
  u20, u50 and u182 values are overlaid as points with intervals. If the real points fall inside
  the bands, the simulation is validated where both exist, and its n = 10,000 end shows the same
  estimator on a Geolife-calibrated population.
- **Limits.** Add one misspecified run: simulate from C3's mixture and fit C1. State that
  map-matcher effects and taxi behaviour are not covered; those are what a T-Drive loader would add
  later.

### 7. Membership signal through `sequence_log_prob`

Yes. Three careless configurations re-introduce a signal:
- **C3:** a catalogue member, or regime constants, fitted on train trips.
- **C2:** within-zone node mass or gravity decay taken from train endpoints, which makes
  P(node | zone) spike on members.
- **C1:** familiarity or path-size edge costs computed from train trips, or a cost-to-go cache
  filled only for training destinations.

The guards:
- The catalogue, OD prior, zone masses, edge costs and cache keys are built from the map and the
  configuration, by constructors that accept no views.
- The `encode_user` / `server_fit` split, with tests 1 and 4 of §2.1.
- One deliberately leaky C1 arm as a positive control, to prove that the attack detects this class
  of leak.

AUC is not 0.5 by construction at ε = 8. With d = 4, one report can move a coordinate mean by up
to 0.09 of its half-range. So check that AUC does not fall as ε grows, instead of treating any
signal above chance as a bug.
