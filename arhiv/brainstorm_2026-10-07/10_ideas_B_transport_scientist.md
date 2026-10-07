# Ideas B: transportation-scientist lens

Four user-level local differential privacy (LDP) generators, one per classical paradigm of
travel-demand modelling: disaggregate choice models (Idea 1), aggregate entropy/gravity models
(Idea 2), activity-based models (Idea 3) and latent-class segmentation (Idea 4). At n≈180 almost
all realism has to come from public structure (the road graph and published behavioural
knowledge); the ideas differ in where they spend the few private bits: route taste, travel
demand, daily schedules, or behavioural segment shares. Shared machinery is defined once below
so that each idea stays short.

## Shared building blocks (used by all four ideas)

**Public graph features.** Free-flow time `t0_e = length_e / v0(class_e)` (OSM `maxspeed` or a
class default). "Minor" roads are residential, service and unclassified. Each consecutive edge
pair gets a turn type from geometry (straight, right, left, U-turn; China drives on the right, so
left turns cross oncoming traffic). Public nested zones: 3×3, 6×6 and 12×12 grids over the map.
The *skim* `c_ij` is the transport term for the zone-to-zone travel-cost matrix, here free-flow
shortest-path minutes between zone centroids. Mass proxies are road lengths per zone (activity
proxy: primary to tertiary roads; residential proxy: residential roads). OD means
origin–destination.

**RL(β): link-based recursive logit route choice** (Fosgerau, Frejinger and Karlström 2013;
equivalent to maximum-entropy inverse reinforcement learning, MaxEnt IRL). The utility of entering
successor edge a from edge k is `v(a|k) = β·x(a|k)` with x = (free-flow minutes, minor-road
minutes, left turn, U-turn, 1 per link). With `M[k,a] = exp v(a|k)` and `b_d[k] = 1` when edge k
ends at destination d, the value vector solves `(I − M) z_d = b_d`: one sparse LU (lower–upper)
factorization of `I − M` per β, then one cheap back-substitution per destination, and
`P(a | k, d) = M[k,a] z_d[a] / z_d[k]`. Sampling walks this chain from the origin until it exits
at d (a public step cap with a shortest-path finish stops rare long loops), so **every synthetic
path is a connected edge sequence of the real graph by construction**. `sequence_log_prob` is the
exact sum of log transition probabilities, finite for every connected path; a gap between
non-adjacent edges is bridged by its shortest path at a fixed public penalty. A public box on β
keeps the spectral radius of M below 1, so the value functions exist; estimates are projected onto
it. When β is public, every RL quantity is identical across the 17 generators of a membership arm
and is computed once and cached.

**S: timing module.** Five local-time periods (UTC+8): night, morning peak, midday, evening peak,
late evening; the departure time is uniform inside the drawn period. Segment time
`t_e = t0_e · exp(r + δ[class, period] + σ_w·z_e)`, with z_e a truncated standard normal. Here r is
the trip's log time ratio (log of observed duration over the free-flow duration of the matched
path), drawn from a three-regime mixture (motorised, cycling-like, walking-like; regimes defined by
public thresholds on r, with public within-regime distributions); δ and σ_w are public priors.
Timestamps are the departure time plus cumulative segment times, and the payload is a list of
(edge id, entry time) pairs. Every idea needs the new unpaired duration and speed metrics. The
current membership attack ignores time, but the timing parameters are covered by the same ε.

**LDP arithmetic.** `fit` groups the training views by `user_id`, and each user sends exactly one
report: a question is drawn on the device with public probabilities and answered with the full ε
(above ε≈5, ⌊ε/2.5⌋ questions with a split budget, as Wang et al. 2019 recommend). Numeric answers
use the Piecewise or Hybrid Mechanism (PM/HM, Wang et al. 2019) on a value clipped to a public
interval; the per-user noise standard deviation is about 4.4 / 2.0 / 0.9 / 0.1 half-ranges at
ε = 0.5 / 1 / 2 / 8. Categorical answers describe one uniformly sampled own trip (or trip end) and
use k-ary randomized response (k-RR) or optimized local hashing (OLH, Wang et al. 2017); the OLH
per-bin standard deviation with all 180 users answering is about 0.30 / 0.14 / 0.06 / 0.003. A
question answered by only n/K users has √K times that error. Rule of thumb at n≈180: ε ≤ 1 buys
1–3 scalars at ±0.15–0.35 half-ranges; ε = 2 buys about five scalars, or one 6–8-category
distribution at ±0.04; ε = 8 buys 10–15 scalars or 16–36-bin histograms (the sampling of users,
not privacy noise, then dominates). At n≈10,000 every error shrinks by √(10,000/180) ≈ 7.5. All
estimators are sums of per-report terms, so later submissions (new privacy units) update them
incrementally.

