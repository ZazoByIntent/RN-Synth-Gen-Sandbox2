# Stage 3 novelty check, group G3: K5 Habit-mode hubs, K6 Mobility-signature users (2026-10-07)

Inputs: `01_task.md`, `03_novelty_task.md`, `20_candidates.md` (K5, K6, X1–X14), `00_baseline.md` §4–§5. Raw English material;
nothing here is decided. Method: each candidate split into its essential elements; 17 web queries for K5 and 23 for K6 across
local differential privacy (LDP), location privacy, synthetic mobility, mobility science, survey and transport practice,
statistics (simulated moments, indirect inference, urn processes) and federated analytics. Every cited work was opened
(abstract, or "paper read" = method section read) unless marked "snippet only". V = verified here by algebra.

## K5 Habit-mode hubs: report the habit, not a sample
**Elements.** E1 the device reduces all its trips to a habit (modal 5-km cell of trip ends; habit share h_u; modal daypart)
and sends one item through a standard ε-LDP oracle (OLH/GRR; HM for h_u). E2 the server debiases into a hub distribution π̂
(public threshold, public fallback). E3 a whole-user decoder: hub H ~ π̂, each trip end is H with probability ĥ, else from a
public distance kernel k_H; Boltzmann routes on OSM; trips emitted unlinked. E4 a hub-mixture OD likelihood for the MIA.

