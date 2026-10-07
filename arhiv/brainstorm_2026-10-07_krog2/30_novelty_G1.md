# Novelty check G1: K1, K7, K8 (novelty checker, 2026-10-07)

Inputs: `01_task.md`, `03_novelty_task.md`, `20_candidates.md` (K1, K7, K8, X1–X14), `00_baseline.md` §4–§5. Round-1 works are
not re-searched unless a candidate leans on them; "(r1)" = abstract opened in round 1. Every other cited work had its abstract
or paper opened here unless marked "snippet only"; classical method sources are marked "(background, not opened)". Effort:
54 web searches (K1 17, K7 21, K8 16) and 33 page fetches. One fetch redirected to a corporate login portal and was not followed.

## K1 Twin-rank calibration

**Elements and what exists**
- E1 A device-side score against a shared model, sent by randomized response (RR). Exists. Penso et al. 2025 (LDP-CP-S): each
  user computes its conformity score with the model, compares it with a server threshold and sends one RR bit. Disjoint cohorts
  run a binary search for the quantile, and each user interacts once. Cormode & Markov 2023: clients apply a shared classifier
  to their own labelled data and send LDP histogram reports (OUE) for calibration by histogram binning. New in K1: the score
  is a conditional probability integral transform (PIT) of a continuous trip attribute. The device estimates it by Monte Carlo
  against K twins that it simulates from a public road-network simulator for the trip's own context. No LDP paper was found
  that reports PIT or rank-histogram cells of a generative model or simulator (queries 1, 6, 9, 10, 11, 16).
- E2 Exact-null gate. "Correct model ⇒ uniform PIT" is classical (Rosenblatt 1952, Diebold et al. 1998, Hamill 2001:
  background, not opened). Talts et al. 2018 (simulation-based calibration) uses ranks among simulated draws, without privacy.
  LDP identity and goodness-of-fit testing is solved (Acharya et al. 2019 RAPTOR: one bit with a public coin; Lam-Weil et
  al.: known reference density, non-interactive). Putting the two together is one line of argument; nobody seems to have
  written it for LDP, but a reviewer will not count it as a contribution.
- E3 Recalibration map (density = prior × g(F_prior)). Without privacy: Kuleshov et al. 2018 recalibrate any regression
  model's predictive CDF with a learned map. With privacy, only for classifiers: Luo et al. 2020 (DP recalibration under
  domain shift), Maddock, Cormode & Maple 2025 (federated, user-level DP histogram binning or temperature scaling), and Cormode
  & Markov 2023 (LDP). K1 is the regression and generator analogue, with 3 bins under GRR. As a statistic it is incremental;
  as a use (recalibrating a released trip generator) it is new.
- E4 Sequential form (a median bit, then a re-centring cohort). Exists. Joseph et al. 2019 (KVGausstimate): half of the users
  give a coarse location; the other half "randomized respond on sgn((x_i − μ̂₁)/σ)", and the analyst inverts the Gaussian CDF
  of the debiased share. K1 replaces Φ with the simulator's conditional law plus a cited heterogeneity law. The same
  construction appears in LDP quantile work: Aamand et al. 2025 (adaptive, each user queried once) and Liu & Hu 2026 (online
  quantile regression with one report per user, conditional on covariates). This form is a CLOSE VARIANT.

**Closest works**
1. Joseph, Kulkarni, Mao, Wu, "Locally Private Gaussian Estimation", NeurIPS 2019, https://arxiv.org/abs/1811.08382 — K1's
   sequential form is their round 2 with a simulator-conditional CDF in place of Φ.
2. Penso, Mahpud, Goldberger, Sheffet, "Privacy-Preserving Conformal Prediction Under LDP", COPA 2025 (PMLR 266),
   https://arxiv.org/abs/2505.15721 — a model-based score of the user's own data, one RR bit per user in disjoint cohorts.
   K1 sends a PIT bin to recover a whole calibration map rather than one quantile, and its model is a context-conditioned
   simulator.
3. Cormode & Markov, "Federated Calibration and Evaluation of Binary Classifiers", PVLDB 16(11) 2023,
   https://arxiv.org/abs/2210.12526 — LDP calibration of a shared model from histogram reports, but for classifier scores
   and labels, not for PITs of a continuous generative law.