**Privacy pattern.** A report is an ε-LDP randomizer applied either to a deterministic, publicly
clipped function of all the user's trips, or to one trip picked with data-independent local
randomness. Because `P(y | x) ≤ e^ε P(y | x')` for any two inputs, a mixture over the user's trips
obeys the same bound, so the whole user is protected at ε however many trips they have. LDP
protects the content of a report, not participation; a user with no usable trip answers for a
public default input. Zones, bands, clipping bounds, priors and question probabilities come from
the map and fixed configuration, never from the data.

---

### Idea 1: Transfer-and-update recursive logit (score reports)
- **One-sentence pitch:** A literature-based travel model (destination logit plus RL route choice) is updated by one Bayesian Newton step computed from users' randomized likelihood-score coordinates.
- **What each user computes locally:** At the public prior θ₀, per own trip: the RL score (observed minus expected free-flow minutes, minor-road minutes, turns, links) divided by the OD's shortest free-flow time, and the deterrence score `c_od − E[c|o]`. g_u is the clipped mean over trips; K = 3 at n≈180, 6–8 at n≈10,000, independent of graph size. Unlike personal fits, scores stay unbiased even with two trips.
- **What is randomized and how:** One of five equiprobable questions: a g_u coordinate by PM, or a sampled trip's period or speed regime by k-RR.
- **What the server does:** Unbiased mean ĝ; Jacobian J of the expected score, precomputed by simulating prior-model trips; `θ̂ = θ₀ + (Σ₀⁻¹ + JᵀV⁻¹J)⁻¹JᵀV⁻¹ĝ` (V: answer variance, Σ₀: prior covariance), projected onto the RL box. Optional later batches re-score at θ̂.
- **How a synthetic trajectory is generated:** Origin by public mass, destination zone ∝ mass·exp(β̂_c c_od), departure from period shares, path simulated from RL(β̂), times by S.
- **Why it is user-level pure LDP:** One ε-randomizer on a clipped function of all the user's trips. Subtle but harmless: the bound holds for any scoring point, even one the server picks adversarially.
- **Expected behaviour at n~180 vs n~10,000:** n≈180, ε = 2: 36 answers per question, scores known to ±0.15 half-ranges, so coefficients move only on clear evidence; ε ≤ 1 returns θ₀, with routes still realistic. Degradation: fewer coordinates, shrinkage. n≈10,000: turn, expressway, per-period and regional coefficients, taste variances (mixed logit).
- **Closest existing work and what differs:** MaxEnt IRL routing (Ziebart et al. 2008), non-private; LDP risk minimization (Duchi et al. 2018), generic; transfer updating (Atherton and Ben-Akiva 1976); routing from DP-perturbed trajectories (*Mathematics* 2024). Together they give estimation from few trips per user plus road-valid timed generation; not found.
- **Implementation effort:** M–L: sparse RL solver, J simulation, PM/k-RR, S; one factorization per generator for log-probabilities.
- **Main risk / failure mode:** At n≈180 the output is the prior, so utility rests on transferring foreign coefficients; map-matching artefacts and T-Drive's sparse GPS bias scores toward the matcher's routing.

