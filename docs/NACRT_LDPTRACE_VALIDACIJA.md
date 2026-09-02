# Načrt: validacija generatorja `ldptrace` proti izvirni kodi

Stanje ob zapisu: 2. september 2026, veja `claude/zm1-ldptrace` (PR #32 na `main`,
čaka na združitev). **Napredek:** PR A (metrike) izveden 2. septembra 2026 na veji
`claude/ldptrace-metrics`; dejanske odločitve so pri D-V.7. PR B in PR C sta odprta. Ta dokument je predaja za eno do tri implementacijske seje, ki
uvedejo (a) metrike uporabnosti iz članka LDPTrace, (b) način branja surovih koordinat
na mreži kot alternativo ujetim zaporedjem odsekov, izbirljiv v konfiguraciji, in
(c) primerjalni pogon izvirne kode in najinega porta nad istimi podatki. Seja prebere
**ta dokument v celoti** in `docs/NACRT_MEHANIZMI.md` §1 (skupni recept); prompt je v §9.

---

## 0. Zakaj in kaj to dokaže

`ldptrace` (`src/trajguard/synthesis/ldptrace.py`, ZM-1) je port članka Du et al.,
PVLDB 2023, z dokumentiranimi odstopanji (celice iz javnega cestnega omrežja namesto
iz surovih točk, prava zadnja celica, payload = celice). Napad na članstvo (MIA) pri
stopnji 20 ne loči porta od naključja (`docs/HANDOFF.md` §2.3), a to ne pove, ali port
**zvesto** posnema izvirnik po uporabnosti. Poročilo (razdelek 7.3) in članek
potrebujeta argument, da je baseline pošten.

**Ponovitev številk iz članka ni mogoča** (preverjeno 2. septembra 2026, glej §2):
repozitorij ne prilaga podatkov, Oldenburg je svež vzorec Brinkhoffovega generatorja,
izbor Porta ni opisan, Hangzhou in Campus nista javna, koda nima argumenta za seme.
Kar je mogoče in kar ta načrt izvede, je **diferencialna validacija**: izvirna koda in
najin port tečeta nad istim vhodom (javni Porto), z istimi parametri in metrikami
članka; ujemanje mora biti znotraj razpršenosti semen, sistematične razlike pa
pojasnjene z dokumentiranimi odstopanji. Dodatno se trendi z ε primerjajo z grafi
članka za Porto le kvalitativno (smer, velikostni red).

## 1. Kar je avtor že odločil (2. september 2026)

1. **Brez ločenega okolja.** Izvirna koda teče v obstoječem okolju `uv` (Python 3.11,
   numpy 2.x), ne v lastnem virtualnem okolju z `numpy == 1.21.4`. Dovoljeni so
   minimalni lokalni popravki v klonu (odstranjeni vzdevki `np.int`/`np.float`/
   `np.bool`, argument za seme), shranjeni kot ena datoteka `.patch` v repozitoriju.
   Rezultat na novem numpy ni bitno enak avtorjevemu, kar je za diferencialno
   primerjavo nepomembno.
2. **Oba načina vhoda v konfiguraciji.** Okolje mora teči z uvozom zaporedij odsekov
   (današnja pot: čiščenje → ujemanje → `as_segments()`) ali z uvozom surovih koordinat
   na mreži (brez zemljevida in ujemanja). Izbira je ključ v YAML, ne ločena koda.
3. **Metrike članka** se uvedejo v trajguard kot čiste funkcije nad populacijami verig
   celic (§3, D-V.5), ne kot klic avtorjeve kode.
4. LDPTrace ostaja **kandidat za baseline** (odločitev D5 v projektu »Izbirni predmeti«
   je odprta); validacija tega ne spreminja.

## 2. Preverjena dejstva o izvirniku (github.com/zealscott/LDPTrace, veja `main`)

Prebral podagent 2. septembra 2026; seja jih ne preverja znova, razen kjer piše
»preveri«.

