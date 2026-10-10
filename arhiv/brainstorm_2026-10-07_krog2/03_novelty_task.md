# Stage 3: novelty check with web search (builds on 01_task.md)

Inputs: `20_candidates.md` (your group's candidates in full, field 9 holds search hints;
also the cross-cutting findings X1-X14), and `00_baseline.md` §4-§5 (round-1 verdicts
and the table of closest works, so you do not repeat round-1 searches without need).

Groups: G1 = {K1, K7, K8}, G2 = {K2, K3, K4}, G3 = {K5, K6}.
Output: `.brainstorm/r2/30_novelty_<group>.md` (for example `30_novelty_G1.md`).

Method:
- Use WebSearch and WebFetch. If they are deferred tools, load them first with
  ToolSearch, query "select:WebSearch,WebFetch".
- Split each candidate into its 2 to 4 essential elements; check each element and the
  combination. Run at least 6 queries per candidate across the relevant fields: local
  differential privacy, trajectory and location privacy, synthetic mobility data,
  transport science and time geography, discrete choice and stated preference,
  statistics (calibration, rank tests, copulas), federated analytics.
- Open the abstract or the paper of every work you cite. A work judged from a search
  snippet only must be marked "snippet only".
- Verdict per candidate, exactly one of:
  EXISTS (a published method does essentially this);
  CLOSE VARIANT (a published method differs only in a detail a reviewer would call
  incremental);
  NOVEL COMBINATION (the parts are known, the combination is unpublished and meaningful);
  NOVEL (no close precedent found).
  Add a confidence: high, medium or low.
- Name the 3 to 5 closest works per candidate with year, venue, link and one line on the
  precise difference.
- Say what the candidate must claim, and must avoid claiming, to stay defensible, and
  whether a small change would raise the verdict.

At most about 60 lines per candidate. End with a table: candidate, verdict, confidence,
closest work.
Reply (at most 15 lines): per candidate the verdict, confidence and the single closest
work, plus anything that changes the picture for another group.
