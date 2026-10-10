# Ideation round 3: ONE new protection mechanism for trajguard (shared task file)

Date 2026-10-09. Scratch folder `.brainstorm/r3/` is local only and never committed.
Everything written here is raw English material. Rules for every agent:
- Paths are relative to the repo root (your working directory). Read this file, then
  only the inputs your role names. Write only the output file your role names. Never
  edit tracked repo files. No code execution is needed; the shell has no Python.
- Your reply to the orchestrator is at most 15 lines; details go into your file.
- Be honest about noise: n = 91 users under pure LDP is tiny. Never claim that an
  estimate survives without a back-of-envelope variance argument.
- Later stages (consolidation, novelty check, evaluation, writing, review) get their
  own small task files 02_..., 03_..., which build on this one.

## 1. Goal and hard requirements
Find ONE new protection mechanism (modules allowed) for the trajguard benchmark.
- R1 Output: synthetic routes that are valid paths on the OpenStreetMap (OSM) road
  graph, each with a departure time and a time per road segment.
- R2 Privacy: pure epsilon-LDP at USER level. The unit is one user's whole data in
  the collection period; the report distribution must differ by at most e^epsilon
  between any two possible users. No shuffler, no secure aggregation and no trusted
  curator in the core argument (allowed only as an optional extension that the
  guarantee does not need).
- R3 One report per user per collection period. A multi-round protocol must use
  disjoint user cohorts. One report may bundle several parts if their epsilons sum
  to the user's total epsilon, but both earlier evaluations found that splitting
  epsilon never pays at n = 91 (baseline X8); prefer one part.

## 2. Settled decisions (do not reopen)
- S1 The public prior may contain only OSM data and cited published constants
  (no other dataset, nothing derived from Geolife).
- S2 Evidence for large n comes from a parameter-recovery simulation (a population
  with known parameters, n up to 10,000), because Geolife has only 182 users, of
  which about 91 are training users who report.
  As in NACRT_ULDP_SINTEZA §5.5, the true parameters may come from a noise-free
  (oracle) fit on the Geolife training users plus public offsets; they only generate
  data and never enter the prior or the released model.
- S3 Benchmark: Geolife, about 91 reporting training users at rung 182, epsilon grid
  {0.5, 2, 8}.
- S4 The membership-inference attack (MIA) calls only `fit()` and
  `sequence_log_prob()` of the generator, so the mechanism must define a likelihood
  for a route (a sequence of road segments).
- S5 Synthetic output in the repo has no timestamps yet (a datamodel prerequisite,
  not a blocker for ideas).

## 3. What the new mechanism must differ from
Two designs are already planned; the new mechanism must be substantially different
from both and from every candidate and raw idea of rounds 1 and 2:
- Round 1 (docs/NACRT_ULDP_SINTEZA.md): the chosen design §4, one mechanism whose
  three modules calibrate a public road-network simulator (C3 regime vote from a
  public catalogue, C2 origin-destination shares via gravity inversion, C1
  behavioural moments plus a router); the unchosen candidates C4-C10; 20 raw ideas.
- Round 2 (docs/NACRT_ULDP_RANGI.md): the chosen design §5, rank calibration across
  and within users (K1 + K8: each phone ranks one of its trips among twins simulated
  by the public simulator and sends one coarse rank by randomized response; the
  server keeps the simulator unless a pre-registered test rejects it); the unchosen
  candidates K2-K7; 18 raw ideas.
`00_baseline.md` lists all of them plus the closest published works; exclude them
explicitly. Reviving one is allowed only through a genuinely new angle that meets a
§3.2 condition of the respective plan (summarised in `00_baseline.md`); name the
condition. Note: the five round-2 lens directions (time-first, whole synthetic users,
one sampled trip per user, multi-round cohorts, compressed local description) are
explored; do not repackage them.