**Findings per element.**
- E1 is published in the local setting, under metric DP. Wang, Qin, Yang, Han, Ma (AAAI 2018, paper read; this is the "AAAI
  coverage paper" K5 could not identify): each phone profiles its owner locally, picks at random one location whose visit
  probability exceeds a threshold (e.g. 0.8), uploads NULL if there is none, obfuscates it once with an LP-optimised
  geo-indistinguishable mechanism on a grid, and the server estimates the population distribution π of these frequent
  locations (Bayes updates over k disjoint user groups, each user uploading once). No generator, no habit share, not pure
  ε-LDP, and a random frequent location rather than the mode. Survey practice draws the same line: the ACS asks how a person
  "usually" got to work last week, while the NHTS uses travel diaries (snippet only; census.gov refused the fetch).
- The modal cell is not semantics-free to a reviewer: "Maximum Amount" (home = the tower holding most of the user's
  activities) is the canonical home-detection rule (Vanhoof, Lee, Smoreda 2018, abstract and criteria read). Q1 will be read
  as an LDP home report, i.e. round-1 E.4 (home-zone slot) inside C4.
- E2: a frequency oracle plus a threshold; DP-WHERE did the curator-side equivalent (Laplace on counts of distinct users per
  home cell, Hay et al. post-processing; paper read).
- E3 is DP-WHERE's generator moved to the local model: home ~ noisy Home distribution, work at a sampled commute distance,
  every call placed at home or work by hourly distributions; neighbours differ in all records of one user; central Laplace.
  Per-user hub-plus-background mixtures are classic non-private models: the PMM/PSMM of Cho, Myers, Leskovec (KDD 2011,
  paper read: per-user Gaussians at latent home and work, time-dependent state prior, plus a social component) and
  TimeGeo's home anchor plus rank-based EPR (PNAS 2016, abstract). E4 is a latent-class mixture likelihood; repo-specific.
- Theory: user-level LDP distribution estimation assumes homogeneous users (Acharya, Liu, Sun, AISTATS 2023, read: "m i.i.d.
  samples from the same (unknown) distribution p"; Kent, Berrett, Yu 2024: mean and density). Heterogeneous users appear in
  user-level DP mean estimation (Cummings, Feldman, McMillan, Talwar, NeurIPS 2022, abstract). No analysis was found of
  "send a per-user summary vs one sampled item" for heterogeneous users under LDP; open, but small.
- No pure-LDP pipeline was found that turns per-user habits into synthetic whole users or trips (queries on LDP home, anchor,
  frequent and top locations, stay points, LDP synthetic populations, LDP with Geolife).

**Closest works.**
1. Wang et al., "Geographic Differential Privacy for Mobile Crowd Coverage Maximization", AAAI 2018,
   https://ojs.aaai.org/index.php/AAAI/article/view/11285 (arXiv 1710.10477): the same client-side habit report and population
   estimate; differs in metric DP, a random frequent location instead of the mode, no h_u, no generator, no likelihood.
2. Mir, Isaacman, Cáceres, Martonosi, Wright, DP-WHERE, IEEE BigData 2013, https://doi.org/10.1109/BigData.2013.6691626: the
   same "anchor distribution → synthetic users who return to their anchors" pipeline; central DP, home/work semantics, call
   records, no road network, no habit share.
3. Cho, Myers, Leskovec, KDD 2011, https://cs.stanford.edu/people/jure/pubs/mobile-kdd11.pdf: the hub-plus-background
   individual model, non-private and fitted per user by EM.
4. Acharya, Liu, Sun, AISTATS 2023, https://proceedings.mlr.press/v206/acharya23a.html: user-level LDP with m samples from one
   shared p; K5's estimand (distribution of personal modes of heterogeneous users) lies outside it.
5. Vanhoof, Lee, Smoreda 2018, https://arxiv.org/abs/1809.09911: the modal location is the standard home detector.
Further: Bagdasaryan et al., PoPETs 2022 (location heatmaps, distributed DP with secure aggregation; abstract); Imola, Roy
Chowdhury, Chaudhuri, CCS 2024 (user-level metric DP via earth mover's distance, local and central; paper read in part).

**Verdict: NOVEL COMBINATION (narrow), confidence medium.** The parts are Wang 2018's local habit report, DP-WHERE's anchor
decoder and a PMM-type hub mixture; their combination (pure ε-LDP at user level, one report, habit share, whole-user decoder on
a road graph, exact likelihood) was not found. The element K5 sells as its novelty, "the mode instead of a sample", is on its
own a CLOSE VARIANT of Wang et al. 2018 (and of survey "usual" questions), so round-1 lesson 1 applies.
**Must claim:** a pure user-level ε-LDP, one-report pipeline that decodes habits into whole synthetic users with a finite edge
likelihood; the measured gain of the habit item over C2's sampled trip-end item on the same users (an empirical result at
n ≈ 91 and in S2, not a principle). It may add that user-level LDP implies the "distribution privacy" of Kawamoto & Murakami
(ESORICS 2019, abstract) for the habit itself: any mixture of inputs keeps the e^ε ratio (V, same step as X1).
**Must avoid:** "report the habit" as a new principle; "no semantics, hence no anchor" (the Maximum Amount rule); novelty of
the hub-plus-kernel model (PMM, DP-WHERE, TimeGeo); any hint that ε 8 hubs are safe in practice: home–work pairs at census-block
level have a median anonymity set of 1 (Golle & Partridge, Pervasive 2009, abstract), and 20 × 20 hubs at ε 8 sit only under
the vacuous e^8 bound.
**Raising the verdict:** (a) a variance-and-bias analysis of the mode report vs the sampled-item report for heterogeneous users
under user-level LDP, with the bias of users with 1–3 trips (not found; one appendix); (b) a joint habit item without precedent
(hub × habit-strength class), which also gives X4's trip weighting. Neither makes K5 NOVEL; (a) defends it against "one
detail". Calling the hub an anchor openly and meeting Cond-C4 with K6's metrics beats arguing the semantics away.

## K6 Mobility-signature users: exploration-and-return calibrated by concentration descriptors, with a copy layer
**Elements.** E1 the device computes classic individual-mobility descriptors over all its trips (distinct 500 m cells S, radius
of gyration r_g, ratio r_g^(2)/r_g; repeat share r_u; trip-count class), bins one publicly and sends it by GRR (HM for r_u);
users, not ε, are split across descriptors. E2 the server calibrates an exploration-and-preferential-return (EPR) population
(Song constants as prior, d-EPR gravity exploration over OSM mass) by simulated method of moments (SMM) and emits whole users
on OSM. E3 a copy layer whose single-trip marginal stays G, plus user-level coherence metrics. E4 the EPR population's
simulated zone OD plus the router as likelihood; the copy layer adds nothing.

**Findings per element.**
- E1: the same descriptors are released with user-level DP, but by a curator: Kapp, Nuñez von Voigt, Mihaljević, Tschorsch,
  "Towards mobility reports with user-level privacy" (J. Location Based Services; arXiv 2022; abstract and package docs read):
  trips per user, radius of gyration, locations per user, time between trips, mobility entropy, with a max_trips_per_user
  bound and Laplace/exponential mechanisms. No per-device (local) release of r_g, S or the returner ratio was found; sending
  a binned deterministic function through GRR is routine (X1).
- E2: calibrating a mobility model through a privacy mechanism is published in the central model. DP-WHERE (private
  distributions drive a simulator that emits synthetic users); Sakong & Zentefis (NBER chapter 2024, abstract): SMM of a
  gravity model of consumer visits on DP mobile-device data by "simulate, privatise with the same mechanism, match moments";
  generic simulation-based and indirect inference from DP releases (Xiong, Ju, Zhang 2023; Wang, Chang, Awan 2025; abstracts).
  EPR, d-EPR/DITRAS, returners/explorers and TimeGeo are non-private (abstracts read; DITRAS names no privacy motive). No work
  was found that fits EPR or any individual mobility-law model from DP or LDP outputs (six queries, incl. exact phrases).
- E2 arithmetic (V): EPR's S(n) = (ρ(1+γ)n)^{1/(1+γ)} (from dS/dn = ρS^−γ) gives S(18) = 8.4 at (ρ, γ) = (0.6, 0.21) and 4.7
  at ρ = 0.3, as K6 states. The constants come from phone traces (Song et al., abstract); the returner/explorer split also
  holds in GPS of ≈ 46,000 vehicles (Pappalardo et al. 2015, abstract), which softens the "call records, not GPS" risk.
- E3: the copy layer is a Pólya-urn construction. Given the urn's limit the draws are i.i.d. from it and each draw's marginal
  is the base measure (Blackwell & MacQueen, Ann. Statist. 1973, abstract), so the invariance K6 proves (X11) is a textbook
  property; preferential return is itself an urn. The coherence metrics are standard: radius of gyration, daily locations,
  G-rank and I-rank are the usual user-level metrics of mobility generators (MoveSim, KDD 2020, snippet only; PateGail, AAAI
  2023, read, on GeoLife's 178 users); per-cell diversity of users' visits is location entropy (To, Nguyen, Shahabi,
  SIGSPATIAL 2016, abstract). Only the convention "an unlinked release counts every trip as its own user" was not found.
- Whole-user generation under DP or LDP exists in learned, iterative form: PateGail (devices train personal discriminators and
  score server-generated trajectories; Laplace noise on averaged rewards; many rounds) and PateGAIL++ (ICLR 2026, abstract
  only: user-level DP, adaptable to LDP). Gibbs et al. (EPJ Data Science 2026, abstract only) test LDP mobility networks.

**Closest works.**
1. DP-WHERE, IEEE BigData 2013 (link above): private distributions drive a mechanistic simulator that emits synthetic users;
   central DP, anchor and calling distributions instead of mobility-law constants, no road network.
2. Kapp et al., https://arxiv.org/abs/2209.08921: the same per-user descriptors under user-level DP; central, no generator.
3. Sakong & Zentefis, "A Simulation-Based Method to Estimating Economic Models with Privacy-Protected Data", NBER 2024 (link in
   `00_baseline.md` §5): SMM of a gravity model through the privacy mechanism; central DP, no individual model, no synthesis.
4. PateGail (Wang, Gao, Wu, Jin, Yao, Li), AAAI 2023, https://ojs.aaai.org/index.php/AAAI/article/view/26700: device-trained
   whole-user generator with DP-noised rewards, judged by the same user-level metrics on GeoLife; learned GAIL, iterative,
   aggregate noise, no road graph.
5. Pappalardo & Simini, DITRAS, DMKD 2018, https://arxiv.org/abs/1607.05952, with Song et al., Nature Physics 2010,
   https://arxiv.org/abs/1010.0436: the d-EPR model K6 calibrates; non-private.

**Verdict: NOVEL COMBINATION, confidence medium.** Each part (descriptor release, calibration through the privacy mechanism,
EPR, urn copies, user-level metrics) is published; an EPR/d-EPR population calibrated from one pure-LDP descriptor per user and
emitted as whole users on a road graph with an exact edge likelihood was not found. Inside the project it is the §4 paradigm
(private knobs drive a public simulator) with a mobility-law simulator, so its difference from §4 rests on the estimand
(concentration of trip ends, ρ), not on the architecture.
**Must claim:** user-level pure-LDP calibration of mobility-law constants (ρ, γ, exploration decay) from binned descriptors;
a measured answer to whether ρ moves unlinked marginals (length W1, OD JSD); the S2 recovery curve.
**Must avoid:** novelty of the descriptors or their private release (Kapp et al.), of "simulate, privatise, match" (Sakong &
Zentefis; Xiong et al.; Wang, Chang, Awan), of the copy layer and its invariance (urn), of the coherence metrics (MoveSim,
PateGail), and "the first user-level LDP whole-user generator" (PateGail, PateGAIL++). Present the copy layer and the
metrics as engineering adopted to meet Cond-C4.
**Raising the verdict:** (a) replace SMM by a closed-form estimator of ρ and γ from one joint LDP item (S-bin × trip-count
class) through S(n) above, with a variance argument; the nearest precedent is LDP estimation of a graph power-law exponent
from privatised log-statistics (Tan, Hefny, Vora 2026, abstract), so the verdict stays NOVEL COMBINATION but the claim becomes
crisp and checkable; (b) put the ≈ 10 % match thinning (X6) inside the EPR moment map, i.e. calibrate EPR from thinned visit
sequences; not searched in depth and possibly the most original piece. Dropping the copy layer loses no novelty.

## Notes that may change another group's picture
- G1 (K7): PateGail (AAAI 2023) has devices answer server-generated trajectories with a locally trained model, the nearest
  published relative of the "proxy respondent" (iterative, aggregate Laplace noise, not one pure-LDP report); PateGAIL++
  (ICLR 2026) claims user-level DP with an LDP variant. G1 (K1): Wang et al. AAAI 2018 already splits users into disjoint
  groups, each uploading once, and refines the server's prior group by group: a published case of R2-D's cohort adaptivity.
- All K: do not claim "the first user-level LDP trajectory generator" (PateGail, PateGAIL++) or novelty for fitting a
  simulator by simulate–privatise–match (Sakong & Zentefis 2024; Xiong et al. 2023; Wang, Chang, Awan 2025). Any K that reports
  a modal or most-visited cell (K4 family C) will be read as home detection (Maximum Amount rule).
- X5: the trips-per-user histogram is a routine user-level DP output (Kapp et al., central); this does not lift S1.

| Candidate | Verdict | Confidence | Closest work |
|---|---|---|---|
| K5 Habit-mode hubs | NOVEL COMBINATION (narrow); "mode, not a sample" alone = CLOSE VARIANT | medium | Wang et al., AAAI 2018 (local frequent-location upload); generator side DP-WHERE 2013 |
| K6 Mobility-signature users | NOVEL COMBINATION | medium | DP-WHERE 2013 (central, simulator driven by private distributions); report side Kapp et al. 2022 |
