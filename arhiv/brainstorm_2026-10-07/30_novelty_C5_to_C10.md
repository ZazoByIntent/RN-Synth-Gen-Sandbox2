# Novelty check: candidates C5–C10

Checked on 7 Oct 2026 against `.brainstorm/20_candidates.md` (C5–C10) and the constraints in
`.brainstorm/01_task.md`. Web searches used: C5 11, C6 8, C7 8, C8 9, C9 3, C10 3, plus page
fetches to confirm details of the closest papers. C9 and C10 got the deliberately shallow check
asked for.

**Abbreviations.** LDP = local differential privacy (every user randomizes on the device, nobody
is trusted). DP = differential privacy; *central DP* = a trusted curator adds the noise;
*distributed DP* = each client adds part of the noise and a secure-summation (secure aggregation)
protocol hides the individual reports, so one report alone is not private. GRR / OLH / OUE =
generalized randomized response / optimized local hashing / optimized unary encoding, the standard
LDP frequency oracles. PM = piecewise mechanism (LDP for one bounded number). PE = Private
Evolution. BO = Bayesian optimization. GP-UCB = Gaussian-process upper-confidence-bound search.
IPF = iterative proportional fitting (raking). OD = origin–destination. DPO = direct preference
optimization.

**Verdict scale (from the task).** EXISTS = the same mechanism is published; CLOSE VARIANT = a
published work differs only in a named detail; NOVEL COMBINATION = the pieces are published, their
combination for user-level LDP timed road-network synthesis is not; NOVEL = no close counterpart.

---

## C5: Vote over a public trip library

**Closest published works**

1. **Lin, Gopi, Kulkarni, Nori, Yekhanin — "Differentially Private Synthetic Data via Foundation
   Model APIs 1: Images" (Private Evolution, PE), ICLR 2024.** https://arxiv.org/abs/2305.15560
   - What it does: draws candidate samples from a public generator; every private record votes for
     its nearest candidate in an embedding space; the vote histogram gets Gaussian noise (central
     DP) and is thresholded; the next generation is resampled in proportion to the noisy votes;
     repeated over several iterations.
   - Collision / difference: D.1's step "one own trip, mapped to the nearest public archetype,
     counted" is PE's nearest-neighbour vote. C5 differs only in where the noise is added (GRR/OLH
     on the device, one symbol per user, pure ε-LDP) and in running a single round without PE's
     variation step.
2. **Lin, Baltrusaitis, Wang, Yekhanin — "Differentially Private Synthetic Data via APIs 3: Using
   Simulators Instead of Foundation Models" (Sim-PE), ICLR 2025 workshop.**
   https://arxiv.org/abs/2502.05505
   - What: the same PE loop with a non-neural simulator (for example a graphics renderer) as the
     source of candidates.
   - Collision / difference: C5's library "generated from the map alone" (gravity OD, shared
     router, public departure prior) is a simulator in exactly this sense. The differences are
     again the noise model (central DP there) and the domain (timed road trips).
3. **Hou et al. — "PrE-Text: Training Language Models on Private Federated Data in the Age of
   LLMs", ICML 2024.** https://arxiv.org/abs/2406.02958
   - What: federated PE. Each client counts, over the server's synthetic samples, how many of its
     own records have each sample as nearest neighbour, adds Gaussian noise, and the server sees
     only the securely summed histogram; user-level (ε, δ) distributed DP over several rounds
     (T = 11 in their experiments).
   - Collision / difference: already user-level and already "the client votes, the server
     resamples". C5 drops secure aggregation (each report is private on its own), sends one
     discrete symbol instead of a noisy vector, and runs one round. These are exactly the changes
     the brief requires, but they are a detail of the same mechanism, not a new one.
4. **Jia, Gong — "Calibrate: Frequency Estimation and Heavy Hitter Identification with Local
   Differential Privacy via Incorporating Prior Knowledge", INFOCOM 2019.**
   https://arxiv.org/abs/1812.02055
   - What: combines LDP frequency estimates with a public prior over item frequencies (a Bayesian
     posterior) to reduce error.
   - Collision: D.1's server step "shrink toward the library's own archetype masses" is this idea;
     C5 adds nothing new on the estimation side.
