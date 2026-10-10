# Stage 6 review: docs/NACRT_ULDP_ODSEKI.md and the accompanying edits (reviewer, 2026-10-09)

**Verdict: accept after minor fixes.** All eleven sections (0-10) exist with the content the
write task demands; the author's decisions A1-A9 are reflected exactly (title, chosen form, window
and pair constants, check, fallback rule, T1 recommendation, P13-P16, honesty label, what is not
reopened, archive ids); every score before and after the objection round, every novelty label and
confidence, every n = 91 noise number and all 41 works in §10 match the sources. The privacy
argument (§5.5) and the variance sketch (§6.2) are correct and recomputed. Five required fixes are
one-sentence corrections: one headline overclaim, one overstated description of how deeply the
novelty check read the literature, one misattributed claim about a cited work, one misattributed
severity, and one statement superseded by the G3 addendum. Nine recommended fixes concern one
technical condition the exact test silently needs, wording precision and cross-document
consistency; thirteen minor notes are style and small consistency items.

Files reviewed (branch `claude/ideation-round3`, uncommitted): `docs/NACRT_ULDP_ODSEKI.md` (new,
694 lines), `CLAUDE.md` (+19: status bullet and doc-map entry), `docs/NACRT_ULDP_RANGI.md` (+1: §8
row 11), `arhiv/README.md` (+1 row), `arhiv/brainstorm_2026-10-09/README.md` (new). Sources:
`01_task.md`, `05_write_task.md` §A, `20_candidates.md`, `30_novelty_G1-G3.md` (with the T6
addendum), `40_evaluation.md` (§6 supersedes), `41_rebuttals.md`, `45_digest.md`, `00_baseline.md`
§1, §6-8; cross-checked against `docs/NACRT_ULDP_SINTEZA.md` and `docs/NACRT_ULDP_RANGI.md`. Line
numbers below are those of `docs/NACRT_ULDP_ODSEKI.md` unless another file is named.

## Required fixes

**R1. Headline overclaim: "the only proposal of the three rounds".** Lines 43-44: "To je edini
predlog treh krogov, ki zasebno popravi časovno zgradbo znotraj poti (zahteva R1); prejšnji zasnovi
popravita le raven hitrosti oziroma trajanje cele poti." Line 117 adds without qualification:
"Nobena ne pove, kako se čas spreminja *vzdolž* poti." Sources: `45_digest.md` line 44 says T3 is
"the only option that adds something neither earlier plan has" (an option of round 3, compared with
the two plans); `40_evaluation.md` line 96 records that round-1 C8/A.4 "sends a speed bit per
[hierarchy] node", i.e. private corridor speeds that do vary along a route; `NACRT_ULDP_SINTEZA.md`
lines 295-296 give C1 at large n "faktorji hitrosti po razredu in obdobju", which also vary along a
route. What the sources support is narrower: no earlier module touches a within-trip contrast, and
at n = 91 both plans move only a level. Fix (line 43): "To je edina izbira tretjega kroga, ki doda
nekaj, česar nobeden od obeh načrtov nima: zasebni popravek časovne zgradbe znotraj poti iz
kontrasta znotraj ene poti (zahteva R1); obe načrtovani zasnovi pri n = 91 popravita le raven
hitrosti oziroma trajanje cele poti." Line 117: "Pri n = 91 nobena ne pove ... (C1 da faktorje
hitrosti po razredu ceste šele pri velikem n, in to kot ravni, ne kot kontrast)."

**R2. The novelty check's reading depth is overstated.** Lines 244-246: "Dela so bila odprta
(povzetek ali članek), razen kjer piše »le povzetek« ali »le izsek«." The checkers opened only a few
pages: G2 fetched four arXiv pages and read only Roth and Avella-Medina §6 in full
(`30_novelty_G2.md` line 22); G1 fetched Canonne et al., one further abstract, the Yang et al. 2014
formula and the Gibbs et al. institute page, plus the Ramaekers IDEAS page (`30_novelty_G1.md` lines
26, 64); G3 fetched Steinberger, Duchi and Ruan by section, Aamand et al., Liu, Hu and Kong (full
text) and the Hu and Liu poster page (`30_novelty_G3.md` lines 11-12, 51, 82, 88). Most other works
in §4.1-4.2 (for example DP-WHERE, Sakong and Zentefis, Kent et al., Ding et al., Ohnishi and Awan,
Rameshwar et al., Haze, Awan and Slavković, Couch et al., Yao and Bekhor, DPMM "per its abstract",
AHEAD, Cunningham et al. "title not re-verified", L-SRR, McKenna et al., Cormode et al. 2019) were
judged from search results or from the records of rounds 1-2. Fix: "Večina del je presojena po
zadetkih iskalnika, povzetkih ali zapisih prvih dveh krogov; besedilo ali posamezne razdelke so
preverbe odprle le pri Roth in Avella-Medina (§6), Duchi in Ruan (§4.4, §5.2, §6), Steinberger, Liu,
Hu in Kong (celotno besedilo) ter Yang et al. 2014 (formula). »Le povzetek« in »le izsek« označujeta
dela, pri katerih je preverba to izrecno zapisala."