4. Kuleshov, Fenner, Ermon, "Accurate Uncertainties for Deep Learning Using Calibrated Regression", ICML 2018,
   https://arxiv.org/abs/1807.00263 — K1's server map is this recalibration, done there without privacy and with full PITs.
5. Acharya, Canonne, Freitag, Tyagi, "Test without Trust", AISTATS 2019, https://proceedings.mlr.press/v89/acharya19b.html,
   and Lam-Weil, Laurent, Loubes, https://arxiv.org/abs/2002.04254 — LDP goodness-of-fit tests; K1's gate is one, applied to
   PITs.
Also: Talts et al. 2018, https://arxiv.org/abs/1804.06788; Aamand et al., ICML 2025, https://arxiv.org/abs/2502.02990; Liu &
Hu 2026, https://arxiv.org/abs/2607.05312; Maddock et al. 2025, https://arxiv.org/abs/2510.01987; Calibrate 2019, Xiong et
al. 2023, Sakong & Zentefis (r1).

**Verdict: NOVEL COMBINATION, medium confidence** for the one-round 3-bin form with the gate and the map. The sequential form
alone is a CLOSE VARIANT of Joseph et al. 2019. No work was found in which each user sends, under user-level LDP, a
simulator-conditional PIT computed against twins simulated on the device, and the result gates and recalibrates a released
generator. Confidence is medium because Cormode & Markov 2023 plus Kuleshov et al. 2018 give "LDP PIT-histogram recalibration"
in two short steps, and a privacy-venue reviewer may call that step incremental.
- **Claim:** a context-conditioned PIT makes every report exactly uniform under a correct public prior, whatever the user's
  trip count, context mix or travel mode (X4). Heterogeneity therefore cannot pose as miscalibration, which is what sets K1
  apart from C1's clipped moments and C3's labels. The pre-registered exact null keeps the prior unless the data reject it.
  The composed density stays normalised and road-valid.
- **Avoid:** "first LDP calibration" (Cormode & Markov 2023 did it for classifiers); "new adaptive protocol" (Joseph et al.,
  Penso et al., Aamand et al.); "new LDP goodness-of-fit test"; any n ≈ 91 utility claim beyond the log-duration shift
  (X10: at that size it moves what C1 and C3 move).
- **Raise:** the joint form helps most. A chained (Rosenblatt) PIT of (departure, duration) or (length, duration), sent as one
  9-cell GRR item at ε 8 (already an option in K1), calibrates the simulator's joint law under LDP, and nothing close to it was
  found. A proof that the gate keeps level α for any trip-count law would also help. Neither change makes K1 NOVEL.

## K7 Proxy respondent

**Elements and what exists**
- E1 A model fitted on the device answers public queries, and the answer is privatised locally. Exists in machine learning.
  In LDP-DL (Zhuang et al. 2022), each data owner trains a teacher on its own data and answers queries on unlabelled public
  samples; the answers pass through the Piecewise Mechanism, ε is split across queries and queries are chosen actively (least
  confidence). FedMD-NFDP (IJCAI 2021) shares predictions on public data. PATE uses a central noisy vote. Dwork & Feldman 2018
  define private prediction. In K7 the "public input" is one designed hypothetical choice scenario per user at full ε, and the
  "student" is a vector of structural parameters, not a classifier.
- E2 A designed hypothetical scenario followed by a parametric inversion. Exists in contingent valuation (Kim 2006: uniform
  against D-optimal bid designs) and, with RR, in dichotomous-choice valuation (snippet only). In LDP, "the server picks the
  query, the user returns an LDP answer, the server fits a surface" is Zhou & Tan 2021 (r1), the shape round 1 gave C7.
- E3 A misclassification-corrected discrete-choice likelihood with a known RR matrix. Exists. Hausman et al. 1998 handle
  misclassified logit and probit outcomes (with the misclassification estimated). Van den Hout & van der Heijden treat RR as
  misclassification with known probabilities in logistic regression (snippet only). Zhang et al., ICML 2025 apply label-DP
  through RR to binary response models, with RR chosen to maximise Fisher information and valid confidence intervals.
  Simulating the likelihood with the local-fit noise inside is indirect inference (background); for privatised data see Awan
  & Wang 2023 and Xiong et al. 2023 (r1).
