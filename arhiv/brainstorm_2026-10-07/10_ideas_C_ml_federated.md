# Ideas C: machine-learning and federated-learning lens

Brainstorm output, 7 Oct 2026, written from `.brainstorm/01_task.md` and `.brainstorm/00_briefing.md` only.

## 0. Shared ground for all four ideas

Terms: LDP local differential privacy; OD origin–destination; GRR generalized randomized response; OLH optimized local hashing; PM piecewise mechanism (Wang et al. 2019); Duchi = the one-bit mechanism for a bounded number (Duchi et al. 2018); MIA membership-inference attack; AR(1) first-order autoregressive noise; EM expectation–maximization; moment matching = choosing θ so that the model's feature averages equal the estimated ones; Laplace posterior = Gaussian approximation at the optimum.

**Users the fit sees.** Only the train split: about 91 users at u182, 25 at u50 and 10 at u20. Every design sends exactly one report per user.

**Dimension budget.** If each user sends one publicly sampled coordinate (of d) of a vector clipped to half-width w, via Duchi or PM, each population mean has standard deviation ≈ w·√(d·V(ε)/n), with V(1)≈4.7, V(2)≈1.7, V(4)≈0.24, V(8)≈0.03. A coordinate beats the public prior only if its true offset δ exceeds about two standard deviations, which needs n* ≈ 4·d·V(ε)·w²/δ² users. For n≈91 and δ≈0.6w that allows d≈1–2 at ε=1, 5 at ε=2 and 30 at ε=4; for n≈5,000 (a T-Drive train split) and δ≈0.3w it allows d≈25, 65 and 450. At u20 and u50 every idea is essentially the public prior for ε≤2.

**Public prior P0, the baseline to beat.** It is built from the map and fixed configuration only. Departure hour follows a fixed diurnal profile (local time is GMT+8); OD edges come from a gravity model over public zones weighted by road length and OSM class; the route follows a destination-directed link logit P(a | k, d) ∝ exp(−β·Δ(k,a,d) + θᵀψ(k,a)), where Δ is the extra cost of edge a over the public class-weighted shortest path to d and ψ holds the road class of a and the turn type. β and θ are eight parameters in total, instead of an edges-by-edges matrix. The distance field (one reverse Dijkstra per destination) does not depend on θ and is cached across all 17 MIA generators. Edge speed is v_class·exp(ρ), with ρ an AR(1) Gaussian along the path, and timestamps accumulate length/speed from the departure. The output is road-valid by construction: the sampler moves only to successor edges and finishes with the public shortest path at a public length cap. `sequence_log_prob` is log P(o, d) plus the summed log transition probabilities, floored at λ/|successors| with a jump term for map-matching gaps, so it is always finite. P0 is a shared component of size M.

**How noisy-update designs silently become trajectory-level.** One report per trajectory (LDPTrace, RN-LDP-Synth v1) costs m·ε for m trips. Clipping each trajectory and summing gives sensitivity m·C, so the user's average must be clipped instead. Repeated rounds with the same user cost T·ε under pure LDP, so iterative schemes need disjoint cohorts. A report whose presence, size or timing depends on the data leaks, so users without matched trips still send a randomized default. The question a user answers (coordinate, tree level, design point) must come from public randomness; clip ranges, grids and bandwidths come from configuration, never from train data; map-matching runs on the device.

**Estimand and evaluation.** On-device averaging weights every user equally, so the output describes the average user, not the trajectory pool that heavy Geolife users dominate. Each idea needs a "P0 only" arm, since the gain over P0 is the only evidence that private data was used. The MIA will almost certainly sit at chance for all four ideas, so the informative comparison is time-aware synthetic utility, which needs new unpaired departure-hour, duration and speed metrics.

