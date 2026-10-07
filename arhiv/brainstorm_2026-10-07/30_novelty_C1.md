# Novelty check: C1 (Behavioural-moment router)

7 Oct 2026. 18 web searches plus abstract lookups (arXiv, OpenAlex, Crossref, Semantic Scholar,
publisher pages). Full text was read only where it is open (LDPTrace, RetraSyn). GeoPM-DMEIRL is
paywalled and no index holds its abstract. The search log is at the end.

What was checked is the mechanism as consolidated in `20_candidates.md`. Each user averages a few
clipped route and time statistics over all of their map-matched trips. Most of these statistics are
residuals against the fastest path between the same endpoints, or against the OSM free-flow speed. A
public draw picks one coordinate, which is randomized at full ε with PM, HM or Duchi (GRR for
categorical slots). The server removes the noise bias, shrinks the means toward an OSM prior, and fits
a handful of route-choice and timing parameters by moment matching. The route model is a recursive
logit (maximum entropy) or a Boltzmann walk on a public cost-to-go. The output is road-valid, with a
departure time, per-edge times and an exact sequence likelihood.

## C1: Behavioural-moment router

### Closest published works

1. **GeoPM-DMEIRL.** Y. Huang, J. Zhang, H. Hou, X. Ye, Y. Chen. *Future Generation Computer
   Systems* 154:123–139, 2024. DOI 10.1016/j.future.2024.01.001.
   https://www.sciencedirect.com/science/article/abs/pii/S0167739X24000025
   - *What it does:* an LDP "geo-piecewise mechanism" perturbs each user's **trajectory** on a
     geo-aware grid with a piecewise mechanism, keeping it consistent with traffic rules. A deep
     maximum-entropy inverse reinforcement learner then learns a reward from these perturbed
     trajectories, and an A2C policy generates the synthetic ones.
   - *Where it collides:* the published pipeline "LDP, then maximum-entropy IRL, then a trajectory
     generator" is the same pairing that C1 relies on.
   - *Where it differs:* GeoPM randomizes the location sequence. C1 randomizes one coordinate of a
     per-user, publicly bounded average of sufficient statistics. GeoPM's reward is a deep network
     fitted to noisy demonstrations. C1 fits a low-dimensional exponential family to debiased
     moments whose noise variance is known. I saw no user-level unit, no departure-time model and no
     exact likelihood in what I could read (search-engine summaries only; see Confidence).
     The same group later published DPIL-Traj (Liao, ..., Huang, Zhang; *CMC* 2025: DP clustering,
     then imitation learning, then a Markov generator on Geolife), so this line of work is active.
2. **PUTS.** X. Sun, Q. Ye, H. Hu, J. Duan, Q. Xue, T. Wo, J. Xu. *IEEE TKDE*, 2023.
   https://doi.org/10.1109/TKDE.2023.3288154
   - *What it does:* DP trajectory synthesis that map-matches the input trajectories and works on
     the road network. It synthesizes in two layers, path first and then trajectory, using path-level
     information such as travel times and route choices.
   - *Where it differs:* a trusted curator publishes the synthetic dataset (central DP). There is no
     randomization on the device and no parametric route-choice model.
3. **MTNet.** Y. Wang, G. Li, K. Li, H. Yuan. *PVLDB* 16(4), 2022.
   https://doi.org/10.14778/3574245.3574277
   - *What it does:* an autoregressive, meta-learned generator over map-matched edge sequences. It
     uses road types and directions and daily and weekly periodicity, and emits the next road
     together with its travel time. Privacy comes from DP gradient clipping (central DP-SGD).
   - *Where it differs:* this is central DP on a deep model, while C1 is pure LDP with 3–25
     parameters. MTNet shows that timed road-network synthesis with DP is already published in the
     central model.
