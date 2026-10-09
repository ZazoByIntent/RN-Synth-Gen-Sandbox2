# Stage 2: consolidation (builds on 01_task.md)

Role: consolidator (one Opus agent). Inputs: `01_task.md` (all), `00_baseline.md`
(all), the five `10_ideas_R3-*.md` files. Output: `20_candidates.md` (at most about
450 lines). Candidate ids of this round are T1-T10 (round 1 used C, round 2 used K).

Goal: merge the raw ideas (about 15 to 25) into 6 to 10 candidates that are (a)
mutually distinct in the user report or in the server estimator, (b) each meets
R1-R3 and S1-S5 or says exactly where it fails, and (c) each is explicitly different
from the two chosen designs (round-1 §4, round-2 K1 + K8) and from C4-C10 and K2-K7.

Procedure:
1. Read every raw idea; tag each with its lens and with the earlier ideas or
   candidates it overlaps (use the baseline's exclusion list and direction map).
2. Drop ideas that repackage an excluded design unless a §3.2 condition is named
   and plausible; list them in a "dropped" section with one line of reason each.
3. Merge ideas that share the same report or the same estimator; keep the strongest
   privacy argument and the most honest n = 91 analysis.
4. Where two ideas are complementary modules of one mechanism, you may propose a
   combined candidate, but say which part is the core and which is optional.
5. Keep the raw authors' numbers only if you can reproduce the variance argument in
   one or two lines; otherwise mark the number "unverified".

Candidate template (at most 45 lines each):
- id and name; one-paragraph mechanism in plain words;
- the single user report (domain, bits, epsilon split, what the client computes);
- privacy argument at user level (what changes when one user's whole data changes,
  the sensitivity, the randomiser, the composition);
- server estimation and the synthesis of road-valid routes with departure time and
  per-segment times;
- `sequence_log_prob`;
- what is estimable at n = 91 per epsilon versus only at n = 10,000, with the
  variance sketch;
- source raw ideas merged (ids);
- differences from round-1 §4, round-2 K1 + K8, C4-C10 and K2-K7 (cite ids);
- prerequisites shared (P0-P5, P10-P12) and new;
- main risks (at least two);
- three web-search queries for the novelty check.

Also write: a cross-cutting section X1-Xn (recurring themes, shared risks, common
gaps such as the n = 91 noise and the missing timestamps), and a table that ranks the
candidates by your own quick judgement (most novel element, privacy risk,
feasibility) without numeric scores.

Reply (at most 15 lines): one line per candidate (id, name, dominant lens, merged
raw ids), the number of dropped ideas, and the two candidates you think are
strongest.
