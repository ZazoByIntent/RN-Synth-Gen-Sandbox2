# Stage 6: review of the Slovenian document (builds on 01_task.md)

Role: fresh reviewer (one Opus agent) that has not seen the writing stage. You only
READ tracked files and compare them with the sources; you never edit anything. The
writer applies your review afterwards. Work in parts; never produce one response
longer than about 1,500 words.

## 1. Inputs
- The document under review: `docs/NACRT_ULDP_<IME>.md` (name given in the launch
  prompt), the diff of `CLAUDE.md` and `arhiv/README.md` (`git diff -- CLAUDE.md
  arhiv/README.md`), and `arhiv/brainstorm_2026-10-09/README.md`.
- Sources: `01_task.md` (requirements, decisions, exclusions), `05_write_task.md` §A
  (the author's binding decisions), `20_candidates.md`, `30_novelty_G1.md`,
  `30_novelty_G2.md`, `30_novelty_G3.md`, `40_evaluation.md` (§6 numbers supersede the
  earlier ones), `45_digest.md`, `00_baseline.md` §6-8.
- Style references: `docs/NACRT_ULDP_RANGI.md` (structure and tone of the previous
  plan) and the "Communication style" and "Conventions" sections of `CLAUDE.md`.

## 2. What to check
1. Fidelity to source: every number (variances, scores, epsilon values, n, line
   counts), every label and verdict, every candidate id, every cited work (author,
   year, venue, link) and every claim about Geolife or the repo must match the
   sources; list each mismatch with the document line and the source line.
2. The author's decisions in §A are reflected exactly (chosen candidate, names,
   scope, what is not reopened).
3. Completeness: all eleven sections (0-10) exist and carry the content the write
   task demands; the §3.2 return conditions, the privacy argument, the n = 91 noise
   analysis, open decisions, prerequisites and the first-session prompt are present.
4. Language: Slovenian prose, English identifiers and labels; plain language for a
   technically capable non-expert (acronyms spelled out on first use, terms
   explained, full sentences, no arrow chains or fragments, no unexplained jargon);
   consistent terminology with the earlier plans (same Slovenian terms for the same
   English concepts); no agent ids or model names; no invented references.
5. Honesty: unverified items are marked as such; search limits are stated; the
   document does not claim more than the digest supports; what Geolife can and
   cannot show is stated without overselling.
6. Accompanying changes: the CLAUDE.md status bullet and doc-map entry follow the
   existing style and say nothing false; the archive README lists the files that
   exist in `arhiv/brainstorm_2026-10-09/`; `arhiv/README.md` lists the new folder.

## 3. Output
`.brainstorm/r3/60_review.md` with: verdict (accept / accept after minor fixes /
major revision); required fixes (numbered, each with document line, the problem and
the fix); recommended fixes; minor notes; a count of facts you verified against the
sources; the three strongest and the three weakest passages.

Reply (at most 15 lines): the verdict, the number of required / recommended / minor
items, and the three most important required fixes in one line each.