- **Podatki.** `LDPTrace/data/{oldenburg,porto,campus}/` vsebujejo samo `readme.txt`.
  Koda bere `../data/oldenburg.dat` (besedilo: vrstica `#0:` in nato vrstice
  `>0: x0,y0;x1,y1;...;`, koordinate v enotah, kot so v datoteki, brez projekcije) in
  `../data/porto.xz`, `../data/campus.xz` (`pickle` v `lzma`, seznam poti, vsaka
  seznam parov `(x, y)`). `dataset_stats` zapiše `../data/{ime}_stats.json` z bbox,
  ki definira mrežo `GridMap(n, min_x, min_y, max_x, max_y)`.
- **Mreža in verige.** `trajectory.trajectory_point2grid(t, g, interp=True)`: točka →
  celica, strnitev zaporednih dvojnikov, med nesosednjimi celicami vstavi
  `g.find_shortest_path` (kraljeva hoja). **Preveri** v `grid.py`, kateri osi pripada
  indeks `i` v `i*n + j` (najin `Grid` in `ldptrace._cell` imata vrstico iz y/lat,
  stolpec iz x/lon, vrstično indeksiranje).
- **OUE.** `OUEServer.aggregate` prišteje poročilo in poveča `n` za ena na poročilo;
  `adjust` = `(vsota − n·q)/(p − q)` brez odreza. Pri prehodih je `n` skupno število
  poročil prehodov, natanko kot v najinem portu.
- **Ukazna vrstica** (`parse.py`): `--epsilon 1.0`, `--grid_num 6`, `--query_num 200`,
  `--dataset oldenburg`, `--re_syn`, `--max_len 0.9`, `--size_factor 9.0`,
  `--multiprocessing`. **Semena ni**: `main.py` dvakrat trdo kodira
  `np.random.seed(2022); random.seed(2022)`. Pet »ponovitev« iz članka torej z javno
  kodo brez popravka ni mogočih.
- **Metrike** (`main.py` + `experiment.py` + `utils.py`), v tem vrstnem redu: Density
  Error (Jensen-Shannonova divergenca gostote celic, glajenje 1e-8; funkcija se
  imenuje »distance«, a računa divergenco `0,5·KL(p,m) + 0,5·KL(q,m)`), Hotspot Query
  Error (`1 − NDCG@k` nad najgostejšimi celicami), Point Query AvRE (200 naključnih
  kvadratnih regij velikosti 1/9 prostora; napaka `|real − syn| / max(real, 1 % · |DB|)`),
  Kendall-tau prehodov skozi celice (`(C − D)/(n(n−1)/2)`), Trip Error (JSD
  porazdelitve parov začetek–konec), Diameter Error in Length Error (JSD nad 20
  predali), Pattern F1 Error in Pattern Support Error (`mine_patterns`, vzorci dolžine
  2–8, top-k). Natančne definicije (k, kaj je dolžina, kako se rudarijo vzorci) seja
  **prebere iz `experiment.py` in `utils.py`** (~12 kB skupaj) s podagentom in jih
  pripne v docstringe.
- **Sinteza** shrani sintetično bazo v `../data/{ime}/` (**preveri** format izpisa).
- **Članek.** Porto: 361.591 poti »iz osrednjih območij« (javni nabor ECML/PKDD 2015),
  mreža 6 × 6, ε ∈ {0,5, 1,0, 1,5}, kvantil 0,9, delitev ε/10 in 9ε/10, poizvedbe
  1/9 prostora, povprečje petih sintez. Oldenburg 500.000 poti (generator), Hangzhou
  348.144 (zaseben), Campus 1.000.000 (generiran po drugem članku, ni objavljen).

## 3. Odločitve (»priporočeno« pomeni predlog, ki ga seja potrdi ali spremeni)

- **D-V.1 Podatki: samo Porto.** Javni nabor (Kaggle »Taxi Trajectory Prediction«,
  `train.csv`, ~1,9 GB; stolpci `POLYLINE` kot JSON seznam `[lon, lat]`, `MISSING_DATA`,
  vzorčenje 15 s). Oldenburg bi zahteval Java generator s spletne strani, ki ni nujno
  dosegljiva; ne dela se. Surova datoteka gre v `data/raw/porto/train.csv`
  (nespremenljivo, ni v gitu).
