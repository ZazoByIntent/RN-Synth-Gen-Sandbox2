# Stage 6 review: docs/NACRT_ULDP_RANGI.md and the four companion edits (reviewer, 2026-10-07)

**Verdict: accept after small edits.** The document is faithful to the sources: 33 spot-checked numbers, verdicts, links, labels and
decisions all match, the author's §A decisions are recorded in full, every "snippet only" / paywalled / abstract-only mark survives, and
the structure, internal references and the CLAUDE.md, NACRT_ULDP_SINTEZA.md and arhiv edits are in order; no must-fix. Five should-fix
items concern one unmarked inference inside the author's decision, one ambiguous term ("par"), one unexplained term, one incomplete
table cell and one omission in the §0 note of NACRT_ULDP_SINTEZA.md; twelve nits are wording and consistency.

Files reviewed (branch `claude/ideation-rank-calibration`, uncommitted): `docs/NACRT_ULDP_RANGI.md` (new, 583 lines), the §0 note in
`docs/NACRT_ULDP_SINTEZA.md` (+5 lines), the status bullet and doc-map entry in `CLAUDE.md` (+15), the new row in `arhiv/README.md` (+1),
`arhiv/brainstorm_2026-10-07_krog2/README.md` (new). Sources: `45_digest.md`, `40_evaluation.md` (incl. §6), `20_candidates.md`,
`30_novelty_G1-G3.md`, `00_baseline.md`, `01_task.md`, `05_write_task.md` §A, and `docs/NACRT_ULDP_SINTEZA.md` for labels.

## Must-fix
None found.

## Should-fix

**S1. An unmarked inference sits inside the author's decision 1.** `docs/NACRT_ULDP_RANGI.md` §0, line 53: "Je samostojen mehanizem,
ne le časovna vprašanja modula C1." Source: `05_write_task.md` §A says only "Chosen mechanism ... pick 1 ... under the conditions from the
pushback round"; `40_evaluation.md` §4 pick 2 lists "ship as a mechanism or fold into §4 as C1's time questions" among the *open*
decisions, and §6 P4 says "Yes, B passes ... Condition, not a redesign". The reading is defensible (the task asked for one mechanism and
the author chose it as such), but the document otherwise marks its own inferences ("izpeljava pisca"). Fix: append "(izpeljava pisca iz
izbire in točke 4 kroga ugovorov; potrdi avtor)" or move the sentence to §8 as an open point.

**S2. "par" denotes two different questions.** `docs/NACRT_ULDP_RANGI.md` §6.1, line 379: "ali par odhod × trajanje | ... 9 celic para
±0.033 na celico"; §4.1, line 248: "skupni zaporedni PIT para (odhod, trajanje)". In §5.1 the document names the K8 rush-hour question
"*a*, par konica–zunaj konice" and the K1 joint item "odhod × trajanje". Source: `20_candidates.md` K1 §6 "the (dep, dur) copula at ±0.033
per cell"; `30_novelty_G1.md` K1 Raise "a chained (Rosenblatt) PIT of (departure, duration) ... one 9-cell GRR item". Fix: write "skupna
postavka odhod × trajanje" and "9 celic skupne postavke" in §6.1 and §4.1; keep "par" for K8a only.

**S3. "ablacija" is not explained on first use.** `docs/NACRT_ULDP_RANGI.md` §3.2, line 187 ("Ključni dokaz bi bila ablacija ..."),
then lines 266, 305, 423. CLAUDE.md "Communication style" requires a gloss on first use; `docs/NACRT_ULDP_SINTEZA.md` §3.2 has one:
"(primerjava različic, ki se razlikujejo le v enem delu)". Fix: add that gloss at line 187 or in §0 "Izrazi".

**S4. The *dur* row's "Kdaj" cell is incomplete.** `docs/NACRT_ULDP_RANGI.md` §5.1, line 292: "pri n = 91 in ε = 2 vsi uporabniki".
Source: `20_candidates.md` header "At ε 0.5 every K reduces to its prior arm" and K1 §6 "ε 0.5: ±0.28 per bin share, ±0.21 for the bit,
so the gate keeps the prior ... ε 8: ... two questions at ≈ 45 users each"; the document's own §6.1 gives the ε 0.5 noise of this question.
Fix: "pri n = 91 vsi uporabniki pri ε ≤ 2 (pri ε = 0.5 vrata obdržijo prior); pri ε = 8 okoli polovica (§6.1)".