- E4 The ε 8 option: an exponential mechanism over public candidate trips, with a clipped log-likelihood ratio as utility.
  New finding: this is locally private sampling. Husain et al. 2020: each user holds a distribution and releases one sample
  under ε-LDP. Park et al. 2024 give LDP samplers that are minimax-optimal for every f-divergence. Zamanlooy et al. 2025 add a
  public distribution per user. The option is a CLOSE VARIANT of this line (plus C5's library). The consolidator's comparison
  list (Private Evolution, posterior sampling) missed it.
- What runs at n ≈ 91: one parameter (speed ratio) with duration-bin scenarios. There the preferred alternative is monotone in
  θ_u, so the answer is a designed threshold query 1[θ̂_u > t_s] on the user's local estimate. That is Joseph et al.'s round 2
  or an LDP quantile query (Aamand et al. 2025) applied to a per-user estimate, the user-level LDP template of Acharya, Liu &
  Sun 2023 and Kent et al. 2024 (query 21). Only multi-attribute scenarios (route alternatives, destination zones) cut θ-space
  in a non-trivial way, and K7 itself defers those (X13; n of several hundred or more).

**Closest works**
1. Zhuang, Li, Chang, "Locally Differentially Private Distributed Deep Learning via Knowledge Distillation" (LDP-DL), arXiv
   2022, https://arxiv.org/abs/2202.02971 — a local model answers public queries under LDP; it uses many queries with split ε
   and a distilled classifier, where K7 uses one designed query and a structural maximum-likelihood fit.
2. Zhou & Tan, "Local Differential Privacy for Bayesian Optimization", AAAI 2021, https://arxiv.org/abs/2010.06709 — the
   server picks the query and the user returns an LDP reward at a server-chosen setting; in K7 the user returns a choice in a
   hypothetical scenario.
3. Hausman, Abrevaya, Scott-Morton, J. Econometrics 87 (1998), https://dspace.mit.edu/handle/1721.1/63829, and Zhang et
   al., ICML 2025, https://proceedings.mlr.press/v267/zhang25x.html — K7's server likelihood; K7 adds design and a simulated surface.
4. Husain, Balle, Cranko, Nock, AISTATS 2020, https://proceedings.mlr.press/v108/husain20a.html; Park, Asoodeh, Lee, NeurIPS
   2024, https://arxiv.org/abs/2410.22699; Zamanlooy, Diaz, Asoodeh, AISTATS 2025, https://arxiv.org/abs/2411.08791 — the
   ε 8 option.
5. Papernot et al., PATE, ICLR 2017, https://arxiv.org/abs/1610.05755 — a central noisy vote of private teachers on public
   queries; the shape a reviewer will name first.
Also: Chopra et al., AAMAS 2024, https://arxiv.org/abs/2404.12983 (simulator calibration by secure multi-party computation);
Dwork & Feldman, COLT 2018; FedMD-NFDP, https://arxiv.org/abs/2009.05537; federated discrete-choice estimation (snippet only:
parameters or gradients over rounds, no designed queries, no pure LDP).

**Verdict: NOVEL COMBINATION, low confidence**, for K7 as specified (designed multi-family scenarios, n ≥ about 1,000). No
paper was found in which a structural model fitted on the device answers a designed stated-choice question by RR and the
server recovers structural parameters through a misclassification-corrected likelihood. Confidence is low (not for thin
search) because an ML reviewer may call it "LDP-DL with one designed query", and because both runnable forms are CLOSE
VARIANTS: the n ≈ 91 form is a threshold query on a local estimate, the ε 8 option is LDP private sampling.
- **Claim:** a bridge from revealed to stated behaviour: the device turns its trips into one answer to a designed choice, so
  the information per user is set by the design, not by where the user travelled. The surface is simulated with the same
  local-fit code, so fit noise, clipping and the trips-per-user law (not public, X5: a sensitivity sweep) sit inside the
  likelihood. Design efficiency (D-optimal against random scenarios) can be measured in S2.