- **D-V.2 Izbor »osrednjih območij«.** Skripta `scripts/porto_to_ldptrace_dat.py`
  (deterministična, brez semena): odvrže `MISSING_DATA == True` in poti z manj kot 2
  točkama, obdrži poti, katerih **vse** točke ležijo v bbox središča Porta. Predlog bbox:
  lon −8,69 … −8,55, lat 41,13 … 41,19; seja izpiše število obdržanih poti in bbox po
  potrebi popravi, da je red velikosti ~360.000; točnega števila iz članka ne lovi.
  Izhod: `data/interim/porto/porto.dat` (format izvirnika, koordinate `lon,lat`) in
  `porto.xz` (za izvirno kodo) ter `porto_stats.json` (bbox, števila). Bbox iz
  statistike je javen vhod v konfiguracijo (D-V.4), tako da najin port in izvirnik
  delita mrežo.
- **D-V.3 Nalagalnik `ldptrace_dat`** (`src/trajguard/datasets/ldptrace_dat.py`,
  podeduje `DatasetLoader`, registrira se kot `dataset`): bere format `.dat`, vsaka pot
  je svoj uporabnik (`user_id = traj_id`, kot v modelu članka »en uporabnik, ena pot«;
  delitev po uporabnikih je s tem delitev po poteh), točke `(lat, lon, t)` s
  sintetičnim časom `t = i·dt_s` (`dt_s` = 15 privzeto; koordinate časa nimajo).
  `native_region = "none"`: tak nalagalnik teče **samo** v načinu celic (D-V.4).
  Čiščenje se v konfiguraciji izklopi (`max_speed_kmh: 1e9`, `min_points: 1`,
  `min_length_m: 0`, `resample_s: 0`; s `resample_s: 0` `clean` obdrži vse točke,
  **preveri** v `datasets/cleaning.py`).
- **D-V.4 Način vhoda v konfiguraciji.** Nov ključ `dataset.representation: segments`
  (privzeto, današnja pot) ali `cells`. V načinu `cells`:
  `dataset.grid: {n_rows, n_cols, bbox: [min_lon, min_lat, max_lon, max_lat]}` je
  obvezen; blok `map` je neobvezen in preverjanje T1 (`map.region == native_region`) se
  izvede le, če je podan; **ujemanje se preskoči**; bazen so `CleanTrajectory` z vnaprej
  izračunano verigo celic (strnitev + kraljeva hoja, D-V.6); zgoščena vrednost različice
  vključi `representation` in `grid`, da se predpomnilniki ne mešajo. Vertikalna
  rezina: v načinu `cells` teče **samo** `membership_inference`; reidentifikacija,
  rekonstrukcija in dom/delo dvignejo jasno napako pred cevovodom (kot obstoječe
  preverbe v `run_experiment`). Roke, ki zahtevajo omrežje (`rn_ldp_synth`), so v
  načinu `cells` zavrnjene pred cevovodom; `markov` in `ldptrace` tečeta.
- **D-V.5 Enotni dostop do zaporedja.** `TrajectoryView` dobi tretjo obliko
  `sequence: tuple[int, ...] | None` (neprozorno zaporedje celih števil v predstavitvi
  pogona: `edge_id` v načinu `segments`, indeksi celic v načinu `cells`) in metodo
  `as_sequence()` (vrne `sequence`, sicer `matched.edge_seq`, sicer `ValueError`).
  `_seq_view` v `attacks/membership.py` zgradi `TrajectoryView(sequence=seq)` namesto
  navidezne `MatchedTrajectory`; `MarkovGenerator.fit` in `LDPTraceGenerator.fit`
  bereta `as_sequence()`. `_mia_pool` gradi kandidate iz `as_sequence()` pogledov
  bazena. Protokol `ShadowGenerator` se ne spremeni (že dela nad zaporedji celih
  števil). `rn_ldp_synth` ostane pri `as_segments()`.