**S5. The §0 note in NACRT_ULDP_SINTEZA.md omits F2.** `docs/NACRT_ULDP_SINTEZA.md` lines 59–62 list "seje namesto poti, kdo poroča,
točnejši šum za §4.3, §4.4 in §5.1, izbira gradnika za C2, vrata ..." (F1, F3, F4, F5, F7). Source: `40_evaluation.md` §5 F2 is the finding
that touches §4.3 most directly ("C3's confusion matrix 'under a public number of trips per user', which no cited constant gives", with a
concrete remedy). §A asks only for a 2–4 line pointer, which the note is, so this is a judgment call. Fix: add "zakon števila poti na
uporabnika za C3" to the parenthesis (the note stays at four lines).

## Nits

- **N1 typo.** `docs/NACRT_ULDP_RANGI.md` line 553 (F8): "zgrajeni okoli okoli 9 ujetih poti" — duplicated "okoli".
- **N2 order of explanation.** Line 296 uses "HM" (K8c row); the gloss "hibridnim mehanizmom HM (za eno omejeno število ...)" comes at
  line 298. Move the gloss into §0 "Izrazi" next to GRR.
- **N3 order of explanation.** Line 236 "»prva kopula pod LDP«" precedes the gloss at line 322 "(modela odvisnosti dveh spremenljivk)".
  Gloss at first use or in §0.
- **N4 unexplained term.** Line 250 "ocenjevalnik s fiksnimi učinki znotraj uporabnika" (G1 Raise: "LDP within-user (fixed-effects)
  estimator"). Add "(model, ki vsakemu uporabniku dovoli lastno raven in oceni le razlike znotraj njega)".
- **N5 one letter, two meanings.** "d" is the rank difference (line 295) and the ⊥ share (line 389). Inherited from the sources (K8
  report; §6 P7), but within one document use "delež ⊥" or another symbol at line 389.
- **N6 two twin counts.** Line 33 "okoli 30 dvojčkov" vs lines 148, 292, 464 "29–50". Both sourced (`45_digest.md` "about 30";
  `20_candidates.md` K1 "K = 29–50"); add "(29 do 50, §5.1)" at line 33 so the reader does not see a discrepancy.
- **N7 CLAUDE.md count.** The status bullet says "two new shared prerequisites come first (... P10; ... P11)", the doc-map entry says
  "prerequisites (new: P10–P12)". Both true (P12 is a metric, not a shared fix), but the lines read as inconsistent; write "two new shared
  prerequisites (P10, P11) and a new metric (P12)" or drop the count.
- **N8 slightly stronger than the source.** Line 176 (§3.2 A′): "nov je le razred zanke". `30_novelty_G2.md` K4 E1 and
  `40_evaluation.md` K4 Novelty name three new elements (the private law, the loop class, the exact-likelihood generator), which §6 P2
  then counts as "one detail". Suggest: "nova so le razred zanke, zasebni zakon in točno verjetje, kar krog ugovorov šteje za eno
  podrobnost".
- **N9 unmarked planning inference.** Line 494 (§9.2 step 2): "od P0 in P1 neodvisen, lahko teče tudi pred njima" is the writer's
  reading, not in the sources; mark it like the other inferences or keep it as a plain plan statement.
- **N10 unsourced mark.** Line 582: Blomqvist 1950 listed under "Ozadje, ni bilo odprto". `30_novelty_G1.md` does not mention Blomqvist
  (it appears only in `20_candidates.md` K8 §4 and §7), so "not opened" is the writer's assumption; harmless, but say "(iz konsolidacije,
  brez povezave)".
- **N11 gloss for the gravity model.** Line 277 "po gravitacijskem OD" has no gloss in this document (NACRT_ULDP_SINTEZA.md §4.1:
  "privlačnost cone pada z razdaljo"). Add it in brackets.
- **N12 length.** 583 lines against the 350–550 aim of `05_write_task.md`; not disproportionate (the §4.2 and §10 tables carry very long
  rows). If trimming, §4.1 "Razlika od zasnove §4 in C4–C10" partly repeats §1.

## Spot-checks (33 facts; all match)