- **Avoid:** "first LDP query of a local model" (LDP-DL, PATE, FedMD-NFDP); calling the option a new sampler; any
  multi-parameter claim at n ≈ 91; calling the one-parameter speed scenario a stated-choice experiment (it is a threshold).
- **Raise:** present K7 and test it as LDP indirect inference. A result or S2 evidence that one designed K-ary answer per user
  recovers several parameters better than sending a privatised θ_u coordinate (HM or PM, the C1 route) would make the method,
  not only the domain, new. Dropping the option removes the overlap with private sampling. An adaptive design over two cohorts
  moves K7 towards Zhou & Tan and does not pay at n ≈ 91 (X8).

## K8 Within-user contrasts and couplings

**Elements and what exists**
- E1 A within-user statistic, sent as one GRR category under user-level LDP: a contrast between the user's own trips, or a
  correlation across them. User-level LDP work privatises functions of a user's whole sample: Acharya, Liu & Sun 2023 (m
  samples per user), Kent, Berrett & Yu 2024 (means, densities, a phase transition in T) and Zhao et al. 2024 (means,
  optimisation, regression). All of them target population means or distributions of per-observation quantities; no
  within-user contrast or correlation was found as an estimand. The closest in spirit is in the central model: Sopa,
  Avella-Medina & Rush 2026 average per-user least-squares slopes, each fitted on that user's own time series and assuming
  common slopes, under user-level DP with a trusted curator. Roth & Avella-Medina 2025 cover dependent data with random-effects
  and longitudinal extensions and a local RR-histogram variant, but have no within-user contrast.
- E2 Paired comparison. Central DP paired tests exist: Couch et al. 2018 (signed-rank) and a DP sign test (Awan & Slavković
  2018, snippet only). Under LDP, a sign test on the user's own paired difference is a one-line RR item. No paper was found,
  probably because it is folklore. LDP A/B tests (Ding et al. 2018) compare groups of different users. Longitudinal LDP (Joseph
  et al. 2018; Ohrimenko et al. 2022, snippet only) tracks population statistics as users' data change, not per-user contrasts.
- E3 Copulas and correlations. Under LDP, dependence has been estimated between attributes of one record (LoPub 2018 and CALM
  2018, both r1; a copula-based LDP synthesis that fits a Gaussian copula from Pearson correlations of RR bit strings, snippet
  only) and as pairwise statistics such as Kendall's τ across users' single records (Ghazi et al. 2023). K8(d) (quadrant →
  Blomqvist β → Gaussian ρ) is a CLOSE VARIANT of these: a 2 × 2 marginal by GRR with a different dependence coefficient.
  K8(c), the within-user Spearman sign across the user's own trips, was not found.
- E4 Use: separating a time-of-day congestion factor of a simulator from who travels when, plus a clock-dependent router. No
  privacy work was found that estimates a within-traveller peak/off-peak effect. Transport DP work pools segment speeds across
  users (Rameshwar et al. 2024, r1; travel-time DP/MPC protocols, snippet only), and MTNet 2022 (r1) learns time-of-day effects
  centrally. Day-to-day variability within the same person is large (about half of travel-time variance in a 3-weekday
  sample; snippet only). That is K8's noise risk, not a precedent.

**Closest works**
1. Sopa, Avella-Medina, Rush, "Differentially Private Inference for Longitudinal Linear Regression", arXiv 2026,
   https://arxiv.org/abs/2601.10626 — within-user (per-user least-squares) estimation under user-level DP, but central and
   continuous. K8 is the local version with one prior-relative category.
2. Kent, Berrett, Yu, "Rate Optimality and Phase Transition for User-Level LDP", arXiv 2024,
   https://arxiv.org/abs/2405.11923, and Acharya, Liu, Sun, AISTATS 2023, https://proceedings.mlr.press/v206/acharya23a.html
   — user-level LDP theory without within-user estimands.
3. Ding, Nori, Li, Allen, "Comparing Population Means under LDP", AAAI 2018, https://arxiv.org/abs/1803.09027 — an LDP
   comparison between groups of different users.
