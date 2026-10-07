# Novelty-check task

Read `.brainstorm/01_task.md` (research gap and constraints) and
`.brainstorm/20_candidates.md` (the candidate list). Read nothing else in the repo.
You are assigned a subset of the candidates (named in your instructions).

For EACH assigned candidate, search the published literature with web search (arXiv,
dblp, Semantic Scholar, ACM/IEEE/VLDB/USENIX/CCS/NDSS/PETS pages, Google Scholar result
pages where reachable). Use several precise queries per candidate (method words +
"local differential privacy" + "trajectory" / "road network" / "route choice" /
"synthesis" / "federated", and the names of the closest works listed by the authors).
Budget: up to ~8 searches per candidate; stop earlier when the picture is clear.

Report, per candidate, in `.brainstorm/30_novelty_<your-part>.md` (English):
- `C<k>: <name>`
- **Closest published works** (3-6): authors, venue, year, one line on what they do,
  and one line on how the candidate differs (or does not). Include the URL you saw.
- **Verdict**, exactly one of: `EXISTS` (the same mechanism is published),
  `CLOSE VARIANT` (published work differs only in a detail; name the detail),
  `NOVEL COMBINATION` (pieces are known, the combination for user-level LDP
  road-network timed synthesis is not), `NOVEL` (no close published counterpart found).
- **Confidence** (high / medium / low) and what you could not verify.
- **Must-cite list**: the 2-4 papers any write-up of this candidate must position
  against.

Be sceptical in both directions: do not declare NOVEL after two thin searches, and do
not declare EXISTS because a paper shares three keywords. Quote the specific feature of
the published method that collides with (or differs from) the candidate.

Reply with ONLY one line per candidate: `C<k> <verdict> (<confidence>) - <closest work,
year> - <10-word reason>`.