- **D-V.6 Generator v načinu mreže.** `LDPTraceGenerator(network=None, bbox=None, ...)`:
  natanko eden od `network`/`bbox` je podan. Z `bbox` (vrstni red kot `Grid`:
  `min_lon, min_lat, max_lon, max_lat`) je mreža `Grid` iz `representation/views.py`;
  `cell_sequence(seq)` v tem načinu vzame `seq` kot zaporedje celic, strne dvojnike in
  vstavi kraljevo hojo (idempotentno na pravilnih verigah). Strnitev in kraljeva hoja
  se preselita v `representation/views.py` kot `Grid.chain(cells)` (ena implementacija
  za generator, orkestrator in metrike); `ldptrace._king_walk` jo kliče. Orkestrator
  (`_generator_ctor`) v načinu `cells` vbrizga `bbox` (če ga podpis sprejme) in
  **ne** vbrizga `network`; v načinu `segments` obratno. V načinu `cells` je `map_id`
  sintetičnih poti prazen niz.
- **D-V.7 Modul metrik** `src/trajguard/evaluation/ldptrace_metrics.py`: čiste funkcije
  nad dvema populacijama verig celic (`Sequence[Sequence[int]]`) in `Grid`, brez
  bootstrapa (izvirnik poroča točkovne vrednosti; interval čez semena naredi ogrodje):
  `density_error`, `hotspot_query_error`, `point_query_avre` (s `rng` in
  `n_queries`, `size_factor`), `coverage_kendall_tau`, `trip_error`, `length_error`,
  `diameter_error`, `pattern_f1_error`, `pattern_support_error`. Definicije so
  **dobesedno** izvirnikove (glajenje 1e-8, 20 predalov, top-k, kot jih seja prebere iz
  `experiment.py`/`utils.py`); kjer izvirnik meri geometrijo (dolžina, premer) nad
  točkami, se meri nad središči celic verige, kar velja enako za obe strani primerjave.
  Obstoječi `evaluation/utility.py` (JSD celic, W1 dolžin iz S4) se **ne** spreminja.

  **Dejanske odločitve PR A (2. september 2026, potrjene v seji):**
  1. Geometrija **nad točkami, ne nad središči celic**: `length_error`, `diameter_error`
     in `point_query_avre` sprejmejo zaporedja točk `(x, y)`; `sample_points(grid, chains,
     rng)` ponovi izvirnikov `trajectory_grid2points` (ena enakomerna točka v celici,
     veriga z eno celico da dve točki). Izvirnik meri dolžino in premer nad surovimi GPS
     točkami (realno) in nad vzorčenimi točkami (sintetično), poizvedbe nad vzorčenimi
     točkami na obeh straneh; `evaluate(real, syn, grid, rng, real_raw_points=…,
     syn_points=…)` uporabi isto delitev. V PR C se realna stran hrani s surovimi točkami
     iz `.dat`, sintetična z izvirnikovimi shranjenimi točkami oziroma s `sample_points`
     nad verigami porta, da so vsi trije stolpci tabele računani enako.
  2. `pattern_f1` (ne `pattern_f1_error`) vrne F1 = |presek top-k| / k, ker izvirnik pod
     oznako »Pattern F1 error« izpiše sam F1; `coverage_kendall_tau` in `pattern_f1` sta
     višje-je-bolje, ostalih sedem so napake.
  3. JSD z naravnim logaritmom (največ ln 2), glajenje 1e-8 samo v razmerju, brez korena
     — dobesedno `utils.jensen_shannon_distance`.
  4. Izenačenja pri top-k se razbijejo deterministično (podpora padajoče, nato indeks
     celice oziroma vzorec naraščajoče); izvirnik razbija po vrstnem redu vstavljanja po
     semenskem premešanju baze, česar ni mogoče ponoviti. Vrednosti so enake, kadar na
     meji top-k ni izenačenja.
  5. Zaščiti pred deljenjem z nič: F1 pri praznem preseku 0, histogram brez mase `nan`.
  6. Mreža v PR C se zgradi z izvirnikovim odmikom bbox za 1e-6 na vsaki strani, da se
     izvirnikove shranjene točke preslikajo v iste celice; indeksiranje celic (naše
     vrstično po y, izvirnikovo `i·n + j` po x) na nobeno vrednost ne vpliva, razen pri
     izenačenjih.
  7. Kendallov tau po izvirniku pri enakih populacijah doseže 1 le brez izenačenj v
     realnih štetjih (preskočeni pari ostanejo v imenovalcu); test to dokumentira.
  8. Populacijske metrike potrebujejo populacijsko velikost: pri 20 poteh na mreži 10 × 10
     so napake velike tudi pri ε = 600 (20 parov začetek–konec med 10.000 predali). Test
     fixtura zato uporabi 200 poti na mreži 6 × 6 in trdi, da sinteza porta premaga
     naključne sprehode enake dolžine (gostota 0,01 proti 0,14, Kendall 0,73 proti 0,3–0,4,
     F1 vzorcev 0,6 proti 0,15); vrednosti so v docstringu testa.
