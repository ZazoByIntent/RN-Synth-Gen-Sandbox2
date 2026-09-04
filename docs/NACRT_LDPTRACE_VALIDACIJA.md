# Načrt: validacija generatorja `ldptrace` proti izvirni kodi

Stanje ob zapisu: 2. september 2026, veja `claude/zm1-ldptrace` (PR #32 na `main`,
čaka na združitev). **Napredek (2. september 2026, zvečer):** PR A (metrike) izveden
kot PR #33 na veji `claude/ldptrace-metrics` (odprt, čaka na združitev); dejanske
odločitve so pri D-V.7. PR B je razrezan na B1 in B2; **načrt B1 je potrjen, izvedba se
ni začela** — predaja s promptom za novo sejo je v §10. PR B2 in PR C sta odprta. Ta dokument je predaja za eno do tri implementacijske seje, ki
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
- **Porto po najini pretvorbi (izmerjeno 3. septembra 2026, PR B1,
  `scripts/porto_to_ldptrace_dat.py`, 371 s, pod 1 GB pomnilnika).** Od 1.710.670
  vrstic datoteke `train.csv` je obdržanih **367.008 poti** (članek: 361.591) z
  12.136.174 točkami; odvrženih 10 zaradi `MISSING_DATA`, 36.508 z manj kot dvema
  točkama in 1.307.144 z vsaj eno točko zunaj bbox. Bbox izbora: lon −8,64 … −8,60,
  lat 41,14 … 41,17 (osrednji Porto, ~3,4 × 3,3 km; prvotni predlog −8,69 … −8,55 ×
  41,13 … 41,19 bi obdržal 81 % poti, ~1,4 milijona). Bbox obdržanih točk: lon −8,64 …
  −8,600004, lat 41,140008 … 41,169996; `grid_bbox` = ta bbox ± 1e-6, zapisan v
  `data/interim/porto/porto_stats.json` (izhod ni v gitu: `porto.dat` 245 MB,
  `porto.xz` 48 MB).

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
  *(Izvedeno v PR B1 z bbox lon −8,64 … −8,60, lat 41,14 … 41,17 → 367.008 poti; §10.6.)*
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
če oboje ne gre v en pregleden PR. **Odločeno 2. septembra 2026: razrez B1 + B2** (veja
B1 `claude/cells-mode` na `claude/ldptrace-metrics`, B2 se sklada na B1); potrjeni načrt
B1 in skica B2 sta v §10. *B1 izveden 3. septembra 2026* (dejanske datoteke in
odstopanja v §10.4, številke Porta v §2 in §10.6); B2 je odprt.

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

---

## 10. Predaja za PR B1 (2. september 2026; seja zaključena pred izvedbo)

### 10.1 Stanje repozitorija

- `main` = `e4adfe3` (PR #32 združen). Veja `claude/ldptrace-metrics` = PR #33 (PR A,
  odprt): modul `src/trajguard/evaluation/ldptrace_metrics.py`, testi, dokumentacija, plus
  dva dokumentacijska commita (`f18c949` ta načrt, `049bd96` docstring), ki nista na `main`.
- **Veja za B1:** `claude/cells-mode`, odcepljena od `claude/ldptrace-metrics` (če je PR #33
  medtem združen, od `main`; preveri z `gh pr view 33 --json state`). PR na `main`; v opisu
  napiši, da se sklada na PR #33, če ta še ni združen.
- `data/raw/porto/train.csv` (1,94 GB, Kaggle) **je na računalniku**; `data/raw/` je
  nespremenljiv. Map `scripts/` in `external/` še ni.
