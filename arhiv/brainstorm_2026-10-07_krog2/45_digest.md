# Round 2 digest: which second mechanism to build (evaluator, 2026-10-07)
Eight candidates were scored, attacked and re-scored after one pushback round (`40_evaluation.md` §6). Two shared fixes come first:
split Geolife logging sessions into trips at stops, and let every training user send exactly one report ("no matched trip" if needed).

## 1. Rank calibration across and within users (K1 + K8), recommended
- **Idea.** For one real trip the phone lets the public road-network simulator produce about 30 "twin" trips with the same route and
  departure, and reports only where the real trip ranks among them; another user instead compares a rush-hour trip with one of their
  own off-peak trips. If the simulator is right the ranks are perfectly balanced for every user, whatever their number of trips, so the
  server tests the simulator, keeps it unless the test fails, and otherwise corrects its travel times.
- **Sends** one coarse rank (3 or 4 values) by randomized response at the full ε.
- **Caveats.** At Geolife size it measures the same walk-versus-vehicle mix as C1 and C3; single-trip ranks all land in "slower" unless
  the public prior mixes walking and driving speeds; travel times are not in the route likelihood, so the membership attack sees nothing.
- **Geolife (91 users).** ε 2: the overall travel-time level, shown head-to-head with C1 on the same users; ε 0.5: nothing; the
  rush-hour comparison is too weak to see. **Only the simulation:** the test keeps its error rate for any number of trips per user, and
  the within-person rush-hour effect stays right when the people who travel at rush hour differ from the rest.
- **Novelty.** Novel combination (medium); closest Cormode & Markov 2023 (private calibration of a shared model) and Sopa et al. 2026
  (within-person estimates, central privacy only). **Decisions:** mixed walking/driving prior or an extra "much slower" bin; the rule for
  eligible trip pairs; a new metric (travel-time distance within each departure period). **Size:** about 4–5 sessions.

## 2. Hubs and exploration: whole synthetic users (K6 + K5)
- **Idea.** Synthetic people instead of separate trips. Each user reports the 5-km square where most of their trips start or end; with
  many users, also how many distinct places they visit for their number of trips. The server fits a published explore-or-return model
  of personal mobility on the OpenStreetMap graph and gives each synthetic person a main place their trips keep returning to.
- **Sends** the square by hashed randomized response; at large n also a "places × trips" class.
- **Caveats.** Needs user-level metrics (the plan's condition for whole-user ideas), measured on only about 36 test users; the main place
  reads as a home location and is almost released at ε 8; the explore-or-return constants cannot be pinned down at 91 users.
- **Geolife.** One main-place square at ε 2, only if about a third of users share it. **Only the simulation:** recovery of the
  explore-or-return constants, and whether they change trip-level metrics at all.
- **Novelty.** Novel combination (medium); closest DP-WHERE 2013 (central privacy) and Wang et al. AAAI 2018 (local report of a frequent
  place). **Decisions:** linked output and user-level metrics; the trips-per-user law asked inside the report; a one-hour public check
  first. **Size:** about 7–8 sessions.

## 3. Route structure (K4)
- **Idea.** The phone says whether one of its trips is one near-shortest stretch, several stretches joined at turning points, or a loop
  back to the start; the server builds routes as chains of near-shortest stretches between public junctions, which the §4 router cannot
  produce. **Sends** one of 4 types by randomized response.
- **Caveats.** The statistic is published (Knapen et al. 2016), so the novelty is thin; after the stay split Geolife will probably not
  differ by the needed 0.15 from published shares (30–55 % of car trips within 5 % of the shortest time; Zhu & Levinson 2015); walkers'
  routes look multi-piece under car costs, which is the mode mix again.
- **Geolife:** probably nothing reliable. **Only the simulation:** structure by trip length, popular corridors. **Novelty:** novel
  combination by the check, likely judged incremental. **Decisions:** cost per mode, published constants for the prior. **Size:** 3–4
  sessions. A time-first option (K2 + K3) scores about the same; prefer it only if time itself must be what users report.

## Findings for the §4 design
1. Sessions, not trips: stops inflate C1's travel times, round trips confuse C2, long stops mislead C3; add a public stay split first.
2. Only users with a matched trip report today, so who reports and the question allocation leak private data; all must report (+5–20 % noise).
3. C3's confusion matrix needs a trips-per-user law that no publication gives; draw C3's label from one sampled trip instead.
4. The plan's noise figures (§4.3, §4.4, §5.1) are 15–40 % optimistic; C2's 3 × 3 zones need plain, not hashed, randomized response.
5. At 91 users C1 and C3 measure the same walk-versus-vehicle mix; add a pre-registered keep-the-prior-unless-rejected test per module.
6. Cite Cormode & Markov 2023, Chopra et al. 2024, Sakong & Zentefis, Bian et al. 2024, Acharya et al. 2023, PateGail, Knapen 2016.