- **D-V.8 Ogrodje** `src/trajguard/experiments/ldptrace_eval.py` (vzorec
  `rnldp_eval.py`, CLI `python -m trajguard.experiments.ldptrace_eval`): vhod `.dat`
  + `Grid` (iz `porto_stats.json` ali argumentov), za vsak ε in seme prilagodi
  `LDPTraceGenerator(bbox=..., epsilon=ε, n_rows=N, n_cols=N, seed=s)`, generira
  `len(db)` verig in izračuna vseh devet metrik; argument `--score-synthesis <pot>`
  namesto sinteze oceni tujo sintetično bazo (izpis izvirne kode) z istimi metrikami.
  Izhod JSON + tabela v konzoli. Uporabnost sinteze v orkestrator **ni** priključena
  (ostane odprta postavka iz `HANDOFF.md` §2.5).
- **D-V.9 Izvirna koda.** `git clone https://github.com/zealscott/LDPTrace external/LDPTrace`
  (mapa `external/` v `.gitignore`; commit klona zapisan v `HANDOFF.md`). Popravki v
  klonu: numpy 2 (odstranjeni vzdevki), argument `--seed` v `parse.py`/`main.py`
  (privzeto 2022), brez `--multiprocessing` na Windows. Popravek se shrani kot
  `scripts/ldptrace_reference.patch` (`git diff` v klonu) in je edini artefakt izvirne
  kode v gitu. Zagon:
  `uv run python main.py --dataset porto --grid_num 6 --max_len 0.9 --epsilon E --re_syn --seed S`
  iz `external/LDPTrace/LDPTrace/code/`.
- **D-V.10 Mreža primerjave.** ε ∈ {0,5, 1,0, 1,5} (članek), mreža 6 × 6, kvantil 0,9,
  semena 1–5, obe strani. Neobvezno še ε = 2, mreža 12 × 12 (privzetki trajguarda), da
  se rezultat veže na stopnjo iz `HANDOFF.md` §2.3.

## 4. Razrez na PR-je in datoteke

Vsak PR je samostojno združljiv; seja začne v plan mode pri vsakem.

**PR A — metrike (`claude/ldptrace-metrics`).** Novo:
`src/trajguard/evaluation/ldptrace_metrics.py`, `tests/test_ldptrace_metrics.py`.
Spremenjeno: `docs/CODEBASE_STRUCTURE.md` (odstavek `evaluation/`). Brez sprememb
orkestratorja, brez podatkov. *Izvedeno 2. septembra 2026*; dejansko spremenjeno še:
`CLAUDE.md` (vrstica stanja) in ta dokument (stanje, D-V.7). Veja je odcepljena od
`claude/zm1-ldptrace`, ker dva dokumentacijska commita (ta načrt, docstring o štetju
poročil) nista bila na `main`; PR A ju prinese.

