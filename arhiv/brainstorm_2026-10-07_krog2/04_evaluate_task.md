# Stage 4: evaluation with a red team (builds on 01_task.md)

Inputs: `00_baseline.md` (above all §1-§2, §6, §9 and the noise cheat sheet),
`20_candidates.md` (K1-K8, cross-cutting findings X1-X14, dropped ideas), and
`30_novelty_G1.md`, `30_novelty_G2.md`, `30_novelty_G3.md`.
You are fresh: you wrote none of these. Judge them; do not defend them.

Output: `.brainstorm/r2/40_evaluation.md`.

1. Scoring. Score every candidate from 1 to 5 on each criterion, with one line of reason:
   - Novelty: start from the verdicts, adjust by your own reading of the closest works.
   - Privacy soundness: is the user-level pure-LDP argument (R2, R3) airtight? Look for
     hidden leaks: data-dependent choices, side channels, public inputs that are not
     S1-clean.
   - Requirement fit: R1 (road-valid routes with a departure time and per-segment
     times) and S4 (`sequence_log_prob` exact and affordable).
   - Evidence at n = 91 (Geolife, epsilon 0.5 / 2 / 8): what measurably moves against
     the prior arm. Be strict and use the corrected noise numbers.
   - Large-n value (parameter-recovery simulation up to n = 10,000).
   - Distinctness from the chosen §4 design (C1-C3) and from C4-C10: would a reviewer
     see a second contribution, or a module of the first?
   - Implementation cost in this repo: sessions, and prerequisites beyond P0-P5.
   - Thesis value: does it answer a research question the §4 design cannot?
   State the weights, give a weighted total and a ranking.
2. Red team: for each of the top four, the strongest attack (privacy, statistics,
   novelty, visibility in the benchmark) and whether the candidate survives it; propose
   a fix where one exists.
3. Combinations: is there ONE mechanism, possibly with modules, built from two or three
   candidates that beats every single candidate? Check that the parts share one report
   and one privacy argument and that the result does not re-tell §4.
4. Final picks: at most three options for the author, each with a one-paragraph plain
   description, the main caveats, what Geolife at n = 91 can show, what only the
   simulation can show, and the open decisions it would raise.
5. Separately, findings that matter for the chosen §4 design itself (for example X5,
   the claim that the public trips-per-user law is not publicly knowable, and related
   works the §4 design should cite).

Reply (at most 15 lines): the ranking with weighted totals, the top three picks in one
line each, and the single weakest point of your top pick. One round of pushback from
the orchestrator will follow; after it you will be asked for a short digest.