4. **LDPTrace.** Y. Du, Y. Hu, Z. Zhang, Z. Fang, L. Chen, K. Zheng, Y. Gao. *PVLDB* 16(8), 2023.
   https://arxiv.org/abs/2302.06180. Together with **RetraSyn** (Y. Hu, Y. Du et al., ICDE 2024,
   https://arxiv.org/abs/2404.11450).
   - *What they do:* LDPTrace uses a uniform grid and assumes each user holds one trajectory. Each
     user reports the length, the start and end cells and the cell transitions through OUE, with
     ε/10 for the length and 9ε/10 for the transitions. Synthesis is a Markov walk, with no time and
     no road network. RetraSyn reports K×K grid transitions through OUE under w-event LDP on
     streams, and is spatial only.
   - *Where they differ:* their report dimension grows with the grid, while C1's is fixed and does
     not depend on graph size. They have no road validity and no timing. They model one trajectory
     per user, while C1 averages over all of a user's trips.
5. **DP-WHERE.** D. Mir, S. Isaacman, R. Cáceres, M. Martonosi, R. Wright. IEEE BigData 2013.
   https://doi.org/10.1109/BigData.2013.6691626
   - *What it does:* adds central-DP noise to the few empirical distributions that drive the WHERE
     mobility simulator: home and work location, commute distance and calling times. Sensitivity is
     set by bounding each user's contribution. The output is synthetic call-record traces with time.
   - *Where it differs:* it is central, works on cell-tower locations, and has no road graph and no
     route choice. It is the structural ancestor of C1: privatize a few behavioural distributions,
     then run a mechanistic simulator.
6. **Generic LDP and DP estimation pieces.**
   - N. Wang, X. Xiao, Y. Yang et al., "Collecting and Analyzing Multidimensional Data with Local
     Differential Privacy", ICDE 2019, https://arxiv.org/abs/1907.00782. It introduces PM and HM and
     the scheme in which each user samples k of d attributes, and applies it to LDP SGD for linear
     and logistic models.
   - G. Bernstein and D. Sheldon, "Differentially Private Bayesian Inference for Exponential
     Families", NeurIPS 2018, https://arxiv.org/abs/1809.02188. It fits exponential families from
     sufficient statistics with Laplace noise, in the central model.
   - J. Duchi and F. Ruan, https://arxiv.org/abs/1806.05756. They give instance-specific rates for
     locally private estimation.
   - *Where these differ:* they are domain-free. C1's randomizer is exactly Wang et al.'s scheme
     with k = 1. "LDP estimation of an exponential family from noisy moments" therefore cannot be
     C1's claimed contribution.

