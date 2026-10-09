# Novelty check G3: T5 and T6 (round 3, 2026-10-09)

Checker G3. Tools: WebSearch (standard and extended mode) and WebFetch on arXiv and ar5iv pages; no rate limit was hit. Works marked "abstract only" were judged from the abstract or a fetched excerpt, not the full text. Bracketed derivations are mine, not taken from a source.

## T5 Metric-gradient report

### Queries run (13)
1. "local differential privacy" "energy score" OR "scoring rule" gradient calibration (extended mode)
2. McKenna Miklau Hay "workload" optimal strategies "local differential privacy" linear queries 2020
3. "local differential privacy" "simulation-based inference" OR "likelihood-free" OR "approximate Bayesian computation"
4. Steinberger "Efficiency in local differential privacy" two-step one-step estimator (+ WebFetch of the arXiv HTML)
5. Duchi Ruan "The right complexity measure in locally private estimation" Fisher information one-step (+ WebFetch of §4.4, §5.2 and §6 of the ar5iv text)
6. "locally private" OR "local differential privacy" "kernel mean embedding" OR "maximum mean discrepancy" OR "energy distance" synthetic data generator
7. "differential privacy" "energy score" OR "CRPS" OR "proper scoring rule" generative model training private
8. "local differential privacy" "experimental design" OR "optimal query" OR "query design" Bayesian prior one-dimensional projection estimation
9. "local differential privacy" simulator calibration OR "agent-based model" OR "traffic simulation" parameters gradient
10. DPZero OR "DP-ZO" private zeroth-order optimization scalar directional derivative random direction
11. "local differential privacy" "M-estimation" OR "empirical risk minimization" one round non-interactive gradient Newton step; Ramesh Han Avella-Medina Rush "user-level local differential privacy" M-estimation
12. "locally differentially private" "Cramér distance" OR "CRPS" OR "energy distance" OR "Wasserstein" gradient one report per user
13. Reference lookups: Pacchiardi Dutta "scoring rule" "energy score" likelihood-free; Chaloner Verdinelli "Bayesian experimental design: a review"

### Closest works
| # | Reference | What it does | Precise difference from T5 |
|---|---|---|---|
| 1 | Duchi & Ruan, "The Right Complexity Measure in Locally Private Estimation: It is not the Fisher Information", Ann. Statist. 52(1), 2024; https://arxiv.org/abs/1806.05756, DOI 10.1214/22-AOS2227 | §5.2.2-5.2.3: one-step corrected estimator. A pilot cohort (about n^(2/3) users) gives θ̃; every later user releases ONE Laplace-noised projection of its sufficient statistic on the influence direction ∇ψ(θ̃)ᵀ∇²A(θ̃)⁻¹ of a target functional ψ; the server makes one Newton-type correction. §6 (flow cytometry) runs it with coordinate directions ψ(θ) = e_jᵀθ | Item-level; exponential-family or GLM log-likelihood score, not a simulator energy score; pilot from a first cohort instead of a public θ₀; direction fixed by one target functional, not designed from a benchmark loss under a prior. Structurally it is T5's report plus T5's Newton step, and §6 is R3-C1's "public knob coordinate" default |
| 2 | Steinberger, "Efficiency in local differential privacy", Ann. Statist. 2024 (journal listing); https://arxiv.org/abs/2301.10600 | Two-step efficient LDP MLE: a first group gives a preliminary estimate; the second group's channel is designed (a linear programme over private channels on a discretised statistic) to maximise Fisher information at that estimate; MLE on the sanitised data | Designs the whole channel for asymptotic efficiency at a data-driven pilot; T5 designs only which scalar to send, for a benchmark loss, at a public point and with no first cohort |
| 3 | McKenna, Maity, Mazumdar, Miklau, "A workload-adaptive mechanism for linear queries under local differential privacy", PVLDB 13(11), 2020; https://arxiv.org/abs/2002.01582, DOI 10.14778/3407790.3407798 | Optimises the LDP strategy (the randomiser) for a given workload of linear counting queries, minimising expected total squared error by projected gradient descent; one round, unbiased reconstruction | Linear counting queries over a discrete item domain and no prior; R3-C3 picks one direction of a nonlinear loss (squared Cramér as the W1 surrogate) under a Bayesian misspecification prior Σ₀. The shared idea is "derive the question from the analyst's workload". The consolidator's flag is confirmed as the nearest LDP precedent for R3-C3, but it is not a match |
| 4 | Zhang et al., "DPZero: Private Fine-Tuning of Language Models without Backpropagation", arXiv 2310.09639 (NeurIPS 2023 workshop version); Tang et al., "Private Fine-tuning of Large Language Models with Zeroth-order Optimization", TMLR 2025, arXiv 2401.04343 | Only the scalar directional derivative of the loss along a public random direction is privatised (clip plus noise), because the direction itself carries no data | Central DP, many rounds, random direction, record-level; T5 is user-level local, one shot, one public or designed direction |
| 5 | Pacchiardi, Khoo, Dutta, "Generalized Bayesian likelihood-free inference", Electron. J. Statist. 18(2), 2024, DOI 10.1214/24-EJS2283 (arXiv 2104.03889); Zhou, Zheng, Ding, Jiang, Tian, "A Strictly Proper Scoring-Rule Theory for Calibrating Stochastic Car-Following Models", arXiv 2609.04988, 2026 (abstract only) | Calibrate simulators with the energy or kernel score estimated from simulator draws (scoring-rule posterior with stochastic-gradient MCMC; car-following traffic simulators, energy score recommended) | No privacy; all data at the server; iterative. They supply T5's loss and nothing private |
| 6 | Ramesh, Han, Avella-Medina, Rush, "M-estimators under user-level local differential privacy constraints", ICORS 2025 abstract, no arXiv found; https://datascience.maths.unitn.it/icors2025/abstracts/AvellaMedina.html | User-level LDP noisy gradient descent: at every step the server averages users' privatised gradients of their own averaged loss | Iterative, full gradient, M-estimation loss; T5 sends one projected number once at a public point. Cohort structure not stated (abstract only) |

