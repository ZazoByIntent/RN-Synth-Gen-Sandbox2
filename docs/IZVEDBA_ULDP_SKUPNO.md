# Izvedba mehanizmov ULDP: skupna pravila samostojne orkestracije

Ta dokument velja za tri implementacijske seje, po eno za vsak mehanizem z lokalno
diferencialno zasebnostjo na ravni uporabnika (ULDP):

1. `docs/IZVEDBA_ULDP_SINTEZA.md`: seja 1, skupni predpogoji in moduli C3, C2, C1.
2. `docs/IZVEDBA_ULDP_RANGI.md`: seja 2, rangi in pari (K1 + K8).
3. `docs/IZVEDBA_ULDP_ODSEKI.md`: seja 3, kontrasti po odsekih (T3).

Algoritmi so opisani v načrtih `docs/NACRT_ULDP_*.md`. Tu je le to, kako seja dela,
kar je za vse tri enako. Datoteka mehanizma doda enote, odločitve in validacijo za
svoj mehanizem. Seje gredo strogo po vrsti, ker vsaka gradi na kodi prejšnje.

## 1. Pooblastilo avtorja (10. oktober 2026)

Avtor je načrt seje vnaprej potrdil s tem dokumentom in z datoteko mehanizma. Za te
seje zato velja naslednje, kar ima prednost pred `CLAUDE.md` in skillom `orchestrate`:

- **Brez plan mode in brez vprašanj.** Seja dela od začetka do konca. Kjer načrt
  pušča odprto točko, ki je ta dokument ali datoteka mehanizma ne zapre, orkestrator
  izbere najbolj konzervativno možnost. Konzervativna je tista, ki ne spremeni
  obstoječih rezultatov in ne nastavlja ničesar po Geolife. Izbiro zapiše v dnevnik
  izvedbe (§6) z oznako `ODLOČITEV SEJE`.
- **Enota sme preseči ~5 datotek** samo, če je tako določeno v tabeli enot
  datoteke mehanizma. Drugače orkestrator enoto razreže sam, brez predloga.
- **Commit, push, PR in združevanje v `main`** izvaja orkestrator sam po pravilih iz
  §5. Za commite in PR-je dovoljenja ne sprašuje.
- **Mreža.** Seja sme brati splet: članke, ki jih načrt zahteva prebrati, in izvoz
  OSM za isti posnetek kot `maps/beijing`. Testi mreže nikoli ne uporabljajo.

Ostala pravila iz `CLAUDE.md` veljajo nespremenjena: vsak nov razred podeduje
ustrezen ABC in je registriran z `@register`; povsod se uporablja seeded
`np.random.Generator`; `data/raw/` je nedotakljiv; testi berejo le `tests/fixtures/`;
koda je v angleščini, dokumenti v slovenščini.

## 2. Skupne odločitve avtorja (10. oktober 2026)

1. **Združevanje.** Orkestrator vsak PR sam združi v `main` z merge commitom (nikoli
   squash), ko velja oboje: recenzent ga označi kot pripravljenega za združitev, in
   `ruff check`, `mypy` in `pytest -q` so čisti.
2. **Validacija na pravih podatkih.** Napad MIA (sklepanje o članstvu) se požene pri
   u20 in u50 s semeni 1, 2 in 3. Stopnje u182 seje ne poganjajo. Reidentifikacija se
   ne požene, ker so novi mehanizmi generatorji.
3. **Razrez sej (P10)** velja samo v novih konfiguracijah `geolife_uldp_*`.
   Zamrznjene konfiguracije S4 in `geolife_mech_*` se ne spremenijo.
4. **Časovno občutljivega napada MIA (P8) seje ne gradijo.** V `docs/HANDOFF.md` ga
   zapišejo kot omejitev: napad ne vidi časov, ki jih mehanizmi spreminjajo.
5. **Pragov uspeha seje ne določajo.** Te prage avtor dogovori z mentorjem. Seja
   poroča dobičke z 95-odstotnimi intervali bootstrap in ne izreka sodb »uspelo« ali
   »ni uspelo«.
6. **Nič se ne nastavlja po Geolife.** Vse konstante simulatorja, zasnove, razredov
   in pravil imajo citiran vir ali izhajajo iz OSM. V konfiguraciji je ob vsaki
   konstanti komentar s citatom. To je ugotovitev F8 iz `NACRT_ULDP_RANGI.md` §10.

## 3. Vloge in modeli

