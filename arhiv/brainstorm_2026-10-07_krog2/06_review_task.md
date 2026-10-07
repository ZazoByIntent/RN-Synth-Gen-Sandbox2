# Stage 6: review of the Slovenian document (builds on 01_task.md)

You are a fresh reviewer and wrote nothing in this session. Review only: edit no file
except your output.

Under review (branch claude/ideation-rank-calibration, uncommitted; use `git status` and
`git diff`): docs/NACRT_ULDP_RANGI.md (new), the note in §0 of docs/NACRT_ULDP_SINTEZA.md,
the status bullet and doc-map entry in CLAUDE.md, the new row in arhiv/README.md, and
arhiv/brainstorm_2026-10-07_krog2/README.md.

Sources: the raw files in arhiv/brainstorm_2026-10-07_krog2/: 45_digest.md,
40_evaluation.md (including the §6 pushback round), 20_candidates.md,
30_novelty_G1.md to G3, 00_baseline.md, 01_task.md and 05_write_task.md (its §A holds the
author's binding decisions). For shared labels and terms: docs/NACRT_ULDP_SINTEZA.md.

Check:
1. Fidelity to the source. Every number, verdict, confidence, citation, link, label and
   decision in the document matches the sources; nothing is invented or overstated;
   claims the sources mark as unverified, "snippet only" or paywalled keep that mark; the
   author's decisions in §A are recorded faithfully; the writer's own inferences are
   marked as such. Spot-check at least 25 concrete facts across all sections and list
   every mismatch.
2. Language. Slovenian grammar, spelling and style; plain language for a colleague from
   a neighbouring field (CLAUDE.md, "Communication style"): technical terms and
   abbreviations explained on first use, full sentences, no arrow chains, no shorthand
   invented mid-task, terminology consistent with NACRT_ULDP_SINTEZA.md. The CLAUDE.md
   additions are in English, concise and in the style of the existing entries, and the
   status bullet respects the rule that PR history lives only in docs/HANDOFF.md.
3. Structure. Missing required sections (see 05_write_task.md), broken internal
   references, any link to `.brainstorm/`, length clearly out of proportion.

Output: `.brainstorm/r2/60_review.md`. At the top a three-line verdict; then findings
ranked by severity (must-fix, should-fix, nit), each with the file, the line or section,
the quoted problem, the source evidence and the proposed fix.
Reply (at most 15 lines): the verdict, the count per severity and the top five findings.