### Idea 1: One-shot score tilt of the public prior
- **One-sentence pitch:** An exponential tilt p_θ ∝ P0·exp(θᵀφ) of the public prior, fitted from one report of per-user average statistics, so nothing grows with the map.
- **What each user computes locally:** The average over all own trips of x ∈ [−1,1]^d, d≈25: departure harmonics and weekend share (5), length and radial-distance terms (4), route scores, i.e. chosen-edge features minus their P0 expectation (8), and speed-ratio moments by road group and period (8), centred on P0 and clipped publicly.
- **What is randomized and how:** One publicly sampled coordinate j, weighted towards speed and length, is sent as (j, PM_ε(x_j)), or via Duchi at small ε; nothing composes.
- **What the server does:** Per-coordinate means feed a Gaussian posterior with the known noise variance, so weak coordinates revert to P0; moment matching fits departure, OD and speed exactly, and one Newton step from θ=0 fits the route logit.
- **How a synthetic trajectory is generated:** Departure, OD and route come from the tilted profile, gravity model and link logit (road-valid, §0); per-edge speeds, hence times, come from the fitted Gaussians with AR(1) noise.
- **Why it is user-level pure LDP:** x has a fixed range whatever the trip count, and PM is ε-LDP for any two inputs. Subtle only in code: j must be data-independent; users without trips send the prior.
- **Expected behaviour at n~180 vs n~10,000:** At n≈91 one (ε=1) to five (ε=2) coordinates move, the speed level first (likely far from P0: Geolife mixes walking, cycling and slow traffic); the rest stays P0. At n≈5,000 all 25 work at ε=1, plus ~100 spatial terms at ε≥2 (graph-eigenvector OD coefficients, low-rank turn terms on public edge embeddings).
- **Closest existing work and what differs:** Non-private maximum-entropy inverse reinforcement learning (Ziebart 2008) and recursive logit (Fosgerau 2013); non-interactive LDP learning from moments (Zheng et al. 2017); LDPTrace counts grid transitions per trajectory. A user-level, map-size-independent timed generator built from them appears new.
- **Implementation effort:** S–M beyond P0: features, PM, shrinkage, moment matching.
- **Main risk / failure mode:** Utility stays near P0 at n≈91; the one-step route estimate is biased if preferences are far from P0.

### Idea 2: Mixed-membership mobility regimes from one key–value report
- **One-sentence pitch:** Each user is a bag of trips from K public mobility regimes; one key–value report per user estimates regime shares and, with many users, per-regime corrections.
- **What each user computes locally:** Under K public variants of P0 (K=2–3 at n~180: walking/cycling, urban motor, fast motor), per-trip regime responsibilities averaged into w_u ∈ Δ_K, and per regime the weighted mean s_{u,k} ∈ [−1,1]^d of residual features; d=0 at n~180, 4–8 at n~10,000.
- **What is randomized and how:** Draw k ~ w_u and, if d>0, a public coordinate j and a bit b ~ Bernoulli((1+s_{u,k,j})/2); send GRR_ε(k), or GRR_ε(k,b) over 2K values (PCKV-style). Drawing is pre-processing; GRR spends all of ε.
- **What the server does:** Debiased frequencies give shares π̂_k and conditional means (f̂(k,1) − f̂(k,0))/π̂_k, shrunk with their known variance (∝ 1/π̂_k², so rare regimes stay public); regimes are then tilted as in Idea 1, and later EM steps use disjoint cohorts.
- **How a synthetic trajectory is generated:** Draw k ~ π̂; departure, OD, a road-valid link-logit route and AR(1) speeds then come from regime k. `sequence_log_prob` is log Σ_k π̂_k P_k(seq).
- **Why it is user-level pure LDP:** GRR is ε-LDP for any two inputs, and its input is a randomized function of the whole user dataset. Subtle: regimes and j must be public; one report per trip would be trajectory-level.
- **Expected behaviour at n~180 vs n~10,000:** At n≈91 (key only) a share has deviation ≈0.11–0.14 at ε=1 and ≈0.07 at ε=2, enough at ε≥2 for the slow-versus-motor split that shapes durations and speeds. Corrections need thousands of users (n≈5,000, K=3, d=4: ≈0.22 at ε=1, ≈0.10 at ε=2); T-Drive's regimes would be taxi states.
- **Closest existing work and what differs:** Key–value LDP (PrivKV, Ye et al. 2019; PCKV, Gu et al. 2020); federated mixtures (FedEM, Marfoq et al. 2021; iterative, no LDP). No LDP trajectory generator models users as timed regime mixtures.
- **Implementation effort:** M: K configured P0 instances, on-device E-step, GRR, M-step, mixture log-probability.
- **Main risk / failure mode:** Misspecified regimes (a bus with stops resembles a bicycle) bias the shares, which at ε≤1 are too noisy to reveal it.

