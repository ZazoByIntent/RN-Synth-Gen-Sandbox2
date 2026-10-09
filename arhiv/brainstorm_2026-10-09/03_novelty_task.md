# Stage 3: novelty check with web search (builds on 01_task.md)

Role: novelty checker (Opus with web search). Several checkers run in parallel, one
per group of candidates; the orchestrator names your group and its candidate ids in
the launch prompt. Inputs: `01_task.md` §1-3, `00_baseline.md` §4-5 (earlier verdicts
and the table of closest works), and in `20_candidates.md` only the candidates of your
group plus the cross-cutting section. Output: `30_novelty_G<k>.md` (at most about 60
lines per candidate).

For each candidate:
1. Run at least 6 web searches with varied vocabulary: "local differential privacy"
   and "LDP", "user-level", "trajectory" / "mobility" / "road network" synthesis or
   release, the candidate's own key terms, and the names of the closest works in the
   baseline table. List the queries you ran.
2. List the 3 to 6 closest works: reference, year, venue if known, link (URL or DOI),
   one line of what it does, one line of the precise difference from the candidate.
   Include works already in the baseline table when they are the closest.
3. Verdict with one of four labels and a confidence (low / medium / high):
   - EXISTS: a published work uses the same report and estimator for the same goal.
   - CLOSE VARIANT: a published work differs only in a detail (domain, noise type,
     one modelling choice).
   - NOVEL COMBINATION: the parts exist separately; their combination for
     user-level LDP trajectory synthesis does not.
   - NOVEL: no published work uses the core report or the core estimator.
4. If EXISTS or CLOSE VARIANT: what change would make it novel, in two lines.
5. One line: does the candidate after all coincide with a round-1 or round-2
   candidate or raw idea (cite the id from `00_baseline.md`)?

Rules: cite only works you actually found (URL or DOI); never invent references;
prefer peer-reviewed or arXiv sources; quote titles exactly; where a search tool is
unavailable or rate-limited, say so instead of guessing.

Reply (at most 15 lines): per candidate the label, confidence and the single closest
work; plus any candidate whose verdict depends on an ambiguity the evaluator must
know.