### Idea 2: Entropy-gravity demand from LDP margins
- **One-sentence pitch:** Spend the whole budget on demand: the server rebuilds the joint OD matrix as the maximum-entropy matrix consistent with users' randomized trip ends, trip-cost bands and the public skim.
- **What each user computes locally:** Own shares of trip ends over Z zones (9 at n≈180, 36–144 at n≈10,000) and of trips over six skim bands, five periods and three speed regimes: Z + 14 numbers, independent of graph size.
- **What is randomized and how:** One question about one sampled own trip (end): zones 0.4 by OLH; bands, periods, regimes 0.2 each by k-RR. Optional trip weighting by padding-and-sampling with a public cap.
- **What the server does:** Debiased targets t̂ with known covariance V; `T = argmin KL(T‖Q) + ½‖AT − t̂‖²_{V⁻¹}`, with Q the public gravity prior on the 144-zone skim and A mapping T to trip-end margins (origins equal destinations, as daily travel is symmetric) and band shares; solved by three-dimensional Furness scaling (proportional fitting over rows, columns and cost bands).
- **How a synthetic trajectory is generated:** Period, zone pair from T, nodes by public mass, RL path with literature coefficients (no budget), S timing.
- **Why it is user-level pure LDP:** One answer about one locally sampled trip gives ε for the whole user by the mixture argument, padding included. Subtle: zones, bands, prior and cap must be fixed without the data; fitting is post-processing.
- **Expected behaviour at n~180 vs n~10,000:** n≈180, ε = 2: 9-zone margins ±0.10 (72 answers), band shares ±0.09 (36): only coarse corrections, but the skim supplies joint start–end structure. Degradation: coarser zones. n≈10,000: 36-zone margins ±0.03 at ε = 1, per-period margins, free per-band deterrence.
- **Closest existing work and what differs:** Wilson's (1967) entropy gravity, Evans and Kirby's (1974) tri-proportional fitting, Cascetta's (1984) least-squares OD estimation, all non-private; L-SRR (LDP OD collection, 2022); gravity from DP phone data (NBER). Adds the joint OD that RN-LDP-Synth v1 lacks; moderate novelty.
- **Implementation effort:** S–M: skims, frequency oracles, regularized fitting; public RL cached.
- **Main risk / failure mode:** At n≈180 the OD is mostly the public mass proxy, missing Geolife's north-west Beijing cluster unless ε ≥ 2; trips are independent; routes are never learned.

### Idea 3: Anchor-and-tour activity synthesis
- **One-sentence pitch:** Model each user as a daily schedule (home, main place, leave and return times), collect one randomized fact about it, and synthesize timed home–activity–home tours on the graph.
- **What each user computes locally:** Public rules give home h (most frequent first origin or last destination of a local day), main anchor w (most frequent daytime non-home end, else h) and median leave and return times τ₁, τ₂. Seven items, independent of graph and zones: home x and y, log commute distance, commute direction toward the centre (cosine), τ₁, τ₂, speed regime.
- **What is randomized and how:** One item (home 0.4, commute 0.3, times 0.2, regime 0.1): PM on a public interval, or k-RR for the regime.
- **What the server does:** Home density: residential mass times a Gaussian envelope fitted to the LDP moments. Work choice `P(w|h) ∝ A_w exp(−β c_hw + κ cos θ_hw)`, with β and κ fitted to the LDP means (Hyman-style calibration). Normal schedules; published motif shares (Schneider et al. 2013).
- **How a synthetic trajectory is generated:** Per person: anchor nodes, home-to-work trip at τ₁, return at τ₂, optional evening trip; RL paths, S timing; emitted unlinked. Log-probability: closed-form OD mixture over trip types times RL path probability.
- **Why it is user-level pure LDP:** Shared pattern; anchors, the most identifying quantity (Golle and Partridge 2009), never leave the device unrandomized. Subtle: anchor rules are public; a missing anchor is encoded deterministically.
- **Expected behaviour at n~180 vs n~10,000:** n≈180, ε = 2, 18–36 answers per item: home centre ±3 km, commute length and direction, two departure means; morning-out, evening-back coupling comes from structure. Degradation: public spreads and motif shares. n≈10,000: home-zone histogram, regional deterrence, pattern shares, schedule spreads.
- **Closest existing work and what differs:** Activity-based models (Bowman and Ben-Akiva 2001); central-DP activity-diary generation (Badu-Marfo, Farooq and Patterson 2020); OnTheMap's central-DP commute flows (Machanavajjhala et al. 2008). Not found under LDP; adds a time-coupled, user-level OD.
- **Implementation effort:** M: anchor extraction, PM moments, two-parameter calibration, tour sampler; public RL cached.
- **Main risk / failure mode:** About nine matched trips per user give noisy anchors; Geolife users are atypical; T-Drive taxis have no home–work anchors, so n≈10,000 needs a taxi-shift variant.