- Definicija končanega: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest -q` (286 testov, ~55 s); izpis v opis PR. Ruff:
  dolžina vrstice 100; mypy `strict`. Ni novih odvisnosti.

### 10.2 Odločitve avtorja za B1 (potrjene v seji 2. septembra 2026)

1. **Razrez B1 + B2.** B1 = predstavitev in vhodi (ta predaja). B2 = orkestrator (način
   `cells` v konfiguraciji, `_cell_pool`, zavrnitve pred cevovodom, `porto_cells_mia.yaml`,
   RUNNING §9.1, ARCHITECTURE); dobi svoj načrt v plan mode po potrditvi B1. PR C
   potrebuje samo PR A + B1.
2. **Vsi trije generatorji berejo `as_sequence()`**, tudi `rn_ldp_synth` (odstopanje od
   D-V.5): pri ujetih pogledih vrne isto zaporedje odsekov kot prej, v načinu celic je
   `rn_ldp_synth` zavrnjen pred cevovodom (B2). `as_segments()` **ne** pade nazaj na
   `sequence`.
3. **Logika pretvorbe Porta živi v paketu** (`src/trajguard/datasets/ldptrace_dat.py`,
   čiste funkcije, testljive na fixturu), `scripts/porto_to_ldptrace_dat.py` je tanek
   `argparse` ovoj (odstopanje od D-V.2 glede mesta kode; vhod/izhod nespremenjen).
4. **Pretvorba Porta se v B1 požene na pravih podatkih** po prehodu testov; število
   obdržanih poti, bbox in `grid_bbox` gredo v opis PR, v ta dokument (§2 in §10.6) in v
   `HANDOFF.md` §2.3. Izhod (`data/interim/porto/`) ni v gitu.

### 10.3 Preverjena dejstva, ki jih nova seja ne odkriva znova

- `TrajectoryView` (`representation/views.py`) ima danes obliki `clean` in `matched`;
  `as_segments()` kliče `_matched()`. Porabniki `as_segments()`: `synthesis/ldptrace.py`
  (`fit`), `synthesis/markov.py` (`fit`), `synthesis/rn_ldp_synth.py` (`fit`, vrstica
  ~271), `experiments/rnldp_eval.py` (`pool`), testi. Vsi ostali gradijo poglede s
  `clean`/`matched` (`orchestrator.py` vrstici ~824 in ~1124).
- `attacks/membership.py`: `_seq_view(edge_seq)` (vrstica ~183) zgradi navidezno
  `MatchedTrajectory` s praznimi id-ji; protokol `ShadowGenerator` zahteva `fit(views)` in
  `sequence_log_prob(seq)`; `run(target, (pool, candidates))` dela nad terkami celih
  števil. Vzdevek `EdgeSeq = tuple[int, ...]`.
- `experiments/orchestrator.py::_generator_ctor` vbrizga po podpisu: `network` (iz
  ponudnika omrežja) in `seed` (`cfg.seed + odmik`; 0 tarča, `1000 + k` senčni). B2 doda
  `bbox` v načinu celic in takrat `network` ne vbrizga. `_mia_pool` bere `m.edge_seq`.
- `LDPTraceGenerator` (`synthesis/ldptrace.py`): `_build_public_structures(network)`
  računa bbox projiciranih vozlišč (`_x0.._y1`), tabelo odsek → (celica u, celica v),
  `_targets[cell, slot]`; `_cell(x, y)` z odmikom `1e-9`; `_king_walk`, `_adjacent`,
  `_slot`; `cell_sequence(edge_seq)` strne dvojnike in vstavi kraljevo hojo. Testi v
  `tests/test_ldptrace.py` (fixture `train_views`: 20 najkrajših poti v `beijing_fixture`,
  ε = 600 za utišan šum; `test_king_walk_interpolates_non_adjacent_cells` kliče
  `gen._king_walk` — prepiši na `Grid.chain`).
- `Grid` (`representation/views.py`): `bbox = (min_lon, min_lat, max_lon, max_lat)`,
  `cell_of(lat, lon)` vrstično (`row·n_cols + col`, vrstica iz lat, stolpec iz lon,
  odrez na rob). PR A `evaluation/ldptrace_metrics.py` uporablja `grid.bbox`,
  `n_rows`, `n_cols`, `n_cells`; `sample_points` računa razpon celic iz bbox.
- `DatasetLoader` (`datasets/base.py`): `dataset_id`, `native_region`,
  `iter_trajectories() -> Iterator[RawTrajectory]`; `RawTrajectory(traj_id, user_id,
  dataset_id, points=((lat, lon, t), …), start_t, end_t, n_points, source_file)`.
  Orkestrator kliče nalagalnik kot `loader_cls(cfg.dataset_path)` (en pozicijski argument).
  Vzorec: `datasets/geolife.py`. Registracija v `experiments/builtins.py`.
- `datasets/cleaning.py::clean`: z `resample_s = 0` obdrži vse točke (pogoj
  `dt >= 0` vedno drži, ker so časi strogo naraščajoči); `min_points`, `min_length_m`,
  `max_speed_kmh` se v konfiguraciji izklopijo (D-V.3). Dvojniki časov (`dt <= 0`) se
  odvržejo — zato mora nalagalnik dati strogo naraščajoče čase `i·dt_s`.
- Konvencije fixturov: vsaka mapa v `tests/fixtures/` ima `README.md` z opisom in
  tabelo (glej `tests/fixtures/geolife_onroad/README.md`). Session fixture
  `fixture_network` v `tests/conftest.py`.
- Izvirnik (github.com/zealscott/LDPTrace, `LDPTrace/code/`): Porto bere kot
  `lzma.open('../data/porto.xz')` → `pickle.load` → `List[List[Tuple[float, float]]]`
  (pari `(x, y)`; koordinatni sistem iz kode ni razviden, vse metrike so neodvisne od
  merila). `dataset_stats` sam izračuna bbox (min/max vseh točk) in mrežo zgradi z
  odmikom `1e-6` na vsaki strani; `.dat` format (`read_brinkhoff`): vrstica `#<id>:` in
  vrstica `>0: x,y;x,y;...;`. `trajectory_point2grid(interp=True)`: točka → celica
  (linearni pregled, prva zadeta celica), strnitev dvojnikov, kraljeva hoja
  (`find_shortest_path`: `i` in `j` hkrati proti cilju). Indeks izvirnika je `i·n + j`
  z `i` po x (transponirano glede na naš `Grid`; na vrednosti metrik ne vpliva).

### 10.4 Potrjeni načrt B1 po datotekah