**PR B — način surovih koordinat (`claude/cells-mode`).** Novo:
`src/trajguard/datasets/ldptrace_dat.py`, `scripts/porto_to_ldptrace_dat.py`,
`tests/fixtures/ldptrace_dat/tiny.dat` (5 poti, ročno napisane, z eno nesosednjo
preskočeno celico), `tests/test_ldptrace_dat.py`, `tests/test_cells_mode.py`,
`config/experiments/porto_cells_mia.yaml` (način `cells`, mreža 6 × 6, bbox iz
`porto_stats.json`, čiščenje izklopljeno, roke `markov` in `ldptrace` ε ∈ {0,5, 1, 1,5},
napad kot v `geolife_mech_mia_u20.yaml`; delež `max_users` po potrebi za čas).
Spremenjeno: `representation/views.py` (`Grid.chain`, oblika `sequence`,
`as_sequence`), `synthesis/ldptrace.py` (`bbox`), `synthesis/markov.py`
(`as_sequence`), `attacks/membership.py` (`_seq_view`), `experiments/orchestrator.py`
(`load_config`: ključa `representation`/`grid`, neobvezen `map`; `_version_hash`;
nova `_cell_pool`; veja v `run_experiment`; `_generator_ctor`; `_mia_pool`),
`experiments/builtins.py` (uvoz nalagalnika), `.gitignore` (`external/`),
`docs/ARCHITECTURE.md` (odstavek o dveh predstavitvah in obliki `sequence`),
`docs/RUNNING.md` (nov razdelek §9.1), `docs/REZULTATI_SHEMA.md` se **ne** spremeni
(vrstice MIA so iste; `n_rematch_dropped` je v načinu celic prazen — to zapiši v
`RUNNING.md`, ne v shemo). To je > 5 datotek: seja naj predlaga razrez na B1
(predstavitev + generator + nalagalnik + skripta) in B2 (orkestrator + konfiguracija),
če oboje ne gre v en pregleden PR.

**PR C — validacijski pogon (`claude/ldptrace-validation`).** Novo:
`src/trajguard/experiments/ldptrace_eval.py`, `tests/test_ldptrace_eval.py` (na
`tiny.dat`), `scripts/ldptrace_reference.patch`. Spremenjeno: `docs/HANDOFF.md` §2.3
(tabela primerjave, commit klona, bbox in števila Porta), `docs/RUNNING.md` §9.1
(ukazi), `CLAUDE.md` (vrstica stanja), `docs/NACRT_MEHANIZMI.md` §2 (validacija
zaključena), ta dokument (oznaka zaključka in dejanske odločitve).

## 5. Testi (samo fixture, brez omrežja in brez `data/`)

- Metrike: enaki populaciji → vse napake 0, tau = 1, NDCG-napaka 0, F1-napaka 0;
  ročno izračunani primer za gostoto (dve celici, znana JSD) in za pare potovanj;
  neodvisnost od vrstnega reda poti; `point_query_avre` determinističen v `rng`;
  na fixturu `beijing_fixture` z `ldptrace` pri ε = 600 so napake majhne (pasovi
  izmerjeni in zapisani v komentar, kot v `test_ldptrace.py`).
- `Grid.chain`: strnitev dvojnikov, kraljeva hoja med nesosednjimi celicami (ročno
  pričakovane verige), idempotenca; `ldptrace.cell_sequence` v obeh načinih da enako
  verigo za enako pot.
- Nalagalnik: `tiny.dat` → 5 `RawTrajectory` z `user_id == traj_id`, časi `0, 15, …`;
  napačna vrstica dvigne `ValueError` s številko vrstice.
- Generator z `bbox`: konstruktor zavrne oba/nobenega od `network`/`bbox`; `fit` +
  `generate` + `sequence_log_prob` na verigah iz `tiny.dat`; determinizem.
- Način celic v orkestratorju: `porto_cells_mia`-podobna konfiguracija nad
  `tiny.dat` (ali nad fixturom Geolife z `representation: cells` in bbox fixtura) da
  vrstice `membership_inference:synthetic:{markov,ldptrace}`; konfiguracija z
  `rn_ldp_synth` ali z `reidentification` v načinu celic pade **pred** cevovodom;
  `map` brez načina `cells` ostane obvezen; T1 še vedno velja, ko je `map` podan.
- Ogrodje: `ldptrace_eval` na `tiny.dat` z ε = 600 vrne JSON z vsemi devetimi
  ključi, `--score-synthesis` na lastnem izpisu da iste vrednosti kot notranja pot.

## 6. Dokaz in merilo uspeha

