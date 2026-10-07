# Ideation round 2: ONE new protection mechanism for trajguard (shared task file)

Date 2026-10-07. Scratch folder `.brainstorm/r2/` is local only and never committed.
Everything written here is raw English material. Rules for every agent:
- Read this file, then only the inputs your role names. Write only the output file
  your role names. Never edit tracked repo files. No code execution is needed.
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
  to the user's total epsilon.

## 2. Settled decisions (do not reopen)
- S1 The public prior may contain only OSM data and cited published constants
  (no other dataset, nothing derived from Geolife).
- S2 Evidence for large n comes from a parameter-recovery simulation (a population
  with known parameters, n up to 10,000), because Geolife has only about 91 users.
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
- The chosen design (docs/NACRT_ULDP_SINTEZA.md §4): one mechanism whose three
  modules calibrate a public road-network simulator: C3 regime vote from a public
  catalogue, C2 origin-destination shares via gravity inversion, C1 behavioural
  moments plus a router.
- The unchosen candidates C4-C10 and all 20 raw ideas of round 1.
`00_baseline.md` lists all of them plus the closest published works; exclude them
explicitly. Reviving one is allowed only through a genuinely new angle that meets a
§3.2 condition (summarised in `00_baseline.md`); name the condition.

## 4. Lenses (unexplored directions; one per brainstormer)
Round-1 raw ideas carry ids A.1-E.4 from different round-1 lenses; raw idea C.1 is not
candidate C1. Round-2 lenses are R2-A to R2-E.
- R2-A Time-first (transport time geography): rhythms and periodicity, activity
  schedules, stays and dwell durations, routing conditioned on departure time,
  time-dependent segment times from public constants. Time is the primary object;
  space follows from the public network.
- R2-B Whole synthetic users: synthesise entire users with several mutually consistent
  trips (anchors such as home and work, trip chains or tours, day plans, habitual
  repetition) instead of independent trips.
- R2-C Trip-level mechanisms lifted to user level by sampling ONE trip (or one day, or
  one sub-path) per user: what a single sampled trip can carry under epsilon-LDP,
  how to correct the sampling bias (users with many versus few trips), how route
  space and time bins are randomised.
- R2-D Interactive multi-round protocols: disjoint cohorts; cohort t answers a question
  the server chose from the answers of earlier cohorts (adaptive refinement,
  sequential design, adaptive candidate sets or time bins). Must say how many rounds
  n = 91 can afford.
- R2-E Local synthesis with a compressed description: each user runs a local model,
  compressor or generator on their own data and publishes a compressed descriptor
  (codebook index, sketch, latent code, a few model parameters, one synthetic route)
  through LDP; the server decodes and assembles. Codebooks may be learned only from
  the public prior (for example simulations on OSM). Wildcard: may combine lenses.
Each brainstormer may borrow from other lenses but delivers at least three ideas in
its own direction.

## 5. Brainstormer output
File `.brainstorm/r2/10_ideas_R2-<letter>_<lens>.md`, 3 to 5 ideas, each at most about
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
7. Closest known work and the precise difference; also the difference from §4 and
   from C4-C10 (cite ids from `00_baseline.md`).
8. Main risk or failure mode.
End the file with a three-line self-ranking.
Reply (at most 15 lines): one line per idea (name plus its most novel element) and
your top pick.

## 6. Baseline agent (runs first; output `00_baseline.md`, at most about 220 lines)
Inputs: docs/NACRT_ULDP_SINTEZA.md §1 (lines 59-92), §3 including §3.2 (lines
105-161) and §4 (lines 162-333); the folder arhiv/brainstorm_2026-10-07/
(00_briefing, the five 10_ideas files, 20_candidates, the three 30_novelty files,
40_evaluation). Sections of `00_baseline.md`:
1. Gap and constraints from §1 (at most 25 lines).
2. The chosen §4 design: modules, the user report, the user split instead of an
   epsilon split, the privacy argument, how `sequence_log_prob` works (at most 25
   lines).
3. Exclusion list: all 20 round-1 raw ideas, one line each (id, name, core
   mechanism, which candidate it was merged into).
4. Candidates C1-C10: one or two lines each with the novelty verdict and the closest
   works.
5. Closest published works found in round 1: a table (short reference, year, what it
   does, link if known).
6. The §3.2 conditions for returning to unchosen candidates (condensed).
7. Repo facts a mechanism designer needs (generator interface, datamodel, map,
   Geolife numbers, evaluation harness), carried over from the round-1 briefing (at
   most 30 lines).
8. Direction map: for each lens R2-A to R2-E of §4 in this file, which round-1 ideas or
   candidates already touch it and which angles remain open.
9. Lessons from the round-1 evaluation: what sank candidates (at most 10 lines).