### Idea 3: Hierarchical vote distillation onto a public trip library
- **One-sentence pitch:** Distil users' data into weights on a public library of road-valid timed trips, through one randomized vote per user at a random tree level.
- **What each user computes locally:** Public input: ~20,000 timed trips from a wide P0 and a tree over them (branching 4–6, depth ≤4, k-means on OD, departure hour, duration, length). The device soft-assigns its trips to leaves with a public kernel and averages them into q_u (at most 1,296 leaves).
- **What is randomized and how:** A public random level ℓ, a node v ~ q_u at ℓ, and the report (ℓ, OLH_ε(v)), with GRR on small levels; full ε.
- **What the server does:** Per-level debiased node frequencies, then top-down shrinkage of p(child | parent) towards P0's library masses by the known noise variance. At large n, disjoint cohorts vote on refined libraries.
- **How a synthetic trajectory is generated:** Sample a leaf, re-route one of its trips over the same OD by the link logit (road-valid), jitter departure and speeds within the leaf's bands. `sequence_log_prob` is log P0(seq) plus the log ratio of learned to public mass of its nodes.
- **Why it is user-level pure LDP:** The vote comes from the whole-month q_u through OLH, which is ε-LDP for any input. Library, tree and kernel are fixed by configuration; refined libraries may use only earlier cohorts.
- **Expected behaviour at n~180 vs n~10,000:** At n≈91 only level 1: 4–6 macro trip types with per-node deviation ≈0.15–0.18 (ε=1) or ≈0.08 (ε=2), a coarse reweighting. At n≈10,000 about 36 types (depth 2) at ε≥2, deeper only under heavy nodes.
- **Closest existing work and what differs:** Federated Private Evolution (PrE-Text, Hou et al. 2024) votes on a shared candidate bank with user-level central DP over several rounds; LDP hierarchical histograms (Cormode et al. 2019). New: pure LDP, one shot, level-sampled votes on timed road trips; arguably an LDP port of PrE-Text.
- **Implementation effort:** M–L: public library and tree, kernel assignment, OLH, tree shrinkage, variation step.
- **Main risk / failure mode:** Coverage: reweighting only selects what P0 proposed; at n≈91 few weights remain, and the log-probability is a coarse density ratio.

### Idea 4: One-bit likelihood-difference regression over simulator knobs
- **One-sentence pitch:** Each user scores one random public setting of a few P0 knobs against the reference with one randomized bit; regression on the design recovers the population likelihood surface.
- **What each user computes locally:** For the assigned setting θ_u of k knobs (e.g. speed multiplier, peak hour, length scale, planning weight on major roads; k≈2 at n~180): the per-edge average log-likelihood gain of own trips under P0(θ_u) over P0(θ_0), clipped to [−c, c]: a scalar for any map.
- **What is randomized and how:** Duchi sends one bit, scaled so that its mean equals the clipped scalar (PM at larger ε); the design index is public; full ε.
- **What the server does:** Debiased bits observe L(θ_u) − L(θ_0); Bayesian least squares fits a quadratic L (2k coefficients with diagonal curvature) whose maximizer θ̂ carries a Laplace posterior. Later cohorts get settings near θ̂.
- **How a synthetic trajectory is generated:** P0 runs at θ̂ (or a few posterior draws): knob-shaped departure profile, fitted length scale, road-valid link-logit route, speeds scaled by the multiplier with AR(1) noise.
- **Why it is user-level pure LDP:** The bit is a randomized function of a clipped whole-month statistic, and Duchi is ε-LDP on [−c, c]. Subtle: the device must not pick its setting, and adaptive designs may use only earlier cohorts.
- **Expected behaviour at n~180 vs n~10,000:** At n≈91 about one knob (ε=1) or two (ε=2), best spent on non-linear knobs Idea 1 cannot tilt, like the planning weight; at n≈5,000 six to eight knobs with full curvature at ε≥2.
- **Closest existing work and what differs:** POPri (Hou et al. 2025) improves a generator from clients' similarity feedback on synthetic samples, with aggregate DP, iteratively; DPZero-style zeroth-order methods are central; Zheng et al. (2017) send many polynomial coefficients per user. No LDP analogue turned up.
- **Implementation effort:** M: knob-parametrized P0 log-likelihood (Dijkstra fields cached on a public knob grid), design, Duchi, quadratic regression.
- **Main risk / failure mode:** User cost grows with the number of surface coefficients. A small c turns reports into signs, giving a median-type optimum, wrong for mixture-share knobs; a large c adds noise.

## Ranking
1. Idea 1 is best: one PM report, exact estimators for every exponential-family part, automatic fallback to P0 through the known noise variance, the lowest cost, and a backbone the others reuse.
2. Idea 2 adds what one tilt cannot express, the multimodal speeds and durations of a population mixing walking, cycling and motor trips; at u182 it learns only shares, and only at ε≥2.
3. Idea 4 is the most novel and the only one that fits knobs entering the model non-linearly, but its user cost grows quickly with the number of knobs.
4. Idea 3 represents joint space–time structure most freely, but needs thousands of users, depends on library coverage and is closest to published work.
5. Plan: build P0 and Idea 1 first, then add Idea 2's regime key and Idea 4's likelihood gain as further publicly sampled question types in the same one-report protocol, so they share users by sampling instead of splitting ε.

Sources checked (three searches): [LDPTrace](https://arxiv.org/pdf/2302.06180), [PrE-Text](https://arxiv.org/pdf/2406.02958), [POPri](https://arxiv.org/html/2504.16438v2), [Canaries in the Bank (federated Private Evolution audit)](https://arxiv.org/pdf/2609.13499). No LDP counterpart of Idea 1 or Idea 4 turned up.