```sh
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q
uv run python scripts/porto_to_ldptrace_dat.py data/raw/porto/train.csv data/interim/porto
# izvirnik, 3 ε × 5 semen (iz external/LDPTrace/LDPTrace/code/)
uv run python main.py --dataset porto --grid_num 6 --max_len 0.9 --epsilon 1.0 --re_syn --seed 1
# port + metrike nad isto datoteko
uv run python -m trajguard.experiments.ldptrace_eval --dat data/interim/porto/porto.dat --grid 6 --epsilons 0.5 1.0 1.5 --seeds 1 2 3 4 5 --out results/ldptrace_validation/port.json
uv run python -m trajguard.experiments.ldptrace_eval --dat data/interim/porto/porto.dat --grid 6 --score-synthesis external/LDPTrace/LDPTrace/data/porto/<izpis> --out results/ldptrace_validation/reference_seed1.json
uv run trajguard repeat config/experiments/porto_cells_mia.yaml --seeds 1 2 3
```

Merilo uspeha (zapiše se v `HANDOFF.md` §2.3 kot tabela z devetimi metrikami × tremi ε,
stolpci: izvirnik (lastne metrike), izvirnik (naše metrike), port (naše metrike),
vsak s povprečjem in razponom čez pet semen):

1. **Metrike se ujemajo:** naše metrike nad izvirnikovo sintezo dajo isto vrednost kot
   izvirnikov lastni izpis (do 1e-6; pri AvRE do razlike zaradi drugih naključnih
   poizvedb).
2. **Port sledi izvirniku:** za vsako metriko in ε je povprečje porta znotraj razpona
   petih semen izvirnika ali razlika ni večja od dvakratne razpršenosti semen;
   vsaka sistematična razlika je pojasnjena (edina znana: prava zadnja celica vpliva
   na porazdelitev koncev pri poteh, daljših od L_k).
3. **Trend z ε** se ujema s smerjo v grafih članka za Porto (napake padajo z ε).
4. Vrstice MIA iz `porto_cells_mia` obstajajo za `markov` in `ldptrace`; `ruff`,
   `ruff format --check`, `mypy`, `pytest` čisti; `ruff format --check .` je korak CI-ja,
   ki ga definicija končanega v `CLAUDE.md` ne našteva.

## 7. Tveganja

- **Čas.** ~360.000 poti × (1 + L_k + 1) poročil OUE nad domeno 8·36 = 288 bitov je v
  čistem Pythonu počasno (najin `oue_perturb` kliče `rng.random(size)` na poročilo;
  ocena 1–3 min na seme pri mreži 6 × 6, več pri 12 × 12). Če je prepočasno,
  vektoriziraj `fit` (vsa poročila ene poti v enem klicu `rng.random((k, d))`) v
  istem PR; semantika se ne spremeni. Najprej poženi na podvzorcu (`max_users`).
- **numpy 2 v izvirniku.** Poleg vzdevkov lahko pade `np.random.choice` s
  seznamom `[1, 0]` (dela) ali `pickle` starih struktur (nimamo jih). Vsak popravek
  gre v `.patch`, nič se ne prepisuje v trajguard.
- **Neenaka mreža.** Če izvirnik indeksira `i` po x, so verige zrcaljene in metrike
  gostote se ne ujemajo; `Grid.chain` in `Grid.cell_of` naj takrat dobita isti vrstni
  red kot izvirnik ali pa se izpis izvirnika preslika pred ocenjevanjem. To se pokaže
  že pri merilu 1.
- **Dolžina in premer.** Izvirnik jih meri nad točkami (sintetične točke so naključne v
  celici), mi nad središči celic; pri merilu 1 zato pričakuj razliko, ki jo je treba
  odpraviti tako, da `--score-synthesis` bere izvirnikove točke in jih preslika enako.
- **Delitev po uporabnikih** pri »en uporabnik = ena pot« pomeni, da `train` vsebuje
  polovico poti; pri 360.000 poteh je 16 senčnih modelov × 180.000 poti drago. Za
  `porto_cells_mia` vzemi `max_users` (npr. 2.000), kar je pošteno, ker MIA tu ni cilj
  validacije.