**Checked and further away (no collision):**
- *Route choice with privacy.* Kweon, Sun and Park, TRR 2021, train a route-choice model by
  federated learning on 30,000 drivers; the abstract mentions no DP
  (https://doi.org/10.1177/03611981211011162). Delling et al., SIGSPATIAL 2015, "Navigation made
  personal", learn per-driver cost functions from GPS traces by coordinate descent on the device,
  with no formal privacy (https://doi.org/10.1145/2820783.2820808). Three queries found **no DP or
  LDP estimation of a recursive-logit, path-size-logit or multinomial-logit route model**. Author D
  expected such a central-DP version to exist; that was not confirmed.
- *User-level and federated learning.* Ahuja, Ghinita and Shahabi, EDBT 2020: DP-SGD for
  next-location prediction (https://openproceedings.org/2020/conf/edbt/paper_54.pdf). FGLP, arXiv
  2106.08946: federated location prediction. LDP for regret minimization in reinforcement learning,
  arXiv 2010.07778: online RL, not inverse RL.
- *Road-network DP perturbation.* DPMM (Haydari et al., ACSAC 2022,
  https://doi.org/10.1145/3564625.3567974) adds planar Laplace noise to the endpoints and picks the
  travel path between sampled waypoints with the exponential mechanism. It perturbs each trajectory
  and fits no parametric model.
- *LDP trajectory work, 2021–2026.* Cunningham et al. (PVLDB 2021, n-grams over a POI hierarchy);
  SVD-based LDP synthesis (APWeb-WAIM 2025); TraCS (arXiv 2412.00620); personalized-LDP synthesis
  (IEEE 2023, document 10293088); real-time LDP publishing (*Entropy* 2026); poisoning of LDP
  trajectory protocols (arXiv 2503.07483). All of them randomize cells, n-grams, transitions or
  points. None collects per-user route or time moments, and none synthesizes on a road graph.
- *Central-DP synthesis.* PrivTrace (USENIX Security 2023, arXiv 2210.00581), AdaTrace (CCS 2018,
  10.1145/3243734.3243741), DP-Star (IEEE TMC 2018, 10.1109/TMC.2018.2874008) and DPT (PVLDB 2015,
  10.14778/2809974.2809978) all build grid or Markov models on a trusted server.
- No hit was found for calibrating a traffic simulator or route-choice model from DP or LDP
  aggregate moments, nor for LDP collection of detour ratio, road-class shares or speed ratios.
- *Correction to `20_candidates.md`.* arXiv 2202.03325 (Chen, Leahy, Jones, Hale) is not about
  traffic. It gives DP for symbolic trajectories and Markov-chain state sequences through a
  Hamming-distance automaton, evaluated on English words, and estimates no choice parameters.

### Verdict

**NOVEL COMBINATION.** Every piece is published:
- LDP mean estimation with a sampled coordinate (Wang et al. 2019).
- Maximum-entropy inverse RL and recursive logit, fitted by feature matching (Ziebart et al. 2008;
  Fosgerau, Frejinger, Karlström 2013).
- LDP plus maximum-entropy IRL trajectory generation, but from perturbed locations
  (GeoPM-DMEIRL 2024).
- Privatized behavioural distributions that drive a simulator (DP-WHERE 2013, central).
- Timed road-network DP synthesis (MTNet 2022 and PUTS 2023, both central).

No published work estimates route-choice and timing parameters from user-level LDP moment reports
and then synthesizes timed, road-valid trajectories.

The combination solves a problem that neither side solves alone. LDP synthesizers estimate
frequency tables whose size grows with the map, so at n ≈ 91 the noise swamps them. Route-choice
estimators need the raw trajectories.

It is not a CLOSE VARIANT. GeoPM-DMEIRL differs in what is randomized (locations rather than a
bounded moment vector) and in how the model is fitted (a deep reward from noisy demonstrations
rather than a moment match with known noise variance), not in a single detail.

### Confidence

**Medium.** What I could not verify:
- **GeoPM-DMEIRL.** The abstract and method are paywalled, and Crossref, OpenAlex and Semantic
  Scholar have no abstract, so my description comes from search-engine summaries. If GeoPM in fact
  randomizes per-user features rather than locations, or claims user-level LDP with a time model,
  the verdict moves to CLOSE VARIANT. Reading this paper is the first check before any write-up.
- **Transport venues.** The TRB compendium, Transportation Research Part B and C, and hEART are
  poorly indexed for "differential privacy" combined with "recursive logit", so a short conference
  paper on DP route-choice estimation could exist undetected.
- **Not re-checked or only partly read.** I did not search Chinese-language journals. I read
  DPIL-Traj and Kweon et al. at abstract level only. I did not re-check the *Mathematics* 2024
  routing paper or arXiv 2501.10934 named by the brainstorm authors.

### Must-cite list

1. Du et al., **LDPTrace**, PVLDB 2023, cited together with RetraSyn (ICDE 2024): the LDP synthesis
   baseline whose map-sized frequency tables C1 replaces.
2. Huang et al., **GeoPM-DMEIRL**, FGCS 2024: LDP plus maximum-entropy IRL generation, and the first
   "already done" objection a reviewer will raise.
3. Sun et al., **PUTS**, TKDE 2023, cited together with MTNet (PVLDB 2022): timed road-network DP
   synthesis, in the central model.
4. Wang et al., **ICDE 2019**, sampled-coordinate PM/HM for LDP learning, cited together with
   Ziebart et al. 2008 and Fosgerau et al. 2013 as the model side: the generic recipe that C1
   instantiates.

Also recommended: DP-WHERE (BigData 2013), the central-DP ancestor of the "few behavioural knobs
drive a simulator" design.

### Which specific feature of C1 would be the claimed contribution

- **The randomized object.** Each user sends one coordinate of a user-level average of
  route-choice sufficient statistics. The statistics are clipped against a per-trip reference
  derived from the map: the fastest path between the same endpoints and the OSM free-flow speed.
  Published LDP trajectory work randomizes locations, cells, n-grams or transitions, and no paper
  found collects route-choice moments under LDP. The map-derived reference works as a control
  variate that narrows the public clipping box. Generic recentring is known; the per-trip map
  reference is what would be new. The report dimension does not depend on graph size.
- **LDP feature-matching inverse RL.** The road-graph route model (maximum entropy or recursive
  logit, or a Boltzmann walk) and the timing model are fitted to debiased LDP moments using their
  known noise covariance. The fit shrinks toward an OSM-only prior, and a public n·ε² rule decides
  how many moments are asked. GeoPM-DMEIRL fits a deep reward to perturbed demonstrations, and PUTS
  and MTNet are central.
- **Timed, road-valid synthesis with an exact likelihood under user-level pure LDP.** The generator
  combines a departure density, per-edge speed factors and an exact `sequence_log_prob`. No LDP
  synthesizer found models time or uses the road graph, and the road-network synthesizers that do
  model time are all central.
- **Not claimable.** LDP estimation of exponential families, and the sampled-coordinate PM itself
  (Wang 2019; Duchi), are known. So is bounding each user's contribution as such (standard in
  central DP and DP-FedAvg), and so is the general idea of privatized behavioural knobs driving a
  simulator (DP-WHERE). The evidence has to be the measured gain over the OSM-only prior arm, not
  attack numbers.

## Search log (18 queries, abridged)

| Direction | Queries | Outcome |
|---|---|---|
| 1. DP or LDP route-choice and discrete-choice estimation | DP + route choice + recursive logit; DP + discrete choice + multinomial logit + transport; federated + discrete choice + route/mode choice; LDP + route/driver preferences + navigation | No DP estimator found. Kweon 2021 (federated, no DP); Delling 2015 (non-private per-user preferences) |
| 2. Maximum entropy, exponential family, inverse RL under DP | DP inverse RL + trajectory generation + road network + maximum entropy; LDP + exponential family + sufficient statistics + maximum entropy; LDP + inverse RL/apprenticeship + feature expectations; "Geo-Piecewise Mechanism" | GeoPM-DMEIRL 2024; DPIL-Traj 2025; Bernstein & Sheldon 2018 (central) |
| 3. LDP low-dimensional mobility summaries | LDP + trip length / travel time / departure time + piecewise mechanism; LDP + travel time / traffic speed on road segments | Only LDPTrace-style OUE length histograms; traffic-speed monitoring (central or cryptographic) |
| 4. Federated and user-level learning | user-level DP + federated next-location / route prediction + DP-FedAvg (plus the federated query in row 1) | Ahuja 2020 (central DP-SGD); FGLP 2021; no route-choice model |
| 5. LDP synthesis on a road network | LDP + road network + trajectory synthesis/generation; LDP + road segments/edges + map-matched synthesis; DP + map-matched edge sequences + autoregressive generator; PUTS | PUTS 2023 and MTNet 2022 (both central); DPMM 2022; no LDP road-network synthesizer |
| 6. Known neighbours and 2024–2026 follow-ups | LDP trajectory synthesis 2025–2026; DP mechanistic mobility models (EPR, TimeGeo, gravity); DP calibration of traffic simulators; direct abstract fetches of LDPTrace, RetraSyn, PrivTrace, AdaTrace, DPT, DP-Star | Neighbours verified; SVD-LDP 2025, TraCS 2024, *Entropy* 2026; DP-WHERE 2013; no DP simulator calibration |