### Idea 4: Latent-class behavioural archetypes
- **One-sentence pitch:** Each user reports one randomized label: which of K public behavioural archetypes (route taste, speed regime, departure profile, trip length) best explains their trips; the server deconvolves the shares and samples the mixture.
- **What each user computes locally:** The log-likelihood of all own trips under each archetype k (public RL coefficients, speed regime, period profile, deterrence); k_u is drawn from the uniform-prior posterior. K = 6 at n≈180 (walker, cyclist, peak commuter, off-peak driver, expressway-loyal driver, bus-like), 24–48 at n≈10,000 with region and weekday factors.
- **What is randomized and how:** k_u by k-RR (K ≤ 8) or OLH, with the full ε; everybody answers the same question.
- **What the server does:** Observed labels pass the true shares through the classification channel C, then the LDP channel; C is simulated once from the catalogue on the public graph (public trips-per-user assumption); expectation–maximization returns the shares.
- **How a synthetic trajectory is generated:** Draw k; origin by public mass, destination by k's deterrence, departure from k's profile, path from RL(β_k), S timing with k's regime. Log-probability: `log Σ_k π̂_k P_k(trip)`.
- **Why it is user-level pure LDP:** One label through an ε frequency oracle; posterior sampling uses local randomness. Subtle: the catalogue must be fixed from public knowledge beforehand; tuning it on Geolife would be an unprotected release.
- **Expected behaviour at n~180 vs n~10,000:** n≈180, ε = 2: label shares ±0.04 (±0.11 at ε = 1) before the misclassification correction inflates them; they carry joint structure (walkers' short, slow, minor-road trips) that per-coordinate reports lose. Degradation: fewer classes. n≈10,000: 48 classes plus within-class score updates (Idea 1).
- **Closest existing work and what differs:** Latent-class choice models (Greene and Hensher 2003), labelled route choice (Ben-Akiva et al. 1984), generic LDP clustering or codebook quantization. New: a generative road-network codebook with simulated confusion correction, giving joint heterogeneity at n≈180.
- **Implementation effort:** M: catalogue YAML, K public RLs, simulated C, EM; per-trip likelihoods cached, so the membership attack is cheap.
- **Main risk / failure mode:** Utility is capped by the catalogue; with few trips per user C is nearly flat; at n≈180 space comes only from the public mass proxy.

## Ranking
1. **Idea 1 is my top pick:** it alone learns how people use the road network, gives exact path likelihoods for the membership attack, stays unbiased with few trips per user, falls back smoothly to its public prior, and grows its dimension with n (a natural fit for T-Drive's taxi drivers).
2. Idea 2 is the best first build: smallest effort and probably the largest effect on spatial metrics at n≈180; its demand module should become Idea 1's origin–destination side (same one-question split and ε, fewer answers per question).
3. Idea 4 extracts the most private information per user at n≈180 and keeps joint mode–route–time structure, but its realism is capped by a hand-made catalogue.
4. Idea 3 has the richest temporal structure, but it is Geolife-specific and spreads 180 users over seven questions.
5. At ε ≤ 1 and n≈180 every idea returns essentially its public prior, so the experiment should report how far each posterior moved from the prior, in prior standard deviations.

## Sources (the three novelty searches)
- [DP-perturbed trajectories for optimal routing, *Mathematics* 12(19):2977, 2024](https://ideas.repec.org/a/gam/jmathe/v12y2024i19p2977-d1485391.html)
- [Recursive route choice estimation with incomplete trip observations (non-private)](https://arxiv.org/pdf/2204.12992)
- [L-SRR: LDP for location-based services, including OD collection](https://arxiv.org/pdf/2209.15091)
- [Central-DP publication of OD matrices with intermediate stops](https://arxiv.org/pdf/2202.12342)
- [Hybrid distributed/local DP OD estimation, *Electronics* 13(22):4545](https://www.mdpi.com/2079-9292/13/22/4545)
- [Gravity model estimated from privacy-protected mobile data (NBER chapter)](https://nber.org/system/files/chapters/c15022/c15022.pdf)
- [Badu-Marfo, Farooq and Patterson: DP deep generation of activity diaries](https://arxiv.org/pdf/2012.14574v1)
