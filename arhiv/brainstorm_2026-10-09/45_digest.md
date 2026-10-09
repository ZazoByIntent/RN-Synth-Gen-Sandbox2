# Round 3 digest: final verdict for the author (2026-10-09)

The evaluator's final word after the objection round; details and every number are in `40_evaluation.md` §6. Scores are out of 40, with privacy and signal counted double. ε is the privacy budget per user (smaller means more private). n = 91 is the number of Geolife users who report. SD is the noise level of an estimate: a change of about 2 SD is the smallest that can be told apart from noise. "The public model" is the shared simulator P3, built only from OpenStreetMap (OSM) and published constants.

## Final top three
1. **T3 Within-trip segment-time contrasts, 27.5.** Within one trip, the phone compares its speed on 100 m street windows lined with shops against similar plain windows of the same trip. The windows lie a few minutes apart and away from junctions and signals, and speed is measured relative to the public model. The phone sends one answer (slower, same, faster, or "no usable pair") by randomized response: it sometimes sends a random answer, which is what makes the answer private. The server learns one number, how much shop frontage slows travel, and applies it to every such segment of the synthetic routes.
2. **T1 Opportunity-rank destination law, 26.5 (27.0 with T4's relation question added, option K-α).** For one trip, the phone counts how many "opportunities" (road length or mapped places) lay closer to the start than the actual destination. It reports, again by randomized response, which third of the public travel law that count falls into. The server learns one number: how far people travel relative to what lies around them.
3. **T2 Hierarchy-ceiling route law, 26.0.** For one trip, the phone reports whether its route stayed below the main-road level used by the shortest path between its two ends. A per-trip randomization makes this answer mean the same thing for every start and end point. The server learns how often people avoid main roads and mixes in public routers that keep to lower roads.

The rest: T4 25.0 (borderline signal, confounded by where Geolife users live), T6 22.5 and T5 22.0. T5 and T6 fail the novelty test because their methods are published.

## Findings that survive
- **Fatal.** T6's report and estimator are published (Liu, Hu & Kong 2024, now confirmed from the full text). T5 is a close variant of a published one-step estimator (Duchi & Ruan 2024) and of round-1 idea B.1. T3's numeric junction form and T4's place-kind questions are close variants and must stay out (T3 has already dropped its form). No candidate has a privacy flaw: each sends one answer from a small public list, using a standard randomizer at the full budget.
- **Serious, T3.**
  - Nobody knows yet whether enough users have usable pairs; the pre-registered public check decides.
  - At ε 2 only a slowdown of about 15 % or more shows (1.6 to 2.5 SD).
  - When the slowdown is a fixed wait (crossings, parking, bus stops), its size is an average over travel modes.
  - Sessions that switch from bus to walking can spoil a pair until sessions are split at stops (prerequisite P10).
  - The membership-inference attack (which tests whether a given trip was in the training data) sees the effect only weakly, through route choice.
- **Serious, T1.**
  - Its report is the report form of round 2's rank calibration (K1), applied to destinations, so it reads as a new question inside K1 rather than a new mechanism.
  - At ε 2 it detects a wrong reach only if the public law is off by about 2.5 times in opportunity mass, which is about 1.6 times in distance.
  - The shape of the law is unverified, and only Geolife's trip-length comparison can test it.
  - On Geolife the number will probably mostly reflect how many trips are walks.
- **Serious, T2.**
  - Its test holds for any pattern of start and end points, but its estimate is exact only if the public router's settings are right.
  - Many trips will be unusable for the randomization.
  - Real avoidance of main roads may barely differ from the public model.
  - It needs an exact per-trip computation that must include the router's step limit.

## Caveats that apply to all three
- At ε 0.5 every option is just its public model. At ε 2 each moves at most one number. The membership-inference attack will sit at chance for all of them, so privacy does not rank them.
- Round 3 found new statistics, not new report protocols: T1 reuses K1's report form and T3 reuses that of round 2's within-person contrasts (K8). Only T2's randomization is new, and T2 has the weakest signal.
- Every public constant must be frozen by commit hash before the 182-user run, taken from published sources and never tuned on Geolife. This covers T1's scale, T3's frontage and window rules, T2's two target probabilities and the hierarchy.

## Most important open decision per candidate
- **T3:** shop frontage, built frontage (any building within 30 m) or stop. Decide by the one-hour public simulation and its pre-registered thresholds. Judge the share of users without pairs in the worst case over 1 to 30 trips per user, not at Geolife's average of 9.
- **T1:** file it as round 3's mechanism or as a destination question inside round 2's K1 design; my advice is the latter. Either way, verify and freeze the cited Beijing trip-distance figure that fixes the public scale.
- **T2:** decide whether the hierarchy matters at all. Before any code, compare hierarchy levels with plain OSM road classes on the public graph, and simulate how often the public model itself avoids main roads.

## Recommendation
Build T3 as the round-3 mechanism once its public check passes, and add T1 as a cheap destination question to round 2's K1 design: about 2 sessions, and the membership-inference attack can see it. If T3's check fails, take T1 (with T4's relation question, option K-α) as the round-3 pick. Keep T2 only if its public checks show that the hierarchy matters.

**Reason:** T3 is the only option that adds something neither earlier plan has: a private correction of the time structure inside routes (requirement R1, per-segment times), with an exact test that does not depend on the walk/car mix. T1 and T2 are cheaper or easier to see on the benchmark, but at 91 users they mostly re-measure that mix, and T1's report is round 2's.