Background, not closer: Wang et al. 2019 (PM/HM; LDP SGD where each user samples k of d gradient coordinates; baseline table) and Chaloner & Verdinelli, "Bayesian Experimental Design: A Review", Statist. Sci. 10(3), 1995, DOI 10.1214/ss/1177009939 (R3-C3's criterion wᵀΣ₀JΣ₀w/(wᵀΣ₀w + σ_n²) is a Bayesian L-optimal design of one linear Gaussian measurement). Not found anywhere: the energy score, CRPS or Cramér distance used as the privatised quantity or the loss under DP or LDP; LDP calibration of a simulator (only the central "simulate, perturb, match" line and secure multi-party calibration, both already in the baseline table).

### Verdict
- **T5 as specified: NOVEL COMBINATION, low confidence.** The parts exist separately (the LDP one-step projected-score estimator, energy-score simulator calibration, workload-adaptive LDP strategies, Bayesian design); their combination for user-level LDP synthesis does not.
- **The R3-C1 core alone (drawn knob coordinate): CLOSE VARIANT, medium-high confidence, of Duchi & Ruan's one-step corrected estimator.** Same report (one privatised projected score per user), same server step (one Newton-type correction); each difference is one modelling choice (energy score instead of the log-likelihood, public θ₀ instead of a pilot cohort, user-level averaging by the standard lift X1).
- **R3-C3 is thin.** [With a single target (rank-one J = ggᵀ) and HM noise small against the prior, the criterion is maximised by w ∝ g, the target's gradient, which is Duchi & Ruan's influence direction up to the Hessian factor.] Only a multi-target J, where w is a generalised eigenvector, goes beyond them, and that step is textbook Bayesian design.

### What would make it novel (two lines)
A result the one-step LDP estimators lack: e.g. a proved exact level for the properness gate with user-level averages over unequal trip counts and simulator replicates, plus a shown P6 gain of the designed w over both the influence direction and a random coordinate at n = 10,000. Without it, describe T5 honestly as "Duchi-Ruan one-step correction with a likelihood-free proper-scoring-rule score at a public pilot".

### Check against rounds 1 and 2
Largely coincides: R3-C1 is round-1 raw idea B.1 (user-averaged recursive-logit score coordinates at a literature θ₀ by PM, one Bayesian Newton step, → C1) with the energy score as the loss, and close to C.1 (one PM coordinate, one Newton step); for a location knob the per-trip quantity is K1's PIT (R2-C.1). Only R3-C3's designed direction is new relative to rounds 1-2. Not C7/C.4 (zero-order).

## T6 Absolute-threshold duration CDF

### Search status (read first)
Both web tools hit the account's session limit on the fourth T6 call ("You've hit your session limit · resets 3:10pm (Europe/Ljubljana)", at 14:15 local). Only 2 searches and 1 fetch ran for T6, plus 2 T5 results that also bear on T6: short of the 6 searches the task prescribes. The decisive work (row 1) is known from search snippets only; its fetch failed, so the exact form of its report is unverified.

### Queries run
1. WebFetch of arXiv 2502.02990 (Aamand et al.): what is the non-adaptive baseline.
2. "local differential privacy" "cumulative distribution function" OR "distribution function" estimation random threshold one bit randomized response (extended mode).
3. "current status" OR "isotonic regression" OR "monotone" "local differential privacy" distribution function NPMLE randomized response.
4. Reused from T5: Duchi & Ruan §4.4 (WebFetch of the ar5iv text); Kalinin & Steinberger 2025 (T5 queries 4 and 11).
5. Failed (session limit): WebFetch of https://proceedings.mlr.press/v235/liu24z.html; search for Liu Hu Kong ICML 2024 "Tuning-free Estimation and Inference of Cumulative Distribution Function under Local Differential Privacy".
Not run, for a rerun after 15:10: "misclassified current status data" NPMLE known misclassification; "differentially private" synthetic data "Wasserstein" "accuracy guarantee" OR certified (R3-C4's certificate); "user-level local differential privacy" CDF OR quantile; "local differential privacy" "travel time" OR "trip duration" distribution.

### Closest works
| # | Reference | What it does | Precise difference from T6 |
|---|---|---|---|
| 1 | Liu, Hu & Kong, "Tuning-free Estimation and Inference of Cumulative Distribution Function under Local Differential Privacy", ICML 2024 (PMLR 235); https://proceedings.mlr.press/v235/liu24z.html (snippets only) | Recasts CDF estimation under LDP as the current-status problem of survival analysis: binary threshold queries give an isotonic estimator; uniform and L2 error bounds for the whole curve, asymptotic normality and inference, no tuning parameters ("refining the grid tightens the bound") | Same report family (one privatised bit "x ≤ t"), same estimator (isotonic fit of the debiased bits), same goal (an LDP CDF). T6 adds only the domain (trip duration per departure period, one sampled trip per user, a ⊥ class) and a downstream use (quantile-map the simulator, F7 gate). Unverified: one threshold per user and RR as the randomiser (the current-status framing implies one inspection time per subject) |
| 2 | Aamand, Boninsegna, Gentle, Imola, Pagh, "Lightweight Protocols for Distributed Private Quantile Estimation", arXiv 2502.02990, 2025 (ICML 2025 per baseline) | Adaptive one-query-per-user LDP and shuffle protocols for one quantile, O(log B/(ε²α²)) users; says prior non-adaptive algorithms need more users "by several logarithmic factors" and proves lower bounds against non-adaptive protocols | Adaptive, one quantile. The abstract does not describe the non-adaptive baseline; its lower bound is the price of T6's single non-adaptive round |
| 3 | "The Power of Factorization Mechanisms in Local and Central Differential Privacy", arXiv 1911.08339 (Edmonds, Nikolov, Ullman, STOC 2020; authors and venue from memory) | Threshold (CDF) queries over a domain of size T in the local model: a log²T-order lower bound for answering all thresholds, against an O(log³T) binary-tree upper bound | Worst-case theory for all thresholds at once; no isotonic estimator, no simulator; background for T6's resolution limit |
| 4 | Cormode, Kulkarni, Srivastava, "Answering Range Queries Under Local Differential Privacy", PVLDB 12(10), 2019; https://www.vldb.org/pvldb/vol12/p1126-cormode.pdf | Range, prefix (CDF) and quantile queries from hierarchical histograms or Haar wavelets, users split across levels | Users report a hierarchy node or a wavelet coefficient, not a threshold bit; no monotone fit. Answers the consolidator's question: not their method |
| 5 | Duchi & Ruan, Ann. Statist. 52(1), 2024, §4.4; https://arxiv.org/abs/1806.05756 | A first cohort sets a threshold T̂; each later user sends a randomized-response bit of 1{T(X) ≥ T̂}; the server inverts a parametric tail probability | Parametric, one data-driven threshold; T6 is nonparametric with fixed absolute thresholds and a monotone fit |
| 6 | Kalinin & Steinberger, "Efficient Estimation of a Gaussian Mean with Local Differential Privacy", AISTATS 2025; https://arxiv.org/abs/2402.04840 (with Joseph et al. 2019, baseline) | Sign bits of each value at a threshold, two stages for efficiency; single-stage designs lose efficiency when the first guess is far off | Parametric (Gaussian mean); their single-stage finding mirrors T6's resolution caveat |

Also seen, not closer: "Non-Stochastic CDF Estimation Using Threshold Queries", arXiv 2301.05682 (non-private, one threshold query per sample); "Functional Approximation Methods for Differentially Private Distribution Estimation", arXiv 2501.06620 (central DP, isotonic post-processing of a private CDF); Ghazi, Kamath, Kumar, Manurangsi, "Private Isotonic Regression", NeurIPS 2022 (central DP); "SoK: Descriptive Statistics Under Local Differential Privacy", IACR ePrint 2024/1464 (one-turn and binary-search quantile schemes). R3-C4's certificate was not searched.

### Verdict
- **Core report and estimator: EXISTS, medium confidence** (Liu, Hu & Kong 2024). Medium because the evidence is snippet-level and the fetch failed.
- **T6 as a whole: CLOSE VARIANT, medium confidence.** It is the published estimator applied to one sampled trip's duration per departure period, with a ⊥ class and a downstream quantile map of the simulator; the gate is K1's F7 gate. Only R3-C4's certified W1 release could add novelty, and it is unchecked.
- The consolidator's first query is answered: "random public threshold + RR + isotonic fit" is not Cormode et al. 2019, but it is (per snippets) the main method of Liu, Hu & Kong 2024, the same group as the baseline's Liu & Hu 2026.

### What would make it novel (two lines)
Not the bit and not the isotonic fit. Possible: R3-C4's release minimising posterior expected W1 with a finite-sample certified W1 bound under the public simulator prior (first check whether Liu-Hu-Kong's inference already gives W1 or uniform bands), or a proved W1-optimal threshold placement from the public prior.

### Check against rounds 1 and 2
No coincidence: K1 (R2-C.1) and R2-D.1 ask relative questions (rank among twins; "above the simulator's median for my context"), and R2-A.1 (K2) sends one trip's duration class at the prior's terciles jointly with tightness. T6's absolute thresholds with an isotonic fit are new against rounds 1-2, but not against the literature.

### Addendum 2026-10-09, 15:29-15:50 (web tools available again)
Run in this addendum: the Liu-Hu-Kong page plus its full PMLR PDF (https://raw.githubusercontent.com/mlresearch/v235/main/assets/liu24z/liu24z.pdf, text extracted locally with pdftotext; a search found no arXiv version), and 7 searches:
1. arXiv version of Liu Hu Kong "Tuning-free" CDF LDP current status isotonic.
2. "misclassified" "current status data" nonparametric maximum likelihood known misclassification.
3. "local differential privacy" synthetic data "Wasserstein" accuracy guarantee OR certified OR "confidence band" (extended mode).
4. "user-level" "local differential privacy" quantile OR CDF, multiple samples per user.
5. "local differential privacy" "travel time" OR "trip duration" distribution.
6. "local differential privacy" Bayesian posterior "randomized response" data augmentation OR Gibbs CDF credible band (+ WebFetch of the ICML 2026 poster page it surfaced).
7. Bayes estimator "Wasserstein" loss distribution function "posterior median".
Not used: the XJTU seminar page redirected to a corporate gateway and was not followed; the NUS and HKBU pages gave no readable text.

**Settled from the full text: Liu, Hu & Kong 2024 use T6's report and estimator (§3.2-3.4, Theorems 4.1-4.3).**
- Report: the curator draws T_i from a known design G and sends it (or the device draws it); each user answers ONE question, "is T_i ≥ X_i?", by randomized response (truthful with probability r, otherwise a fair coin; ε = log((1+r)/(1−r))). No budget split.
- Design G: "density-based" (e.g. uniform) or "preselected sampling" on a chosen grid of exact values of interest (their example: the share below a poverty line). They also suggest choosing G close to F when prior knowledge of F exists, which is T6's frozen absolute grid and, in spirit, R3-C4's prior-weighted placement.
- Estimator: constrained isotonic NPMLE over non-decreasing F in [0, 1] (Huang & Wellner 1997 algorithm). Guarantees: uniform and L2 consistency; a Chernoff limit for a random design (Groeneboom & Wellner 1992); √n asymptotic normality on a fixed grid, with inference and empirical coverage.
- Absent: any Wasserstein metric, posterior, quantile map, user-level unit or per-group strata. Their experiments start at n = 1,000 (ε 0.51-2.94), so the n = 91 regime is untested.

| Reference | What it does | Difference from T6 |
|---|---|---|
| Hu & Liu, "Censoring with Plausible Deniability: Asymmetric Local Privacy for Multi-Category CDF Estimation", ICML 2026 poster; https://icml.cc/virtual/2026/poster/64491 (abstract only, no arXiv) | Same group: CDFs of several categories (group-level distributions) under utility-optimised LDP with asymmetric protection, also valid under symmetric LDP; uniform consistency, pointwise weak convergence | Per-group CDFs match T6's per-period CDFs; its report is unverified |
| McKeown & Jewell, "Misclassification of current status data", Lifetime Data Anal. 2010, DOI 10.1007/s10985-010-9154-0; Sal y Rosas & Hughes, Stat. Commun. Infect. Dis. 3(1), 2011, https://biostats.bepress.com/uwbiostat/paper364 | Non-private NPMLE (adjusted pool-adjacent-violators) for current-status data with known misclassification | The non-private ancestor of T6's server step; randomized response is a known misclassification |
| "Consistent Estimation of Numerical Distributions under Local Differential Privacy by Wavelet Expansion", arXiv 2509.19661; "Differentially Private Sampling from Distributions via Wasserstein Projection", arXiv 2605.10015; Donhauser et al., "Certified private data release for sparse Lipschitz functions", AISTATS 2024, arXiv 2302.09680 | A priori Wasserstein error bounds for an LDP distribution estimate; LDP sampling with minimax worst-case Wasserstein error; a data-dependent utility certificate in transport cost, under central DP | None releases a CDF under LDP with a data-dependent (posterior or certified) W1 bound |

**R3-C4 check.** No LDP work releases a posterior-median CDF or a certified W1 bound. Both pieces are textbook. On the line, W1 is the area between the CDFs (https://ar5iv.arxiv.org/html/2111.03570), so [my derivation] the Bayes act under W1 is the pointwise posterior median of F(x), and the certificate is a posterior credible bound. LDP posteriors by data augmentation for randomized response exist (Kulkarni et al., arXiv 2110.14426; Aydın & Yıldırım, arXiv 2405.07020; Beraha et al., arXiv 2310.09818). Nothing was found for user-level LDP CDF estimation or for LDP travel-time distributions (nearest: Acharya, Liu & Sun 2023 for discrete laws; LDPTrace's OUE length histogram).

**Updated verdict (labels unchanged, confidence raised).**
- Core report and estimator: EXISTS, high confidence (was medium).
- T6 as a whole: CLOSE VARIANT, high confidence (was medium). Its only differences are the domain (duration per departure period), the noise alphabet (GRR over 3 with ⊥), the one-trip user-level lift and the downstream simulator quantile map.
- R3-C4's posterior-median release with a certified W1 bound: no LDP precedent found. It is at most a NOVEL COMBINATION of textbook parts (low confidence) and is the only novelty T6 could claim.
- Still unverified: the report of the Hu & Liu 2026 poster, and whether a Bayesian current-status NPMLE under LDP exists elsewhere (one search only).
