# Consolidation task

Read, in this order: `.brainstorm/01_task.md` (the research gap, constraints and the
idea template), `.brainstorm/00_briefing.md` (benchmark facts), then the five idea files
`.brainstorm/10_ideas_*.md`. Read nothing else in the repo.

Goal: turn 15-20 raw ideas from five independent authors into a clean candidate list
for a novelty check and a final evaluation.

1. **Cluster and merge.** Ideas that share the same core mechanism (same thing computed
   locally, same randomization, same server-side model) are one candidate; keep the
   clearest formulation and fold in the better details of the duplicates. Ideas that
   differ only in a detail become one candidate with a "variants" line.
2. **Drop** ideas that (a) violate pure user-level LDP (trusted party, per-trajectory
   budget without composition, data-dependent choices made without budget),
   (b) cannot produce road-valid timed trajectories, or (c) are clearly a known
   published method under a new name. List every dropped idea with a one-line reason.
3. **Produce 6-10 candidates**, ordered by your overall promise estimate. For each:
   - `C<k>: <name>` and provenance (which lens files / idea numbers were merged)
   - Mechanism in 8-12 lines: local computation (parameter vector + dimension),
     randomization (primitive, sensitivity bound, budget split), server side
     (aggregation, debiasing, road-graph post-processing), generation (path + departure
     time + per-segment timing)
   - Privacy argument quality: clean / needs care (why) / doubtful (why)
   - Scale: what is estimable at n~180; what needs n~10,000; degradation strategy
   - Closest known works named by the authors (just list them; the novelty check comes
     later) and the authors' own novelty guess
   - Effort (S/M/L) and the main risk
   - Your own 1-2 sentence critique (be specific: what would make it fail in the
     benchmark described in the briefing)
4. End with a compact table: candidate | privacy argument | n needed | effort |
   novelty guess | your promise score 1-5.

Write everything to `.brainstorm/20_candidates.md` (English). Reply with ONLY: the
candidate names with one line (max 25 words) each, the number of dropped ideas, and the
single sentence you consider the most important warning for the evaluator.
