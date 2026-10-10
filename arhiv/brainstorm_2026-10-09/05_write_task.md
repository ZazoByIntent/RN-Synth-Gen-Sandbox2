# Stage 5: write the Slovenian plan document (builds on 01_task.md)

Role: writer (one Opus agent). You turn the round-3 material into the plan document
the repo keeps, plus three small accompanying changes. You MAY edit tracked files, but
only the four named in §2. Work in parts (one Write for the skeleton, then one Edit per
section); never produce one response longer than about 1,500 words.

## 1. Inputs
- `01_task.md` (requirements R1-R3, decisions S1-S5, lenses, exclusions);
- `00_baseline.md` §1-2 and §6-8 (gap, the two earlier designs, return conditions,
  findings F1-F9, repo facts and planned prerequisites);
- `20_candidates.md` (all six candidates T1-T6, dropped ideas, cross-cutting X1-Xn);
- `30_novelty_G1.md`, `30_novelty_G2.md`, `30_novelty_G3.md` (verdicts, closest works
  with links; the T6 addendum included);
- `40_evaluation.md` (scores, red team, combinations, verdict, §6 objection round
  whose numbers supersede the earlier ones) and `45_digest.md` (the final digest);
- §A of this file: the author's binding decisions (which candidate, names, scope);
- style references: `docs/NACRT_ULDP_RANGI.md` (the most recent plan; copy its
  section logic and tone, do not copy its content) and the "Communication style" and
  "Conventions" sections of `CLAUDE.md`.

## 2. Outputs (the only files you may create or edit)
1. `docs/NACRT_ULDP_<IME>.md` (name given in §A), in Slovenian, about 450-650 lines,
   with a table of contents and these sections in this order:
   0. Namen, stanje in odločitve (purpose; status "nothing implemented"; the
      author's decisions of 9 Oct 2026; what this plan does not reopen; how it
      relates to NACRT_ULDP_SINTEZA and NACRT_ULDP_RANGI).
   1. Raziskovalna vrzel in omejitve (the gap; R1-R3 and S1-S5 in plain words; why
      a third design next to the two planned ones).
   2. Kako je izbor nastal (the round-3 process in a few lines: lenses R3-A to R3-E,
      20 raw ideas, 6 candidates, novelty check, evaluation and objection round;
      pointer to the archive folder).
   3. Banka kandidatov T1-T6 (table: id, name, lens, report, what it estimates,
      novelty label, score before and after the objection round, fate), then §3.2
      "Kdaj bi se splačalo vrniti k neizbranim" with one named condition per
      unchosen candidate, as the earlier plans do.
   4. Izidi preverjanja novosti (per candidate: label, confidence, the closest
      works with year and link, the precise difference; the chosen design in detail,
      the others briefly; search limits stated honestly).
   5. Izbrana zasnova (the user report step by step; the server; how road-valid
      routes with departure time and per-segment times are synthesised; how
      `sequence_log_prob` is computed; the privacy argument at user level, written
      so that a reader can follow every step: what one user's whole data changes, the
      sensitivity, the randomiser, the composition, no hidden data dependence).
   6. Kaj lahko Geolife pokaže in kako merimo (noise at n = 91 for epsilon 0.5, 2 and
      8 with the variance sketch; what only the recovery simulation with n up to
      10,000 shows; control arms, metrics, what counts as evidence; why the MIA can or
      cannot see the mechanism).
   7. Tveganja in varovala (the surviving fatal and serious findings of the red team
      with the agreed safeguards; the cross-cutting rules the author adopted).
   8. Odprte odločitve (each with the options and the author's current leaning, in
      plain language, and when it must be decided).
   9. Predpogoji in načrt sej (which planned prerequisites P0-P5 and P10-P12 it
      shares, which new ones it needs with new ids continuing the numbering; the
      order of sessions as vertical slices; a prompt for the first session, in the
      style of the earlier plans' §8.3 / §9.3).
   10. Viri (every work cited in the document, with year and link or DOI; only works
       that appear in the novelty files or the baseline table; never invent).
2. `CLAUDE.md`: (a) add ONE status bullet after the round-2 bullet in "## Status",
   same style as the existing bullets (ideation round 3 closed on 9 Oct 2026, the
   chosen mechanism in one sentence, "nothing of it is implemented", prerequisites,
   pointer to the new doc); (b) add ONE doc-map entry after the NACRT_ULDP_RANGI entry
   in "## Doc map", same style (what the doc contains, the bold "Read only when ..."
   trigger naming the candidate ids and labels a user might mention). Touch nothing
   else in CLAUDE.md.
3. `arhiv/brainstorm_2026-10-09/README.md`, in Slovenian, in the style of
   `arhiv/brainstorm_2026-10-07_krog2/README.md`: a note that this is a record, not an
   instruction; one line per file of the round-3 scratch folder (the orchestrator
   copies the files; you only describe them: 00_baseline, 01_task, 02-06 task files,
   the five 10_ideas files, 20_candidates, 30_novelty_G1-G3, 40_evaluation,
   45_digest, 60_review). Say that round-3 ids are T1-T6 and raw ideas R3-A.1 to
   R3-E.4, and that the plan beats the material wherever they differ.
4. `arhiv/README.md`: add one line for the new folder in the existing list style.
5. `docs/NACRT_ULDP_RANGI.md`: exactly ONE new bullet in §8 "Odprte odločitve" as
   §A5 prescribes; nothing else in that file.

## 3. Rules
- Slovenian prose throughout; code identifiers, file names, config keys and English
  labels (EXISTS, CLOSE VARIANT, NOVEL COMBINATION, NOVEL) stay in English.
- Plain language for a technically capable reader who is not an expert in every
  domain: spell out every acronym on first use (LDP, MIA, GRR, HM, PIT, W1, OSM,
  CDF, ...), explain each technical term in a few words, write full sentences, no
  arrow chains, no sentence fragments, say what each thing means in practice.
- Fidelity to source: every number, label, score, verdict, name and link must come
  from the input files; where the objection round changed a number, use the §6 /
  digest value and say so once. Where the sources disagree, the digest beats the
  evaluation, which beats the candidates file. Where something is unverified in the
  sources, say "nepreverjeno". Never mention agent ids or model names.
- Do not change `docs/NACRT_ULDP_SINTEZA.md` or `docs/NACRT_ULDP_RANGI.md` unless §A
  says so.
- Do not run Python or tests; this is a docs-only change.

Reply (at most 15 lines): the line count of the new document, the four files
touched, any input you found contradictory and how you resolved it, and the three
places a reviewer should check first.

## §A The author's decisions (binding, 9 Oct 2026)
- A1 Chosen candidate: T3 "Within-trip segment-time contrasts on a public edge
  covariate", in the form that survived the objection round (`40_evaluation.md` §6,
  `41_rebuttals.md`, `45_digest.md`): only the categorical paired frontage form; the
  junction covariate and the numeric junction form are dropped (close variant of Roth
  and Avella-Medina 2025). Pairs are junction-free 100 m mid-block windows of matched
  length, one road-class group, inside one trip, at most 3 minutes apart, trimmed
  40 m at nodes, 80 m upstream of signals and at bus stops; speed is measured
  relative to the public model P3; one answer per user (slower / same / faster / no
  usable pair) by generalised randomized response at the full epsilon; the server
  estimates one frontage slowdown factor with an exact conditional binomial test and
  applies it to per-segment times and router costs of synthetic routes.