**R3. Egéa and Escobar-Bach did not publish a Kaplan-Meier estimate at ε = 8.** Line 236, last
sentence: "Kaplan–Meierjeva ocena pri ε = 8 je objavljena (Egéa in Escobar-Bach 2023)." Source
`30_novelty_G1.md` line 74: they privatise the failure indicators of right-censored data and use a
kernel estimator of the cumulative hazard; T2's ε 8 variant would use a discrete Kaplan-Meier over 4
bands, and "LDP estimation under right censoring exists, so the censored identification alone carries
no novelty claim"; `40_evaluation.md` line 205 accepts Kaplan-Meier "as a cited tool". Fix:
"Ocenjevanje pod desnim cenzuriranjem pod LDP je objavljeno (Egéa in Escobar-Bach 2023), zato
cenzurirana identifikacija pri ε = 8 sama ne nosi novosti; Kaplan-Meierjev produkt je le citirano
orodje."

**R4. §7 attributes "serious" to every row.** Lines 547-548: "spodnja tveganja je ocenjevalec po
krogu ugovorov ocenil kot resna, ne usodna." The digest names five serious T3 findings: too few
pairs, weak signal, fixed waits, multimodal sessions and weak MIA visibility (`45_digest.md` lines
14-19). Other rows come from elsewhere and carry other weights: noisy window times are "Minor"
(`40_evaluation.md` line 92), prior contamination is Y8's procedural risk (line 130), the
self-made metric T3-d was resolved in §6.3(b) (line 210), and confounding and noise-scale dependence
are the T3 proponent's open points (`41_rebuttals.md` lines 45-49). Fix: "Pet tveganj (premalo
parov, šibek signal, fiksne zamude, večnačinske seje, slepota benchmarka) povzetek ocenjevalca šteje
za resna; ostale vrstice so manjše ali postopkovne točke iz rdeče ekipe, iz odgovora predlagatelja
T3 in iz ugotovitve Y8. Nobeno ni usodno."

**R5. The T6 condition repeats a check the G3 addendum has already done.** Line 239: "najprej bi
bilo treba preveriti, ali sklepanje Liu, Hu in Kong že da meje W1 ali enakomerne pasove." The
addendum read the full text (`30_novelty_G3.md` lines 92-96): its guarantees are uniform and L2
consistency and √n asymptotic normality with inference on a fixed grid. It has no Wasserstein
metric, posterior, quantile map, user-level unit or per-group strata, and its experiments start at
n = 1,000. Fix: "Polno besedilo Liu, Hu in Kong (dodatek preverbe G3) nima ne metrike W1 ne
posteriorja, sklepanje pa je točkovno na fiksni mreži; enakomernih pasov zaupanja preverba ni
našla (nepreverjeno, ali obstajajo drugje)."

## Recommended fixes

**S1. The exact test needs equal public free-flow time per metre in both windows (reviewer's
observation, not in the sources).** Lines 376-379 (§5.2) and 287-289 (§4.1, point 2) say the null
holds "za vsako mešanico fiksnih in sorazmernih zamud in za vsak način potovanja", following
`41_rebuttals.md` lines 22-24. The residual is ρ = log(t_izmerjen / τ₀) with τ₀ from OSM `maxspeed`
or the class default (§5.1; `NACRT_ULDP_SINTEZA.md` §4.1). A walker's time does not scale with τ₀,
so for a walker ρ_visoka − ρ_nizka = log of the ratio of the two windows' free-flow speeds (and of any cited access adjustment that differs between the two windows). If shop
streets inside one road-class group carry lower speed limits, walkers report "hitreje ob fasadi"
with no frontage effect, and the test can reject on Geolife, where walking is common. P15 would not
catch it if P3's walk regime is a multiplicative factor on τ₀: that is exactly the symmetric model
the evaluator warned about (`40_evaluation.md` line 208, point 4). Fix: add "enak javni čas prostega
toka na meter v obeh oknih (isti `maxspeed` ali ista privzeta hitrost razreda)" to the pair rule in
§5.1 step 3 and to §8 item 4, or state the condition in §5.2 and list "hoja, katere čas ni sorazmeren
τ₀" among the asymmetries P15 must simulate (§6.1, line 471).

