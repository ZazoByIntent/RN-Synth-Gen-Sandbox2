# Novelty check G2: K2, K3, K4 (novelty checker, 2026-10-07)

Inputs: `01_task.md`, `03_novelty_task.md`, `20_candidates.md` (K2–K4, X1–X14), `00_baseline.md` §4–§5. Raw English material.
Marks: **(abs)** abstract or landing page opened in this session; **(snippet only)** judged from a search-engine summary (publisher
page blocked or not opened); **(round 1)** opened in round 1, link in `00_baseline.md` §5. Springer, Elsevier, Inderscience and two
EPFL pages refused fetching; three links resolved to the corporate web filter and were not followed. Searches: K2 19, K3 15, K4 17
queries, about 45 page fetches. Round-1 searches (LDPTrace, DP-WHERE, TimeGeo, AHEAD, PCKV, L-SRR) were not repeated.
Main news: K4's route model is published non-privately (Knapen et al. 2016), K3's motion model is close to BerlinMOD, and Google
already releases time per transport mode under user-level (central) DP. None of the three has a private precedent.

## K2 Time-budget prisms — NOVEL COMBINATION, medium confidence
**Elements and findings.**
- E1 Report (one sampled trip → GRR over duration tercile × prism tightness u = τ/T; family W adds a dwell class). The LDP part is
  standard (sample one observation, then a frequency oracle; user-level frame in Acharya et al. 2023, see K3). No LDP or DP work
  found that collects a duration jointly with its slack against the network's fastest time. u is the inverse of a per-trip
  travel-time index (actual / free-flow time) and 1 − u is the slack share of the time budget: known measures, new only as an
  LDP item.
- E2 Generator ("space follows from time": destinations from iso-time rings). Prism- and budget-constrained destination choice is
  established transport practice: PCATS/FAMOS, Thill & Horowitz 1997 (choice sets cut by a maximum travel time; snippet only),
  Yoon et al. 2012 (prism potential path areas as destination choice sets), MITO (logit destination choice that respects a
  household travel-time budget; Moreno & Moeckel 2016), network-time prisms (Kuijpers et al. 2009). TimeGeo 2016 (round 1) is
  already time-first, but its space comes from exploration-and-return, not from the network's isochrones.
- E3 Family W: travel-time-ratio budgets (Dijst & Vidakovic 2000; Schwanen & Dijst 2002; snippet only), dwell → purpose → opening
  hours are standard activity-based inputs; no LDP analogue found.