| # | Fact in the document | Source | Result |
|---|---|---|---|
| 1 | 18 ideas (4 + 3 + 3 + 4 + 4), eight candidates, X1–X14 | archive README; `20_candidates.md` header | OK |
| 2 | about 145 web searches in the novelty check | G1 54 + G2 (19 + 15 + 17) + G3 (17 + 23) = 145 | OK |
| 3 | eight weighted criteria, max 100; pushback: privacy a gate, max 95; scoring noise ±3 | `40_evaluation.md` §1, §6 | OK |
| 4 | K1 60/57, K2 57/51, K3 53/48, K4 66 / A′ 56, K5 56/52, K6 62/60, K7 53/51, K8 64/62 | §1 totals; §6 re-score | OK |
| 5 | B 69 then 70, C 65 then 62, A 72 then 61, A′ 56, T 54 | §3, §6 | OK |
| 6 | cleaning: > 200 km/h dropped, ≥ 5 s, ≥ 20 points, ≥ 500 m; one trajectory per `.plt`; `fit` sees matched train trips only | §0 R-1, R-2 | OK |
| 7 | 17 313 cleaned, 1 770 matched, about 809 training trips; about 91 / 25 / 10 users; 17 generators; 300 s / 1 200 s | `00_baseline.md` §1, §7 | OK |
| 8 | ε 0.5: ±0.28 (3 bins), ±0.21 (bit), prior ≥ 1.5 spreads off | `20_candidates.md` header, K1 §6 | OK |
| 9 | ε 2: ±0.073 / ±0.074; shift ±0.17 spreads = ±0.07 nat at 0.42 nat; "≥ 1.3 nats" | K1 §6; §0 R-3, R-5 | OK |
| 10 | ε 8: HM ±0.045 vs bit ±0.055 nat; 9 cells ±0.033; two questions at about 45 users | K1 §6 | OK |
| 11 | K8a effect: 0.22 to about 0.36 and about 0.12; about 40 of 91 eligible; 1.1 SD (ε 2), 2.3 SD (ε 8); inputs are claims | §0 R-5 | OK |
| 12 | ⊥ cost × 1/√(1 − d) (× 1.05 at 0.1, × 1.2 at 0.3) vs today's harness; × 1/(1 − d) vs informative users; gates stay exact | §6 P7 | OK |
| 13 | membership bound TPR ≤ e^ε·FPR: 0.017 (ε 0.5), 0.074 (ε 2) at FPR 0.01 | `00_baseline.md` §1 | OK |
| 14 | pair rule 7–9 h / 17–19 h vs 6–22 h, free-flow ratio ≤ 1.5; 29 twins; d thresholds ±10; GRR over 4 | K8 §2 | OK |
| 15 | K8c: Spearman at ≥ 3 trips, ±0.3, HM on the clipped value at ε 8; Gaussian copula shrunk to 0 | K8 §2, §4 | OK |
| 16 | two ε = 1 bits act as one bit at ε ≈ 0.43 | K8 §3 | OK |
| 17 | about 40 ms per queried destination; twins seeded by hash(O, D, map, config); caches shared by 17 generators | K1 §5 | OK |
| 18 | 8–10 cohorts of about 1 000, SD 0.021; 5–10 dithered bins; maps per period × length class | K1 §6 | OK |
| 19 | F4 corrected noise 0.136 / 0.073; 0.206 / 0.079 / 0.11; 0.125; 0.126 / 0.137; OLH 0.095 / 0.15; margins shrink 15–40 % | §5 F4 | OK |
| 20 | F5: k = 9 < 3e^ε + 2 = 10.2 (ε 1), 24 (ε 2); 0.079 vs 0.095; OLH from 36 zones | §5 F5 | OK |
| 21 | 30–55 % of car trips within 5 % of shortest time (Zhu & Levinson 2015); needed shift ≥ 0.15; Knapen tables paywalled | §6 P1 | OK |
| 22 | C: about 36 test users at u182; one-hour public check of ρ; trips law asked in the report; home-cell risk at ε 8 | §2 K6, §3 C, §6 P5 | OK |
| 23 | session estimates: B 4–5, C 7–8, A′ 3–4; A's 5–6 "beyond P0–P5" | `45_digest.md`; §4 pick 1 | OK |
| 24 | G1 links (Joseph 1811.08382, Penso 2505.15721, Cormode 2210.12526, Kuleshov 1807.00263, Acharya v89, Lam-Weil 2002.04254, Sopa 2601.10626, Kent 2405.11923, Acharya v206, Ding 1803.09027, Couch 1809.01635, LoPub 1612.04350, Ghazi) | `30_novelty_G1.md` | OK |
| 25 | G2 links (RATR polyu, Brauer doi, FAMOS itspubs, Yoon ideas, Bian 2407.03496, BerlinMOD mobilitydb, Knapen ideas, DPMM berkeley, Abraham microsoft, Fischer 1909.08801, Manley ideas, Zhu PMC4534461) | `30_novelty_G2.md` | OK |
| 26 | G3 links (Wang AAAI 11285, DP-WHERE doi, Cho kdd11, Vanhoof 1809.09911, Kapp 2209.08921, PateGail 26700, DITRAS 1607.05952, Song 1010.0436); Golle & Partridge median anonymity set 1 | `30_novelty_G3.md` | OK |
| 27 | K7 links (LDP-DL 2202.02971, Zhou & Tan 2010.06709, Hausman dspace, Zhang v267); §11 links (Chopra, Maddock, Aamand, Liu & Hu, Talts, Zhao, Roth, Joseph 2018, Xiong, Sakong) | G1; `00_baseline.md` §5 | OK |
| 28 | marks kept: Awan & Slavković, Yoon, within-person variance "le izsek"; Brauer full text unavailable; Knapen tables paywalled; PateGAIL++ abstract only | G1, G2, G3, §6 | OK |
| 29 | verdicts and confidence K1–K8 as in the three summary tables; combination novelty 4 of 5 because K8 brings a new estimand | G1–G3 tables; `40_evaluation.md` §3 B, §6 P2 | OK |
| 30 | §A decisions: pick 1 under P4's two conditions; two shared fixes as prerequisites; title and file name; folder; §10 plus a 2–4 line §0 note (4 lines); unchosen picks with return conditions in §3.2; §8 holds the digest's three decisions | `05_write_task.md` §A; `45_digest.md` §1 | OK |
| 31 | P0–P6 labels and efforts (S, S, M, M, S–M, S, S–M); P7–P9 occupied; new P10–P12 | `docs/NACRT_ULDP_SINTEZA.md` §8.1 | OK |
| 32 | cross-references to NACRT_ULDP_SINTEZA.md §3.2, §4.1 (P3), §4.7, §5.3, §5.5, §7.1 points 2–4, §8.1, §8.3 exist and say what is claimed | `docs/NACRT_ULDP_SINTEZA.md` | OK |
| 33 | provenance K1 from R2-C.1, R2-D.1; K8 from R2-C.3, R2-A.4, R2-E.4; C1 from A.1, B.1, C.1, D.2, E.3 | `20_candidates.md` table; `00_baseline.md` §4 | OK |