**S2. Decision 1 says the test estimates.** Lines 61-62: "strežnik s točnim pogojnim binomskim
testom oceni en faktor upočasnitve". The wording mirrors §A1, but in §5.2 (line 387) the test only
decides, and the ordered probit estimates. Fix: "strežnik s točnim pogojnim binomskim testom
preveri, ali fasada vpliva na čas, in šele ob zavrnitvi z urejenim probitom oceni en faktor".

**S3. "Avtor" means both the doctoral author and an idea's proponent.** Lines 64 ("kot jo je
predlagal avtor T3", inside the list "Odločitve avtorja"), 183 ("odgovore avtorjev T1, T3 in T2",
followed directly by "Avtor je izbral T3") and 560 ("avtor kandidata"); also
`arhiv/brainstorm_2026-10-09/README.md` line 40 and the new row in `arhiv/README.md` ("odgovori
avtorjev"). `NACRT_ULDP_RANGI.md` reserves "avtor" for the user (lines 45, 54, 462). Fix:
"predlagatelj T3", "predlagateljev T1, T3 in T2", "predlagatelj kandidata", "odgovori
predlagateljev" (§2 already uses "predlagatelji", line 174).

**S4. The placebo arm reads as part of the one-hour check.** Line 67 lists "dodana je placebo roka"
among the check's amendments, but §6.1 (lines 469-474) has no placebo; the arm belongs to the
measurement (`40_evaluation.md` line 210, §6.3(b)), where the document correctly puts it (§6.4,
line 536). §A3 bundles both, so this is a clarity fix only. Fix: "...; za meritve je skupaj s
preverbo vnaprej prijavljena placebo roka (§6.4); ...".

**S5. Name the evaluator's alternative judging point.** The writer's observation (line 474) rightly
says that the worst case over m = 1 to 30 is in practice m = 1 and makes the fallback likely. The
evaluator offered a second option, "or at m = 3" (`40_evaluation.md` line 208, point 3), which the
document omits. Add one clause to line 474 or §8 item 1 (line 579): "ocenjevalec je kot drugo
možnost ponudil presojo pri m = 3; avtor je izbral strožji najslabši primer". This keeps the choice
informed without reopening it.

**S6. The check's region should be the public map frame.** Line 471: "20 000 poti P3 nad
pravokotnikom, ki obdaja Geolife". If this rectangle is computed from Geolife points, a
Geolife-derived quantity enters a frozen design choice (S1; §5.5 step 5 says the check runs
"brez Geolife"). Fix: "nad javnim okvirjem zemljevida Pekinga" (the term of
`NACRT_ULDP_SINTEZA.md` §7.2).

**S7. Say how the T1 recommendation and the fallback interact.** §8 item 3 (line 581) lists (a)
*dest* in K1 and (b) K-α as round 3's mechanism after a fallback; they are not exclusive, and the
document does not say whether T1 stays in K1's list if the fallback triggers. Add "Če velja umik,
gradivo ne določa, ali T1 ostane tudi na seznamu K1." In `docs/NACRT_ULDP_RANGI.md` §8 row 11 add
one clause: "če javna preverba T3 pade, postane T1 kot K-α mehanizem tretjega kroga
(`NACRT_ULDP_ODSEKI.md` §8, točki 2 in 3)", so that a K1 session reading only RANGI knows.

**S8. Make the shared-prerequisite lists agree.** Lines 92-93: "si z obema deli P3, P0–P6, P10 in
P11" (P3 is inside P0-P6; P12, used in §9.2 step 8 and listed in §9.1, is missing; P8 is optional).
The `CLAUDE.md` status bullet repeats "shares P0–P6, P10 and P11". Source: `20_candidates.md` line
112 (X12: "P2 and P12 for evaluation"). Fix in both places: "P0–P6 in P10–P12 (P8 neobvezno)" and
"P0–P6 and P10–P12 (P8 optional)".

**S9. Point to the shared decision on the session split.** T3 depends on P10 more than any earlier
design, but whether the split applies to every arm (it changes the S4 numbers of all arms) is open
in `NACRT_ULDP_RANGI.md` §8 item 4. Add a §8 row or a clause in item 10: "ali razrez P10 velja za
vse roke, odloča `NACRT_ULDP_RANGI.md` §8, točka 4; T3 ga potrebuje vklopljenega".

## Minor notes

1. Lines 47-49: "pred tem pridejo ... štirje novi (P13–P16)", but in §9.2 P16 (step 8) comes after
   the check P15 (step 7). Write "pred tem pridejo ... ter nova P13 in P14".
2. Lines 393, 486 and 524-525: the large-n layer "skupina razreda ceste × obdobje × vrsta fasade"
   replaces the source's "× covariate" (frontage or junction, `20_candidates.md` line 19). With the
   junction covariate dropped, the "≈ 12 numbers" may shrink; mark "vrsta fasade" as the writer's
   adaptation.
3. Line 456: "Za napad MIA iz tega sledi meja" reads as if the TPR bound followed from locating power
   1; it follows from user-level ε-LDP. Write "Iz ε-LDP na ravni uporabnika sledi ...".
4. Terms used before they are explained, or never explained: "urejeni probit" (line 94, explained
   only at 387-389), "dvojčki" (194, 289), "vrata" (196, explained at 376), "kontekst" (216),
   "Newtonov korak" (219), "izotonična prilagoditev" (220), "Kaplan–Meierjeva ocena" (236),
   "Dijkstrovo iskanje" (414). A few words each, as RANGI §0 does for its terms.
5. Line 216 (T2 report): "enaki javni verjetnosti brez stropa in s stropom" can be read as "the two
   probabilities are equal". Write "isti javni verjetnosti, α brez stropa in β s stropom, v vsakem
   kontekstu".
6. Lines 267 and 687: "Awan, Slavković (2018)" with arXiv 1904.00459. The year comes from the
   baseline table (`00_baseline.md` line 147), the link is the later journal version
   (`30_novelty_G2.md` line 30); add "(povezava: revijska različica)".
7. §5.2 (lines 376-386): at ε = 8 the domain has six values; say that the test then compares the two
   "slower" classes with the two "faster" classes (Binomial(m, ½) still holds because the GRR
   probability q is the same for every false value). The sources are silent, so mark it as the
   writer's derivation.
8. Line 494: the square root of (0.20 squared + 0.15 squared) is 0.25, not 0.24; the document copies
   the evaluator (`40_evaluation.md` line 92), and with 0.25 the balance is 0.42 (the consolidator's
   figure, `20_candidates.md` line 19). No change of substance; optional footnote.
9. Line 235 cites the CAUPD and Baidu commuting report (`41_rebuttals.md` line 50), which is absent
   from §10. Add it as "kandidat, nepreverjeno, brez povezave", or say in §10 that unverified
   candidate sources are not listed.
10. Length: 694 lines against the write task's 450-650. Acceptable, but the §3.2 cells for T1 and T2
    (lines 235-236) are 150-200 words each; consider splitting them into short paragraphs below the
    table.
11. Line 95 points to "§2" for the new estimand; §4.1 (lines 285-291) is the better target.
12. `arhiv/brainstorm_2026-10-09/README.md` line 44: once this file is copied, replace "doda se po
    recenziji" with the verdict and the counts, as the round-2 README does.
13. `docs/NACRT_ULDP_RANGI.md` has LF line endings in the working copy, while `CLAUDE.md`,
    `docs/NACRT_ULDP_SINTEZA.md` and `arhiv/README.md` have CRLF. Git normalises this (autocrlf is
    on, and the diff shows one added line); no action needed.

## Accompanying changes

- `CLAUDE.md` status bullet: placed after the round-2 bullet, same structure (closing date, the
  mechanism in one sentence, "Nothing of it is implemented", prerequisites, pointer). Nothing in it
  is false; the shared-prerequisite list omits P12 (S8). Doc-map entry: placed after the RANGI
  entry, same structure, and the bold "Read only ..." trigger names T1-T6, K-α, K-β, P13-P16 and
  R3-A.1 to R3-E.4. No other line of `CLAUDE.md` changed.
- `docs/NACRT_ULDP_RANGI.md`: exactly one new row (§8, item 11) in the style of the existing rows.
  Its content matches `45_digest.md` lines 38 and 42 and `40_evaluation.md` line 199: the T1 tercile
  with ⊥ by GRR over 4, a *dest* item beside *dur*, *dep* and *len*, about 2 sessions, visible to the
  MIA, the Beijing trip-distance figure to verify and freeze, P10 first, decided by the K1 sessions.
  One clause on the fallback is recommended (S7).
- `arhiv/brainstorm_2026-10-09/README.md`: lists all 19 files present in the folder plus
  `60_review.md`, which is legitimately marked as added after the review. It says that it is a
  record and not an instruction, that the plan beats the material, how ids are written (T1-T6,
  R3-A.1 to R3-E.4, and the dot-less spelling in the raw files) and how the X labels overlap with
  round 2. Only the wording "odgovori avtorjev" needs S3.
- `arhiv/README.md`: one new row in the existing style; correct apart from S3.

## Facts verified against the sources

About 220 facts were checked one by one:
- all 41 works of §10 (authors, venue, year, link) against the three novelty files and the
  baseline table;
- about 95 numbers: the scores before and after the objection round for T1-T6 and K-α, K-β, K-γ;
  the GRR values p = 0.711, q = 0.096 and p − q = 0.615; the SDs 0.134, 0.17, 0.30, 0.38, 0.11 and
  0.17; the balance 0.43 with its 2.5 and 2.0 SD; the range 1.6-2.5 SD; TPR 0.017 and 0.074; 20,000
  routes, m in {1, 3, 9, 30}, the thresholds 0.5 and 0.06; K = 10, 30 m, 0.5 and 0.1, 40 m, 80 m,
  200 m, 60 s, 3 minutes, ±0.1 and ±0.3 nat and the γ grid; 5 × 1,100 × 40 ms ≈ 220 s; 71 searches
  as 27 + 22 + 22 with their times; the Geolife and repo numbers 91, 9, 17,313, 1,770, 809, 25, 10,
  5 s, 35,764 nodes, 17 generators, 300 s and 1,200 s; the P6 grid and its 20 seeds;
- about 30 labels and verdicts with their confidences;
- about 25 candidate and raw-idea ids, including the six dropped ideas;
- about 15 cross-document references and repo paths: SINTEZA §4.1, §4.5, §4.7, §5.3, §5.5, §7.1
  items 2 and 4, §8.1 and §8.3; RANGI §8 items 8, 10 and 11, §9.1 and §9.3; the files maps/osm.py
  and maps/build.py exist; commit 19e7555 is the branch head and main is at 5db5f56;
- about 15 facts in the accompanying changes.

Mismatches found: the five required items. Everything else matches.

## Three strongest passages

1. §5.5, lines 422-458: the privacy argument in five steps. It states what one user's whole data
   can change, gives the GRR ratio with the numbers at k = 4 and ε = 2, writes out the lift
   inequality, says why there is no composition, and lists every frozen public input, including
   the P11 reporting rule. A non-expert can follow every step.
2. §6.2, lines 476-509: the noise analysis reproduces the evaluator's numbers step by step (f± =
   0.311, SD 0.134, c normal with mean 0.15 and SD 0.24, balance 0.43, then 2.5 and 2.0 SD),
   applies the ⊥ dilution rule explicitly, and says that the true ⊥ share is unknown and must not
   be measured on Geolife before the freeze.
3. §4.1, lines 273-300, together with §4.3, lines 312-330: the strict reading of Roth and
   Avella-Medina, the explicit list of claims the thesis must not make, and precise search limits
   (counts, times, failed fetches, and the narrowed form that was never searched separately).

## Three weakest passages

1. §4 introduction, lines 244-246, together with line 236: the only places where the document
   claims more verification than the sources record, or attributes to a cited work something it
   does not contain (R2, R3).
2. §0, lines 43-44, and §1, line 117: the headline sentence widens "neither earlier plan" to "the
   only proposal of the three rounds" and drops the n = 91 qualifier (R1).
3. §5.2, lines 376-379: the central exactness claim ("za vsak način potovanja") is stated without
   the condition that both windows have the same public free-flow time per metre; on Geolife, with
   many walkers, this is the most likely way for the test to reject without any frontage effect
   (S1). The §7 introduction (R4) is a close fourth.