- E4 Combination (pure user-level ε-LDP time items → isochrone-ring destination generator on OSM with an edge likelihood): not
  found. A 2024 survey of DP in transport (Bhadani, arXiv 2407.15868; abs, full text read only through the fetch tool's summary)
  lists no DP work on travel times, speeds, modes, prisms or route structure.

**Queries (19).** space-time prism + DP synthetic trajectories; travel-time budget + LDP; "Time will not tell"; RATR; TLDP
re-sorting; PCATS prism destination choice; network-time prisms; isochrone destination choice + time budget; LDP dwell / stay
duration; Thill & Horowitz; Yoon et al.; isochrone + DP OD; time geography + location privacy + DP; DP activity-based demand +
time budget; LDP synthesis + road network + timestamps; LDP time use / activity duration; travel-time ratio; LDP trip duration ×
departure time; the transport-DP survey.

**Closest works.**
1. RATR, Zhang, Ye, Liu, Huang, Mao, Sun, Dong, Hu, IEEE TDSC, Nov 2025 (abs),
   https://research.polyu.edu.hk/en/publications/ratr-optimized-trajectory-release-with-temporal-local-differentia/ — temporal LDP
   (TLDP; neighbours differ by swapping two timestamps' values, snippet only) plus road-network reachability; releases each
   user's re-sorted trajectory. No time-budget statistic, no population model, no synthesis.
2. Brauer, Mäkinen, Ruotsalainen, Oksanen, "Time will not tell", CEUS 112, 2024 (abs; full text blocked),
   https://doi.org/10.1016/j.compenvurbsys.2024.102154 — client-side time-only protection: timestamp shifts under a generalised DP
   and a Markov-chain speed perturbation; each user's real path is published. No synthesis.
3. FAMOS/PCATS, Pendyala, Kitamura, Kikuchi, Yamamoto, Fujii, TRR 1921, 2005 (abs; prism-to-choice-set detail snippet only),
   https://itspubs.ucdavis.edu/publication_detail.php?id=127 — prism-constrained activity-travel simulation, survey-fitted, no
   privacy.
4. Yoon, Deutsch, Chen, Goulias, Transportation 39(4), 2012 (snippet only; IDEAS page has no abstract, publisher blocked),
   https://ideas.repec.org/a/kap/transp/v39y2012i4p807-823.html — potential path areas in a dynamic network as destination choice
   sets; no privacy.
5. Bian, Cheu, Guzman, Gruteser, Kairouz, McKenna, Roth, arXiv 2407.03496, 2024 (abs + text), https://arxiv.org/abs/2407.03496 —
   Google EIE: trip count, distance and duration per mode and region under user-level DP (on-device clipping, central Laplace via
   federated analytics). Time aggregates under user-level DP exist, but central and without a generator.

Also (abs): MITO, https://www.mos.ed.tum.de/tb/forschung/models/travel-demand/mito/ ; Kuijpers, Miller, Neutens, Othman, Dagstuhl
08471, 2009, https://drops.dagstuhl.de/entities/document/10.4230/DagSemProc.08471.2 . DP-WHERE 2013 (round 1) is the central-DP
"few private knobs drive a simulator" ancestor. Not close (abs): HRNet 2024, DP-STTS 2024 (arXiv 2408.12842), Zhu et al. TKDE 2026
(spatio-temporal point perturbation): central or per-point, no time budget.

**Must claim.** The first pure user-level ε-LDP release of time-budget items (duration × prism tightness, optionally dwell) in which
no spatial quantity is released: trip length and OD distance are derived from the time items through the public time-dependent
network's isochrones, with an edge likelihood the MIA can query.
**Must avoid claiming.** Prism- or budget-constrained destination choice (PCATS, Thill & Horowitz, Yoon et al., MITO); "temporal
LDP for trajectories" as a first (TLDP/RATR 2025, Brauer 2024); u as a new behavioural measure (inverse travel-time index that
folds C1's speed ratio and a detour, as `20_candidates` admits); time-first generation as such (TimeGeo); any spatial gain at
n ≈ 91 without the ring-kernel vs gravity ablation on the same items (X10).
**Would a small change raise it?** No change makes it NOVEL. The defensible core is the derivation (space from time), so the
ring-kernel vs gravity ablation is the key evidence, not an optional reviewer request. Dropping family W costs no novelty (all its
parts are standard and no metric sees purpose). Field 7 should add MITO, Yoon et al. and Thill & Horowitz.

## K3 Clock-sampled speed states — NOVEL COMBINATION (narrow), medium confidence
**Elements and findings.**
- E1 Report (speed state at one time-uniform second of the user's travel, GRR over 4; 12 with road class at ε 8). The LDP part is
  generic: sample one of a user's observations, then a frequency oracle; Acharya, Liu, Sun 2023 formalise user-level LDP with m
  samples per user and beat the one-sample baseline in some regimes. No LDP trajectory paper samples by time, but the identity
  behind it is textbook (a trip's mean speed is the time-weighted mean of its instantaneous speeds; traffic-flow theory's time-mean
  vs space-mean speed), so it must not be claimed.
- E2 Estimand (time shares per speed state × road class): known in emissions modelling as operating-mode distributions (fraction
  of time per speed/power bin and road type, EPA MOVES; snippet only). Under user-level privacy, Google's Environmental Insights
  Explorer releases duration per mode and region (Bian et al. 2024, central DP).
- E3 Generator (semi-Markov speed clock with public holding times on OSM, road class tied to the state, forward-algorithm
  likelihood). Markov-chain driving-cycle synthesis is mature (Lee & Filipi 2011, snippet only; Gong et al. 2011, abs; Balau et
  al. 2015, abs: a road-type chain first, then accelerations per road type, no network). BerlinMOD on OSM (documentation opened)
  already draws slow-down and stop events whose probabilities depend on the edge's speed limit and on the road categories of
  consecutive segments, with exponential waits. The joint state–path HMM exists for inference (Chen & Bierlaire 2015, joint mode
  detection and map matching; snippet only). Brauer et al. 2024 perturb speeds with a Markov chain per trajectory.
- E4 Combination (pure user-level LDP time shares → jump-chain weights ν ∝ π̂/m of a state-dependent router with an exact
  likelihood and per-segment times with stops): not found.

**Queries (15).** LDP + speed distribution / driving cycle / telematics; LDP + transport mode share; LDP + crowdsourced traffic
speed; Markov-chain driving cycles (Lee & Filipi); EPA MOVES operating modes; BerlinMOD generator (twice); LDP + one random time
point per user; HMM speed state + route generation + privacy; stops-and-moves + DP synthesis; driving cycles conditioned on road
type; user-level LDP distribution estimation; joint mode detection + map matching; multimodal synthetic trajectory generators;
Brauer's speed perturbation.

**Closest works.**
1. Bian et al. 2024, arXiv 2407.03496 (abs + text), https://arxiv.org/abs/2407.03496 — user-week DP time and distance per mode and
   region; central Laplace after on-device clipping; mode labels, no speed states, no generator, not LDP.
2. Brauer et al. 2024, CEUS 112 (abs), https://doi.org/10.1016/j.compenvurbsys.2024.102154 — Markov-chain speed perturbation of
   each published trajectory, client side; no population law, no synthesis.
3. Balau, Kooijman, Vazquez Rodarte, Ligterink, SAE 2015-01-0488 (abs), https://saemobilus.sae.org/articles/stochastic-real-world-
   drive-cycle-generation-based-a-two-stage-markov-chain-approach-2015-01-0488 — road type → speed coupling (the reverse of K3's
   state → road class), no graph, no privacy. Also Gong et al., SAE 2011-01-0880 (abs).
4. BerlinMOD, Düntgen, Behr, Güting, VLDB J. 18, 2009 (abs), and its OSM implementation
   https://docs.mobilitydb.com/MobilityDB-BerlinMOD/master/ch02s07.html (opened) — stop and slow-down events by speed limit and road
   category with exponential waits; hand-set constants, no privacy, no likelihood.
5. Acharya, Liu, Sun, AISTATS 2023 (abs), https://proceedings.mlr.press/v206/acharya23a.html — user-level LDP discrete distribution
   estimation; K3's one-sample GRR is their baseline.

**Must claim.** A pure user-level ε-LDP time-share item for speed states, and a generator whose clock reproduces the private time
shares exactly (jump weights ∝ π̂_s/m_s with public holding times) while road classes follow the state; an exact forward-algorithm
likelihood; per-segment times including stop spells, which fill the empty time field (S5, P1).
**Must avoid claiming.** Time-weighted shares (MOVES, traffic-flow theory), Markov speed synthesis (driving cycles since Lin &
Niemeier 2003), road-category stop events on OSM (BerlinMOD), user-level DP time-by-mode statistics (Google EIE), temporal
trajectory perturbation (Brauer, TLDP/RATR), and spatial utility without the reach rule (routes then depend on the private numbers
only weakly). At n ≈ 91 the item measures the mode mix (X10), which Google already releases under central user-level DP.
**Would a small change raise it?** Not to NOVEL. The reach rule (destinations from K2's ring kernel at τ* = T·ū/v_car) is the only
change that lets the private items shape space as well as time. Standalone, K3 is best presented as a time-and-stops module (for
K2 or for §4's C1 router), not as a mechanism of its own. Field 7 should add BerlinMOD and Bian et al. 2024.

## K4 Via-point route structure — NOVEL COMBINATION, medium confidence (the route model itself is published)
**Elements and findings.**
- E1 Statistic (family S: number of maximal near-shortest pieces, plus a loop class). Direct non-private precedent missed by
  `20_candidates`: Knapen, Hartman, Schulz, Bellemans, Janssens, Wets 2016 test exactly the hypothesis that a utilitarian route
  "consists of a small number of concatenated least cost paths", give an algorithm for minimum path decompositions (split-vertex
  suites), report decomposition-size distributions from GPS traces for multimodal person movements and car trips, and propose
  using that distribution for route choice set generation; split vertices are way points. Hartman, Knapen, Bellemans 2017
  (Procedia CS) enumerate all minimum decompositions; Knapen, Hartman, Bellemans 2020 (FGCS 107) use them in route choice models
  (both snippet only). K4's greedy split at τ = 0.05 is a variant of this statistic; the loop class is new (Knapen's hypothesis
  covers utilitarian trips).
- E2 Window variant (one RR bit "a random window is near-shortest" → via intensity λ) measures local optimality, a known route
  property: Abraham, Delling, Goldberg, Werneck 2013 (single-via-vertex alternatives that are locally optimal); Fischer 2020
  (choice sets of locally optimal routes, "travellers acting rationally on local scales").
- E3 Generator (concatenated near-shortest walks through public anchors, offset kernel around the OD axis, loops, corridor
  waypoints). Precedents: via-vertex routing (Abraham et al.), intermediate-destination route generation (Knapen et al.),
  anchor-based route choice (Manley et al. 2015: major urban features act as anchors; shortest paths predict poorly), the OD
  ellipse that bounds routes (Lima et al. 2016), BerlinMOD leisure trips with 1–3 destinations. Corridor family: subnetworks of
  familiar corridors (Frejinger & Bierlaire 2007) and mental representation items (Kazagli, Bierlaire, Flötteröd 2016), both
  snippet only.
- E4 Privacy (one trip, GRR over 4 classes): standard. LDP/DP route work releases paths, not structure: DPMM 2022; Yang et al.
  2020 hot paths (LDP + secret sharing, per trajectory); a Sogang University thesis on LDP for sensitive sub-paths with
  variable-length windows on road networks (snippet only; its page resolved to the corporate web filter). The combination (a
  user-level LDP route-structure law calibrating a via-point generator with an exact likelihood) was not found.

**Queries (17).** via point + route generation + LDP; route decomposition into minimum shortest paths; LDP frequent sub-trajectories
/ popular routes; DPMM waypoints; minimum path decompositions (Hartman et al.); anchor-based route choice; mental representation
items; path decomposition enumeration (Knapen et al. 2020); via-node alternative routes; DP + route choice estimation; map-based
random waypoint (ONE simulator); loop / round trips; habitual routes (Lima et al.); LDP top-k paths 2024–25; via-node choice-set
generation; subnetworks (Frejinger & Bierlaire); local optimality of observed routes.

**Closest works.**
1. Knapen et al., "Determining structural route components from GPS traces", TR-B 90:156–171, 2016 (abs),
   https://ideas.repec.org/a/eee/transb/v90y2016icp156-171.html — same statistic, same use, non-private; no loop class, no
   generator likelihood.
2. Haydari, Chuah, Zhang, Macfarlane, Peisert, DPMM, ACSAC 2022 (abs), https://its.berkeley.edu/node/5589 — per trajectory: planar
   Laplace on O and D, sampled waypoints, exponential mechanism over candidate paths; releases each user's perturbed path, no
   population law, no time.
3. Abraham, Delling, Goldberg, Werneck, "Alternative routes in road networks", ACM JEA 18, 2013 (abs),
   https://www.microsoft.com/en-us/research/?p=165224 — single-via-vertex locally optimal alternatives; algorithmic.
4. Fischer, "Locally optimal routes for route choice sets", TR-B 141:240–266, 2020 (abs), https://arxiv.org/abs/1909.08801 — K4's
   window bit estimates the same property, privately.
5. Manley, Addison, Cheng, JTG 43:123–139, 2015 (abs), https://ideas.repec.org/a/eee/jotrge/v43y2015icp123-139.html — anchor-based
   routing in about 700,000 minicab routes; the behavioural basis for vias on major roads.

Also (abs): Lima et al. 2016, J. R. Soc. Interface, https://pmc.ncbi.nlm.nih.gov/articles/4843678 (few habitual routes per driver,
routes inside an OD ellipse); Zhu & Levinson 2015, PLoS ONE, https://pmc.ncbi.nlm.nih.gov/articles/PMC4534461/ (34 % of trips and
13.5 % of commutes on the shortest-time path, about 40 % within 10 %); Yang et al. 2020, IEEE TSC, https://arxiv.org/abs/2012.13807 .

**Must claim.** The first pure user-level ε-LDP estimate of a route-structure law (decomposition size into near-shortest pieces
after Knapen et al. 2016, plus a loop class), feeding a via-point generator with an exact likelihood that also produces the loops a
destination-directed walk cannot.
**Must avoid claiming.** The few-concatenated-shortest-paths hypothesis, the decomposition, via-vertex generation, local optimality,
anchors and corridor familiarity; family C as more than an LDP heavy-hitter query over a public list (it releases nothing at ε 2,
n ≈ 91).
**Would a small change raise it?** Not to NOVEL, but two changes make it sturdier. (1) A prior from cited constants (S1-clean):
Knapen et al.'s decomposition-size distributions, Zhu & Levinson's shortest-path shares, Lima et al.'s ellipse; align τ and the
cost metric with Knapen's least-cost definition or document the gap (their traces are Belgian, not Beijing). With such a prior the
ε 2 item (±0.074 per share) can correct it only where it misses by ≥ 0.15. (2) Turn the window variant into a scale profile (the
near-shortest probability per public window-length class, inside one GRR item): an estimand new under LDP that maps directly onto
local optimality. Field 7 must name Knapen et al. 2016 as the closest work.

## Notes for other groups
- Acharya, Liu, Sun 2023 (user-level LDP, m samples per user): every "sample one trip, then GRR" (X1, X2, X4) is their baseline; a
  reviewer may ask why their estimator is not used (G1: K1, K8; G3: K5, K6).
- Bian et al. 2024 (Google EIE): mode, distance and duration under user-level central DP; any K that claims the mode mix (X10: K1's
  dur, K7's speed scenario) under user-level privacy must cite it and stress pure LDP (G1).
- BerlinMOD on OSM: a non-private whole-vehicle generator with commute trips at fixed times and leisure trips to 1–3 destinations
  in the vehicle's neighbourhood or anywhere; G3 should check it against K6 and C4.
- RATR (TDSC 2025) and "Time will not tell" (CEUS 2024) are now abstract-verified (the consolidator had snippets). PrivShape (Mao,
  Ye, Hu, Wang, Huang, arXiv 2404.03873, 2024; abs) extracts time-series shapes with a trie under user-level LDP: relevant to K8's
  temporal contrasts and K1's cohort design (G1).
- Knapen et al. 2016 publish route-structure constants that any router may cite as a public prior (S1), including §4's C1.

## Summary table
| Candidate | Verdict | Confidence | Closest work |
|---|---|---|---|
| K2 Time-budget prisms | NOVEL COMBINATION | medium | RATR, IEEE TDSC 2025 (privacy side); PCATS/FAMOS 2005 and Yoon et al. 2012 (generator side) |
| K3 Clock-sampled speed states | NOVEL COMBINATION (narrow) | medium | Bian et al. 2024, Google EIE (user-level central DP time per mode); BerlinMOD (motion) |
| K4 Via-point route structure | NOVEL COMBINATION | medium | Knapen et al., TR-B 2016 (same statistic, non-private); DPMM, ACSAC 2022 (privacy side) |