5. **Du et al. — "LDPTrace: Locally Differentially Private Trajectory Synthesis", PVLDB 2023.**
   https://arxiv.org/abs/2302.06180
   - What: per-trajectory LDP; OUE reports of grid-cell transitions, begin/end transitions and
     length; Markov synthesis.
   - Difference: C5 votes over whole timed trips from a public library, not over cell transitions,
     and is user-level. LDPTrace is the trajectory-LDP baseline any write-up must compare with.

**Verdict: CLOSE VARIANT.** The detail that differs from PE / PrE-Text: the noise is moved onto
the device (GRR/OLH over K archetypes, one symbol per user, no secure aggregation) and only one
round is run (no PE variation loop). The C.3 tree version adds LDP hierarchical frequency estimation
with users assigned to random levels, which is also standard (AHEAD under C8; the hierarchical
histograms of Cormode et al. 2019 named by the authors were not opened here).

**Confidence: medium.** I searched for an LDP version of PE three ways (PE with LDP, PE with
randomized response, PE for trajectories) and found none; the newest PE paper found (Tab-PE, Tran
et al., June 2026, https://arxiv.org/abs/2606.08259) is central DP. Not verified: federated or
industrial reports that run PE-style voting under pure LDP without calling it PE, and whether any
mobility paper has used a map-only simulator library.

**Must-cite:** Lin et al. 2024 (PE); Lin et al. 2025 (Sim-PE); Hou et al. 2024 (PrE-Text); Du et
al. 2023 (LDPTrace).

---

## C6: Graph-spectral low-pass field

**Closest published works**

1. **Duchi, Jordan, Wainwright — "Minimax Optimal Procedures for Locally Private Estimation",
   JASA 2018.** https://arxiv.org/abs/1604.02390
   - What: an LDP density estimator by orthogonal series. Each user evaluates the first K functions
     of a bounded orthonormal basis (trigonometric or Walsh) at its data point, privatizes that
     vector with a bounded-vector mechanism, and the server averages the vectors to estimate the
     coefficients, truncating at K.
   - Collision / difference: C6's local step (project the user's node distribution on the first K
     basis vectors, bound coefficient k by b_k, privatize, average) is this estimator. What changes
     is the basis: road-graph Laplacian eigenvectors instead of a Euclidean basis on an interval,
     plus a one-slot PM report instead of the vector mechanism. Duchi's construction relies on a
     uniformly bounded basis; graph eigenvectors can concentrate on small parts of the graph, which
     is the one new technical question.
2. **Chedemail, de Loynes, Navarro, Olivier — "Large Graph Signal Denoising with Application to
   Differential Privacy", IEEE Transactions on Signal and Information Processing over Networks
   2022.** https://arxiv.org/abs/2209.02043
   - What: central DP (Gaussian mechanism) on taxi pick-up counts at the nodes of the Manhattan road
     graph built with OSMnx, followed by denoising in a spectral graph wavelet frame with James–Stein
     thresholding x·max(0, 1 − t²/x²).
   - Collision / difference: C6's server rule ĉ_k·max(0, 1 − σ_k²/ĉ_k²) is the same James–Stein
     shrinkage, applied to a location density on an OpenStreetMap road graph. Differences: there the
     noise is added centrally to node counts and the basis is a wavelet frame; C6 privatizes the
     spectral coefficients on the device and uses the Laplacian eigenbasis.
3. **Butucea, Dubois, Kroll, Saumard — "Local differential privacy: Elbow effect in optimal density
   estimation and adaptation over Besov ellipsoids", Bernoulli 2020.**
   https://arxiv.org/abs/1903.01927
   - What: LDP density estimation from Laplace-perturbed wavelet coefficients with adaptive
     selection; argues that localized (wavelet) bases beat global Fourier-type bases.
   - Difference: Euclidean domain. Relevant as a warning: Laplacian eigenvectors are a global basis,
     which may suit a concentrated density such as Geolife's poorly.
4. **Takagi, Cao, Asano, Yoshikawa — "Geo-Graph-Indistinguishability: Location Privacy on Road
   Networks Based on Differential Privacy", DBSec 2019.** https://arxiv.org/abs/2010.13449
   - What: location privacy measured by shortest-path distance on the road graph; a graph
     exponential mechanism perturbs each reported location.
   - Difference: perturbs individual locations; estimates no population density and uses no
     spectral basis.