- A2 Document: `docs/NACRT_ULDP_ODSEKI.md`, title in the style of the earlier plans,
  for example "Načrt: kontrasti časov po odsekih znotraj poti pod LDP na ravni
  uporabnika (T3)".
- A3 Pre-registered public check before the freeze (about one hour, P3 only, no
  Geolife data), exactly as in the T3 rebuttal with the evaluator's amendments: split
  sessions (P10) first; judge the no-pair share in the worst case over 1 to 30 trips
  per user, not at the Geolife mean of 9; trim at bus stops; add a placebo arm;
  keep / switch / stop rule with the stated thresholds (shop and retail frontage
  first, built frontage within 30 m second).
- A4 Fallback rule (pre-registered, in §0 and §8): if the public check fails for both
  frontage layers, T3 becomes a large-n module shown only in the recovery simulation
  (P6) and the round-3 mechanism becomes T1 with T4's relation question (combination
  K-α of the evaluation), whose plan is then written in a new session.
- A5 T1 recommendation: state in the new document (§3.2 and §8) that T1 is
  recommended as a cheap destination question inside the K1 design of round 2; AND
  add ONE bullet to `docs/NACRT_ULDP_RANGI.md` §8 "Odprte odločitve", in the style of
  the existing bullets, saying that round 3 proposes a destination item (T1,
  opportunity-rank tercile, see the new document §3.2) for K1's question list and
  that the decision belongs to the K1 sessions. Nothing else in that file changes.
- A6 New metric as a new prerequisite: the pre-registered segment-speed metric (W1
  distance of window speeds on 100 m mid-block windows against held-out test-split
  matched trips, bootstrap over users, reported per OSM road-class group, signalised
  versus not, and frontage class; plus the W1 of the within-route spread of log
  window speeds), computed the same way for every arm. New prerequisites continue the
  numbering after P12 (P13, P14, ...); you choose their names and order.
- A7 Honesty requirements: name the label "K8 extended from across-trip to
  within-trip contrasts on an edge covariate", the verdict NOVEL COMBINATION (medium
  confidence) with Roth and Avella-Medina 2025 as the closest work, the detectability
  of about 15 % slowdown or more at epsilon 2 (1.6 to 2.5 SD depending on the no-pair
  share), the weak visibility to the MIA (only through router costs; a time-aware MIA
  P8 would be the real test), the dependence on P10, and the search limits of the
  novelty check (rate limits; what stayed unverified).
- A8 Not reopened: S1-S5, the decisions of the two earlier plans, the lens set of
  round 3, the dropped candidates T5 and T6 (published cores).
- A9 Archive folder: `arhiv/brainstorm_2026-10-09/`; round-3 ids are T1-T6; raw ideas
  are cited by lens and number (for example R3-D.3 is the frontage clock).
