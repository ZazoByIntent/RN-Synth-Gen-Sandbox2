# Evaluation task (sparring partner)

You are a fresh, sceptical evaluator. Read, in this order and nothing else in the repo:
`.brainstorm/01_task.md` (research gap, constraints), `.brainstorm/00_briefing.md`
(benchmark facts), `.brainstorm/20_candidates.md` (10 candidates C1-C10 with a
promise table), and the novelty reports `.brainstorm/30_novelty_*.md`.

Goal: recommend AT MOST THREE candidates to implement in the next sessions, with a
rationale a doctoral author can defend, and name what they must decide first.

## Criteria (score each candidate 1-5 on each; justify any 1 or 5 in one line)
1. **Novelty**, taken from the novelty reports (EXISTS -> 1, CLOSE VARIANT -> 2,
   NOVEL COMBINATION -> 3-4 depending on how much the combination solves, NOVEL -> 5).
2. **Privacy argument**: user-level pure LDP with a short, checkable proof; bounded
   per-user contribution; composition across components stated; no data-dependent
   choice (hyper-parameters, model structure, whether to report, how many trips) made
   without budget; metadata leaks handled.
3. **Measurable gain over a "public prior only" baseline** at the benchmark's real
   scale (about 91 reporting train users at the 182-user rung, 10 at the 20-user rung)
   and at T-Drive scale (~10,000 taxis). Name the metric that would show the gain.
   A candidate that is provably indistinguishable from its public prior at n~91 can
   still be chosen if the T-Drive story is strong, but say so explicitly.
4. **Benchmark fit**: can it implement `fit`, `sequence_log_prob(edge_seq)` (finite for
   every sequence) and `generate` with road-valid edge sequences plus timestamps; is the
   public precomputation cacheable across the 17 generators of one attack arm; runtime.
5. **Effort and risk** for one doctoral student working with an AI coding assistant,
   2-4 sessions per mechanism: S/M/L and the single most likely reason it fails.
6. **Thesis story**: does the final portfolio of <=3 read as complementary
   contributions (e.g. behavioural / demand-side / structural) rather than three
   flavours of one idea? Prefer diversity of mechanism type and of risk level.

## Red team (for the four highest-scoring candidates)
For each: (a) try to break the user-level LDP claim and say exactly where the budget
leaks if the implementation is careless; (b) name one concrete attack on the
server-side model that a careless implementation would enable (memorisation,
likelihood-ratio membership signal through `sequence_log_prob`, metadata); (c) say
what the implementer must do to close it.

## Output
Write `.brainstorm/40_evaluation.md` (English) with: the scoring table; the red-team
notes; your recommended <=3 with a defensible rationale and what each would be called
in a paper (one sentence each); the ordered list of open decisions the author must make
before implementation; the benchmark prerequisites that must be built first
(e.g. time-aware synthetic utility metrics, a "public prior only" arm, timestamps in the
synthetic payload, a T-Drive loader) with an effort guess each; and a short "what I
would NOT do and why" list.

Reply with at most 20 lines: the <=3 picks with one-line reasons, the main caveat, and
the three most important open decisions. Expect a follow-up message with pushback;
keep your reasoning so you can answer it.
