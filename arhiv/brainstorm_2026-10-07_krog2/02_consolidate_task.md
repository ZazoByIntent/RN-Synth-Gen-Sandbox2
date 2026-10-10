# Stage 2: consolidation (builds on 01_task.md)

Inputs: `01_task.md`, `00_baseline.md` and the five `10_ideas_R2-*.md` files (18 ideas:
R2-A.1-4, R2-B.1-3, R2-C.1-3, R2-D.1-4, R2-E.1-4). Read the ideas files in full; their
§0 notes hold findings that matter for every candidate.

Output: `.brainstorm/r2/20_candidates.md` with 6 to 10 candidates labelled K1, K2, ...
(the letter K is unused in the repo; never reuse C1-C10).

Rules:
- Merge raw ideas that share a core mechanism. A candidate may also be one mechanism
  with modules that combine lenses, if the modules fit one report and one privacy
  argument. Convergences visible in the brainstormers' replies (hints, not orders):
  ranks of a real trip against public-simulator predictions (R2-C.1, R2-D.1);
  within-user coupling or copula items (R2-E.4, R2-D.4, R2-C.3); exploration-and-return
  user models (R2-E.2, R2-B.2).
- Every candidate must meet R1-R3 and S1-S5 and be substantially different from §4 and
  from C4-C10; if it revives one of them, name the §3.2 condition (Cond-C4 ... Cond-C10).
- Re-check every noise claim against `00_baseline.md` and the corrections in the ideas
  files (for example the GRR standard deviation when shares are near 1/3). Where
  brainstormers disagree, say so; do not average.

Per candidate (at most about 45 lines):
1. Label, name, provenance (raw idea ids), one-sentence pitch.
2. The single user report: what is computed locally, what is sent, domain size.
3. Privacy argument at user level (proof sketch) and any epsilon split.
4. Server: what is estimated, what is public prior, how road-valid routes with a
   departure time and per-segment times are synthesised; modules, if any.
5. `sequence_log_prob` and its cost.
6. Estimable at n = 91 (epsilon 0.5 / 2 / 8) versus only at n = 10,000.
7. Difference from §4 and C4-C10; closest known works so far.
8. Main risks, and what a reviewer will ask for (control arms).
9. Novelty-check hints: 3 to 5 search queries and the works to compare against.

After the candidates add:
- Cross-cutting findings from the ideas files' §0 notes and replies, each marked as
  verified or as a claim. Examples: privacy of a data-dependent trip choice; one sampled
  trip versus Duchi's mechanism on the user's share; heavy versus light users and user
  weighting; the control arm "ldptrace lifted to user level, one trip per user, snapped
  to OSM"; the claim that the chosen design's "public trips-per-user law" is not publicly
  knowable; `fit` receives only map-matched trips.
- Dropped ideas, one line each with the reason.

Reply (at most 15 lines): one line per candidate (label, name, provenance) and a proposed
split of the candidates into two or three groups for parallel novelty checks.