## Structure and companion files
- All twelve required sections (0–11) of `05_write_task.md` are present with the required content; the table of contents matches the
  headers; every internal reference (§8 points 1, 4, 7, 10; §9.1–9.3; §10 F1–F3, F8; §6.2) resolves. No link to `.brainstorm/` in any
  changed file (grep clean). No arrow chains (the only arrow is the mathematical "ε → 0").
- `CLAUDE.md`: both additions are English, in the style of the neighbouring entries, no PR numbers or merge commits (HANDOFF rule kept);
  nothing else changed. `arhiv/README.md`: one row in the style of the `brainstorm_2026-10-07` row.
  `arhiv/brainstorm_2026-10-07_krog2/README.md`: all 17 archived files listed with correct idea counts; the warning that P1–P7 in
  `40_evaluation.md` §6 are pushback points, not prerequisites, is a good addition. `docs/NACRT_ULDP_SINTEZA.md`: the note is four
  lines, in §0, and nothing else changed (see S5).
- Language: grammar and spelling are clean apart from N1; sentences are full; terms are glossed on first use except S3, N2–N4, N11;
  labels K1–K8, C1–C10, P0–P12, R1–R3, S1–S5, X1–X14 and F1–F9 are used consistently with the sources and with NACRT_ULDP_SINTEZA.md.