| Vloga | Kako | Naloga |
|---|---|---|
| Orkestrator | glavna seja (priporočeno Opus 5.5, napor *high*) | razrez, delegiranje, dnevnik, git, združevanje; kode ne bere in je ne piše |
| Izvajalec | `Agent`, `subagent_type: "general-purpose"`, `model: "opus"`, za vsako enoto svež | koda, testi, konfiguracija, dokumenti enote |
| Validator | enako kot izvajalec | pogoni na pravih podatkih, primerjava z obstoječimi rezultati |
| Recenzent | `Agent`, `subagent_type: "general-purpose"`, `model: "fable"`, za vsak PR svež | neodvisen pregled diffa |
| Risar | enako kot izvajalec | artefakt na koncu seje (§8) |

Pogan s `subagent_type: "fork"` ni dovoljen nikoli. Neodvisne enote, ki se ne
dotikajo istih datotek, orkestrator požene vzporedno v enem sporočilu.

## 4. Pravila za nizek kontekst orkestratorja

Seje so dolge, zato orkestrator v svoj kontekst ne spušča ničesar, česar ne
potrebuje za naslednjo odločitev.

- Orkestrator ne bere kode, diffov, celih dokumentov ali dnevnikov pogonov. Iz načrta
  ne bere ničesar. Podagentu pove le, katere razdelke (§) naj prebere sam.
- Vsak podagent vrne največ 15 vrstic v obliki iz §7. Če vrne več, orkestrator
  odgovora ne citira naprej in povzame le stanje enote.
- Stanje seje je v dnevniku izvedbe na dnu datoteke mehanizma (§6), ne v pogovoru.
  Po vsaki enoti orkestrator doda eno ali dve vrstici. Ob stiskanju konteksta (to je,
  ko sistem pogovor povzame) ali po prekinitvi seja nadaljuje iz dnevnika.
- Dolge pogone validator zažene v ozadju (`run_in_background`). Ko se končajo,
  prebere le `run.json` in zadnjih 20 vrstic dnevnika.
- Iz izpisa ukazov se vzame največ zadnjih 20 vrstic. `pytest` teče kot `pytest -q`.

## 5. Potek enote in PR

Datoteka mehanizma razdeli delo na **PR-bloke**, vsak blok pa na **enote**.

1. Orkestrator iz `main` odpre vejo bloka `claude/uldp-<mehanizem>-<blok>`.
2. Za vsako enoto pošlje svežega izvajalca po predlogi §7.1. Na odgovor se odzove
   takole: če je enota zelena, gre naprej; če ni, pošlje enega novega izvajalca s
   pripetim odgovorom. Če je enota po dveh poskusih še vedno rdeča, se ustavi po
   pravilu iz te točke spodaj.
3. Ko so vse enote bloka zelene, orkestrator sam commita (sporočilo v angleščini, s
   pripisom iz sistemskega opomnika seje), pushne in odpre PR. Opis PR je v
   angleščini in navaja razdelke načrta, ki jih blok pokrije.
4. Pošlje recenzenta po predlogi §7.3. Kritične popravke da novemu izvajalcu, nato
   recenzenta požene še enkrat.
5. Ko recenzent reče »merge« in so preverbe čiste, PR združi
   (`gh pr merge <n> --merge`), posodobi lokalni `main` in vpiše dnevnik.

**Pravilo ustavitve.** Če enote ni mogoče spraviti v zeleno ali če recenzent tudi po
drugem krogu zahteva kritične popravke, orkestrator PR pusti odprt, opiše vzrok v
dnevniku in v PR. Odvisnih blokov ne začne. Neodvisne bloke dokonča in sejo zaključi
z artefaktom in poročilom (§9). Ustavitev ni napaka, napaka je zamolčana ustavitev.

## 6. Dnevnik izvedbe

Na dnu vsake datoteke mehanizma je razdelek `## Dnevnik izvedbe`. Vanj zapisuje samo
orkestrator, ena vrstica na dogodek:

```
- 2026-10-11 · blok A · enota P0 · zeleno · 4 datoteke · pytest 412 passed
- 2026-10-11 · blok A · PR #60 · recenzija: merge · združeno 1a2b3c4
- 2026-10-11 · ODLOČITEV SEJE · C2 obdobja dneva: 4 (vir: …), načrt jih ne določa
```

Dnevnik gre v commit vsakega bloka. Tako tudi naslednja seja vidi, kaj je narejeno.

## 7. Predloge pozivov za podagente

V predlogah orkestrator zamenja `<…>`. Pozivi so v angleščini, ker podagent piše
kodo. Ta izjema velja samo za besedilo pozivov.

### 7.1 Izvajalec