- **Porto prenos** zahteva račun na Kaggle; alternativa je stran tekmovanja ECML/PKDD
  2015. To uredi avtor pred sejo (§8).

## 8. Predpogoji, ki jih uredi avtor pred sejo

- `data/raw/porto/train.csv` (Kaggle: »Taxi Trajectory Prediction (ECML/PKDD 2015)«,
  datoteka `train.csv.zip`, ~1,9 GB razpakirano). Mapa je nespremenljiva in ni v gitu.
- Nič drugega: klon izvirnika, `.dat`, rezultati in popravek nastanejo v seji.

## 9. Prompt za sejo (kopiraj v celoti)

```
Nadaljujeva delo v repozitoriju trajguard: validacija generatorja ldptrace proti izvirni
kodi LDPTrace. Preberi CLAUDE.md, docs/ARCHITECTURE.md, docs/NACRT_LDPTRACE_VALIDACIJA.md
V CELOTI (to je načrt in predaja) ter iz docs/NACRT_MEHANIZMI.md SAMO §1; arhiva arhiv/ ne
odpiraj. Kot vzorec preberi src/trajguard/synthesis/ldptrace.py (celoten modul),
src/trajguard/representation/views.py, src/trajguard/experiments/rnldp_eval.py,
src/trajguard/datasets/geolife.py in cleaning.py, v src/trajguard/experiments/orchestrator.py
funkcije load_config, _version_hash, _matched_pool, _generator_ctor, _mia_pool,
_membership_values in začetek run_experiment, ter tests/test_ldptrace.py. Natančne
definicije metrik naj prebere podagent iz https://github.com/zealscott/LDPTrace
(LDPTrace/code/experiment.py, utils.py, grid.py; skupaj ~20 kB) in jih vrne kot kratek
seznam formul; glavni kontekst naj ostane čist.

Odločitve avtorja, ki jih ne sprašuj znova: izvirna koda teče v obstoječem uv okolju brez
ločenega virtualnega okolja (popravki v klonu gredo v scripts/ldptrace_reference.patch);
oba načina vhoda (zaporedja odsekov / surove koordinate na mreži) sta izbirljiva s ključem
dataset.representation v konfiguraciji; metrike članka se implementirajo kot čiste funkcije
v evaluation/ldptrace_metrics.py; podatki so samo Porto; LDPTrace ostaja kandidat za
baseline. Priporočene odločitve D-V.1 do D-V.10 iz načrta §3 potrdi ali predlagaj
spremembo v plan mode; kjer bi od načrta odstopil, to najprej predlagaj.

Vrstni red (načrt §4): PR A metrike (veja claude/ldptrace-metrics), PR B način surovih
koordinat (veja claude/cells-mode; če je > 5 datotek, predlagaj razrez B1/B2), PR C
validacijski pogon (veja claude/ldptrace-validation). Vsak PR: začni v plan mode in počakaj
na mojo potrditev; definicija končanega je uv run ruff check ., uv run ruff format --check
., uv run mypy src, uv run pytest -q čisti, izpis prilepljen; potisk na origin in PR na main
z gh (opis z dokazi, brez novih odvisnosti). Testi berejo samo tests/fixtures/ (načrt §5).
Datoteka data/raw/porto/train.csv je pri meni; data/raw/ je nespremenljiv. V PR C poženi
ukaze iz načrta §6, tabelo z devetimi metrikami × tremi ε (izvirnik z lastnimi metrikami,
izvirnik z našimi, port z našimi; povprečje in razpon čez pet semen) zapiši v
docs/HANDOFF.md §2.3 skupaj s commitom klona, bboxom in številom poti Porta; posodobi
vrstico stanja v CLAUDE.md, docs/RUNNING.md §9.1, docs/CODEBASE_STRUCTURE.md,
docs/ARCHITECTURE.md (dve predstavitvi) in označi validacijo kot zaključeno v
docs/NACRT_LDPTRACE_VALIDACIJA.md in docs/NACRT_MEHANIZMI.md §2. Koda, identifikatorji,
docstringi in testi v angleščini; pogovor z mano v slovenščini, brez nepojasnjenih
kratic.
```