4. Couch, Kazan, Shi, Bray, Groce, "A Differentially Private Wilcoxon Signed-Rank Test", 2018,
   https://arxiv.org/abs/1809.01635 — a paired within-subject test under central DP.
5. LoPub (Ren et al., TIFS 2018, https://arxiv.org/abs/1612.04350, r1) and Ghazi et al., NeurIPS 2023,
   https://proceedings.neurips.cc/paper_files/paper/2023/hash/5642b9811a9ac5281be1cc84c275f251-Abstract-Conference.html —
   LDP dependence within one record or across users, never across one user's records.
Also: Zhao et al. 2024, https://arxiv.org/abs/2405.17079; Joseph, Roth, Ullman, Waggoner, NeurIPS 2018,
https://arxiv.org/abs/1802.07128; Roth & Avella-Medina 2025, https://arxiv.org/abs/2511.18583.

**Verdict: NOVEL COMBINATION, medium confidence.** The mechanism is a standard GRR item on a function of the user's data (X1),
so the method is not new. The estimand is: no LDP or mobility-privacy paper was found that releases within-user contrasts or
couplings. The identification argument is also absent from the user-level LDP literature: a within-person contrast removes the
composition confounding that per-trajectory and between-user mechanisms cannot remove. A central-DP analogue exists (Sopa et
al. 2026). Item (d) alone is a CLOSE VARIANT of LDP copula estimation, and item (a) inherits K1's twins.
- **Claim:** the estimand and its identification. (i) Per-trajectory LDP cannot produce a within-person contrast by
  construction. (ii) The prior-relative paired rank (personalised twins) cancels the user's speed level and keeps only the
  contrast. (iii) The selection law of eligible pairs is public, so the estimand is defined. (iv) Within-user and pooled (d)
  estimates can be compared on a simulated population in which who travels when is confounded.
- **Avoid:** a new LDP primitive; "first LDP paired test"; "first copula under LDP"; "first within-user estimator under
  user-level DP" (the central version exists); any utility gain on P2 at n ≈ 91 (only a very large effect is visible there,
  and X11 makes items a, c and d invisible to the MIA).
- **Raise:** generalise one contrast into an LDP within-user (fixed-effects) estimator. Each user sends a categorical report
  of its local slope; the server corrects for coarsening, the eligibility law and unequal trip counts; a consistency and
  variance result compares it with the pooled between-user estimator. No LDP fixed-effects estimator for panel data was found
  (queries 7, 10, 13), so this could reach NOVEL as a method. It is, however, a statistics contribution rather than a
  mechanism, and it needs thousands of users to show.

## Summary table
| Candidate | Verdict | Confidence | Closest work |
|---|---|---|---|
| K1 | NOVEL COMBINATION (the sequential form alone: CLOSE VARIANT) | medium | Joseph et al., NeurIPS 2019; Penso et al., COPA 2025 |
| K7 | NOVEL COMBINATION (n ≈ 91 threshold form and ε 8 option: CLOSE VARIANTS) | low | LDP-DL, Zhuang et al. 2022; Zhou & Tan, AAAI 2021 |
| K8 | NOVEL COMBINATION (item d alone: CLOSE VARIANT) | medium | Sopa, Avella-Medina & Rush 2026 (central user-level DP, within-user regression) |

## Findings for other groups and for the chosen §4 design
- LDP private sampling (Husain et al. 2020; Park et al. 2024; Zamanlooy et al. 2025) bears on any "release one sample per user"
  or "report the habit, not a sample" claim (K5 in G3). The fair baseline is a minimax-optimal LDP sampler, not a naive sampled
  trip.
- "Privately calibrate a public simulator" has published neighbours that §4 and every K should cite: Chopra et al., AAMAS 2024
  (simulator calibration by secure multi-party computation) and Cormode & Markov 2023 (LDP calibration of a shared model).
- Per-user estimators under user-level DP (Sopa et al. 2026, central) bear on K6's per-user descriptors (G3).
- One-bit adaptive LDP quantile protocols (Aamand et al. 2025; Liu & Hu 2026; Penso et al. 2025) bear on any binary question
  with a re-centring cohort.