## 4. Lenses (unexplored directions; one per brainstormer)
Round-1 raw ideas carry ids A.1-E.4, round-2 raw ideas R2-A.1 to R2-E.4; raw idea
C.1 is not candidate C1. Round-3 lenses are R3-A to R3-E.
The baseline's §9 direction map lists, per lens, what earlier rounds already took;
read it before writing. The "taken" lines below are its summary and are binding.
- R3-A Graph-first: the road graph itself carries the report, with the time
  component attached to edges (per-segment times) or to hierarchy levels. Must say
  how the enormous OSM domain of Beijing is reduced by public structure before any
  LDP report, and what one user's whole data becomes. Taken: edge, transition and
  flow oracles (C10, LDPTrace-style, the user-level lift of rn_ldp_synth, X7),
  frequency oracles over a public road hierarchy (C8, AHEAD, Yang 2020's trie,
  Cunningham 2021), spectral fields (C6), cordons (A.3), via-points and corridors
  (K4, Knapen 2016). Open: routing hierarchies (contraction hierarchies, shortcuts,
  hub and landmark labels), path-space encodings over them, graph coarsening and
  sampling driven by public structure only, and anything else §9 marks open.
- R3-B Attack-first (the adversary's view): the attack that applies to a synthesizer
  in this benchmark is the MIA through `fit()` and `sequence_log_prob()` (the
  likelihood of a route shape); reidentification by dynamic time warping runs only on
  perturbation mechanisms, never on synthetic output. Design a report and a release
  whose structure is useless for linking any single user while still carrying
  population structure, taking as design drivers the MIA and the stronger attacks a
  reviewer could run on the released model and routes (reconstruction, attribute
  inference, linkage that uses released routes as a gallery). The formal guarantee
  stays user-level epsilon-LDP; attack resistance is a driver, not a substitute.
  Taken: round-1 lens D already designed backwards from the attacks (its attack
  analysis, the distance-to-closest-record bound, the P4 safeguard kit); build on
  that, do not redo it. Not allowed: a prior-only or flat likelihood that blinds the
  MIA by construction (K1 at n = 91, X11) and releasing one object per user (R2-E.3,
  K7's epsilon-8 option, which is LDP private sampling). Call out any drift there.
- R3-C Utility-first (query-driven): start from the utility the thesis plans to
  report (travel-time Wasserstein-1 distance within each departure period, P12;
  origin-destination shares; trip duration and speed distributions; the synthetic
  utility metrics P2, not built yet) and derive the minimal per-user statistic that
  pins those quantities down under user-level LDP (frequency, mean and quantile
  oracles, sufficient statistics). The synthesis is a consequence. Must say which
  queries survive at n = 91 and which only at n = 10,000. Taken: C1 and A.1 (a
  maximum-entropy fit to LDP-estimated moments, Bernstein and Sheldon), C2 and B.2 (a
  minimum-KL origin-destination fit under LDP margins, L-SRR), CALM, LoPub,
  Calibrate, and "simulate, perturb, match" (Sakong and Zentefis, Xiong 2023). So
  maximum-entropy matching of moments is not open; the open angle is which other
  statistic and which other matching step (for example the user's own contribution
  to the metric as the report, quantile matching, reweighting of simulator output).
- R3-D Semantic layer: OSM land use, points of interest, building and amenity tags
  form the public prior. Home and work anchors are the most sensitive part of a
  user's data: say precisely how the report avoids revealing them. Taken: D.4 and
  C4 (day-chain types, home-work relation classes, anchors drawn from OSM land use;
  return condition Cond-C4), B.3 and E.4, R2-A.3 and K2-W (dwell class plus OSM
  points of interest and opening hours turned into purpose and destination), K5's
  modal cell with its land-use ablation, DP-WHERE, TimeGeo. So activity chains and
  anchor types as the report are not open. Open: the OSM semantic tags as the report
  alphabet instead of the trip chain (for example which amenity or land-use classes
  a user's routes pass or stop at, which road classes they prefer), OSM-derived
  attractiveness as a public generative prior with one user-level correction, and
  anything else §9 marks open. Reviving C4 needs Cond-C4 named and a new angle.
- R3-E Robust statistics (wildcard, may combine lenses): n = 91 is tiny and per-user
  trip counts are undocumented (fit sees about 9 matched trips per user on average;
  the distribution of counts is not public, X5, F2, F8), so the estimator matters as
  much as the report. Medians, quantiles, trimmed and Huber-type estimators,
  bounded-contribution clipping, poisoning resistance of LDP aggregates, the
  trade-off between bias from clipping and variance from noise, self-normalising
  reports, estimating the per-user count law itself. Taken: K1 + K8 and K1's
  sequential form, R2-D.1 (a median bit plus a re-centring cohort, close to Joseph
  2019), adaptive LDP quantiles with one report per user (Aamand 2025, Liu and Hu
  2026, Penso 2025), the user-level templates of Acharya, Liu and Sun 2023, Kent
  2024 and Zhao 2024, C1's clipped boxes and X4's caps. The direction here is which
  statistic and which estimator, not the simulator-calibration protocol.
Each brainstormer may borrow from other lenses but delivers at least three ideas in
its own direction.

## 5. Brainstormer output
File `.brainstorm/r3/10_ideas_R3-<letter>_<lens>.md`, 3 to 5 ideas, each at most about
40 lines, with these fields:
1. Name and a one-sentence pitch.
2. The single user report: what the client computes locally and what it sends
   (domain size or bits).
3. Privacy: why the whole report is epsilon-LDP at user level (proof sketch in a few
   lines) and how epsilon is split, if it is.
4. Server: what is estimated, what comes from the public prior, and how road-valid
   routes with departure time and per-segment times are synthesised.
5. `sequence_log_prob`: how the likelihood of a route is computed.
6. Estimable at n = 91 for epsilon 0.5 / 2 / 8 (which quantities survive the noise,
   with a rough variance argument) versus only at n = 10,000.
7. Closest known work and the precise difference; also the difference from the §4
   design of round 1, the K1 + K8 design of round 2, and from C4-C10 and K2-K7
   (cite ids from `00_baseline.md`).
8. Main risk or failure mode.
End the file with a three-line self-ranking.
Reply (at most 15 lines): one line per idea (name plus its most novel element) and
your top pick.

## 6. Baseline agent (runs first; output `00_baseline.md`, at most about 280 lines)
Inputs (line numbers are approximate; use `grep -n '^#'` to confirm):
- docs/NACRT_ULDP_SINTEZA.md: §1 (lines 64-97), §3 with §3.2 (110-166), §4 (167-338),
  §8.1 prerequisites P0-P5 (532-550).
- docs/NACRT_ULDP_RANGI.md: §1 (78-121), §3 with §3.2 (135-200), §4 novelty outcomes
  (201-278), §5 chosen design (279-371), §9.1 prerequisites P10-P12 (470-488),
  §10 findings F1-F9 (539-559).
- arhiv/brainstorm_2026-10-07/ (round 1: 00_briefing, five 10_ideas files,
  20_candidates, three 30_novelty files, 40_evaluation) and
  arhiv/brainstorm_2026-10-07_krog2/ (round 2: 00_baseline, five 10_ideas files,
  20_candidates, three 30_novelty files, 40_evaluation, 45_digest). Read the
  candidate and novelty files closely; skim the raw idea files for the one-line
  exclusion list; the round-2 00_baseline already condenses round 1 and may be reused.
Sections of `00_baseline.md`:
1. Gap and constraints from both plans' §1 (at most 25 lines).
2. The two chosen designs: round 1 §4 (modules, user report, user split instead of an
   epsilon split, privacy argument, `sequence_log_prob`) and round 2 §5 (twins, the
   one coarse rank, the pre-registered test, recalibration, privacy argument,
   `sequence_log_prob`); at most 40 lines together.
3. Exclusion list: all 20 round-1 raw ideas and all 18 round-2 raw ideas, one line
   each (id, name, core mechanism, which candidate it was merged into).
4. Candidates C1-C10 and K1-K8: one or two lines each with the novelty verdict, the
   evaluation score and the closest works.
5. Closest published works found in rounds 1 and 2: one deduplicated table (short
   reference, year, what it does, link if known).
6. The §3.2 conditions of both plans for returning to unchosen candidates (condensed,
   cite each condition by its name or number).
7. Findings F1-F9 of round 2 about the round-1 design, condensed (at most 10 lines).
8. Repo facts a mechanism designer needs (generator interface, datamodel, map,
   Geolife numbers, evaluation harness), carried over from the round-2 baseline §7
   (at most 30 lines), plus the already planned prerequisites P0-P5 and P10-P12 in at
   most 8 lines so that new ideas can say which they share.
9. Direction map: for each lens R3-A to R3-E of §4 in this file, which earlier ideas or
   candidates already touch it and which angles remain open.
10. Lessons from the round-1 and round-2 evaluations: what sank candidates (at most
    12 lines).
Reply (at most 15 lines): line counts per section, the three most dangerous overlaps
each lens must avoid, and anything in the inputs that contradicts this task file.
