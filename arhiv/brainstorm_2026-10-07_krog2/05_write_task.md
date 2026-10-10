# Stage 5: write the Slovenian plan document (builds on 01_task.md)

Inputs, in this order: `45_digest.md`, `40_evaluation.md` (including the pushback round),
`20_candidates.md`, `30_novelty_G1.md`, `30_novelty_G2.md`, `30_novelty_G3.md`,
`00_baseline.md`, `01_task.md`. For structure, tone and shared labels also read
docs/NACRT_ULDP_SINTEZA.md §0, §3 and §8 (a template; do not copy its content) and
CLAUDE.md (sections Status, Doc map, Communication style).
The author's decisions are in §A at the end of this file and are binding.

Outputs:
1. `docs/<NAME>.md` in Slovenian (NAME in §A), with these sections:
   0. Namen, stanje in odločitve: purpose; status (ideation closed on 7 Oct 2026,
      nothing implemented); the author's decisions with the date.
   1. Raziskovalna vrzel in omejitve: the gap this mechanism fills next to the §4
      design; hard requirements R1-R3 and settled decisions S1-S5 in plain words.
   2. Kako je izbor nastal: the process in 5 to 8 lines (five lenses, 18 ideas,
      8 candidates, novelty check, evaluation with a red team and one pushback round,
      the author's choice).
   3. Banka kandidatov K1-K8: a table (label, name, one-line idea, novelty verdict and
      confidence, closest work, weighted score, status) and a subsection on when it
      would pay to return to the unchosen ones.
   4. Izidi preverjanja novosti: per candidate the verdict and the closest works with
      links; for the chosen design, what it must claim and must not claim.
   5. Izbrana zasnova: the user report, the server, how road-valid routes with a
      departure time and per-segment times are synthesised, `sequence_log_prob`, the
      privacy argument at user level (proof sketch in plain words), modules if any.
   6. Kaj lahko Geolife pokaže in kako merimo: what moves at n = 91 for epsilon
      0.5 / 2 / 8 (exact noise numbers), what only the parameter-recovery simulation
      shows, and the control arms a reviewer will ask for.
   7. Tveganja in varovala.
   8. Odprte odločitve.
   9. Predpogoji in načrt sej: shared prerequisites under their existing labels P0-P5
      (docs/NACRT_ULDP_SINTEZA.md §8.1) where they apply, new ones under new labels;
      the order of sessions as vertical slices; a prompt for the first session.
   10. Ugotovitve za zasnovo iz NACRT_ULDP_SINTEZA §4: the evaluator's separate
      findings, recorded here and not applied to that document.
   11. Viri: sources with links.
2. CLAUDE.md: one status bullet at the end of "## Status" (ideation round 2 closed on
   7 Oct 2026, the chosen mechanism in one sentence, nothing implemented, pointer to the
   new doc) and one doc-map entry in "## Doc map" in the style of the NACRT_ULDP_SINTEZA
   entry (language, what it holds, when to read it). Change nothing else in CLAUDE.md;
   CLAUDE.md stays in English.
3. `arhiv/<FOLDER>/README.md` (FOLDER in §A; one line per archived file, in Slovenian
   like arhiv/brainstorm_2026-10-07/README.md) and one row in the table of
   arhiv/README.md in the style of the brainstorm_2026-10-07 row.

Rules:
- Slovenian, plain language for a colleague from a neighbouring field (CLAUDE.md,
  Communication style): explain every technical term and abbreviation on first use;
  full sentences; no arrow chains; no shorthand invented mid-task.
- Fidelity: every number, verdict, citation and decision comes from the inputs. Mark
  claims that the inputs mark as unverified or "snippet only". Invent nothing. Keep the
  labels K1-K8, C1-C10, P0-P5, R1-R3 and S1-S5 consistent with the sources.
- Length: aim for 350 to 550 lines; use tables for parallel items.
- Touch no other tracked file. Do not commit.
Reply (at most 15 lines): files written with line counts, and anything you could not
source.

## §A The author's decisions (binding)
- Chosen mechanism (the author, 7 Oct 2026): pick 1 of `45_digest.md`, "rank calibration
  across and within users" (K1 + K8), under the conditions from the pushback round in
  `40_evaluation.md` §6: the mechanism asks no moment or vote questions, and the n = 91
  travel-time level is shown head-to-head with C1 on the same users. The two shared fixes
  (split Geolife recording sessions into trips at stops; every training user sends exactly
  one report, with a "no matched trip" answer) are prerequisites.
- NAME = NACRT_ULDP_RANGI, so the file is docs/NACRT_ULDP_RANGI.md. Choose a Slovenian
  title in the style of NACRT_ULDP_SINTEZA, for example "Načrt: umerjanje simulatorja z
  rangi pod LDP na ravni uporabnika (K1 + K8)".
- FOLDER = arhiv/brainstorm_2026-10-07_krog2. The raw files are already copied there;
  list them in its README.md.
- Writer model: Opus (you). A fresh Fable reviewer checks the document afterwards.
- Findings for the §4 design: write them in section 10 of the new document AND add one
  short note (two to four lines, Slovenian) to §0 of docs/NACRT_ULDP_SINTEZA.md that
  points to that section. Change nothing else in docs/NACRT_ULDP_SINTEZA.md.
- The unchosen final picks (whole synthetic users with hubs and exploration, K6 + K5;
  route structure, K4; the time-first combination K2 + K3) go into §3 with the conditions
  under which it would pay to return to them.
- Section 8 (open decisions) includes those named in `45_digest.md` §1 (a mixed walking
  and driving prior or an extra "much slower" bin; the rule for eligible trip pairs; a new
  metric, travel-time distance within each departure period) plus any others the
  evaluation raises.