**Verdict: NOVEL COMBINATION.** The pieces are Duchi's orthogonal-series LDP estimator (local
step) and graph-spectral James–Stein denoising of road-graph location counts (server step, central
DP in Chedemail et al.). I found no paper that privatizes graph-Fourier coefficients on the device.
What the combination gives that neither piece gives: a user-level LDP spatial density that is
smooth along the road network rather than across the plane, with the number of resolved modes set
automatically by the noise level. The contribution is narrow (the basis swap and its per-mode bound
b_k); the 2-D cosine fallback named in the candidate is plainly Duchi's estimator and would not
count.

**Confidence: medium.** Searches covered LDP with graph Fourier transforms or graph signals, DP
graph signal processing on road networks, LDP orthogonal-series density estimation, and LDP
location distributions on road networks. Not verified: non-English venues. The critique's
feasibility worry (low eigenvectors of the Beijing graph concentrating on dead-end clusters, which
would make b_k large) is a computation to run on the graph, not a literature question.

**Must-cite:** Duchi et al. 2018; Chedemail et al. 2022; Butucea et al. 2020.

---

## C7: One-bit likelihood-gain regression over prior knobs

**Closest published works**

1. **Zhou, Tan — "Local Differential Privacy for Bayesian Optimization", AAAI 2021.**
   https://arxiv.org/abs/2010.06709
   - What: black-box optimization in which the learner picks a query point, the user asked at that
     point returns a reward perturbed locally (LDP, Laplace-type mechanisms), and the learner fits a
     Gaussian-process surrogate (GP-UCB variants) to find the maximizer; regret upper and lower
     bounds.
   - Collision / difference: C7's structure — the server assigns a setting θ_u, the user evaluates a
     bounded number there and privatizes it, the server fits a surrogate and moves later cohorts
     toward its maximizer — is LDP Bayesian optimization. The differences: the objective is the
     user's clipped per-edge log-likelihood gain of a public trip model at θ_u over a baseline θ₀
     (so the fitted θ is a private, approximate maximum-likelihood fit of the prior's knobs); the
     surrogate is a quadratic, not a Gaussian process; Duchi's one-bit mechanism replaces Laplace
     noise; users come in batch cohorts rather than one per round.
2. **Liebenow, Peinemann, Mohammadi — "DP-Hype: Federated Differentially Private Hyperparameter
   Search", PoPETs 2026.** https://arxiv.org/abs/2510.04902
   - What: each client evaluates every candidate hyperparameter on its own data, sets a k-hot vote
     for its k lowest losses, adds Gaussian noise, and a single secure summation releases the totals
     (client-level distributed DP).
   - Difference: needs secure summation (one report alone is not private) and has every client
     evaluate all candidates and vote, instead of one randomly assigned setting plus a regression
     surface. The pattern "evaluate a public setting on your own data, report it privately, let the
     server choose" is the same.
3. **Ding, Nori, Li, Allen — "Comparing Population Means under Local Differential Privacy: with
   Significance and Power", AAAI 2018.** https://arxiv.org/abs/1803.09027
   - What: LDP A/B testing: users in randomly assigned groups send locally privatized bounded values
     and the server tests the difference of means.
   - Collision / difference: public random assignment of users to settings plus an LDP mean per
     setting is C7's data-collection design; C7 extends it from a few arms to a continuous design
     with a fitted response surface.
4. **Hou, Wang, Zhu, Lazar, Fanti — "POPri: Private Federated Learning using Preference-Optimized
   Synthetic Data", ICML 2025.** https://arxiv.org/abs/2504.16438
   - What: clients score server-generated synthetic samples against their private data; the
     privatized scores become preference pairs for DPO fine-tuning of the generator, over several
     rounds.
   - Difference: tunes a large language model under aggregate (not pure local) DP; C7 tunes one or
     two knobs of a public parametric model under pure LDP. Same idea of steering a synthetic-data
     generator with private client feedback.
5. **Zheng, Mou, Wang — "Collect at Once, Use Effectively: Making Non-interactive Locally Private
   Learning Possible", ICML 2017.** https://proceedings.mlr.press/v70/zheng17c.html
   - What: one-shot LDP learning in which users send privatized basic statistics of their data and
     the server approximates loss gradients by a Chebyshev expansion.
   - Difference: users report features of their data, not loss values at assigned parameters; it is
     the alternative route a write-up of C7 must argue against.
6. **Xiong, Ju, Zhang — "Simulation-based Bayesian Inference from Privacy Protected Data", arXiv
   2023 (revised 2025).** https://arxiv.org/abs/2310.12781
   - What: infers simulator parameters from DP-protected releases with approximate Bayesian
     computation and neural density estimators.
   - Difference: works from released DP statistics, not from per-user evaluations at assigned
     settings; another way to calibrate the same public prior.

**Verdict: CLOSE VARIANT.** The detail that differs from LDP Bayesian optimization (Zhou & Tan): the
reward is the user's own log-likelihood gain of a public trajectory model, and the surrogate is a
quadratic instead of a Gaussian process. The author's statement "no LDP analogue found" does not
hold: optimization from locally privatized evaluations at server-chosen points is published.

**Confidence: medium.** Not verified: whether LDP zeroth-order or LDP bandit methods have already
been used specifically to fit generative or simulation models (none found in eight searches); the
LDP bandit literature was not reviewed in depth.

**Must-cite:** Zhou & Tan 2021; Liebenow et al. 2026 (DP-Hype); Ding et al. 2018; Hou et al. 2025
(POPri).

---

## C8: Adaptive road-corridor sieve with key–value reports

**Closest published works**

1. **Du, Zhang, Bai, Liu, Ji, Cheng, Chen — "AHEAD: Adaptive Hierarchical Decomposition for Range
   Query under Local Differential Privacy", CCS 2021.** https://arxiv.org/abs/2110.07505
   - What: builds the LDP hierarchy adaptively. Users are split into groups, one group per tree
     level; a node is split further only if its noisy frequency passes a threshold; post-processing
     makes the tree consistent.
   - Collision / difference: C8's "batch b expands the children of nodes above 3σ in batch b − 1"
     plus tree-consistent least squares is AHEAD's adaptive descent. Differences: AHEAD's tree is
     over a numeric (or multi-dimensional numeric) domain and its nodes carry no value; C8's tree
     is a public road hierarchy (zone × class group, then named corridors, then 1 km pieces) and
     each report carries a speed bit.
2. **Gu, Li, Cheng, Xiong, Cao — "PCKV: Locally Differentially Private Correlated Key-Value Data
   Collection with Optimized Utility", USENIX Security 2020.** https://arxiv.org/abs/1911.12834
   - What: each user pads and samples one of its key–value pairs, then perturbs key and value
     (value discretized to ±1) with correlated randomized response; estimates key frequencies and
     per-key means with an optimized budget split.
   - Collision / difference: C8's report (key = hierarchy node, value = rounded log speed ratio ±1)
     is PCKV used as published; PCKV has a flat, fixed key domain and no adaptivity.
3. **Yang, Tjuawinata, Lam, Zhao, Sun — "Secure Hot Path Crowdsourcing with Local Differential
   Privacy under Fog Computing Architecture", IEEE Transactions on Services Computing 2020.**
   https://arxiv.org/abs/2012.13807
   - What: finds frequent road paths with a trie grown iteratively: sampled groups of workers report
     prefix extensions and low-count prefixes are pruned; LDP combined with additive secret sharing
     through fog nodes.
   - Difference: adaptive, user-partitioned refinement of road structures under LDP is published
     here, but over path prefixes, without speeds, and not as pure LDP (secret sharing).
4. **Balioglu, Khodaie, Taweel, Gursoy — "Grid-Based Decompositions for Spatial Data under Local
   Differential Privacy", arXiv 2024** (https://arxiv.org/abs/2407.21624), **and Alptekin (advisor
   Gursoy) — "Hierarchical spatial decompositions under local differential privacy", Koç University
   thesis 2024**
   (https://research.hub.ku.edu.tr/entities/publication/6d638d74-02b2-4c86-829b-3ff8ace2aaef).
   - What: adaptive grids (PrivAG, AAG), quadtrees and kd-trees for spatial density under LDP.
   - Difference: geometric cells, no road-class or corridor nodes, no attached values.
5. **Rameshwar, Tandon, Gupta, Singh, Chakraborty, Sharma — "Mean Estimation with User-Level Privacy
   for Spatio-Temporal IoT Datasets", arXiv 2024.** https://arxiv.org/abs/2401.15906
   - What: user-level DP release of mean bus speeds from traffic data, for users with different
     numbers of samples.
   - Difference: central DP; relevant only as the user-level speed-statistics neighbour.
6. **Jia, Gong — Calibrate, INFOCOM 2019.** https://arxiv.org/abs/1812.02055
   - Collision: C8's "unresolved nodes keep the prior split" is a cruder form of prior-informed LDP
     frequency estimation.

**Verdict: NOVEL COMBINATION.** The pieces are AHEAD-style adaptive descent over disjoint user
batches, PCKV key–value reports, and IPF raking of a public candidate pool (raking to DP margins is
standard in central-DP synthetic data, e.g. https://arxiv.org/abs/2206.01362). I found no paper that
runs an adaptive LDP hierarchy whose nodes carry a numeric value, and none whose hierarchy is built
from road classes and named corridors. What the combination gives that neither piece gives: speed
means resolved at whatever depth of the road hierarchy the data supports, whereas AHEAD gives no
values and PCKV gives values only over a fixed flat domain. Caveat from the candidate's own
critique: at n ≈ 91 there is a single batch, so the adaptive step, which is where the novelty sits,
never runs; the novelty can only be shown on T-Drive.

**Confidence: medium.** Not verified: hierarchical key–value LDP under another name (one targeted
search found none); Chinese-language LDP traffic-speed papers; whether IPF raking of a public trip
pool to LDP road-volume shares has been published.

**Must-cite:** Du et al. 2021 (AHEAD); Gu et al. 2020 (PCKV); Yang et al. 2020 (hot paths);
Balioglu et al. 2024 (LDP spatial grids).

---

## C9: Manoeuvre × road-class token n-grams (shallow check, 3 searches)

**Closest published works**

1. **Cunningham, Cormode, Ferhatosmanoglu, Srivastava — "Real-World Trajectory Sharing with Local
   Differential Privacy", PVLDB 2021.** https://www.vldb.org/pvldb/vol14/p2283-cunningham.pdf
   - What: perturbs overlapping n-grams of a trajectory under LDP, using a public multi-dimensional
     hierarchy built from place-of-interest data and reachability constraints to keep the output
     realistic, then reconstructs a perturbed trajectory.
   - Collision / difference: n-gram units, public external knowledge and semantic generalization of
     tokens are published. Differences: the tokens are places, the output is each user's perturbed
     trajectory (per-trajectory privacy), and no population n-gram model is estimated; C9 uses
     location-free move tokens (turn × road class) and estimates a population bigram.
2. **Du et al. — LDPTrace, PVLDB 2023.** https://arxiv.org/abs/2302.06180
   - What: OUE reports of grid-cell transitions (up to a length quantile L_k per trajectory, budget
     ε₂/L_k each), begin/end transitions and length; first-order Markov synthesis.
   - Collision / difference: "frequency oracle over a pair domain, then a first-order generator" is
     C9's estimator. C9 changes the alphabet and samples one move per user at full ε (user-level).
3. **Zheng, Hu — "TraCS: Trajectory Collection in Continuous Space under Local Differential
   Privacy", PoPETs 2026.** https://arxiv.org/abs/2412.00620
   - What: TraCS-D perturbs the direction and distance of each location in continuous space.
   - Difference: per-point direction perturbation for data collection; no road classes and no
     generative model.

**Verdict: CLOSE VARIANT.** The detail that differs: the alphabet. The LDP transition (n-gram)
frequency oracle, back-off smoothing and Markov generation follow LDPTrace and Cunningham et al.;
only the manoeuvre × road-class tokens and the tilting of a public random walk on the graph are new.

**Confidence: medium** (shallow check). Not verified: non-private turn × road-class Markov route
generators (the author suspected one exists; not searched further); follow-ups of Cunningham et al.
after 2023.

**Must-cite:** Cunningham et al. 2021; Du et al. 2023 (LDPTrace); Zheng & Hu 2026 (TraCS).

---

## C10: Conservation-consistent zone-flow oracle (shallow check, 3 searches)

**Closest published works**

1. **Du et al. — LDPTrace, PVLDB 2023.** https://arxiv.org/abs/2302.06180
   - What (checked in the paper's text): each trajectory reports its length, its transitions between
     grid cells, and begin/terminate transitions to a virtual start and end cell; synthesis samples
     a length L and extends the walk until it reaches the virtual end cell or length L.
   - Collision / difference: zone transitions with explicit start and stop states, and a
     first-order walk that ends at an end state, already exist. C10's differences: the report is
     the user's averaged unit-flow vector over all trips (user-level, Duchi's ℓ₂-ball mechanism)
     instead of per-trajectory OUE reports; several zone levels; a flow-conservation projection;
     and no separate length cap.
2. **Hay, Rastogi, Miklau, Suciu — "Boosting the Accuracy of Differentially Private Histograms
   Through Consistency", PVLDB 2010.**
   https://people.cs.umass.edu/~miklau/assets/pubs/social/hay2010boosting.pdf
   - What: least-squares constrained inference that makes noisy hierarchical counts consistent, as
     post-processing.
   - Collision: C10's cross-level sums and weighted least squares are this technique, applied to
     flows.
3. **Pan — "A Consistent Differential Privacy Dynamic Trajectory Flow Prediction Method" (CDP-DTP),
   Engineering Reports 2025.** https://api.crossref.org/works/10.1002/eng2.70159
   - What: Laplace-noise DP on a trajectory flow graph with a consistency-constraint adjustment,
     followed by CNN-LSTM forecasting.
   - Difference: central DP and forecasting, not LDP synthesis. The publisher page returned HTTP 403,
     so whether its constraint is node-level flow conservation is not confirmed.
4. **Tsao, Gopalakrishnan, Yang, Pavone — "Differentially Private Stochastic Convex Optimization for
   Network Routing Applications", arXiv 2022.** https://arxiv.org/abs/2210.14489
   - What: observes that flow-conservation constraints expose sources and sinks, and moves the OD
     data into the objective to optimize routing with DP stochastic gradient descent.
   - Difference: central-DP routing. Relevant as a reminder that conservation constraints reveal
     origins and destinations; C10 applies them only as post-processing of private output, which is
     safe.
5. **Duchi, Jordan, Wainwright — JASA 2018.** https://arxiv.org/abs/1604.02390
   - Source of the ℓ₂-ball (and ℓ∞) vector mechanisms C10 uses for the user-level flow vector.

**Verdict: CLOSE VARIANT.** The detail that differs from LDPTrace: its transition-plus-end-state
design with the per-trajectory transition reports replaced by one user-level ℓ₂-ball report of the
averaged flow vector, and a consistency (flow-conservation) projection that lets the walk drop the
length cap. Each change is a standard primitive (Duchi's vector mechanism, Hay et al.'s consistency
post-processing, a random walk built from conserved flows).

**Confidence: medium** (shallow check). Not verified: whether RetraSyn (real-time LDP trajectory
synthesis, https://arxiv.org/abs/2404.11450) uses entering/leaving states with a conservation-like
constraint; CDP-DTP's exact constraint.

**Must-cite:** Du et al. 2023 (LDPTrace); Hay et al. 2010; Pan 2025 (CDP-DTP); Duchi et al. 2018.

---

## Summary

| Candidate | Verdict | Confidence | Closest work |
|---|---|---|---|
| C5 | CLOSE VARIANT | medium | PE (Lin et al. 2024), PrE-Text (Hou et al. 2024), Sim-PE (Lin et al. 2025) |
| C6 | NOVEL COMBINATION | medium | Duchi et al. 2018 + Chedemail et al. 2022 |
| C7 | CLOSE VARIANT | medium | Zhou & Tan 2021 (LDP Bayesian optimization) |
| C8 | NOVEL COMBINATION | medium | AHEAD (Du et al. 2021) + PCKV (Gu et al. 2020) |
| C9 | CLOSE VARIANT | medium | LDPTrace (Du et al. 2023), Cunningham et al. 2021 |
| C10 | CLOSE VARIANT | medium | LDPTrace (Du et al. 2023) |

What this means in practice: none of C5–C10 clears the novelty bar of `01_task.md` on its own. Only
C6 and C8 are unpublished combinations, and both are fragile. C6's novelty is a change of basis
whose usefulness depends on an unchecked property of the Beijing road graph. C8's novelty sits in an
adaptive step that does not run at Geolife scale.