**Izvedeno 3. septembra 2026 (veja `claude/cells-mode`, odcepljena od
`claude/ldptrace-metrics`, ker PR #33 še ni bil združen).** Načrt spodaj je izveden
dobesedno, z naslednjimi potrjenimi drobnimi odstopanji:

1. `LDPTraceGenerator._params` dobi ključ `bbox` **samo v načinu `bbox`** (načrt je
   predvideval `None` v načinu omrežja), da `params_hash` sintetičnih zapisov v
   današnjem načinu ostane bit za bitom enak. Dokaz nespremenjenosti: »zlati« izpis
   generatorja v načinu omrežja (verige, `generate` pri fiksnih semenih,
   `sequence_log_prob` nad 20 fixture potmi, štiri konfiguracije) je pred in po
   spremembi identičen (isti md5), glej opis PR.
2. `porto_stats.json` ima poleg načrtovanih polj še `source`, `bbox_filter`,
   `max_trajectories` in `n_read` (sledljivost pogona brez opisa PR).
3. Vrstica `>0:` brez točk je napaka nalagalnika (pisec je nikoli ne zapiše); pri
   `max_trajectories` branje ustavi takoj, ko je doseženo, `n_read` šteje prebrane vrstice.
4. Test kraljeve hoje v `tests/test_ldptrace.py` kliče `gen.grid.chain`; isti ročno
   pričakovani primeri so še v `tests/test_views.py`. Dodana testa: omrežni način
   sprejme poglede samo s `sequence` (senčni modeli napada članstva) in da isti izpis kot
   z ujetimi pogledi; oba načina dasta isto verigo za isto pot.
5. `docs/RUNNING.md` §1: pričakovano število testov popravljeno na 316.
6. Pretvorba Porta je **varčna s pomnilnikom**: obdržane poti hrani kot polja `numpy`
   oblike `(n, 2)` (16 B na točko namesto ~100 B za terko), `porto.dat` piše sproti,
   `porto.xz` pa kot ročno sestavljen tok `pickle` (opkode `EMPTY_LIST`/`MARK`/`APPENDS`,
   `BINFLOAT` + `TUPLE2`), ki ga `pickle.load` prebere kot isti
   `list[list[tuple[float, float]]]`, kot bi ga dal `pickle.dump` (test čez meje paketov
   `APPENDS`). Razlog: prvi zagon s seznami terk je na 16 GB računalniku presegel 8 GB.
   Privzeti bbox `PORTO_CENTRE_BBOX` je popravljen na izmerjeno vrednost (§10.6), fixture
   `train_tiny.csv` ima eno pot premaknjeno v ta bbox.

**`src/trajguard/representation/views.py`**
- `Grid.chain(cells: Sequence[int]) -> list[int]`: preveri obseg indeksov, strne
  zaporedne dvojnike, med nesosednjimi celicami vstavi kraljevo hojo (vrstica in stolpec
  hkrati proti cilju: diagonalno, nato naravnost — natanko današnji `ldptrace._king_walk`).
  Idempotentna na pravilnih verigah. `Grid.adjacent(a, b) -> bool` (Čebiševljeva
  razdalja 1, `a != b`).
- `TrajectoryView(clean=None, matched=None, sequence=None)`: tretja oblika
  `sequence: tuple[int, ...] | None`; vsaj ena oblika, sicer `ValueError`.
  `as_sequence()`: `sequence` → sicer `matched.edge_seq` → sicer `ValueError`.
  `traj_id`/`user_id`: `clean` → `matched` → `""`. `split`, `map_id`, `as_gps`,
  `as_segments`, `as_cells` nespremenjeni.

**`src/trajguard/synthesis/ldptrace.py`**
- `__init__(self, network=None, bbox=None, epsilon=1.0, n_rows=12, n_cols=12, quantile=0.9,
  length_share=0.1, alpha=0.3, beta=0.2, seed=0)`: natanko eden od `network`/`bbox`.
  Pozicijski klic `LDPTraceGenerator(network, ...)` iz obstoječih testov in
  `_generator_ctor` mora še delati.
- `self.grid: Grid` v obeh načinih: omrežje → bbox projiciranih vozlišč (osi CRS
  zemljevida), `bbox` → podani lon/lat bbox. `_targets` in `_slot` ostaneta; `_king_walk`
  in `_adjacent` se odstranita, `cell_sequence` kliče `self.grid.chain(cells)`.
- `cell_sequence(seq)`: način omrežja → odseki → celici krajišč (kot danes; `_cell` z
  `1e-9` ostane, da se izmerjene vrednosti ne premaknejo) → `grid.chain`; način `bbox` →
  `seq` so indeksi celic → `grid.chain(seq)`.
- `fit` bere `view.as_sequence()`; `sequence_log_prob` nespremenjen; `_params` dobi
  `"bbox"` (None v načinu omrežja); `map_id` sintetičnih poti v načinu `bbox` je `""`.
  Docstring modula: odstavek o dveh načinih vhoda.

**`src/trajguard/synthesis/markov.py`, `src/trajguard/synthesis/rn_ldp_synth.py`**:
`fit` bere `view.as_sequence()`; docstring.

**`src/trajguard/attacks/membership.py`**: `_seq_view(seq)` vrne
`TrajectoryView(sequence=tuple(seq))`; docstring protokola `ShadowGenerator`.

**`src/trajguard/datasets/ldptrace_dat.py` (novo) + `experiments/builtins.py`**
- `LDPTraceDatLoader(path, dt_s=15.0)`, `@register("dataset", "ldptrace_dat")`,
  `dataset_id = "ldptrace_dat"`, `native_region = "none"`. Bere `.dat` v formatu
  izvirnika: zapis = `#<id>:` + `>0: lon,lat;lon,lat;...;`. `user_id = <id>`,
  `traj_id = "ldptrace_dat/<id>"`, točke `(lat, lon, i·dt_s)`, `start_t = 0`,
  `end_t = (n−1)·dt_s`. Napačna vrstica → `ValueError` s številko vrstice.
- Pretvorba Porta kot čiste funkcije: `iter_porto_polylines(csv_path)` (pretočno,
  `csv` + `json`, dvig `csv.field_size_limit`), filtriranje (odvrže
  `MISSING_DATA == "True"`, poti z < 2 točkama, poti, ki niso v celoti v bbox),
  `write_dat(path, trajs)`, `write_reference_xz(path, trajs)` (`lzma` + `pickle` seznama
  seznamov parov `(lon, lat)`), `convert_porto(csv_path, out_dir, bbox,
  max_trajectories=None) -> dict` (zapiše `porto.dat`, `porto.xz`, `porto_stats.json`:
  `bbox` obdržanih točk, `grid_bbox` = isti bbox ± 1e-6, števila obdržanih/odvrženih po
  razlogu, število točk). Deterministično, brez semena; zavrne pisanje pod `data/raw/`.
  Pomnilnik: seznam ~12 M točk za `pickle` (~1,4 GB) — sprejeto, izvirnik ga tako ali
  tako naloži v celoti.

**`scripts/porto_to_ldptrace_dat.py` (novo)**: `argparse` ovoj,
`uv run python scripts/porto_to_ldptrace_dat.py data/raw/porto/train.csv data/interim/porto [--bbox -8.69 41.13 -8.55 41.19] [--max-trajectories N]`.

**Fixturi (novo, vsak z `README.md`)**
- `tests/fixtures/ldptrace_dat/tiny.dat`: 5 ročno napisanih poti v bbox `0..6 × 0..6`
  (mreža 6 × 6, celica = `row·6 + col` pri celoštevilskih koordinatah), z eno nesosednjo
  preskočeno celico (kraljeva hoja), eno potjo z eno samo točko in eno s ponovljeno celico.
- `tests/fixtures/porto_csv/train_tiny.csv`: 6 vrstic v shemi Kaggle (`TRIP_ID, CALL_TYPE,
  ORIGIN_CALL, ORIGIN_STAND, TAXI_ID, TIMESTAMP, DAY_TYPE, MISSING_DATA, POLYLINE`):
  3 veljavne v bbox, 1 `MISSING_DATA=True`, 1 z eno točko, 1 delno zunaj bbox.

**`.gitignore`**: `external/`.

**Testi**
- `tests/test_views.py`: `Grid.chain` (strnitev; kraljeva hoja z ročno pričakovanimi
  verigami — primeri iz `test_king_walk_interpolates_non_adjacent_cells`: `(0,0) → (3,1)`
  gre skozi `(1,1), (2,1)`; sosednji brez vmesnih; `(2,2) → (0,0)` skozi `(1,1)`;
  idempotenca; obseg), `Grid.adjacent`, pogled s `sequence` (`as_sequence`, padec nazaj na
  `matched`, napaka brez oblik, prazni id-ji, `map_id == ""`).
- `tests/test_ldptrace.py`: test kraljeve hoje prepisan na `Grid.chain`; novo: konstruktor
  zavrne oba/nobenega; način `bbox` nad verigami iz `tiny.dat` (`fit` + `generate` +
  `sequence_log_prob`, determinizem, `map_id == ""`); enaka veriga v obeh načinih za isto
  pot (celice krajišč odsekov iz mreže omrežnega generatorja → generator `bbox` z istim
  projiciranim bbox).
- `tests/test_ldptrace_dat.py` (novo): nalagalnik na `tiny.dat` (5 poti, `user_id == id`,
  časi `0, 15, …`, registrirano ime), napačna vrstica → `ValueError` s številko vrstice;
  `convert_porto` na `train_tiny.csv` v `tmp_path` (števila po razlogih, bbox, `porto.dat`
  se prebere nazaj z nalagalnikom, `porto.xz` vsebuje seznam parov, `grid_bbox` = bbox ±
  1e-6, zavrnitev `data/raw`).
- `tests/test_membership.py`, `test_markov.py`, `test_rn_ldp_synth.py`: brez sprememb —
  dokaz, da je `as_sequence()` pri ujetih pogledih neopazen.

**Dokumentacija**: `docs/CODEBASE_STRUCTURE.md` (registrirana imena: `ldptrace_dat`;
stavek o `datasets/ldptrace_dat.py` in `scripts/`), `docs/ARCHITECTURE.md` (odstavek pri
`TrajectoryView` o obliki `sequence` in `as_sequence()`; `ldptrace_dat` z
`native_region = "none"` v tabeli konsistentnosti, opomba, da teče samo v načinu celic
iz B2), `docs/RUNNING.md` (nov §9.1 »LDPTrace validation inputs« z ukazom skripte in
pričakovanim izpisom), ta dokument (§2 in §10.6: število poti in bbox Porta; oznaka
B1 izveden), `CLAUDE.md` (vrstica stanja).

### 10.5 Skica B2 (svoj načrt po potrditvi B1)

*Skica je nadomeščena s potrjenim načrtom in predajo za B2 v §11 (3. september 2026);
spodnje besedilo ostaja kot izvor.*

`experiments/orchestrator.py`: `load_config` bere `dataset.representation`
(`segments` privzeto | `cells`) in v načinu `cells` obvezen `dataset.grid: {n_rows, n_cols,
bbox}` ter neobvezen `map`; `_version_hash` vključi `representation` in `grid`; nova
`_cell_pool` (čiščenje → delitev → veriga celic `Grid.chain(as_cells(grid))` na pot,
predpomnjena kot `clean.parquet` + `chains.parquet`); `run_experiment` preveri T1 le, če je
`map` podan, in v načinu `cells` pred cevovodom zavrne vse napade razen
`membership_inference` ter roko `rn_ldp_synth`; `_generator_ctor` vbrizga `bbox` namesto
`network`; `_mia_pool`/`_membership_values` gradita kandidate in poglede iz verig
(`TrajectoryView(clean=..., sequence=chain)`). Nova `config/experiments/porto_cells_mia.yaml`
(mreža 6 × 6, `grid_bbox` iz `porto_stats.json`, čiščenje izklopljeno: `max_speed_kmh: 1e9`,
`min_points: 1`, `min_length_m: 0`, `resample_s: 0`; roki `markov` in `ldptrace`
ε ∈ {0,5, 1, 1,5}; napad kot v `geolife_mech_mia_u20.yaml`; `max_users` ~2.000 za čas),
`tests/test_cells_mode.py`, `docs/RUNNING.md` §9.1, `docs/ARCHITECTURE.md`;
`docs/REZULTATI_SHEMA.md` se ne spremeni.

### 10.6 Zagon pretvorbe Porta (v B1, po prehodu testov)

`uv run python scripts/porto_to_ldptrace_dat.py data/raw/porto/train.csv data/interim/porto`
s predlaganim bbox lon −8,69 … −8,55, lat 41,13 … 41,19; če je število obdržanih poti daleč
od ~360.000, bbox popravi (širši → več poti) in oboje zapiši sem in v `HANDOFF.md` §2.3.

**Izmerjeno 3. septembra 2026.** Predlagani bbox je bil daleč prevelik: na prvih
300.000 vrsticah je obdržal 81 % poti (ocena ~1,4 milijona na celotni datoteki), zato je
bil na istem vzorcu izbran ožji bbox z deležem ~0,22: **lon −8,64 … −8,60, lat 41,14 …
41,17** (zdaj privzeta vrednost `PORTO_CENTRE_BBOX` v `datasets/ldptrace_dat.py`, ukaz
zgoraj teče brez `--bbox`). Celotna pretvorba: 1.710.670 vrstic → **367.008 poti**
(članek 361.591), 12.136.174 točk, 371 s; bbox točk lon −8,64 … −8,600004, lat 41,140008
… 41,169996, `grid_bbox` = ± 1e-6 (natančne vrednosti v `porto_stats.json` in v
`RUNNING.md` §9.1). Prvi poskus s seznami terk je porabil > 8 GB pomnilnika in je bil
prekinjen; pretvorba zato hrani poti kot polja `numpy` in piše pickle pretočno (§10.4,
odstopanje 6).

### 10.7 Prompt za sejo B1 (kopiraj v celoti)

```
Nadaljujeva validacijo generatorja ldptrace proti izvirni kodi LDPTrace v repozitoriju
trajguard: PR B1 (predstavitev in vhodi za način surovih koordinat). Preberi CLAUDE.md,
docs/ARCHITECTURE.md in docs/NACRT_LDPTRACE_VALIDACIJA.md §10 V CELOTI (to je predaja s
potrjenim načrtom) ter iz istega dokumenta §3 (D-V.2 do D-V.6) in §5; arhiva arhiv/ ne
odpiraj. Kot vzorec preberi src/trajguard/representation/views.py,
src/trajguard/synthesis/ldptrace.py (celoten modul), src/trajguard/datasets/geolife.py,
src/trajguard/datasets/base.py, v src/trajguard/attacks/membership.py funkcijo _seq_view in
protokol ShadowGenerator, v src/trajguard/synthesis/markov.py in rn_ldp_synth.py samo fit,
src/trajguard/experiments/builtins.py, tests/test_ldptrace.py, tests/test_views.py in
tests/fixtures/geolife_onroad/README.md (konvencija fixturov).

Odločitve avtorja, ki jih ne sprašuj znova (§10.2): razrez B1 + B2; vsi trije generatorji
berejo as_sequence(); logika pretvorbe Porta v src/trajguard/datasets/ldptrace_dat.py,
skripta scripts/porto_to_ldptrace_dat.py je tanek ovoj; pretvorba se po prehodu testov
požene na data/raw/porto/train.csv (je na računalniku; data/raw/ je nespremenljiv), izhod
v data/interim/porto/, številke v opis PR, v §2 in §10.6 tega dokumenta in v
docs/HANDOFF.md §2.3.

Načrt B1 je potrjen (§10.4): začni v plan mode, načrt na kratko povzemi in ga predloži v
potrditev; odstopanja od §10.4 najprej predlagaj. Veja claude/cells-mode se odcepi od
claude/ldptrace-metrics (PR #33), če ta še ni združen (preveri z gh pr view 33), sicer od
main. Definicija končanega: uv run ruff check ., uv run ruff format --check ., uv run mypy
src, uv run pytest -q čisti, izpis prilepljen; potisk na origin in PR na main z gh (opis z
dokazi, brez novih odvisnosti, opomba o skladanju na PR #33). Testi berejo samo
tests/fixtures/. Po oddaji B1 predlagaj načrt za B2 (§10.5) v plan mode in počakaj na
mojo potrditev. Koda, identifikatorji, docstringi in testi v angleščini; pogovor z mano v
slovenščini, brez nepojasnjenih kratic.
```

## 11. Predaja za PR B2 (3. september 2026; seja zaključena pred izvedbo)

### 11.1 Stanje repozitorija

- `main` = `e4adfe3` (PR #32 združen). Odprta sta PR #33 (`claude/ldptrace-metrics`, PR A)
  in **PR #34 (`claude/cells-mode`, PR B1, skladan na #33)**: commiti `8bd3d42` (nalagalnik
  `ldptrace_dat` + pretvorba Porta), `144e526` (oblika `sequence`, `Grid.chain`, način `bbox`
  generatorja `ldptrace`), `68a0f96` (varčna pretvorba, privzeti bbox), `7aa475d`
  (dokumentacija) in commit s to predajo.
- **Veja za B2:** `claude/cells-mode-orchestrator`, odcepljena od `claude/cells-mode` (če je
  PR #34 medtem združen, od `main`; preveri z `gh pr view 34 --json state`). PR na `main`; v
  opisu napiši, da se sklada na PR #34, če ta še ni združen.
- **Podatki na računalniku** (niso v gitu): `data/interim/porto/porto.dat` (245 MB, 367.008
  poti), `porto.xz` (48 MB), `porto_stats.json` z `grid_bbox`
  `[-8.640001, 41.140007000000004, -8.600003000000001, 41.169996999999995]` (§10.6);
  `data/raw/porto/train.csv` je nespremenljiv. Zemljevida Porta ni in ga B2 ne potrebuje.
- Definicija končanega: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest -q` (316 testov, ~68 s); izpis v opis PR. Ruff: dolžina
  vrstice 100; mypy `strict`. Ni novih odvisnosti.
- Praktična opomba iz B1: ukazi v ozadju orodja Bash imajo omejitev 10 minut; daljši pogoni
  (branje 367.008 poti v predpomnilnik, `repeat` čez tri semena) naj tečejo kot samostojen
  proces (`Start-Process` v PowerShellu z izpisom v dnevnik) in se spremljajo prek dnevnika.
  Vsaka pot Porta je svoj uporabnik, zato `max_users` pomeni število poti.

### 11.2 Odločitve avtorja za B2 (potrjene v seji 3. septembra 2026)

1. **Načrt B2 iz §11.4 je potrjen** skupaj s petimi dopolnitvami skice §10.5:
   (a) blok `map_matching` je v načinu `cells` neobvezen; (b) `privacy_mechanisms` je v
   načinu `cells` zavrnjen pred cevovodom (zaščite potrebujejo ponovno ujemanje na
   zemljevidu); (c) v generator se poleg `bbox` vbrizgata `n_rows`/`n_cols` mreže, nasprotujoče
   vrednosti v konfiguraciji so napaka; (d) `representation` in `grid` vstopita v
   `_version_hash` **samo v načinu `cells`**, da hash današnjih konfiguracij ostane bit za
   bitom enak in se obstoječi bazeni (stopnja 182) ne preračunavajo; (e) test konec-do-konca
   teče nad fixturom `geolife_onroad` v načinu `cells`, `tiny.dat` služi enotnemu testu bazena.
2. `docs/REZULTATI_SHEMA.md` se ne spremeni (nov stolpec ni potreben; `n_rematch_dropped` je
   v načinu celic prazen, kar se zapiše v `RUNNING.md`).
3. Pravi pogon `config/experiments/porto_cells_mia.yaml` (`max_users: 2000`) in
   `trajguard repeat … --seeds 1 2 3` se poženeta po prehodu testov; vrstice gredo v
   `docs/HANDOFF.md` §2.3, `RUNNING.md` §9.2 in v §11.5 tega dokumenta.
4. B2 se izvede v sveži seji: začne v plan mode, načrt povzame in ga predloži v potrditev.

### 11.3 Preverjena dejstva, ki jih nova seja ne odkriva znova

Številke vrstic veljajo za `src/trajguard/experiments/orchestrator.py` na commitu `7aa475d`
(datoteka ima ~1.630 vrstic; B1 je ni spreminjal).

**Konfiguracija.** `RunConfig` (zamrznjen dataclass, vrstice 108–147) ima polja `exp_id`,
`seed`, `split_seed`, `output_dir`, `cache_dir`, `protected_dir`, `map_source`, `map_region`,
`map_bbox`, `map_crs`, `map_dir`, `dataset_id`, `dataset_path`, `dataset_native_region`,
`max_users`, `cleaning: CleaningConfig`, `matcher_id`, `radius_m`, `gps_error_m`,
`k_candidates`, `min_match_score`, `fractions`, `mechanisms`, `generators`, `attacks`,
`metric_names`, `top_k`, `utility_names`, `utility_grid`, `bootstrap_n`, `bootstrap_ci`,
`measure_memory`, `attack_time_budget_s`, `export`, `plots`; polja zemljevida so
neopcijska. `MechanismSpec` (93–106, lastnost `ref` = `id:k=v,…`) je skupen mehanizmom in
generatorjem; `AttackSpec` 78–91; `_ORCHESTRATOR_ATTACKS` 66–68; `_req(d, key, ctx)` 149–152.
`load_config` (329–461): obvezni bloki `experiment`, **`map`**, `dataset`, `cleaning`,
**`map_matching`**, `split`, `metrics` (335–341); `map.bbox` 4 vrednosti (342–344); polja
zemljevida 422–427; `dataset.id` = ime nalagalnika, `dataset.path`, neobvezen
`native_region`, `max_users` ≥ 1 (413–415, 428–431); `cleaning` zahteva vse štiri ključe
(432–437); `map_matching` zahteva `matcher` in `min_match_score` (438–442); `split.scheme`
samo `by_user`, `fractions` obvezne (346–348, 443); generatorji/mehanizmi neobvezni prek
`_variant_specs` (301–326, seznami parametrov se razširijo v mrežo); napadi 378–381 +
`_attack_specs` 155–289 (napad na članstvo 237–273: `attacker` ⊆ `{n_shadow, subsample}`,
`target_scope == ['synthetic']`, `fprs` v (0, 1)); `metrics` 365–377 in 444–451; `reporting`
350–364; semena 410–411. **Preverba T1 ni v `load_config`**, ampak na začetku
`run_experiment` (1187–1202): `ConsistencyError`, če `cfg.map_region != loader_cls.native_region`;
`LDPTraceDatLoader.native_region == "none"` zato danes pade pri vsakem zemljevidu.

**Hash in predpomnilnik.** `_version_hash` (509–534): sha256 slovarja
`{"map": [source, region, crs, bbox, str(map_dir), _built_map_timestamp], "dataset": [id,
str(path)], "cleaning": asdict, "matching": [matcher_id, radius_m, gps_error_m,
k_candidates, min_match_score], "sample": max_users, "split": [sorted(fractions),
split_seed]}`, 16 šestnajstiških znakov; seme pogona, roke in napadi niso v hashu.
`_built_map_timestamp` (493–507) bere `map_dir/map_region/meta.json`. Predpomnilnik bazena:
`cfg.cache_dir / _version_hash(cfg)` (682) s `matched.parquet` (`_MATCHED_SCHEMA` 466–476),
`clean.parquet` (`_CLEAN_SCHEMA` 478–490) in atomarno zapisanim `meta.json`
(`{"dropped", "split_counts", …}`); `_write_pool_cache` 566–616, `_read_pool_cache` 618–651.
`_matched_pool(cfg, provide)` (678–707): predpomnilnik → `provide()` (687) → nalagalnik
`registry.get("dataset", cfg.dataset_id)(cfg.dataset_path)` → `clean` (689–693) →
`_subsample_users(cleaned, max_users, split_seed)` (694–695, 709–723) → `split_by_user`
(696) → `match_many` (701) → `clean_by_id` samo za ujete (702–703) → zapis. `dropped` so
izgube pri ujemanju surovega bazena in gredo v `run.json` kot `n_dropped` (1592);
`n_rematch_dropped` je izguba pri ponovnem ujemanju zaščitene izdaje in pri vrsticah MIA
ni nikoli nastavljen.

**Omrežje.** `_NetProvider` (464), `_net_provider(cfg)` (654–676, memoiziran); klici
`provide()` samo na vrsticah 687 (`_matched_pool`), 832 (`_protected_pool`) in 1062
(`_generator_ctor.make`).

**`run_experiment`** (od 1181): zaščita pisanja pod `data/raw` (1184–1186) → T1
(1187–1202) → načrti napadov (1204–1272; MIA 1245–1259: zahteva neprazne generatorje in
deleža `train` ter `test` > 0, sonda konstruktorja napada) → načrti mehanizmov
(1273–1280) → `provide = _net_provider(cfg)` (1282) → načrti generatorjev (1283–1294:
`inspect.signature(gen_cls).bind_partial(**params)`, nato `_generator_ctor`) →
`_matched_pool` **brezpogojno** (1296) → `_build_metrics` (1297) → `_target_pools`
(1298; 853–871: obseg `synthetic` ne ustvari bazena, pri konfiguraciji samo z MIA je
`pools == {}`) → razpošiljanje napadov (1305–1369; MIA 1317–1323 kliče
`_membership_values(cfg, spec, attack_cls, matched, clean_by_id, gen_plans)`) → blok
koristnosti (1371–1413; `Grid(bbox=cfg.map_bbox, …)` na 1371 se zgradi brezpogojno, telo
teče le za bazene `protected:` z `metrics.utility`) → `arms` (1415–1425, samo iz `pools`) →
`_write_results` (klic 1428–1439, definicija 1535–1618; `run.json` 1589–1616 z
`n_matched = len(matched)` (1591), `n_dropped` (1592), `split_counts`, `arms`,
`over_budget`, `warnings`).

**Napad na članstvo.** `_generator_ctor(gen_cls, params, cfg, provide)` (1047–1068):
vbrizg po podpisu, `network = provide()[0]`, `seed = cfg.seed + odmik` (0 tarča, `1000 + k`
senčni). `_mia_pool(matched, clean_by_id)` (1070–1097): bazen = senčne + učne + testne
poti (`m.edge_seq`, 1092–1094), kandidati `(indeks, je_član)`, napaka brez učnih ali
testnih poti (1087–1091). `_membership_values` (1100–1174): tarča se prilagodi na
`TrajectoryView(clean=clean_by_id[m.traj_id], matched=m)` (1124), `result_id =
f"membership_inference:synthetic:{gspec.ref}"` (1130–1131), varovalo S4-2 (1132–1139),
vrstice (1149–1173) z `arm_id`, `target_ref`, `epsilon` (iz atributa generatorja),
`n_shadow`, `n_pool` (= število kandidatov), `n_members`, `n_nonmembers`. Pogledi se v
orkestratorju gradijo samo na vrsticah 824 (`_protected_pool`) in 1124. Konstruktorji:
`LDPTraceGenerator(network=None, bbox=None, epsilon=1.0, n_rows=12, n_cols=12, quantile,
length_share, alpha, beta, seed=0)`; `MarkovGenerator(order, alpha, max_len)` brez
`network` in `seed`; `RNLDPSynthGenerator(network, …)` zahteva omrežje.

**Ostalo.** `experiments/cli.py`: `run` → `_print_summary` (`load_config`, pri `--seed`
`replace(cfg, seed=…, output_dir=cfg.output_dir / f"seed{seed}")`, `run_experiment`);
`repeat` → `run_repetitions` v `experiments/repeat.py`. `datasets/split.py::split_by_user(trajs,
fractions, seed)`; `datasets/cleaning.py::clean(raw, cfg) -> CleanTrajectory | None` je z
`max_speed_kmh: 1e9, min_points: 1, min_length_m: 0, resample_s: 0` prepustno.
`reporting/results_schema.py::RESULTS_COLUMNS` (21–59) in `tests/test_results_schema.py`
pripenjata shemo na `docs/REZULTATI_SHEMA.md`; vrstice MIA že polnijo vse potrebne stolpce.
`docs/RUNNING.md`: §9.1 je zaseden (pretvorba Porta), razdelek za pogon v načinu celic je
§9.2; §10 (predpomnjenje) omenja samo hash današnje poti.

**Testi.** `tests/test_orchestrator.py`: `base_config(tmp_path, maps_dir, region)` (17–67;
`experiment.cache_dir`, `experiment.protected_dir`, `map.dir` so ključi samo za teste),
`beijing_maps_dir` (70–76, kopija `tests/fixtures/maps/beijing_fixture` v
`tmp_path/maps/beijing`), `write_config` (79–82), `mia_config` (281–294: `n_shadow: 8`,
`subsample: 0.5`, `fprs: [0.25]`), enotna testa `_mia_pool` (348–402), MIA konec-do-konca
(405–427; bere vrnjeni seznam `MetricValue`, `out/metrics.csv`, `out/run.json`), test
predpomnilnika (137–146: natanko `{matched.parquet, clean.parquet, meta.json}`), test hasha
(152–163). Testi zavrnitev pred cevovodom podajo neobstoječo mapo zemljevidov, da bi vsak
korak cevovoda padel. `tests/test_repeat.py:10` uvaža pomožne funkcije iz
`test_orchestrator`. Fixture `geolife_onroad`: 8 poti, 2 uporabnika (005, 006); delitev
po uporabnikih z deleži 0,5/0,2/0,2/0,1 da učnega in testnega uporabnika (4 nečlani, zato
`fprs: [0.25]`); čiščenje s privzetimi vrednostmi obdrži vse točke. Fixture `tiny.dat`:
5 poti, pričakovane verige v `tests/fixtures/ldptrace_dat/README.md`.

**Pomnilnik pravega pogona.** Vrstni red `nalagalnik → clean → subsample` očisti vseh
367.008 poti (12,1 M točk kot terke, ~1,7 GB), preden `max_users` izbere 2.000; na 16 GB
je to sprejemljivo in se zgodi enkrat (predpomnilnik).

### 11.4 Potrjeni načrt B2 po datotekah

**`src/trajguard/experiments/orchestrator.py`** (edina datoteka s pravo logiko)

- `RunConfig`: novi polji `representation: str` (`"segments"` | `"cells"`) in
  `cell_grid: Grid | None`; lastnost `has_map` (`map_source != ""`).
- `load_config`: bere `dataset.representation` (privzeto `segments`; druga vrednost →
  `ValueError`). V načinu `cells`: `dataset.grid: {n_rows, n_cols, bbox}` obvezen
  (`n_rows`, `n_cols` ≥ 2, bbox 4 števila, min < max); blok `map` neobvezen (če manjka:
  `map_source/region/crs = ""`, `map_bbox` = bbox mreže, ker je polje neopcijsko); blok
  `map_matching` neobvezen (ujemanja ni). V načinu `segments` se nič ne spremeni: `map` in
  `map_matching` ostaneta obvezna.
- `_version_hash`: v načinu `cells` doda ključa `representation` in `grid`
  (`[n_rows, n_cols, bbox]`); v načinu `segments` slovar ostane natanko današnji (isti
  hash → obstoječi predpomnilniki veljajo).
- Nov zapis `CellChain(traj_id, user_id, chain: tuple[int, ...])` in nova
  `_cell_pool(cfg) -> (chains, clean_by_id, split_counts)`: nalagalnik → `clean` →
  `_subsample_users` → `split_by_user` (isti vrstni red kot `_matched_pool`) → za vsako pot
  `grid.chain(TrajectoryView(clean=t).as_cells(grid))`. Predpomnilnik v
  `cache_dir/<hash>/`: `clean.parquet` (ista shema kot danes), `chains.parquet`
  (`traj_id, user_id, chain: list<int64>`), `meta.json` (`dropped: 0`, `split_counts`,
  `representation`, `grid`). `_write_pool_cache`/`_read_pool_cache` se razdelita na
  pomožne funkcije po tabelah (`_write_clean_table`, `_read_clean_table`, …), obstoječi
  klici ostanejo.
- `run_experiment`: preverba T1 samo, če je `map` podan (`has_map`); v načinu `cells`
  pred cevovodom zavrne vsak napad razen `membership_inference`, neprazen
  `privacy_mechanisms` in vsako roko generatorja, katere podpis zahteva `network`, ne
  sprejme pa `bbox` (`rn_ldp_synth`); bazen pride iz `_cell_pool` (`matched = []`,
  `dropped = 0`), `_target_pools` da prazen slovar, blok koristnosti se izvede le, če bazeni
  obstajajo; `run.json` dobi `representation`, `n_matched` v načinu celic šteje verige.
- `_generator_ctor`: v načinu `cells` vbrizga `bbox` (bbox mreže) ter `n_rows`/`n_cols`,
  če jih podpis sprejme in jih konfiguracija ne podaja; če jih podaja z drugo vrednostjo kot
  mreža → `ValueError` že pri načrtovanju rok; `network` se ne vbrizga. Način `segments`
  nespremenjen.
- `_mia_pool` in `_membership_values` sprejmeta `Sequence[MatchedTrajectory | CellChain]`;
  pomožni `_item_sequence(item)` (`edge_seq` ali `chain`) in `_item_view(item, clean)`
  (`TrajectoryView(clean=…, matched=…)` ali `TrajectoryView(clean=…, sequence=chain)`).
  Obstoječi enotni testi `_mia_pool` z `MatchedTrajectory` ostanejo nespremenjeni.

**`config/experiments/porto_cells_mia.yaml` (novo)**: brez `map` in `map_matching`;
`dataset: {id: ldptrace_dat, path: data/interim/porto/porto.dat, representation: cells,
grid: {n_rows: 6, n_cols: 6, bbox: [-8.640001, 41.140007, -8.600003, 41.169997]},
max_users: 2000}` (bbox = `grid_bbox` iz `porto_stats.json`); čiščenje izklopljeno
(`max_speed_kmh: 1.0e9, min_points: 1, min_length_m: 0, resample_s: 0`); delitev
(0,5/0,2/0,2/0,1) in napad (`n_shadow: 16`, `subsample: 0.5`, `fprs: [0.001, 0.01, 0.1]`)
kot v `geolife_mech_mia_u20.yaml`; roki `markov {order: 1}` in `ldptrace
{epsilon: [0.5, 1.0, 1.5]}` (mreža se vbrizga); `metrics.privacy: []`, `bootstrap
{n: 1000, ci: 0.95}`, `memory: false`, `attack_time_budget_s: 300`; `reporting.export:
[csv]`. Glava datoteke pojasni, da je `max_users` (= število poti) izbran za čas in da je
celotna populacija možna z brisanjem ključa.

**`tests/test_cells_mode.py` (novo)**, uvozi `base_config`/`write_config` iz
`test_orchestrator` (vzorec `test_repeat.py`), brez fixtura zemljevida:
- konec-do-konca nad fixturom `geolife_onroad` (8 poti, 2 uporabnika, isti razrez kot
  obstoječi test MIA) v načinu `cells` z mrežo 6 × 6 nad bbox fixtura
  `[116.30, 39.98, 116.32, 39.995]`, roki `markov` in `ldptrace` (ε = 600): vrstice
  `membership_inference:synthetic:{markov:order=1, ldptrace:epsilon=600.0}`, AUC v [0, 1],
  `markov` > 0,5; predpomnilnik vsebuje natanko `clean.parquet`, `chains.parquet`,
  `meta.json`; `run.json`: `n_matched == 8`, `n_dropped == 0`, `representation == "cells"`;
  drugi zagon bere predpomnilnik in da iste vrednosti; `results.csv`: `epsilon == "600.0"`
  pri `ldptrace`, `n_rematch_dropped` prazen;
- `_cell_pool` nad `tiny.dat` (`ldptrace_dat`, mreža 6 × 6 nad `0..6 × 0..6`, čiščenje
  izklopljeno): 5 verig enakih README-ju fixtura, `user_id` `"0".."4"`, vsota
  `split_counts` = 5, ponovni klic vrne enake verige iz Parqueta;
- zavrnitve pred cevovodom (pot do podatkov namerno neobstoječa): `reidentification` v
  načinu `cells`; `rn_ldp_synth`; `privacy_mechanisms: [{id: none}]`; `cells` brez
  `dataset.grid`; slaba mreža (`n_rows: 1`, bbox s tremi števili); `segments` brez `map`
  → še vedno `missing required key map`; `cells` z `map.region: ljubljana` nad Geolife
  → `ConsistencyError` (T1 velja, ko je zemljevid podan); `ldptrace_dat` s katerim koli
  `map` → `ConsistencyError`; `ldptrace` z `n_rows: 5` ob mreži 6 × 6 → `ValueError`;
- `_version_hash`: `segments` ≠ `cells` za isto konfiguracijo; hash se spremeni z
  `n_rows` in z bbox mreže; obstoječi test o semenih ostane nespremenjen.

**Dokumentacija**: `docs/RUNNING.md` (nov §9.2 »Membership inference in the cells
representation (Porto)« z ukazom `uv run trajguard run config/experiments/porto_cells_mia.yaml`,
izmerjenim izpisom in opombo, da je `n_rematch_dropped` v načinu celic prazen; kazalo;
§10 predpomnjenje: `representation`/`grid` v hashu, `chains.parquet`),
`docs/ARCHITECTURE.md` (veja celic v diagramu toka podatkov, ključa
`dataset.representation`/`dataset.grid` v razdelku o konfiguraciji, opomba v tabeli
skladnosti), ta dokument (§4 PR B2 izveden, §11.4 dejanske odločitve, §11.5 izmerjeno),
`docs/HANDOFF.md` §2.3 (izmerjene vrstice MIA za Porto), `CLAUDE.md` (vrstica stanja).
`docs/REZULTATI_SHEMA.md` se ne spremeni.

**Dokaz nespremenjenosti današnje poti**: obstoječi `tests/test_orchestrator.py`
(predpomnilnik, hash, MIA) brez sprememb; pred spremembo se shrani zlati izpis
(`_version_hash` in `results.csv` konfiguracije `mia_config` nad fixturom v načinu
`segments`) in se po spremembi primerja — razlika mora biti prazna.

### 11.5 Pravi pogon Porta (v B2, po prehodu testov)

`uv run trajguard run config/experiments/porto_cells_mia.yaml` (prvi zagon prebere in očisti
vseh 367.008 poti v predpomnilnik, nato napad nad 2.000 potmi), nato
`uv run trajguard repeat config/experiments/porto_cells_mia.yaml --seeds 1 2 3`. Zapiši:
čas prvega branja in napada na seme, `l_k` roke `ldptrace` po ε (iz izpisa ali `run.json`,
če ga B2 doda), tabelo AUC in `tpr@fpr = 0,1` (povprečje in interval čez tri semena) za
`markov` in `ldptrace` ε ∈ {0,5, 1, 1,5} v `HANDOFF.md` §2.3 in `RUNNING.md` §9.2.
*(Izmerjeno: še ni.)*

### 11.6 Prompt za sejo B2 (kopiraj v celoti)

```
Nadaljujeva validacijo generatorja ldptrace proti izvirni kodi LDPTrace v repozitoriju
trajguard: PR B2 (način celic v orkestratorju). Preberi CLAUDE.md, docs/ARCHITECTURE.md
in docs/NACRT_LDPTRACE_VALIDACIJA.md §11 V CELOTI (to je predaja s potrjenim načrtom) ter
iz istega dokumenta §3 (D-V.4 do D-V.6) in §10.5; arhiva arhiv/ ne odpiraj. Kot vzorec
preberi src/trajguard/experiments/orchestrator.py v celoti (po kosih; številke vrstic so
v §11.3), src/trajguard/experiments/cli.py, src/trajguard/representation/views.py,
src/trajguard/datasets/ldptrace_dat.py (samo razred LDPTraceDatLoader in konstante),
src/trajguard/synthesis/ldptrace.py (samo __init__ in cell_sequence),
config/experiments/geolife_mech_mia_u20.yaml, tests/test_orchestrator.py (base_config,
beijing_maps_dir, write_config, mia_config, teste _mia_pool, test MIA konec-do-konca in
teste zavrnitev pred cevovodom), tests/test_repeat.py (uvoz pomožnih funkcij iz
test_orchestrator), tests/fixtures/ldptrace_dat/README.md in
tests/fixtures/geolife_onroad/README.md.

Odločitve avtorja, ki jih ne sprašuj znova (§11.2): načrt B2 iz §11.4 je potrjen skupaj s
petimi dopolnitvami skice §10.5 (neobvezen map_matching v načinu cells, zavrnitev
privacy_mechanisms, vbrizg n_rows/n_cols v generator z zavrnitvijo nasprotujočih
vrednosti, representation/grid v hashu samo v načinu cells, test konec-do-konca nad
fixturom geolife_onroad); docs/REZULTATI_SHEMA.md se ne spremeni; pravi pogon
config/experiments/porto_cells_mia.yaml (max_users 2000) in repeat s semeni 1 2 3 se
požene po prehodu testov, vrstice gredo v docs/HANDOFF.md §2.3, RUNNING §9.2 in v §11.5.

Začni v plan mode: načrt na kratko povzemi in ga predloži v potrditev; odstopanja od
§11.4 najprej predlagaj. Veja claude/cells-mode-orchestrator se odcepi od
claude/cells-mode (PR #34), če ta še ni združen (preveri z gh pr view 34), sicer od main.
Definicija končanega: uv run ruff check ., uv run ruff format --check ., uv run mypy src,
uv run pytest -q čisti, izpis prilepljen; pred spremembo shrani zlati izpis današnje poti
(_version_hash in results.csv konfiguracije MIA nad fixturom v načinu segments) in ga po
spremembi primerjaj; potisk na origin in PR na main z gh (opis z dokazi, brez novih
odvisnosti, opomba o skladanju na PR #34). Testi berejo samo tests/fixtures/. Ukazi,
daljši od 10 minut, tečejo kot samostojen proces (PowerShell Start-Process) z nadzorom
dnevnika. Koda, identifikatorji, docstringi in testi v angleščini; pogovor z mano v
slovenščini, brez nepojasnjenih kratic.
```
