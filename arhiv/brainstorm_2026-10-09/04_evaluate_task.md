# Stage 4: evaluation with a red team (builds on 01_task.md)

Role: fresh evaluator (Opus) that has seen none of the earlier stages. Inputs:
`01_task.md` (all), `00_baseline.md` §1-2, §6-8 and §10, `20_candidates.md` (all),
every `30_novelty_G*.md`. Output: `40_evaluation.md` (at most about 400 lines) and,
after the objection round, `45_digest.md` (at most 60 lines).

## Part A: scoring
Rubric, each criterion 0-5 with a one-line justification per candidate:
1. Privacy rigour: the user-level pure epsilon-LDP argument is complete (sensitivity
   of one user's whole data, the randomiser, the composition) with no hidden
   dependence on the data in the prior, the domain, the candidate sets or the
   hyperparameters.
2. Signal at n = 91: what survives at epsilon 0.5, 2 and 8 by a variance argument;
   penalise claims without one; recompute the weakest claim yourself.
3. Novelty: from the novelty label and your own reading; penalise overlap with the
   two chosen designs and with the earlier candidates (cite ids).
4. Utility of the output: road-valid routes with departure time and per-segment
   times (R1) and a defined `sequence_log_prob` (S4); does the synthesis keep the
   structure the report carries, or does the public prior dominate the output?
5. Benchmark fit: Geolife, 91 users, the planned prerequisites P0-P5 and P10-P12,
   the recovery simulation (S2); estimated implementation effort in sessions.
6. Scientific story: can one paper's worth of claims be stated and tested (what
   Geolife shows, what only the simulation shows)?
Weights: privacy rigour and signal at n = 91 count double. Report the weighted total
(maximum 40) in a ranked table.

## Part B: red team
For every candidate attack: (1) the privacy argument (find the input that breaks the
e^epsilon bound; hyperparameters chosen from data; a domain or candidate set built
from data; several reports hidden in one); (2) the estimability claim (recompute the
variance of the weakest quantity at epsilon = 2 and n = 91); (3) leakage through the
public prior or through the synthesis step; (4) benchmark gaming (flat or degenerate
likelihoods, releasing almost nothing, fitting to the attack code rather than the
attack class); (5) the strongest reason a reviewer would reject the paper. Mark each
finding fatal / serious / minor.

## Part C: combinations
Propose at most three combinations of candidates or parts (the core, the optional
part, what is gained), scored by the same rubric.

## Part D: verdict
The top three (candidates or combinations) with the caveats the author must hear,
in plain language; the single most important open decision for each.

## Objection round
The orchestrator will send you the rebuttals of the authors of the top candidates.
Answer each rebuttal in `40_evaluation.md` §6 (accepted / rejected, with reason),
update the scores (the §6 numbers supersede the earlier ones), then write
`45_digest.md`: the final top three with scores, the fatal and serious findings that
survive, caveats and open decisions, in plain language for the author (technically
capable, not an expert in every domain; no unexplained jargon).

Reply (at most 15 lines): the ranked top five with weighted totals, the fatal
findings, and the three candidates for the objection round.