```
You are implementing one unit of the trajguard repo (Python 3.11, src/trajguard/).
Repo root: <pot>. Branch: <veja> (already checked out; do not switch branches, do
not commit).

Unit: <ID> — <cilj enote v 1–3 stavkih>.
Files you are expected to touch: <seznam ali "propose ≤5">.
Read first: CLAUDE.md (Golden rules, Conventions), docs/ARCHITECTURE.md (only the
sections you need), and ONLY these plan sections: <datoteka §x.y, …>. Find a section
with `grep -n '^#' <file>` and read it with `sed -n`. Do not read anything else
under docs/ and never open arhiv/.
Decisions already made (do not reopen): <odločitve iz datoteke mehanizma>.
If something is unspecified, choose the conservative option (changes no existing
result, tunes nothing on Geolife) and report it as SESSION DECISION.

Rules: subclass the relevant ABC and @register(kind, name); seeded
np.random.Generator only; data/raw is read-only; tests use only tests/fixtures/ and
never the network; English code and docstrings, one-line docstring and type hints on
public functions; existing configs under config/experiments/ stay byte-identical
unless the unit says otherwise.
Done means: `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` all clean.

Reply in at most 15 lines: (a) STATUS green|red, (b) 3–5 lines what changed and why,
(c) changed files, (d) SESSION DECISIONs if any, (e) the command and last 3 lines of
pytest output. No file contents, no full logs.
```

### 7.2 Validator

```
You validate unit <ID> of trajguard on real Geolife data. Repo root: <pot>. Do not
edit code under src/ or tests/. Read only docs/RUNNING.md §7.2 and <razdelki>.

Runs (Windows; detached via run_in_background; PYTHONHASHSEED=0; one run at a time):
<seznam ukazov `uv run trajguard repeat <config> --seeds 1 2 3`>.
Regression check: <kateri obstoječi rezultati morajo biti bit za bitom enaki>. Never
overwrite anything under results/ that already exists: if a run would write into an
existing results folder, copy the config into the scratchpad with a new experiment
name first, and delete that temporary output folder after comparing.
When a run ends, read only run.json and the last 20 log lines. Compare with pandas,
print only the summary table (≤ 25 rows).

Reply in at most 15 lines: (a) STATUS green|red, (b) wall time per seed,
(c) the summary table of the main metric per arm with 95% CI, (d) regression check
result (identical / differs: which rows), (e) warnings or over-budget calls.
```

### 7.3 Recenzent

```
Review PR <n> (branch <veja>) of trajguard against main for correctness, privacy
argument violations, repo-rule violations and missing tests. Run `git diff main
--stat`, then read the full diff of the changed files only; run `uv run ruff check .`,
`uv run mypy src`, `uv run pytest -q`. You may open at most these plan sections:
<razdelki>. Check specifically: <posebne točke iz datoteke mehanizma>.
Golden rules of the repo: <prilepi razdelek Golden rules iz CLAUDE.md>.
Reply in at most 40 lines: verdict (merge | fix first), numbered critical fixes with
file:line, then minor notes.
```

## 8. Artefakt na koncu seje

Ko je zadnji blok združen, orkestrator pošlje risarja. Risar najprej naloži skill
`artifact-design` in, za diagram, skill `artifact-diagramming`. Nato napiše eno
stran HTML v mapo scratchpad in jo objavi z orodjem `Artifact`. Če risar tega orodja
nima, objavi orkestrator: pred objavo stran prebere v celoti, ker tako zahteva
orodje.

Vsebina strani je **podroben miselni vzorec dejanskega delovanja mehanizma**:

- Pot enega uporabnika od začetka do konca: kaj ima telefon, kaj izračuna, kaj
  pošlje in s katero verjetnostjo resnico.
- Kaj strežnik naredi s poročili: test ali vrata, ocenjevalnik in kateri parameter
  simulatorja se spremeni.
- Kako nastane sintetična pot s časi.
- Kje je meja zasebnosti in zakaj je ε na ravni uporabnika.
- **Prave številke iz validacijskega pogona**: n, histogram poročil, izid testa,
  ocenjeni parametri, dobiček proti rokama priorja in orakla z intervali, AUC napada
  MIA proti kontrolnim rokam.

Vsak pojem je razložen v enem stavku, brez nepojasnjenih kratic. URL artefakta gre v
dnevnik in v končno poročilo.

## 9. Konec seje

Zadnji izvajalec v zadnjem bloku posodobi tri dokumente:

- `docs/HANDOFF.md`: nov podrazdelek z izmerjenimi vrsticami, potekom pogona in
  omejitvami.
- Vrstico stanja v `CLAUDE.md`.
- Razdelek z vrstnim redom sej v načrtu mehanizma, kjer označi opravljene korake.

Orkestrator na koncu uporabniku v slovenščini, brez nepojasnjenih kratic, poroča:

- Kaj je zgrajeno in združeno (PR-ji, merge commiti).
- Kaj je bilo izmerjeno, z zadnjimi vrsticami testov kot dokazom.
- Vse vrstice `ODLOČITEV SEJE` iz dnevnika, ker jih avtor lahko še spremeni.
- Kaj je ostalo odprto in URL artefakta.
