# Predaja dela: stanje kampanje S4 in odprte postavke

**Različica:** 3. september 2026 (skrajšana); odločitve o odprtih postavkah vpisane
22. septembra 2026 (uvod razdelka 2). Celotna zgodovina predaje — analiza vrzeli
z dne 4. avgusta 2026, recenzija, dnevnik izvedbe valov 0–2 in prvotni zapisi kampanje —
je v `arhiv/HANDOFF_2026-08-21.md`; načrt in izid popravkov S4-1 do S4-4 v
`arhiv/HANDOFF_S4_POPRAVKI.md`. Ta datoteka hrani samo tisto, kar prihodnja seja
potrebuje: izmerjeni zapis kampanje po stopnjah (razdelek 1) in seznam odprtih postavk
(razdelek 2). Merjeni odstavki so preneseni dobesedno; spremenjene so le številke
razdelkov in poti do arhiviranih datotek.

**Kdaj brati:** ob načrtovanju naslednjega dela, ko poročilo potrebuje izmerjeno
številko, ali ko se naročilo sklicuje na kampanjo S4, stopnjo lestvice (20/50/182) ali
oznako S4-x. Seja, ki spremeni stanje (nov pogon, zaprta postavka), posodobi ta dokument
in statusno vrstico v `CLAUDE.md` v istem PR-ju.

---

## 1. Kampanja S4 — izmerjeni zapis po stopnjah lestvice vzorcev

Kampanja teče z dvema konfiguracijama na stopnjo: `geolife_geoind_reid[_uN]` (geoind,
semena 1–5) in `geolife_synth_mia[_uN]` (napad na članstvo, semena 1–3), `split_seed` 42,
`metrics.memory: false` (pravilo R0, `docs/RUNNING.md` §7.3). Zagoni so v
`results/<exp_id>/seed<N>/`, glavna tabela v `reports/results_master.csv`, slike v
`reports/s4_figures/<stopnja>/`, izvedeni zvezek je `notebooks/03_s4_sweep.ipynb`.
Nič od tega ni v gitu (mape so ignorirane); v gitu so konfiguracije in izvedeni zvezek.

### 1.1 Stopnja 20 — prvi pogon (15.–16. avgust 2026) in vrzeli S4-1 do S4-5

Prvi pogon na pravem Geolife je razkril štiri vrzeli in eno opažanje. Oznake se še
vedno uporabljajo v kodi in dokumentaciji, zato jih tu povzemam (podroben zapis:
`arhiv/HANDOFF_2026-08-21.md` §1.10; odločitve in izvedba: `arhiv/HANDOFF_S4_POPRAVKI.md`):

- **S4-1 — populacija.** Pri pragu `min_match_score: 0.6` je preživelo 2,8 % očiščenih
  sledi (45 od 1607, 9 od 20 uporabnikov). Odločitev: populacija poročila so vozne
  sledi, definirane operativno s pragom, ki se izbere iz izmerjene porazdelitve ocen
  (diagnostična celica v zvezku 03, §9). Prag 0,05 na merilnih stopnjah 20 in 50
  (PR 3), 0,3 na poročevalski stopnji 182 (odločitev 17. avgusta 2026, glej 1.3).
  Pravila in zgodovina izbire: `docs/RUNNING.md` §6 in §7.4.
- **S4-2 — varovalo `tpr@fpr`.** Točka `tpr@fpr = f` potrebuje vsaj `1/f` nečlanov,
  sicer napad zapiše NaN z opozorilom v `run.json`; operativne točke so
  `{0.001, 0.01, 0.1}`. Izvedeno v PR 1 (`attacks/membership.py`, `evaluation/roc.py`,
  `reporting/report.py`, ki starejše neveljavne vrednosti zamolči v razdelku Warnings).
- **S4-3 — umerjanje `rn_ldp_synth`.** Faktor napihnjenosti dekodiranja je odvisen samo
  od zemljevida in parametrov umerjanja, zato se predpomni po ključu in izračuna enkrat
  namesto sedemnajstkrat na vejo (755–866 s → ~20 s na klic). Izvedeno v PR 2; prvi
  znani protiprimer lestvice krčenja, zapisan kot korak 0 v `docs/RUNNING.md` §7.3.
- **S4-4 — `trajguard report` nad ponovitvami.** Poročilo najde tudi `seed<N>/run.json`
  in ponovitve združi čez semena (ena vrstica na roko, Studentov t interval). Izvedeno
  v PR 1 (`docs/RUNNING.md` §8).
- **S4-5 — ničelni intervali.** Veji `raw` in `protected:none` nimata vira naključnosti
  (seme premakne šum mehanizma in senčne podmnožice, ne enakomerno izbranih znanih
  točk), zato je njun interval čez semena širine nič; ni napaka
  (`docs/RUNNING.md` §7.1).

Časi prvega pogona za primerjavo: geoind ~105 s na seme na toplem predpomnilniku
(811 s hladno), napad na članstvo ~42 minut na seme.

### 1.2 Stopnja 20 — validacijski pogon (17. avgust 2026)

Pogon je bil izveden po združitvi PR 1–3, pri `max_users: 20`, z istima
konfiguracijama in semeni kot prvi pogon (`geolife_geoind_reid_u20` s semeni 1–5,
`geolife_synth_mia_u20` s semeni 1–3). **Vseh pet meril je izpolnjenih; pogon je
uspešen.**

| # | Merilo | Zahteva | Izmerjeno |
|---|--------|---------|-----------|
| 1 | Nečlani v bazenu napada na članstvo | ≥ 11 | **15** v vseh treh semenih in vseh štirih rokah (`n_pool = 105`, `n_members = 90`; prvi pogon: 3) |
| 2 | Pokritost galerije reidentifikacije | ≥ 15 od 20 uporabnikov | **16 od 20** v vseh petih semenih (veja `raw`; ujetih 238 od 1607 sledi; prvi pogon: 9) |
| 3 | Klic napada na članstvo proti `rn_ldp_synth` | < 300 s | **19,6–20,2 s** za vseh devet klicev (3 veje ε × 3 semena; prvi pogon: 755–866 s); `over_budget.attacks` prazen v vseh `run.json` |
| 4 | `trajguard report` | uspe; `report.md` + `risk_matrix.csv`, ena vrstica na roko | uspe: `risk_matrix.csv` ima **9 vrstic** (5 rok geoind + 4 roke generatorjev), razdelek Warnings navaja zamolčane vrednosti (prvi pogon: `FileNotFoundError`) |
| 5 | Varovalo `tpr@fpr` (S4-2) | točki 0,001 in 0,01 NaN + opozorilo; točka 0,1 izmerjena | točki 0,001/0,01 sta NaN z opozorilom v `run.json` (»needs >= 1000/100 non-members, run has 15«); točka 0,1 izmerjena: markov 0,98–1,00, `rn_ldp_synth` 0,02–0,23 |

Vrednosti so prebrane iz `results/geolife_geoind_reid_u20/seed{1..5}/` in
`results/geolife_synth_mia_u20/seed{1..3}/` (`results.csv`, `run.json`,
`metrics.csv`) ter `reports/risk_matrix.csv`; zvezek `notebooks/03_s4_sweep.ipynb`
je znova izveden nad temi rezultati in vseh 11 slik v `reports/s4_figures/` je
svežih (izvedeni zvezek je priložen PR-ju kot dokaz). Vsebinski vzorci držijo:
AUC stropa memorizacije (markov) ostaja 0,99–1,00, `rn_ldp_synth` ostaja blizu
naključnega ugibanja (AUC 0,38–0,64 čez semena in ε).

Opombe za načrtovanje vzpona (stopnja 50 → 182):

- **Cena reidentifikacije je zrasla na ~27 minut na seme** (prvi pogon: ~2 minuti),
  ker je bazen z nižjim pragom zrasel s 45 na 238 sledi in se primerjava z
  dinamičnim ukrivljanjem časa (DTW) draži približno kvadratično z velikostjo
  galerije. Celoten geoind pogon pri 20 uporabnikih zdaj traja ~2,5 ure; pri
  stopnji 50 bo bazen spet večji, kar je treba všteti v proračun pogona.
- **Cena napada na članstvo je padla z ~42 na ~1,5 minute na seme** — predpomnjenje
  umerjanja (S4-3) deluje; en proces `repeat` plača umerjanje enkrat za vse veje
  in semena.
- Operativna opomba: pogon `repeat` za geoind je bil med izvedbo dvakrat prekinjen
  od zunaj; semena 1–4 so iz `repeat`, seme 5 iz `trajguard run --seed 5` (razrez
  ostane pripet prek `split_seed`, glej §7.1 v `docs/RUNNING.md`), skupni
  `repetitions.csv` pa je bil obnovljen z isto funkcijo `aggregate` iz
  `trajguard.experiments.repeat`. Vrednosti so identične neprekinjenemu `repeat`.

**Sklep.** Popravki S4-1 do S4-4 so potrjeni pri `max_users: 20`. Naslednji korak
po lestvici (`arhiv/HANDOFF_S4_POPRAVKI.md` §3): stopnja 50 (prva meritev skaliranja
podatkovno odvisnega dela cene MIA in reidentifikacije), nato 182. Ob stopnji 50 se
po avtorjevi zabeležki iz PR 3 preveri tudi, ali bi strožji prag 0,5 zadoščal
(`docs/RUNNING.md` §7.4).

### 1.3 Stopnja 50 — prva izmeritev (17. avgust 2026)

Prvi pogon stopnje `max_users: 50` po lestvici iz `arhiv/HANDOFF_S4_POPRAVKI.md` §3
(konfiguraciji `geolife_geoind_reid_u50` in `geolife_synth_mia_u50`, kopiji u20 z edino
spremembo `max_users`; geoind semena 1–5, MIA semena 1–3, prag ujemanja nespremenjeno
0,05). Namen stopnje je bil meriti, ne odločati: skaliranje podatkovno odvisnega dela
cene za napoved proračuna pri 182 in preveritev avtorjeve zabeležke o strožjem pragu
0,5. Vse vrednosti so iz `results/geolife_geoind_reid_u50/seed{1..5}/` in
`results/geolife_synth_mia_u50/seed{1..3}/` (`run.json`, `results.csv`) ter izvedenega
zvezka `notebooks/03_s4_sweep.ipynb` (razdelek 9, tabela za stopnjo 50).

**Izmerjeni časi.** Hladno čiščenje + ujemanje pri 50 uporabnikih: **12,3 minute**
(enkraten strošek stopnje). Geoind: **~62–63 minut na seme** na toplem predpomnilniku
(`run_runtime_s` 3725–3808 s; seme 1 s hladnim ujemanjem 4422 s); pri 20 je bilo
~27 minut. Napad na članstvo: **~74–115 s na seme**, praktično enako kot pri 20
(114/72/72 s) — **cena MIA je na teh obsegih podatkovno neodvisna**, prevladuje
konstrukcija generatorjev, ne velikost bazena. Celotna kampanja stopnje 50: ~6,5 ure.

**Prekoračitev proračuna 300 s.** V vseh petih semenih sta ista dva klica nad
proračunom: `reidentification:raw:k10` in `reidentification:protected:none:k10`
(467–475 s); `over_budget.attacks` v `run.json` ima zato 10 vnosov, vsi ostali klici
so pod 240 s, MIA brez prekoračitev (najdražji klic 20,8 s). Korak 0 iz
`docs/RUNNING.md` §7.3 je opravljen: cena **je** podatkovno odvisna — z galerijo
238 → 465 sledi je čas klica zrasel s 134 na ~471 s, eksponent ≈ 1,9, torej praktično
kvadratično z velikostjo galerije (DTW). Lestvica krčenja torej velja, njena naslednja
koraka (nižji `max_users` ali opustitev `k10`) pa spreminjata zasnovo eksperimenta —
po pravilu R1 pogon stoji, ukrep je avtorjeva odločitev in ni bil izveden.

**Zdravje vzorca (primerjava z 20).** `n_matched` 465 (prej 238); galerija
reidentifikacije pokrije 41 od 50 uporabnikov (prej 16 od 20); bazen napada na
članstvo 163 kandidatov, od tega **33 nečlanov** (prej 15) in 130 članov — točka
`tpr@fpr = 0.1` je izmerjena, točki 0,01 in 0,001 sta po varovalu S4-2 še `NaN`
(potrebnih 100 oz. 1000 nečlanov).

**Meritev za prag 0,5 — projekcija iz §7.4 se NE potrdi.** Diagnostična celica §9 nad
bazenom stopnje 50 (3243 očiščenih sledi): pri pragu 0,5 preživi 111 sledi, 30 od 50
uporabnikov, **8 nečlanov**, projekcija pri 182 pa **81 nečlanov** — pod mejo 100 za
oživitev točke `fpr = 0.01` (zabeležka iz PR 3 je predvidevala ~116). Po izmerjeni
tabeli je najstrožji prag, ki mejo 100 ravno doseže, **0,4** (137 sledi, 30
uporabnikov, 10 nečlanov, projekcija 100); prag 0,3 da projekcijo 118. Odločitev o
morebitni zamenjavi praga je avtorjeva in ni sprejeta; 0,05 ostaja v vseh
konfiguracijah.

**Projekcija proračuna za stopnjo 182** (preživetje ujemanja 14,3 % je čez stopnji
stabilno; očiščenih sledi pri 182 ≈ 11 800, galerija ≈ 1690): klic `k10`
≈ 5300–6250 s (~90–104 min); vsota napadov na seme ≈ 20 500–26 400 s; z režijo
(zaščita, ponovno ujemanje) **~7–9 ur na seme, pet semen ~36–44 ur**, plus ~30–45 min
hladnega ujemanja; MIA ostane pri minutah. Nad proračunom 300 s bi bili pri 182 poleg
`k10` zanesljivo tudi klici `k5` (~2700–3200 s) in `k3` (~1600–1900 s) rok `raw` in
`protected:none`, verjetno pa tudi roka ε = 10 (`k10` 94,5 s pri 50 → ~1000 s). Tudi
ob morebitnem strožjem pragu 0,5 bi bil `k10` pri 182 tik nad proračunom (galerija
~404 sledi → ~360 s).

**Vsebinska opazka za poročilo.** Strop memorizacije `markov` je pri 50 uporabnikih
padel: AUC 0,542 [0,46; 0,62] čez tri semena (pri 20: 0,996–1,000); `rn_ldp_synth`
ostaja pri naključnem ugibanju (AUC 0,47–0,50, `tpr@fpr=0.1` 0,09–0,13). Verjetna
razlaga je, da večji učni nabor pomeni manj memorizacije na posamezno sled — ob
pisanju poročila je treba to preveriti in strop interpretirati na stopnji, na kateri
se poroča, ne prenašati vrednosti 1,0 z manjše stopnje.

**Operativne opombe.** (1) Zvezek `03_s4_sweep.ipynb` zdaj riše slike razdelkov 4–7
ločeno po stopnjah v podmapi `reports/s4_figures/u20/` in `u50/`, ker funkcije v
`reporting/plots.py` združujejo po rokah ne glede na `exp_id` in bi se stopnje sicer
tiho zmešale v isto sliko; diagnostika §9 teče za obe stopnji (stopnja 50 nad bazenom
praga 0,05 — brez novega hladnega ujemanja, tabela za prage ≥ 0,05 je popolna).
(2) Ključ predpomnilnika bazena (`_version_hash`) vsebuje `str(dataset_path)`; zvezek
poti spremeni v absolutne, zato si diagnostika gradi svoj vnos v `data/processed`
tudi ob vsebinsko enakem cevovodu — enkraten strošek ~12 min na stopnjo, ne napaka.
(3) `trajguard repeat` je bil za geoind zagnan v dveh delih (seme 1 posebej zaradi
kontrolne točke proračuna, semena 2–5 skupaj); skupni `repetitions.csv` čez vseh pet
semen je obnovljen z isto funkcijo `aggregate` iz `trajguard.experiments.repeat` kot
pri validacijskem pogonu.

### 1.4 Stopnja 182 — poročevalski pogon (18.–21. avgust 2026)

Polni obseg po lestvici iz `arhiv/HANDOFF_S4_POPRAVKI.md` §3, s konfiguracijama
`geolife_geoind_reid` in `geolife_synth_mia` (brez pripone stopnje), ki nosita obe
avtorjevi odločitvi z dne 17. avgusta 2026: prag populacije `min_match_score: 0.3`
in proračun `attack_time_budget_s: 1200`; poleg tega izrecni `dataset.max_users: 182`
in `metrics.memory: false` (R0). Geoind semena 1–5, MIA semena 1–3, `split_seed` 42.
Vse vrednosti so iz `results/geolife_geoind_reid/seed{1..5}/` in
`results/geolife_synth_mia/seed{1..3}/` (`run.json`, `results.csv`, obnovljeni
`repetitions.csv`) ter izvedenega zvezka `notebooks/03_s4_sweep.ipynb`.

**Izmerjeni časi — projekcija iz 1.3 je bila ~9-krat prenizka.** Hladno čiščenje +
ujemanje: ~57 minut (znotraj semena 1). Geoind: **13,2 ure na toplo seme**
(47 428–47 606 s; seme 1 s hladnim delom 50 272 s), celotna kampanja geoind
**66,7 ure** (projekcija: ~8–9 ur). Vzrok razhajanja sta oba faktorja projekcije:
očiščenih sledi pri 182 je 17 313 (linearna projekcija s stopnje 50 je dala 11 805)
in preživetje praga 0,3 je 10,2 % (pri 50 izmerjeno 5,0 %), zato je galerija 1770
sledi namesto projiciranih ~590. MIA: **101–161 s na seme** (skupaj 6,1 min) —
cena ostaja podatkovno neodvisna, `over_budget` prazen, najdražji klic 28,7 s.

**Proračun 1200 s.** V vseh petih geoind semenih je istih **7 klicev** nad
proračunom (`memory_traced: false` povsod): `k10` raw/none ~12 000–12 255 s,
`k5` raw/none ~6 000–6 160 s, `k3` raw/none ~3 610–3 680 s ter `k10` roke ε = 10
1 318–1 499 s. Korak 0 iz `docs/RUNNING.md` §7.3 je bil opravljen na kontrolni
točki po semenu 1 (cena je podatkovno odvisna; eksponent glede na velikost galerije
~2,4 čez stopnje 50 → 182); ker naslednja koraka lestvice spreminjata zasnovo, je
pogon stal, avtor pa je 18. avgusta 2026 odločil, da semena 2–5 tečejo naprej s
temi prekoračitvami (pravilo R1 — zagoni stojijo, prekoračitve so zabeležene v
`run.json` in v tem razdelku).

**Zdravje vzorca.** `n_matched` 1770 od 17 313 očiščenih (razrez čez očiščene:
train 9665, test 2302, shadow 3355, attack 1991). Galerija reidentifikacije pokrije
**114 od 182 uporabnikov** (raw in `protected:none`); roka ε = 10 obdrži 445 sledi
(74 uporabnikov), roki ε = 1 in ε = 0,1 izgubita vse sledi pri ponovnem ujemanju
(znani vzorec »zaščita z uničenjem izdaje«). Bazen napada na članstvo: 1105
kandidatov = 809 članov + **296 nečlanov** — merilo ≥ 100 je izpolnjeno z rezervo in
**točka `tpr@fpr = 0.01` je prvič izmerjena**; točka 0,001 ostaja `NaN` po varovalu
S4-2 (potrebnih 1000 nečlanov), kar vsak MIA `run.json` in razdelek Warnings v
`reports/report.md` pravilno izpišeta.

**Izid `tpr@fpr = 0.01`** (`repetitions.csv`, povprečje čez 3 semena): `markov`
0,027 ob stropu AUC 0,776 [0,730; 0,822]; `rn_ldp_synth` 0,011 / 0,020 / 0,012 za
ε = 0,5 / 2 / 8 ob AUC 0,513 / 0,517 / 0,472 — mehanizem ostaja pri naključnem
ugibanju tudi na strogi operativni točki. Strop `markov` je pri 182 spet višji kot
pri 50 (0,776 proti 0,542; pri 20 ~1,0) — potrjuje opozorilo iz 1.3, da je treba
strop memorizacije interpretirati na stopnji, na kateri se poroča.

**Diagnostika §9 nad bazenom 182** (izmerjena meja populacije pri pragu 0,3;
slika `match_score_diagnostic_u182.png`): prag 0,3 → 1769 sledi / 114 uporabnikov /
296 nečlanov; 0,4 → 1485/102/243; 0,5 → 1213/98/167; 0,6 → 971/82/104;
0,7 → 663/68/62. Nečlanov je torej bistveno več, kot so napovedovale projekcije s
stopnje 50 (pri 0,5: izmerjeno 167 proti projekciji 81) — tudi strožji pragi do 0,6
bi ohranili točko 0,01, vendar po skalirni oceni noben ne spravi klica `k10` pod
1200 s.

**Posebnosti.** (1) Diagnostika §9 šteje 1769 sledi, orkestrator 1770 — ena sled na
meji praga, ker si zvezek zaradi absolutnih poti zgradi svoj predpomnilniški vnos
(1.3, op. 2); na števila eksperimenta ne vpliva. (2) Pri roki ε = 0,1 imata
`poi_inference` napaki manj končnih ponovitev (n = 1 oz. 3 od 5) — izrojena roka,
šum raztopi postanke. (3) `trajguard report`: `risk_matrix.csv` 27 vrstic (9 rok ×
3 stopnje), `results_master.csv` 1314 vrstic. (4) `repetitions.csv` za geoind je
obnovljen čez semena 1–5 z `aggregate` (78 vrstic, 76 z n = 5), ker je bil repeat
zagnan v dveh delih kot pri stopnji 50.

---

## 2. Odprte postavke

Vse spodnje je bilo odprto ob zadnjem pregledu (21. avgust 2026). Zaprte vrzeli iz
prvotne analize (O1–O6, D1–D4, S4-1 do S4-4) tu niso ponovljene; njihova zgodovina in
commiti so v `arhiv/HANDOFF_2026-08-21.md`.

**Pregled odločitev z dne 22. septembra 2026.** Avtor je ta dan odločil o vseh odprtih
odločitvah razen pragov (čakajo mentorico) in D5 (projekt »Izbirni predmeti«). Vsaka
odločitev je zapisana ob svoji postavki spodaj z oznako »Odločeno 22. 9. 2026«. Iz njih
sledi zaporedje pred primerjalnim zvezkom (`docs/NACRT_MEHANIZMI.md` §1.6):

1. PR kode: nova vrednost `attacker.distance: dtw_norm` (2.3, ZM-3 in 2.5).
2. PR kode: stolpca `exp_id` in `config_hash` v `repetitions.csv` (2.5).
3. PR kode: dejstva PrivTrace v `run.json` (2.3, ZM-4).
4. PR kode: M3 — metriki uporabnosti `duration_dist_error` in `speed_dist_error` (2.1,
   2.2). Avtor želi obe v primerjalnem zvezku, zato mora PR priti pred pogon 182, ki ju
   izračuna.
5. Kopija `geolife_mech_mia_u182.yaml` (danes obstaja samo `_u20`).
6. Avtor sam požene vse sestrske konfiguracije pri stopnji 182; stopnja 50 za mehanizme
   se preskoči.
7. Primerjalni zvezek nad stopnjo 182.

Neodvisno od tega zaporedja je odblokiran A4.

### 2.1 Odločitve avtorja (niso koda; blokirajo poročilo, ne repozitorija)

- **Pragovi zadostnosti zaščite** (poročilo §8.2): pri kateri vrednosti metrike
  mehanizem velja za zadostnega. Avtorjev predlog je vpisan v poročilo 24. avgusta
  2026 (po zapisu tiste seje; poročilo ni v gitu): reidentifikacija top-1 < 5 % pri
  k ≤ 10; MIA `tpr@fpr = 0.01` ≤ 0,02 in interval AUC vsebuje 0,5; rekonstrukcija
  povprečna napaka ≥ 500 m; dom/delo lokalizirana ≤ 10 %. **Čaka potrditev
  mentorice**; v repozitoriju pragovi niso kodirani.
- **Pomen »odstopanja statistik gibanja«** (M3, poročilo §7.5): `UTILITY_METRICS` že
  ima `cell_js_divergence` in `length_dist_error`. **Odločeno 22. 9. 2026:** M3 je
  razlika porazdelitev čez vse poti izdaje, v isti obliki kot `length_dist_error`, za
  dolžino, trajanje in hitrost. Dodata se `duration_dist_error` in `speed_dist_error`.
  Ker sintetične poti (`markov`, `ldptrace`, `privtrace`, `rn_ldp_synth`) nimajo časov,
  veljata novi metriki samo za perturbacijske mehanizme; pri sintezi M3 ostane dolžina
  in celice. Postavka je zdaj koda (val 3, 2.2).
- **Definicija »poznanega vhodnega vzorca«** za rekonstrukcijo z delnim predznanjem
  (A4, poročilo §6.3). **Odločeno 22. 9. 2026:** napadalec pozna k enakomerno
  razporejenih točk tarčne poti (k = 3 / 5 / 10), enako predznanje kot pri
  reidentifikaciji (`known_points`, `_evenly_spaced` v `attacks/reidentification.py`);
  rekonstrukcija jih uporabi kot sidra. A4 ni več blokiran (2.2).
- **Prekoračitve proračuna pri 182** (sedem klicev reidentifikacije na seme, glej 1.4)
  so sprejete po pravilu R1. **Odločeno 22. 9. 2026:** ostane tako; poročilo prekoračitev
  samo navede, `k10` in stopnja 182 ostaneta. Postavka je zaprta.

### 2.2 Val 3 — dopolnitve znotraj obstoječih štirih scenarijev

- **A3 — rekonstrukcija z omejitvijo cestnega omrežja** (zasnova §6.3, poročilo §7.4):
  primerjava »z omrežjem proti brez omrežja« je empirični argument za omrežno
  zavednost. Danes je `attacks/reconstruction.py` Whittakerjev glajevalnik brez
  zemljevida. Brez blokad.
- **M2 — top-k točnost POI** (poročilo §7.5) skupaj s pogledom `as_poi_visits()`
  (`representation/views.py`, danes `NotImplementedError`). Predpogoj: v repozitoriju
  ni vira točk interesa in testi ne smejo na omrežje — potreben je fixture sloj POI.
- **M3 — `duration_dist_error` in `speed_dist_error`** (definicija v 2.1): metriki
  uporabnosti po vzoru `length_dist_error`, samo za perturbacijske mehanizme. Brez blokad.
- **A4 — rekonstrukcija z delnim predznanjem** (definicija v 2.1: k enakomerno
  razporejenih točk tarče kot sidra). Brez blokad.

### 2.3 Val 4 — širina mehanizmov in LDPTrace

- Mehanizmi iz zasnove §7, ki manjkajo: prostorsko zaokroževanje, časovno redčenje,
  Gaussov šum, SquareWave, segmentna perturbacija, k-anonimnost, kombinacije (točkovni
  LDP je izveden kot ZM-2, glej spodaj). Dodajaj po naraščajoči zahtevnosti; segmentna
  perturbacija zadnja (najbližja RN-LDP-Synth, zato najkoristnejša primerjava).
- **LDPTrace** prednostno: brez njega se razdelek 7.3 poročila primerja samo proti
  nezasebnemu Markovu. Točkovni LDP in LDPTrace gradita na `privacy/ldp.py` (GRR, OUE).
- **Načrt izvedbe (2. september 2026):** `docs/NACRT_MEHANIZMI.md`. Izbrani so štirje
  koraki, vsak ena seja in en PR: ZM-1 LDPTrace, ZM-2 točkovni LDP, ZM-3 naivna trojica
  (prostorsko zaokroževanje, časovno redčenje, Gaussov šum), ZM-4 PrivTrace. Odločitve,
  datoteke, testi in prompti za seje so v tistem dokumentu. Nabor baseline-ov za članek
  (odločitev D5 v projektu »Izbirni predmeti«) ostaja odprt; ti mehanizmi so kandidati.

**ZM-1 LDPTrace — zaključen (2. september 2026, PR #32, združen v `main` 2. septembra
2026).** Generator `ldptrace` (`src/trajguard/synthesis/ldptrace.py`; dejanske odločitve
v `docs/NACRT_MEHANIZMI.md` §2, uvodni odstavek). Izmerjeno pri stopnji 20 s konfiguracijo
`config/experiments/geolife_mech_mia_u20.yaml` (sestrska datoteka zamrznjene S4
konfiguracije; ista populacija, razrez in napad), ukaz
`uv run trajguard repeat config/experiments/geolife_mech_mia_u20.yaml --seeds 1 2 3`,
commit kode `a3c79c7`. Bazen napada: 90 članov, 15 nečlanov (`n_pool = 105`), enako kot v
1.2. Vrednosti iz `results/geolife_mech_mia_u20/repetitions.csv` (povprečje in Studentov
95-odstotni interval čez tri semena; rezultati ostajajo lokalni, `results/` ni v gitu):

| Roka | AUC | `tpr@fpr = 0,1` | Čas napada na seme |
|------|-----|------------------|--------------------|
| `markov` (strop memorizacije) | 0,996 [0,985; 1,007] | 0,989 [0,961; 1,016] | 0,1–0,4 s |
| `rn_ldp_synth` ε = 2 (sidro S4) | 0,572 [0,376; 0,768] | 0,107 [−0,169; 0,384] | 21,0–21,2 s |
| `ldptrace` ε = 0,5 | 0,432 [0,345; 0,518] | 0,063 [0,006; 0,120] | 9,4–9,6 s |
| `ldptrace` ε = 2 | 0,484 [0,409; 0,559] | 0,107 [0,065; 0,150] | 9,4–9,7 s |
| `ldptrace` ε = 8 | 0,528 [0,439; 0,616] | 0,156 [0,018; 0,294] | 9,4–9,6 s |

Branje: vsi trije intervali AUC za `ldptrace` vsebujejo 0,5, torej napad na članstvo pri
stopnji 20 ne zazna memorizacije; povprečje raste z ε (0,43 → 0,48 → 0,53), kar je
pričakovana smer. Točki `tpr@fpr` 0,001 in 0,01 sta NaN z opozorilom v `run.json`
(varovalo S4-2, 15 nečlanov), `over_budget.attacks` je prazen v vseh treh semenih.
Sidro `rn_ldp_synth` ε = 2 se ujema z vrednostjo iz S4 (1.2: AUC 0,572 [0,376; 0,768]).

Opombi k mehanizmu pri tej velikosti vzorca (n = 90 učnih poti, verige dolge 1–18
celic, mediana 3, na mreži 12 × 12):

- **Meja dolžine L_k je nestabilna**, ker histogram dolžin nad 144 predalih pri
  proračunu ε/10 prevladuje šum: L_k po semenih 1/2/3 je 1/24/38 pri ε = 0,5, 1/26/32
  pri ε = 2 in 60/70/77 pri ε = 8 (prava največja dolžina je 18). Pri L_k = 1 naprava v
  drugem krogu pošlje samo začetek in konec (nič prehodov), sinteza da enocelične poti,
  statistika MIA pa ostane definirana. To je pravilo izvirne kode pri vzorcu, ki je
  daleč pod obsegom članka (tisoči uporabnikov), ne napaka izvedbe; pri stopnjah 50 in
  182 je pričakovati stabilnejši L_k.
- Roka je **poceni**: ~9,5 s na seme za 17 prilagajanj (16 senčnih modelov + tarča),
  brez umerjanja z Dijkstro, zato so kopije konfiguracije za u50 in 182 računsko
  neproblematične. **Odločeno 22. 9. 2026:** dekodiranja celic v odseke ne bo (tudi ne
  za `privtrace`) in roke `ldptrace` v `experiments/rnldp_eval.py` ne bo — članka LDPTrace
  in PrivTrace cestnega omrežja ne uporabljata, izhod ostane zaporedje celic; kjer so
  potrebne točke, velja pravilo člankov (ena naključna točka v celici, s semenom).
  Postavka je zaprta.
- **Validacija proti izvirni kodi** (metrike članka, način surovih koordinat na mreži
  v konfiguraciji, primerjalni pogon nad javnim Portom): načrt, predaja in prompt v
  `docs/NACRT_LDPTRACE_VALIDACIJA.md`. Ponovitev številk iz članka ni mogoča (izvirnik
  ne prilaga podatkov in nima semena); cilj je diferencialna primerjava port ↔ izvirnik
  nad istim vhodom. **Stanje 4. septembra 2026: vsi štirje PR-ji validacije (#33, #34,
  #35, #36) so združeni v `main` 4. septembra 2026** (z merge commitom, v vrstnem redu
  33 → 34 → 35 → 36). PR A (devet metrik članka,
  `src/trajguard/evaluation/ldptrace_metrics.py`) je PR #33, združeno v `main`
  4. septembra 2026; PR B je razrezan na B1 in B2. **B1 je izveden** (PR #34, združeno v
  `main` 4. septembra 2026):
  oblika `sequence` in `as_sequence()` pri `TrajectoryView`, `Grid.chain`, način `bbox`
  generatorja `ldptrace`, nalagalnik `ldptrace_dat` in pretvorba Porta
  (`scripts/porto_to_ldptrace_dat.py`). Današnja pot je nespremenjena: zlati izpis
  generatorja `ldptrace` v načinu omrežja je pred in po spremembi identičen. **Porto,
  izmerjeno 3. septembra 2026:** iz 1.710.670 vrstic `train.csv` je z bbox lon −8,64 …
  −8,60, lat 41,14 … 41,17 (osrednji Porto, ~3,4 × 3,3 km) obdržanih **367.008 poti**
  (članek: 361.591) z 12.136.174 točkami; odvrženih 10 (`MISSING_DATA`), 36.508 (< 2
  točki), 1.307.144 (zunaj bbox); bbox točk lon −8,64 … −8,600004, lat 41,140008 …
  41,169996, `grid_bbox` = ± 1e-6; 371 s. Izhod `data/interim/porto/` (245 MB `.dat`,
  48 MB `.xz`, `porto_stats.json`) ni v gitu. Prvotno predlagani bbox (−8,69 … −8,55 ×
  41,13 … 41,19) bi obdržal 81 % poti. **B2 je izveden** (3. september 2026, PR #35,
  združeno v `main` 4. septembra 2026): orkestrator pozna
  `dataset.representation: cells` (mreža iz `dataset.grid`, brez zemljevida in ujemanja,
  samo napad na članstvo), konfiguracija `config/experiments/porto_cells_mia.yaml`, testi
  `tests/test_cells_mode.py`; današnja pot `segments` je nespremenjena (isti hash
  predpomnilnika, zlati izpis pred in po spremembi enak). **PR C je izveden** (4. september
  2026, PR #36, združeno v `main` 4. septembra 2026; tabela z devetimi metrikami × tremi ε
  in branje sta spodaj).

**Porto, napad na članstvo v načinu celic (izmerjeno 3. septembra 2026, commit `829e69f`).**
Ukaza `uv run trajguard run config/experiments/porto_cells_mia.yaml` in
`uv run trajguard repeat config/experiments/porto_cells_mia.yaml --seeds 1 2 3`;
`max_users: 2000` (= 2.000 poti, vsaka pot je svoj uporabnik), mreža 6 × 6 nad
`grid_bbox`, čiščenje izklopljeno, `n_shadow: 16`, `subsample: 0,5`. Bazen napada: 1.000
članov, 400 nečlanov (`n_pool = 1400`), 400 senčnih, 200 v razrezu `attack`. Prvi zagon
58 s (od tega ~57 s branje in čiščenje vseh 367.008 poti, preden `max_users` izbere 2.000;
predpomnilnik `data/processed/17a5b3fba2ac1341`: `clean.parquet` 511 kB, `chains.parquet`
41 kB za 2.000 poti); vsak nadaljnji zagon ~3 s na seme, napad 0,3 s (`markov`) oziroma
0,7 s (`ldptrace`) na roko; ponovitve čez tri semena 11 s. Vrednosti iz
`results/porto_cells_mia/repetitions.csv` (povprečje in Studentov 95-odstotni interval
čez semena 1, 2, 3; `tpr@fpr = 0,001` je NaN, ker potrebuje 1.000 nečlanov, S4-2):

| Roka | AUC | `tpr@fpr = 0,1` | `tpr@fpr = 0,01` |
|------|-----|------------------|-------------------|
| `markov` (strop memorizacije) | 0,582 [0,558; 0,607] | 0,166 [0,116; 0,216] | 0,028 [−0,022; 0,078] |
| `ldptrace` ε = 0,5 | 0,511 [0,471; 0,551] | 0,096 [0,042; 0,149] | 0,016 [−0,010; 0,042] |
| `ldptrace` ε = 1 | 0,498 [0,450; 0,547] | 0,100 [0,081; 0,119] | 0,022 [0,013; 0,031] |
| `ldptrace` ε = 1,5 | 0,496 [0,458; 0,535] | 0,110 [0,085; 0,136] | 0,017 [0,013; 0,021] |

Branje: na mreži 6 × 6 so verige kratke (učne: 1–25 celic, mediana 5) in si jih poti
delijo, zato je tudi strop memorizacije nizek (AUC 0,58); vsi trije intervali AUC za
`ldptrace` vsebujejo 0,5 in se z ε ne ločijo. Pogon z enim semenom (42) da AUC 0,589
(`markov`) in 0,514 / 0,525 / 0,522 (`ldptrace` ε = 0,5 / 1 / 1,5). **Meja dolžine L_k je
nestabilna tudi pri n = 1.000** (histogram dolžin nad 36 predali pri proračunu ε/10): L_k
po semenih 42/1/2/3 je 1/4/1/1 pri ε = 0,5, 1/5/1/1 pri ε = 1 in 1/7/2/7 pri ε = 1,5
(prava največja dolžina je 25; pri L_k = 1 naprava poroča samo začetek in konec). L_k ni
zapisan v `run.json`: vrednosti so iz ponovne prilagoditve ciljnega generatorja
(`LDPTraceGenerator(bbox=grid_bbox, n_rows=6, n_cols=6, epsilon=ε, seed=seme pogona)`)
nad učnimi verigami iz predpomnilnika v vrstnem redu datoteke, kar natanko reproducira
generator orkestratorja (`docs/NACRT_LDPTRACE_VALIDACIJA.md` §12.2); od PR C orkestrator
`l_k` in `report_epsilon` ciljnega generatorja zapisuje v `run.json` pod
`arms["synthetic:<roka>"]`, ta pogon pa ni bil ponovljen. Članek dela z
~360.000 potmi; celotna populacija je dosegljiva z brisanjem ključa `max_users`
(predpomnilnik vsebuje samo izbranih 2.000 poti, prvi zagon spet prebere datoteko).
Primerjava z izvirno kodo nad istim vhodom je PR C (spodaj).

**Validacija `ldptrace` proti izvirni kodi nad Portom (PR C, izmerjeno 4. septembra 2026,
PR #36, združeno v `main` 4. septembra 2026, commit kode `5106966`).** Izvirnik: klon
`github.com/zealscott/LDPTrace` (danes preusmerjen na `yuntaod/LDPTrace`), commit
`2d30e4135db11fd50d1fb98f59a1e84ebc61b218` (13. november 2023), v `external/LDPTrace` (ni
v gitu), s popravkom `scripts/ldptrace_reference.patch` — samo argument `--seed` namesto
dvakrat trdo kodiranega semena 2022 in seme v imenu izhodne datoteke; popravki za numpy 2
niso bili potrebni (izvirnik uvaža samo numpy in teče v obstoječem okolju `uv`). Vhod:
istih 367.008 poti (`porto.xz` za izvirnik, `porto.dat` za port), mreža 6 × 6 nad
`grid_bbox` (izvirnik jo izračuna sam iz podatkov; njegov bbox točk in robovi mreže so
bitno enaki našim), kvantil 0,9, ε ∈ {0,5, 1, 1,5}, semena 1–5 na obeh straneh, brez
razreza in podvzorčenja; izvirnik poroča odrezano zadnjo celico, port pravo. Ukazi in časi:
`docs/RUNNING.md` §9.3; ogrodje `experiments/ldptrace_eval.py`, metrike
`evaluation/ldptrace_metrics.py`; izhod `results/ldptrace_validation/` (ni v gitu).

Preverba pred meritvijo: verige izvirnika (`trajectory_point2grid`) in ogrodja so enake na
vseh prvih 20.000 poteh, a šele potem, ko ogrodje uporabi izvirnikovo pravilo zaprtih
intervalov za točko na meji celice (`reference_cells`): meja med stolpcema 2 in 3 leži
natanko pri lon −8,620002, kar je koordinata s šestimi decimalkami, ki jo točke Porta
zares zadenejo; `Grid.cell_of` (polodprti intervali) je dal drugačno verigo pri 108 od
20.000 poti (0,5 %). Način celic v orkestratorju (§9.2 v `RUNNING.md`) še vedno uporablja
`Grid.cell_of` (postavka v 2.5).

Časi: port bere `.dat` 80 s, na (ε, seme) prilagoditev 24–37 s, sinteza 367.008 poti
78–134 s, devet metrik 107–137 s, torej ~4 min; vseh 15 zagonov 60 min ob sočasnih dveh
procesih izvirnika. Izvirnik 10–23 min na zagon (pretvorba točk 1,5 min, poročila OUE
2 min, sinteza 3 min, lastne metrike ~10 min, od tega premer 6 min), 15 zagonov v dveh
vzporednih procesih 2 h 16 min; ocena njegovih sintez z našimi metrikami 27 min.

Tabela (povprečje [najmanj; največ] čez pet semen; sedem metrik so napake, nižje je bolje;
Kendall in F1 sta oceni, višje je bolje; `l_k` je javna meja dolžine iz kroga dolžin):

| ε | metrika | izvirnik (lastne metrike) | izvirnik (naše metrike) | port (naše metrike) |
|---|---|---|---|---|
| 0.5 | density_error | 0.1032 [0.0332; 0.1685] | 0.1032 [0.0332; 0.1685] | 0.0663 [0.0325; 0.1561] |
| 0.5 | hotspot_query_error | 0.6586 [0.2003; 1.0000] | 0.6586 [0.2003; 1.0000] | 0.4788 [0.1529; 1.0000] |
| 0.5 | point_query_avre | 1.0736 [0.2861; 1.9185] | 0.9703 [0.3092; 1.6011] | 0.6192 [0.3211; 1.5564] |
| 0.5 | coverage_kendall_tau | 0.2908 [0.0413; 0.6317] | 0.2908 [0.0413; 0.6317] | 0.4781 [0.1460; 0.6667] |
| 0.5 | trip_error | 0.3788 [0.2883; 0.4800] | 0.3788 [0.2883; 0.4800] | 0.3184 [0.2538; 0.3755] |
| 0.5 | diameter_error | 0.0234 [0.0148; 0.0345] | 0.0234 [0.0148; 0.0345] | 0.0245 [0.0202; 0.0346] |
| 0.5 | length_error | 0.0849 [0.0329; 0.1155] | 0.0849 [0.0329; 0.1155] | 0.0535 [0.0192; 0.1105] |
| 0.5 | pattern_f1 | 0.1760 [0.1400; 0.2500] | 0.1760 [0.1400; 0.2500] | 0.2500 [0.1200; 0.3200] |
| 0.5 | pattern_support_error | 0.8522 [0.8175; 0.8750] | 0.8522 [0.8175; 0.8750] | 0.8212 [0.7511; 0.8911] |
| 0.5 | l_k | 13.8 [3.0; 35.0] | — | 7.4 [4.0; 17.0] |
| 1.0 | density_error | 0.0669 [0.0446; 0.0966] | 0.0669 [0.0446; 0.0966] | 0.0376 [0.0201; 0.0510] |
| 1.0 | hotspot_query_error | 0.4632 [0.1529; 0.7001] | 0.4632 [0.1529; 0.7001] | 0.2841 [0.0464; 0.5676] |
| 1.0 | point_query_avre | 0.7352 [0.4096; 1.3445] | 0.6482 [0.4200; 1.1107] | 0.3559 [0.1912; 0.4681] |
| 1.0 | coverage_kendall_tau | 0.4546 [0.1778; 0.6000] | 0.4546 [0.1778; 0.6000] | 0.6032 [0.5333; 0.6952] |
| 1.0 | trip_error | 0.3096 [0.2452; 0.4220] | 0.3096 [0.2452; 0.4220] | 0.2365 [0.2289; 0.2423] |
| 1.0 | diameter_error | 0.0217 [0.0082; 0.0333] | 0.0217 [0.0082; 0.0333] | 0.0211 [0.0147; 0.0251] |
| 1.0 | length_error | 0.0540 [0.0325; 0.0681] | 0.0540 [0.0325; 0.0681] | 0.0348 [0.0254; 0.0509] |
| 1.0 | pattern_f1 | 0.2820 [0.2300; 0.3600] | 0.2820 [0.2300; 0.3600] | 0.3920 [0.3200; 0.4600] |
| 1.0 | pattern_support_error | 0.7769 [0.7304; 0.8156] | 0.7769 [0.7304; 0.8156] | 0.7114 [0.6456; 0.7957] |
| 1.0 | l_k | 14.4 [6.0; 34.0] | — | 6.6 [6.0; 8.0] |
| 1.5 | density_error | 0.0427 [0.0229; 0.0697] | 0.0427 [0.0229; 0.0697] | 0.0308 [0.0202; 0.0463] |
| 1.5 | hotspot_query_error | 0.2088 [0.1142; 0.3216] | 0.2088 [0.1142; 0.3216] | 0.1530 [0.0699; 0.2107] |
| 1.5 | point_query_avre | 0.5142 [0.2590; 0.9926] | 0.4899 [0.2656; 0.8180] | 0.3189 [0.2338; 0.4231] |
| 1.5 | coverage_kendall_tau | 0.5537 [0.3143; 0.7111] | 0.5537 [0.3143; 0.7111] | 0.6546 [0.5968; 0.7238] |
| 1.5 | trip_error | 0.2400 [0.2242; 0.2651] | 0.2400 [0.2242; 0.2651] | 0.2178 [0.2053; 0.2298] |
| 1.5 | diameter_error | 0.0305 [0.0161; 0.0426] | 0.0305 [0.0161; 0.0426] | 0.0310 [0.0204; 0.0460] |
| 1.5 | length_error | 0.0358 [0.0227; 0.0521] | 0.0358 [0.0227; 0.0521] | 0.0291 [0.0211; 0.0345] |
| 1.5 | pattern_f1 | 0.3840 [0.3300; 0.4400] | 0.3840 [0.3300; 0.4400] | 0.4400 [0.3800; 0.5100] |
| 1.5 | pattern_support_error | 0.7039 [0.6641; 0.7210] | 0.7039 [0.6641; 0.7210] | 0.6739 [0.6256; 0.7239] |
| 1.5 | l_k | 9.8 [6.0; 16.0] | — | 7.2 [6.0; 8.0] |

Branje po merilih iz `docs/NACRT_LDPTRACE_VALIDACIJA.md` §6:

1. **Metrike se ujemajo.** Naše metrike nad izvirnikovo sintezo dajo isto vrednost kot
   izvirnikov lastni izpis pri osmih od devetih metrik v vseh 15 zagonih (največja razlika
   1,1 · 10⁻¹⁶); AvRE se razlikuje za 0,09 (največ 0,32) v povprečju, ker izvirnik središča 200 poizvedb
   žreba iz globalnega `random`, ogrodje pa iz svojega `rng` (ista porazdelitev, drug žreb).
2. **Port sledi izvirniku.** Od 27 celic (9 metrik × 3 ε) je povprečje porta znotraj
   razpona petih semen izvirnika v 19; v preostalih osmih (ε = 1: gostota, AvRE, Kendall,
   potovanja, F1, podpora vzorcev; ε = 1,5: potovanja, F1) je razlika manjša od dvakratne
   razpršenosti semen in v vseh osmih je port boljši. To ni sistematična napaka porta: pri
   enakem L_k se strani ujemata (ε = 1, seme 3, L_k = 6 na obeh straneh: gostota 0,051
   proti 0,047, Kendall 0,53 proti 0,55, potovanja 0,242 proti 0,245, F1 0,37 proti 0,36;
   ε = 1,5, seme 3, L_k = 6: 0,031 proti 0,028, 0,64 proti 0,65, 0,230 proti 0,224, 0,44
   proti 0,44), razlika povprečij pa izvira iz žreba L_k: izvirnik je v petih semenih dobil
   L_k 35/8/3/9/14 (ε = 0,5), 34/9/6/9/14 (ε = 1) in 16/8/6/9/10 (ε = 1,5), port
   17/5/5/4/6, 8/6/6/6/7 in 8/7/7/6/8. L_k je 0,9-kvantil zašumljenega histograma dolžin pri
   proračunu ε/10 (pravilo je v obeh izvedbah enako: neodrezana ocena OUE, tekoča vsota
   ≥ 0,9 · vsota, rezerva 36) in je tudi pri 367.008 poročilih nestabilen: na 40 semenih samega kroga dolžin porta je L_k pri ε = 0,5 mediana 8, povprečje 11,2, razpon 1–34 (5 % semen ≥ 30, 20 % semen ≤ 5), pri ε = 1 mediana 8 in razpon 5–27, pri ε = 1,5 mediana 8 in razpon 6–20, medtem ko je pravi 0,9-kvantil dolžin verig 9; izvirnikovih 15 vrednosti (tudi 34 in 35) in portovih 15 so vzorci iz te težkorepe porazdelitve. Znano
   sistematično odstopanje (port poroča pravo zadnjo celico) se ne vidi kot poslabšanje.
3. **Trend z ε.** Na obeh straneh napake padajo in oceni rasteta z ε pri gostoti, vročih
   točkah, AvRE, Kendallu, potovanjih, dolžini, F1 in podpori vzorcev; premer je pri obeh
   ravno 0,02–0,03 in ne sledi ε (v grafih članka za Porto je premer prav tako najmanjša
   napaka).
4. Vrstice MIA za `markov` in `ldptrace` nad Portom so iz B2 (zgoraj) in niso ponovljene.

Sklep: port je nad istim vhodom funkcionalno enakovreden izvirniku (isti postopek, iste
metrike do zadnje decimalke, razlike v razponu semen); LDPTrace ostaja kandidat za
baseline (odločitev D5 je odprta).

**ZM-2 točkovni LDP — zaključen (4. september 2026, PR #38, veja
`claude/zm2-point-ldp`).** Mehanizem `point_ldp` (`src/trajguard/privacy/point_ldp.py`; dejanske
odločitve v `docs/NACRT_MEHANIZMI.md` §3, uvodni odstavek): vsaka GPS točka se preslika
v celico mreže 20 × 20 nad bbox zemljevida (k = 400 celic, celica ~1,5 × 1,7 km nad
Pekingom), celica gre skozi k-arni randomizirani odgovor (prava celica ostane z
verjetnostjo e^ε/(e^ε + 399): 0,12 / 0,50 / 0,88 pri ε = 4 / 6 / 8, sicer enakomerno
naključna druga celica), izdana točka je enakomerno naključna točka v poročani celici,
čas ostane. ε je **na točko** (`spent_budget` = ε · število izdanih točk; bazen u20 ima
83.849 točk), zato neprimerljiv s per-pot ε pri `ldptrace` in `rn_ldp_synth` in z ε na
100 m pri geo-ind. Orkestrator vbrizga bbox zemljevida v konstruktor mehanizma po podpisu
(edina sprememba orkestratorja v tem koraku). Izmerjeno pri stopnji 20 s konfiguracijo
`config/experiments/geolife_mech_reid_u20.yaml` (sestrska datoteka zamrznjene S4
konfiguracije `geolife_geoind_reid_u20.yaml`: ista populacija, čiščenje, prag 0,05,
razrez, napadi in proračun; roke `none`, `geo_indistinguishability` ε = 1 in `point_ldp`
ε ∈ {4, 6, 8}), ukaz `uv run trajguard run config/experiments/geolife_mech_reid_u20.yaml`
s `PYTHONHASHSEED=0`, seme 42, commit kode `9f454fc`. Celoten pogon 864 s (14,4 min), kar
je nad dogovorjenim pragom 10 min na seme, zato brez ponovitev `repeat`;
`over_budget.attacks` in opozorila so prazni. Bazen `raw`: 238 sledi, 16 od 20
uporabnikov v galeriji, 237 sond (enako kot v 1.2). Vrednosti iz
`results/geolife_mech_reid_u20/` (`run.json`, `results.csv`; interval je bootstrap
95-odstotni interval znotraj pogona; rezultati ostajajo lokalni, `results/` ni v gitu):

| Roka | `n_pool` | `n_rematch_dropped` | `top1_acc` pri k = 3 / 5 / 10 | Čas napada k = 3 / 5 / 10 |
|------|----------|---------------------|-------------------------------|---------------------------|
| `raw` | 238 | 0 | 0,283 [0,228; 0,338] / 0,384 [0,325; 0,447] / 0,489 [0,426; 0,557] | 42 / 72 / 138 s |
| `none` (identiteta) | 238 | 0 | enako kot `raw` | 42 / 70 / 136 s |
| `geo_indistinguishability` ε = 1 (sidro S4) | 1 | 237 | 0,236 [0,186; 0,291] pri vseh k (degenerirano: ena sled v galeriji, vse sonde dobijo njenega uporabnika) | 0,02–0,04 s |
| `point_ldp` ε = 4 | 0 | 238 | 0,000 pri vseh k (prazen bazen) | 0,01 s |
| `point_ldp` ε = 6 | 0 | 238 | 0,000 pri vseh k | 0,01 s |
| `point_ldp` ε = 8 | 0 | 238 | 0,000 pri vseh k | 0,01 s |

`spent_budget`: 83.849 (geo-ind ε = 1), 335.396 / 503.094 / 670.792 (`point_ldp` ε = 4 /
6 / 8, tj. ε · 83.849). Vrstici `raw` in `none` se do zadnje decimalke ujemata z zapisom S4
pri stopnji 20 (`results/geolife_geoind_reid_u20/repetitions.csv`: 0,283 / 0,384 /
0,489); geo-ind ε = 1 je pri semenu 42 obdržal eno sled (pri semenu 1 v S4 nobene;
povprečje `top1_acc` čez semena 1–5 v S4 je 0,034).

Ostale družine napadov in uporabnost (ena vrednost na roko):

| Roka | `poi_inference`: `home_error_m` / `work_error_m` / `home_localised` / `work_localised` | `cell_js_divergence` (mreža 20 × 20) | `length_dist_error` (m) |
|------|------|------|------|
| `none` | 0 / 0 / 1,00 / 1,00 | 0 | 0 |
| `geo_indistinguishability` ε = 1 | 14.520 / 2.030 / 0 / 0,21 | 0,0065 | 9,4 · 10⁴ |
| `point_ldp` ε = 4 | NaN / 720 / 0 / 0 | 0,421 | 5,6 · 10⁶ |
| `point_ldp` ε = 6 | NaN / 11.120 / 0 / 0 | 0,180 | 4,2 · 10⁶ |
| `point_ldp` ε = 8 | 10.940 / 4.166 / 0 / 0 | 0,032 | 1,4 · 10⁶ |

Rekonstrukcija teče po zasnovi samo nad geo-ind ε = 1 (ena preživela sled):
`mean_spatial_error_m` 107 (pod povprečnim premikom mehanizma 200 m), `hausdorff_m` 386,
15 s. Časi `poi_inference` so 1,1–2,1 s na roko.

Branje:

- **Ponovno ujemanje odvrže vse sledi pri vseh treh ε** (`n_rematch_dropped = 238/238`),
  kot je načrt napovedal: tudi ko je poročana prava celica, je izdana točka premaknjena
  za stotine metrov (enakomerno v celici ~1,5 km), daleč nad polmerom ujemanja 50 m;
  geo-ind pri ε = 1 (povprečni premik 200 m) pri istem pragu obdrži 0–1 sled.
  Reidentifikacija po ponovnem ujemanju točkovnega LDP na tej mreži zato ne loči od
  »zaščite z uničenjem izdaje«; roka je v grafu `mechanisms` z vrednostjo 0.
- **Uporabnost sledi ε natanko po napovedi GRR:** `cell_js_divergence` 0,42 → 0,18 →
  0,03 pri ε = 4 → 6 → 8 (delež pravih celic 0,12 → 0,50 → 0,88), ker mreža uporabnosti
  in mreža mehanizma sovpadata. `length_dist_error` (Wassersteinova razdalja med
  porazdelitvama dolžin, v metrih) je za dva reda velikosti nad geo-ind, ker vsak
  »napačni« odgovor GRR skoči v naključno celico čez celoten bbox (~16 km na skok);
  pri ~350 točkah na sled to da tisoče kilometrov navidezne dolžine pri ε = 4 in še
  vedno ~1.400 km pri ε = 8.
- **Sklepanje o domu/delu** ne umesti nikogar (`home_localised = work_localised = 0` pri
  vseh ε); `home_error_m` je NaN pri ε = 4 in 6, ker napad ne najde nobene postajne
  točke (zaporedne točke v isti celici so razpršene po njej), napake dela 0,7–11 km pa so
  povprečje nad redkimi uporabniki, ki jih napad sploh umesti, ne populacijska vrednost.
  Geo-ind ε = 1 za primerjavo umesti 21 % delovnih mest v 200 m.
- **Praktični sklep:** pri celicah 1,5 km je točkovni LDP v tem okviru uporaben samo za
  populacijske statistike nad celicami (histogram celic), ne za izdajo sledi; finejša
  mreža (50 × 50, k = 2.500) bi za isti delež pravih celic zahtevala ε ≳ 10 in bi izdano
  točko še vedno premaknila za ~300 m. To je pričakovana lastnost LDP na točko, ne napaka
  izvedbe. Točkovni LDP ostaja kandidat za baseline (odločitev D5 je odprta).
- Kopiji konfiguracije za stopnji 50 in 182 obstajata (`geolife_mech_reid_u50/u182`, glej
  ZM-3 spodaj; `point_ldp` ε = 8 je roka pri 182). **Odločeno 22. 9. 2026:** stopnja 50 se
  za mehanizme preskoči; avtor požene stopnjo 182 pred primerjalnim zvezkom, s ponovitvami
  čez semena, kjer ima roka seme.

**ZM-3 naivna trojica — zaključen (4. september 2026, PR #39, veja
`claude/zm3-naive-baselines`).**
Mehanizmi `spatial_rounding`, `temporal_downsampling` in `gaussian_noise`
(`src/trajguard/privacy/naive.py`; dejanske odločitve v `docs/NACRT_MEHANIZMI.md` §4,
uvodni odstavek), vsi **brez formalne garancije** (`guarantee = "none"`, `spent_budget`
`None`, brez atributa `epsilon`, zato jih graf `by_epsilon` preskoči, graf `mechanisms` pa
izriše po parametru): zaokroževanje premakne vsako točko v središče celice `cell_m` ×
`cell_m` m na globalni metrski mreži (največji premik `cell_m`·√2/2 = 71 / 354 / 1.414 m,
povprečni ≈ 0,38·`cell_m`; zaporedne točke v isti celici postanejo enake izdane točke in se
obdržijo), redčenje obdrži prvo točko, nato po eno na `interval_s` in zadnjo (čiščenje
vzorči na 5 s; izdaja ima v povprečju 352 → 74 / 23 / 6,5 točk pri 30 / 120 / 600 s,
najmanj 5 / 2 / 2), Gaussov šum doda neodvisen N(0, σ²) v metrih po obeh oseh (RMS premik
σ·√2 = 71 / 283 / 1.414 m). Orkestrator se ni spremenil. Izmerjeno pri stopnji 20 z isto
konfiguracijo kot ZM-2 (`config/experiments/geolife_mech_reid_u20.yaml`, devet novih rok ob
sidrih `none`, geo-ind ε = 1 in `point_ldp` ε ∈ {4, 6, 8}), ukaz
`uv run trajguard run config/experiments/geolife_mech_reid_u20.yaml` s `PYTHONHASHSEED=0`,
seme 42, commit kode `1b72e79`. Celoten pogon 1.054 s (17,6 min; ~495 s reidentifikacija
nad `raw` in `none`, ponovno ujemanje vseh devetih rok skupaj ~75 s, ostalo napadi nad
preživelimi bazeni), torej nad pragom 10 min na seme in brez ponovitev `repeat`;
`over_budget.attacks` in opozorila so prazni. **Regresija:** vrstice `raw`, `none`,
geo-ind ε = 1 in vse tri roke `point_ldp` (reidentifikacija, sklepanje o domu/delu,
uporabnost, rekonstrukcija) se do zadnje izpisane decimalke ujemajo z zapisom ZM-2 zgoraj
(isto seme, predpomnjeni bazeni), zato spodaj niso ponovljene. Vrednosti iz
`results/geolife_mech_reid_u20/` (`run.json`, `results.csv`; interval je bootstrap
95-odstotni interval znotraj pogona; rezultati ostajajo lokalni):

| Roka | `n_pool` (uporabnikov) | `n_rematch_dropped` | `top1_acc` pri k = 3 / 5 / 10 | Čas napada k = 3 / 5 / 10 |
|------|----------|---------------------|-------------------------------|---------------------------|
| `raw` = `none` (sidro) | 238 (16) | 0 | 0,283 [0,228; 0,338] / 0,384 [0,325; 0,447] / 0,489 [0,426; 0,557] | 42 / 70 / 136 s |
| `spatial_rounding` 100 m | 104 (14) | 134 | 0,266 [0,215; 0,325] / 0,350 [0,291; 0,409] / 0,422 [0,363; 0,481] | 8 / 14 / 27 s |
| `spatial_rounding` 500 m | 32 (8) | 206 | 0,181 [0,135; 0,232] / 0,177 [0,135; 0,228] / 0,228 [0,177; 0,283] | 3 / 4 / 8 s |
| `spatial_rounding` 2000 m | 10 (5) | 228 | 0,042 [0,021; 0,072] / 0,042 [0,021; 0,072] / 0,046 [0,021; 0,076] | 1 / 2 / 3 s |
| `temporal_downsampling` 30 s | 222 (16) | 16 | 0,485 [0,418; 0,549] / 0,473 [0,409; 0,536] / 0,570 [0,506; 0,633] | 8 / 13 / 25 s |
| `temporal_downsampling` 120 s | 207 (16) | 31 | 0,544 [0,481; 0,608] / 0,536 [0,473; 0,599] / 0,557 [0,494; 0,624] | 2 / 3 / 6 s |
| `temporal_downsampling` 600 s | 212 (16) | 26 | 0,485 [0,422; 0,549] / 0,494 [0,430; 0,557] / 0,498 [0,430; 0,561] | 0,7 / 1,0 / 1,9 s |
| `gaussian_noise` σ = 50 m | 11 (4) | 227 | 0,346 [0,283; 0,409] / 0,325 [0,266; 0,388] / 0,295 [0,236; 0,350] | 0,2 / 0,3 / 0,5 s |
| `gaussian_noise` σ = 200 m | 1 (1) | 237 | 0,274 [0,219; 0,338] pri vseh k (degenerirano: ena sled v galeriji) | 0,02–0,03 s |
| `gaussian_noise` σ = 1000 m | 0 (0) | 238 | 0,000 pri vseh k (prazen bazen) | 0,01 s |

`top5_acc` pri k = 3 / 5 / 10: `raw` 0,679 / 0,679 / 0,776; zaokroževanje 0,734 / 0,734 /
0,751 (100 m), 0,734 / 0,743 / 0,722 (500 m), 0,430 pri vseh k (2000 m); redčenje 0,789 /
0,823 / 0,865 (30 s), 0,802 / 0,835 / 0,861 (120 s), 0,861 / 0,852 / 0,848 (600 s); Gauss
0,574 pri vseh k (50 m), 0,274 (200 m), 0 (1000 m). Pri galerijah z ≤ 8 uporabniki je
`top5_acc` neinformativen (pet od osmih uporabnikov pokrije že naključje), `top1_acc` pa je
tam vezan na delež sond preživelih uporabnikov (pri σ = 200 m 0,274 = delež sond
uporabnika edine preživele sledi, kot pri geo-ind ε = 1 zgoraj).

Ostale družine napadov in uporabnost (ena vrednost na roko; `poi_inference` 1,0–2,0 s na
roko; rekonstrukcija po zasnovi teče samo nad geo-ind):

| Roka | `poi_inference`: `home_error_m` / `work_error_m` / `home_localised` / `work_localised` | `cell_js_divergence` (mreža 20 × 20) | `length_dist_error` (m) |
|------|------|------|------|
| `none` | 0 / 0 / 1,00 / 1,00 | 0 | 0 |
| `geo_indistinguishability` ε = 1 (sidro) | 14.520 / 2.030 / 0 / 0,21 | 0,0065 | 9,4 · 10⁴ |
| `spatial_rounding` 100 m | 1.030 / 681 / 0,29 / 0,50 | 0,0011 | 1.146 |
| `spatial_rounding` 500 m | 6.533 / 972 / 0,14 / 0,36 | 0,0141 | 2.384 |
| `spatial_rounding` 2000 m | 9.713 / 2.395 / 0 / 0 | 0,181 | 4.190 |
| `temporal_downsampling` 30 s | 11.040 / 528 / 0,14 / 0,57 | 0,0030 | 558 |
| `temporal_downsampling` 120 s | 12.880 / 1.202 / 0,14 / 0,50 | 0,0096 | 1.426 |
| `temporal_downsampling` 600 s | 1.023 / 2.245 / 0 / 0,14 | 0,0368 | 2.760 |
| `gaussian_noise` σ = 50 m | 2.859 / 797 / 0,43 / 0,50 | 0,0011 | 2,4 · 10⁴ |
| `gaussian_noise` σ = 200 m | 2.426 / 3.123 / 0 / 0 | 0,0088 | 1,1 · 10⁵ |
| `gaussian_noise` σ = 1000 m | NaN / 2.224 / 0 / 0 | 0,0767 | 6,1 · 10⁵ |

Branje:

- **Zaokroževanje** ščiti pred povezovanjem samo tako, da izdajo uniči: pri 100 m se
  ponovno ujame še 104 od 238 sledi (največji premik 71 m je nad polmerom ujemanja 50 m,
  a del točk ostane v dosegu) in med preživelimi je reidentifikacija skoraj enaka surovi
  (0,27 / 0,35 / 0,42 proti 0,28 / 0,38 / 0,49); pri 500 in 2000 m preživi 32 oziroma 10
  sledi in vrednosti padejo zaradi majhne galerije, ne zaradi neločljivosti. Sklepanje o
  domu/delu pri 100 m umesti 29 % domov in 50 % delovnih mest v 200 m (središče celice je
  od prave točke oddaljeno ≤ 71 m, dvojniki v celici tvorijo »postanke«); šele 2000 m
  pade na 0 / 0. `length_dist_error` je 1–4 km (dvojniki krajšajo, cikcak med središči
  celic daljša), `cell_js_divergence` pri 2000 m (0,18) je primerljiv s `point_ldp` ε = 6.
- **Redčenje je najbolj presenetljiva roka: reidentifikacija se dvigne nad surovo — a
  zaradi napadalca, ne mehanizma.** Pri 30 / 120 / 600 s preživi 222 / 207 / 212 sledi
  (vseh 16 uporabnikov), `top1_acc` pri k = 3 pa je 0,49 / 0,54 / 0,49 proti 0,28 nad
  surovim bazenom, in to pri 20–100-krat krajšem času napada. Razlaga je **preverjena in
  potrjena** (4. september 2026; tabela, merilo in odprta odločitev v 2.5): napad računa
  nenormirano DTW razdaljo, ki sešteva po celotni poravnavi, zato nad surovim bazenom
  skoraj vedno zmaga ena najkrajših galerijskih sledi (mediana razmerja med dolžino
  zmagovalca in mediano galerije 0,06 pri k = 3); redčenje galerijske sledi skrajša s
  povprečno 106 na 21 / 4,7 / 1,4 ujetih točk in to pristranskost odpravi. Z normirano
  razdaljo (`dtw / L`) je surovi bazen pri 0,52 / 0,57 / 0,60 (k = 3 / 5 / 10), redčene
  roke pa pri 0,48–0,61, torej na isti ravni ali pod njo (600 s pri k ≥ 5: −0,08 / −0,10).
  Izmerjeno je torej: časovno redčenje pod tem napadalcem **ne ščiti pred povezovanjem**
  (kvečjemu rahlo pri 600 s in normiranem napadalcu), njegov navidezni dvig tveganja pa
  je artefakt nenormirane razdalje, ki velja za ves zapis S4. Sklepanje o domu/delu: delovna
  mesta umeščena pri 57 % / 50 % / 14 %, domovi pri 14 % / 14 % / 0 % (odkrivanje
  postankov potrebuje zadostno pokritost `dwell_s`; pri 600 s večina postankov izgine).
  Uporabnost: `length_dist_error` 0,6–2,8 km (tetivna dolžina se krajša), `cell_js`
  ≤ 0,04.
- **Gaussov šum** ima pri σ = 50 m RMS premik 71 m, kar je že nad polmerom ujemanja:
  preživi 11 sledi štirih uporabnikov, pri σ = 200 m ena (enaka usoda kot geo-ind ε = 1 s
  povprečnim premikom 200 m: ena sled, `length_dist_error` istega reda 1,1 · 10⁵ proti
  9,4 · 10⁴), pri σ = 1000 m nobena. `top1_acc` 0,35 pri σ = 50 m je vrednost degenerirane
  galerije (štirje uporabniki), ne mere neločljivosti. Sklepanje o domu/delu pa šuma 50 m
  ne opazi: 43 % domov in 50 % delovnih mest v 200 m, ker se centroid postanka čez mnogo
  zašumljenih točk povpreči nazaj na pravo lokacijo; pri 200 m pade na 0 / 0. Uporabnost:
  `cell_js` ostane majhen (točke ostanejo v svojih celicah 1,5 km), `length_dist_error`
  pa eksplodira (23 km pri 50 m, 610 km pri 1000 m), ker vsak korak med zaporednima
  točkama doda naključni hod reda σ, pomnožen s ~350 točkami na sled.
- **Praktični sklep za matriko tveganj:** noben od treh naivnih mehanizmov ne zniža
  reidentifikacije, ne da bi hkrati uničil ponovno ujemanje (zaokroževanje ≥ 500 m, Gauss
  ≥ 200 m) — isti vzorec »zaščita z uničenjem izdaje« kot pri geo-ind ε = 1 in
  `point_ldp`; redčenje ne uniči ničesar in reidentifikacijo celo poveča. Za sklepanje o
  domu/delu sta zaokroževanje 100 m in Gauss 50 m praktično brez učinka. Vsi trije
  ostajajo kandidati za baseline (odločitev D5 je odprta).
- **Odločeno 22. 9. 2026** (točke 1–3 spodaj): (1) dolžinska pristranskost DTW —
  kombinacija obeh možnosti iz 2.5: nova vrednost `attacker.distance: dtw_norm` (`dtw / L`,
  L = dolžina optimalne poravnave) v `attacks/reidentification.py`, `dtw` ostane privzeta,
  zato izmerjeni zapis S4 ostane nedotaknjen; nove meritve mehanizmov poročajo obe
  razdalji, S4 dobi v poročilu opombo in kontrolno vrstico, ne ponovnega pogona;
  (2) stopnja 50 se za mehanizme preskoči, avtor pred primerjalnim zvezkom sam požene
  `geolife_mech_reid_u182.yaml` (z `dtw_norm`, ko bo v kodi); (3) Gaussov šum dobi
  ponovitve čez semena pri tem pogonu 182, ne pri u20.
- Ozadje (stanje pred odločitvijo): (1) hipoteza o dolžinski pristranskosti DTW je
  **preverjena in potrjena** (4. september 2026, 2.5); (2) kopiji konfiguracije za stopnji 50 in 182
  **obstajata in nista pognani** (4. september 2026): `config/experiments/geolife_mech_reid_u50.yaml`
  (vse roke iz u20, prag 0,05, proračun 300 s — merilna stopnja odloči, kaj gre na 182, kot
  pri S4) in `config/experiments/geolife_mech_reid_u182.yaml` (prag 0,3 in proračun 1.200 s,
  poročevalski vrednosti S4 z dne 17. avgusta 2026; sidri `none` in geo-ind ε = 1 ter po
  ena roka na mehanizem: `point_ldp` ε = 8, zaokroževanje 100 m, redčenje 120 s, Gauss
  50 m — roke, ki pri u20 ohranijo merljiv bazen ali dajo neizrojene vrstice sklepanja o
  domu/delu in uporabnosti; uničevalne roke so ena vrstica YAML). Pogon je odločitev
  avtorja; ocena cene v glavi vsake datoteke (~45 min na seme pri u50, ~13–14 h pri 182,
  ker reidentifikacija nad `raw`/`none` raste kvadratno z bazenom in pri 182 prekorači
  proračun kot v S4; pri pragu 0,3 bo preživetje zaokroževanja 100 m in Gaussa 50 m nižje
  kot pri 0,05); (3) ponovitve čez semena za Gaussov šum, edino roko s semenom
  (zaokroževanje in redčenje sta deterministična, njuni intervali so samo bootstrap
  znotraj pogona).

**ZM-4 PrivTrace — zaključen (20. september 2026, PR #40, združen v `main` z zlivnim commitom
`5cb6c50`; validacija proti izvirniku v PR #41, združenem istega dne z zlivnim commitom
`e82e1fd`, tabela spodaj; postavke končnega pregleda so zaprte v PR #42, 22. september 2026).**
Generator `privtrace` (`src/trajguard/synthesis/privtrace.py`, dvoplastna mreža v
`src/trajguard/synthesis/adaptive_grid.py`; dejanske odločitve v `docs/NACRT_MEHANIZMI.md`
§5, uvodni odstavek). **Model zaupanja je drugačen od vseh drugih rok:** PrivTrace je
centralna diferencialna zasebnost — zaupanja vreden zbiralec vidi vse surove poti in
Laplaceov šum doda gostotam mreže 6 × 6 nad bbox vozlišč zemljevida (ε₁ = 0,2ε), števcem
Markovovega modela 1. reda (ε₂ = 0,4ε) in 2. reda (ε₃ = 0,4ε), negativne vrednosti popravi
NormCut; ε je **na pot pri zaupanja vrednem zbiralcu** (soseda zbirka se razlikuje za eno
pot; uporabnik z m potmi je pokrit z m·ε), zato je enak nominalni ε kot pri `ldptrace` in
`rn_ldp_synth` (ε na pot na napravi, brez zaupanja) neprimerljiv in vrstice `privtrace`
berejo kot **zgornjo mejo uporabnosti**, ne kot enakovrednega tekmeca. Port sledi članku
(Wang et al., USENIX Security 2023, arXiv 2210.00581); avtorjeva javna koda
(`github.com/DpTrace/PrivTrace`, commit `b06cef7`, brez licence) od članka odstopa na več
mestih in ima nezasebne korake, port tega ne posnema (seznam v docstringu modula in v
`NACRT_MEHANIZMI.md` §5). Orkestrator se ni spremenil. Izmerjeno pri stopnji 20 z
`config/experiments/geolife_mech_mia_u20.yaml` (ista populacija, razrez in napad kot pri
ZM-1; nova roka `privtrace` ε ∈ {0,5, 2, 8} ob sidrih `markov`, `rn_ldp_synth` ε = 2 in
`ldptrace`), ukaza `uv run trajguard run …` (seme 42) in `uv run trajguard repeat … --seeds 1 2 3`
s `PYTHONHASHSEED=0`. **Meritev je bila 20. septembra 2026 zvečer ponovljena** po popravkih
neodvisnega pregleda (vrata delitve berejo zašumljeno vsoto, vzorčenje in točkovanje si delita
enak zasilni začetek, izbirna maska sosednosti), tokrat iz zavezanega drevesa: `run.json` vseh
štirih pogonov zapisuje `git_commit b0a7dae`. Prejšnji zapis je imel v `run.json` `ef0cbcf`,
commit **brez** kode PrivTrace, ker je bil pognan iz nezavezanega drevesa — to je zdaj
popravljeno. Bazen napada: 90 članov, 15 nečlanov (`n_pool = 105`). Cel pogon 128 / 125 / 88 /
88 s na seme (42 / 1 / 2 / 3); roka `privtrace` 7,0–8,0 s na seme za 17 prilagajanj (16 senčnih
+ tarča). **Regresija:** vseh 20 vrstic starih rok v `repetitions.csv` (markov, rn_ldp_synth,
ldptrace; povprečje in interval) je do zadnje decimalke enakih zapisu ZM-1 zgoraj, prav tako
sta vrstici `privtrace` pri ε = 2 in ε = 8 enaki prejšnjemu zapisu; premaknile so se samo
vrstice pri ε = 0,5, ker vzorčenje in točkovanje zdaj uporabljata isti enakomerni zasilni
začetek (točkovanje je prej jemalo prag 10⁻¹²), prilagoditve tarče in senc pri tem ε pa imajo
prazno vrstico začetka. Vrednosti iz `results/geolife_mech_mia_u20/repetitions.csv`
(povprečje in Studentov 95-odstotni interval čez semena 1–3; v oklepaju vrednost pogona s
semenom 42; `tpr@fpr` 0,001 in 0,01 sta NaN z opozorilom S4-2 pri 15 nečlanih;
`over_budget.attacks` prazen v vseh štirih pogonih; rezultati ostajajo lokalni):

| Roka | AUC | `tpr@fpr = 0,1` | Čas napada na seme |
|------|-----|------------------|--------------------|
| `markov` (strop memorizacije) | 0,996 [0,985; 1,007] | 0,989 [0,961; 1,016] | 0,2 s |
| `rn_ldp_synth` ε = 2 (sidro S4) | 0,572 [0,376; 0,768] | 0,107 [−0,169; 0,384] | 21,9 s |
| `ldptrace` ε = 0,5 / 2 / 8 | 0,432 / 0,484 / 0,528 (kot pri ZM-1) | 0,063 / 0,107 / 0,156 | 9,9–10,5 s |
| `privtrace` ε = 0,5 | 0,529 [0,361; 0,696] (0,581) | 0,133 [−0,103; 0,369] (0,278) | 7,0–7,9 s |
| `privtrace` ε = 2 | 0,540 [0,514; 0,566] (0,690) | 0,048 [−0,021; 0,118] (0,167) | 7,0–7,9 s |
| `privtrace` ε = 8 | 0,571 [0,325; 0,816] (0,636) | 0,270 [0,166; 0,375] (0,267) | 7,1–8,0 s |

Po semenih 1 / 2 / 3: AUC 0,602 / 0,515 / 0,470 (ε = 0,5; prej 0,550 / 0,390 / 0,511),
0,541 / 0,529 / 0,550 (ε = 2), 0,492 / 0,539 / 0,681 (ε = 8). Časi napada pri sidrih so iz
prve meritve (20. septembra 2026 popoldne); njihove vrednosti AUC in `tpr@fpr` so v ponovitvi
enake do zadnje decimalke, časi `privtrace` pa so iz ponovitve.

Branje:

- **Pri tej velikosti vzorca je PrivTrace zašumljen Markov 1. reda nad 36 celicami.**
  Ponovna prilagoditev ciljnih generatorjev (kot orkestrator: učne poti iz predpomnilnika,
  seme pogona) pri vseh ε in semenih 42 / 1 / 2 / 3 da 36 stanj, **nič razdeljenih celic in
  nič stanj 2. reda**: bbox vozlišč zemljevida meri 30 × 33 km, celica 5,0 × 5,6 km, učne
  verige so dolge povprečno 2,06 stanja; vrata delitve (0,05·|D|/36; po popravku pregleda,
  odstopanje **D-4.1**, je |D| **zašumljena vsota gostot 1. plasti po NormCut**, ne prava
  masa 90, zato prag niha s šumom — pri pravi masi bi bil 0,125 na celico) so pri tako grobi
  mreži res presežena, a
  κ = ⌈√(d/200)⌉ pri gostotah ≤ 90 ostane 1, zato se celica tako ali tako ne razdeli in
  sprememba vrat na tej stopnji ne premakne ničesar; prag 2. reda θ₁ = √2·36/(0,4ε) = 127/ε
  pa daleč presega maso, ki jo 90 poti lahko da eni vrstici. Šum prevlada nad števci: vsota
  matrike 1. reda po NormCut je 770 / 256 / 128 pri ε = 0,5 / 2 / 8 (prava masa 90), masa
  vrstice začetka pri tarči pri ε = 0,5 pa je 108,2 / 45,5 / 79,6 / 0,00 po semenih
  42 / 1 / 2 / 3 — pri semenu 3 je NormCut vrstico izpraznil, in takrat **tako vzorčenje kot
  točkovanje** uporabita isti enakomerni začetek čez 36 stanj (prej je točkovanje jemalo prag
  10⁻¹², zato hoja in njena ocena nista bili skladni). To je pričakovano vedenje centralne DP
  pri vzorcu dva reda velikosti pod obsegom članka (17.621 poti Geolife), ne napaka izvedbe;
  pri stopnjah 50 in 182 je pričakovati prve delitve, 2. red pa šele pri tisočih poti na
  celico.
- **Napad na članstvo memorizacije ne zazna:** vsi trije intervali AUC čez semena
  vsebujejo 0,5 ali se ga dotikajo (pri ε = 2 je interval ozek, 0,51–0,57, ker so tri
  semena po naključju blizu); povprečje raste z ε (0,53 → 0,54 → 0,57), kar je pričakovana
  smer in enaka kot pri `ldptrace` (0,43 → 0,48 → 0,53). Pri 15 nečlanih je `tpr@fpr = 0,1`
  kvantiziran na korake 1/15, zato so njegovi intervali široki in vrednost 0,27 pri ε = 8
  ni razlika, ki bi jo bilo mogoče trditi. Vrednost pogona s semenom 42 pri ε = 2 (0,690)
  je osamelec enega semena, ne lastnost mehanizma — zato poročamo povprečje čez semena.
- **Napovedana asimetrija (§5.5 načrta: nižja AUC in boljša uporabnost kot LDP roke) se
  pri stopnji 20 ne vidi**, ker sta obe strani na ravni naključja in uporabnost sinteze v
  orkestratorju ni priključena (2.5); primerjava uporabnosti je narejena nad Portom v
  ogrodju validacije (spodaj), kjer PrivTrace dela z 20.000 potmi in mreža zares deli.
- (1) **Zaprto (odločitev avtorja, 20. september 2026):** šum na diagonali matrike 1. reda
  (prava vrednost 0, ker so zaporedni dvojniki strnjeni) ostane, kot je v članku in v
  izvirniku. Izmerjen učinek je premajhen, da bi upravičil še eno odstopanje: diagonala nosi
  0,06–0,19 % mase realnega bloka 1. reda in 0,06–0,08 % korakov hoj pri 20.000 poteh Porta
  (~0,1 % pri stopnji 20). Eno posledico je vseeno treba povedati pošteno: če v vrstici
  2. reda po NormCut preživi samo diagonala, hoja postane vsrkajoča in teče do `max_len`
  (videno enkrat na 200 hoj na majhni testni zbirki); ujame jo varovalka D-4.3 (zdaj s
  ponovnim žrebom).
- **Odločeno 22. 9. 2026:** (3) se izvede — `run.json` bo zapisoval dejstva PrivTrace
  (`n_states`, število stanj 2. reda, število ponovnih žrebov), majhen PR pred pogonom 182;
  (2) in (4) ostaneta odprti za kasneje, ker ju primerjalni zvezek ne potrebuje; kopija
  `geolife_mech_mia_u182.yaml` se naredi pred pogonom 182 (stopnja 50 se preskoči).
- Ozadje (stanje pred odločitvijo): (2) roka z gostejšo mrežo (npr. `first_level_k: 12`, kot `ldptrace`) in kopiji
  konfiguracije za stopnji 50 in 182 (roka je poceni: ~8 s na seme); (3) `run.json` ne
  zapisuje dejstev PrivTrace (`n_states`, stanja 2. reda) — dobijo se s ponovno
  prilagoditvijo, kot L_k pri LDPTrace pred PR C; (4) **reševalec potovanj ali eksplicitni
  model dolžine**: odstopanje D-4.2 opusti prav tisti popravek pristranskosti, zaradi
  katerega je reševalec v članku (§4.4: normalizacija 1/(L+1) prešteje kratke poti preveč in
  dolge premalo), in to se vidi v dolžini — prave poti Porta imajo 12,0 strnjenih stanj,
  port brez šuma 8,6 (30 % prekratko; meritev v bloku validacije spodaj).

**Validacija `privtrace` proti izvirni kodi nad Portom (izmerjeno 20. septembra 2026, PR #41,
združen v `main` z zlivnim commitom `e82e1fd`; stolpec `port_masked` je bil 22. septembra 2026
ponovno izmerjen v PR #42, ker je varovalka D-4.3 dobila ponovni žreb).** Izvirnik: klon
`github.com/DpTrace/PrivTrace`, commit `b06cef7d8df0305b10f309e8b75660949946f22a` (9. december
2022, **brez licence**; v paket ni prekopirano nič), v `external/PrivTrace` (ni v gitu), s
popravkom `scripts/privtrace_reference.patch` (skupaj z diagnostičnim
`scripts/privtrace_reference_no_or.patch` edina artefakta izvirnika v gitu): `np.int` →
`int` na 11 mestih, odstranjen `import fcntl` (samo POSIX), `import torch` mrtve kode v
`try/except`, ter trije parametri `--seed` (koda semena ni imela; vse naključje je globalno
stanje numpy/random), `--level1_k` (izvirnikovo pravilo K = min(60, ⌊√(N_točk/600)⌋) bi tu
dalo K = 32 in tisoče stanj, kar ne konča) in `--output_file` (šest decimalk namesto dveh).
Algoritem — šum, NormCut, delitev, adaptivno pravilo, množilniki konca, zavračanje hoj,
reševalec `cvxpy` — je nespremenjen. `cvxpy` je enkratno nameščen v obstoječe okolje `uv`
(ni v `pyproject.toml`; brez ECOS, zato izvirnikova gola `except:` pristane na SCS). Vhod:
**prvih 20.000 poti** `porto.dat` (640.519 točk, 32 na pot) v izvirnikovem tekstovnem
formatu (`--write-subset`), bbox po izvirnikovem pravilu (min/max ± 10⁻⁵ razpona), **K = 6 na
obeh straneh**, ε ∈ {0,5, 1, 2}, semena 1–5, brez razreza in podvzorčenja. Ta bbox je prebran
iz surovih podatkov in **ni diferencialno zaseben — na nobeni strani, pri izvirniku prav tako
ne**; obravnavamo ga kot del skupne, javno predpostavljene postavitve poskusa (območje, v
katerem podatki živijo, določeno pred porabo proračuna in enako za vse stolpce), ne kot del
mehanizma. Ocena: obe strani z devetimi metrikami članka LDPTrace
(`evaluation/ldptrace_metrics.py`) nad enotno mrežo 20 × 20 nad istim bbox (izvirnik lastnih
metrik nima; ena enakomerna točka na list na obeh straneh). **Vsak pogon je ocenjen dvakrat:**
z mostovi (dogovor LDPTrace — `Grid.chain` zapolni vsak preskok med nesosednjima celicama z
ravno »kraljevo« potjo, tako da preskok šteje kot cela vrsta celic, ki jih preleti) in brez
mostov (iste vrednosti pod imeni `nobridge_*`, kjer šteje samo celica, v kateri res leži
točka). Delež vrinjenih celic (`interpolated_share`) je izpisan za vsako stran, ker meri
velikost te razlike. Tretji stolpec je port z izbirno masko sosednosti (odstopanje D-4.6,
privzeto izklopljeno): prehod med stanjema, katerih celici 1. plasti nista isti ali
4-sosednji, je ničen skupaj s strukturnimi ničlami, po šumu in pred NormCut — to je pravilo
izvirnikove kode, preneseno v naknadno procesiranje nad javno geometrijo mreže. Maska sama ne
porabi nobenega žreba in ne prebere podatkov, zato je porabljeni proračun nespremenjen; ker pa
pade pred NormCut in pred izbirnim pravilom, se nabor stanj 2. reda in s tem število Laplaceovih
matrik 3. stopnje lahko razlikuje od neizmaskirane prilagoditve (pri ε = 2 izbere port 5,4
stanja, port z masko 4,2). ε₃ se porabi enkrat, ne glede na to število. Ukazi in časi:
`docs/RUNNING.md` §9.4;
ogrodje `experiments/privtrace_eval.py` (commit portove strani `ef9811c`); izhod
`results/privtrace_validation/` (ni v gitu).

Preverba pred meritvijo: obe strani zgradita **enako mrežo** — izvirnik 159–164 listnih stanj
(24 od 36 celic razdeljenih, κ 1–5; iz pilota), port 161–164 (23–24 razdeljenih, κ ≤ 5),
enak bbox; delna primerjava pilota na 2.000 poteh (39 stanj) je bila skladna.

Časi (ponovna meritev, 15 pogonov na stolpec): port bere 20.000 poti v 1,5 s, prilagoditev
1,9–2,1 s na (ε, seme), sinteza 20.000 hoj 7,4–10,9 s, metrike z mostovi 8,3–10,8 s in brez
mostov 9,8–11,9 s — 15 pogonov v 8,3 min; port z masko (ponovna meritev 22. septembra 2026)
bere v 8,6 s, prilagoditev 1,9–2,2 s na (ε, seme), sinteza 9,3–14,7 s (najdaljših 14,7 s je
ε = 0,5 pri semenu 1 z 1.287 ponovnimi žrebi), metrike z mostovi 8,0–9,3 s in brez mostov
10,7–12,2 s — 15 pogonov v 8,4 min; ocena 15 sintez izvirnika 18–20,5 s na sintezo, skupaj
5,2 min. Izvirnik sam je tekel
70–90 s na pogon (3,5 min, ko je vzporedno tekel port), 15 pogonov 33 min; diagnostična pogona
brez pogojev »ALI« 138 s in 119 s (ustrezna glavna pogona pri tem ε 263 s in 207 s, oba
vzporedno s portom), njuna ocena in kontrola na semenih 1–2 po ~1 min.

Tabela je dobesedni izpis ogrodja (decimalna pika, povprečje [najmanj; največ] čez pet
semen). Stolpci: `port` je port po članku, `port_masked` isti port z masko sosednosti D-4.6,
`reference` izvirnikova koda; vse tri ocenjujejo naše metrike. Sedem metrik so napake, nižje
je bolje; Kendall in F1 sta oceni, višje je bolje. Vrstice `n_states`, `n_second_order` in
`synthetic_mean_length` so dejstva porta (izvirnik jih ne izpisuje). Vrstice `nobridge_*` so
iste metrike, ocenjene brez mostov, in ponovi se **sedem od devetih**: šest, ki berejo verige
celic, in poizvedba po točkah. Ta se premakne zato, ker se njena realna stran vzorči po
celicah realnih verig (ena enakomerna točka na celico, `ldptrace_metrics.evaluate`) — brez
mostov imajo realne verige manj celic, zato je realni vzorec drugačen, in to velja za vse
tri strani v vseh 45 pogonih. Ker isti tok naključja ta vzorec izžreba pred 200 središči
poizvedb, se brez mostov premaknejo tudi središča; znotraj enega prehoda pa vsi stolpci
vidijo isti realni vzorec in ista središča, zato ostanejo med sabo primerljivi. Iz surovih
točk se računata samo premer in dolžina: ta dva sta v obeh prehodih enaka do zadnje decimalke
(preverjeno v vseh 45 pogonih) in se zato ne ponavljata.
`interpolated_share` je delež celic v verigi, ki jih je vstavila kraljeva pot; pri
pravih poteh je 0.0800 na vseh treh straneh, torej je vse nad tem umetnost točkovanja:

| ε | metric | port | port_masked | reference |
|---|---|---|---|---|
| 0.5 | density_error | 0.0630 [0.0586; 0.0679] | 0.0564 [0.0489; 0.0649] | 0.1522 [0.1103; 0.1885] |
| 0.5 | hotspot_query_error | 0.1133 [0.0035; 0.3056] | 0.0254 [0.0000; 0.0474] | 0.4532 [0.0131; 1.0000] |
| 0.5 | point_query_avre | 0.5436 [0.5108; 0.5828] | 0.3944 [0.3393; 0.4700] | 0.6743 [0.6546; 0.6834] |
| 0.5 | coverage_kendall_tau | 0.5886 [0.5730; 0.6009] | 0.5963 [0.5468; 0.6234] | 0.3897 [0.3194; 0.4701] |
| 0.5 | trip_error | 0.5461 [0.5385; 0.5534] | 0.5284 [0.5144; 0.5474] | 0.6062 [0.5908; 0.6216] |
| 0.5 | diameter_error | 0.1108 [0.0944; 0.1291] | 0.0874 [0.0728; 0.0989] | 0.2551 [0.1817; 0.3015] |
| 0.5 | length_error | 0.1468 [0.1389; 0.1579] | 0.1111 [0.1055; 0.1243] | 0.1690 [0.1091; 0.2062] |
| 0.5 | pattern_f1 | 0.3540 [0.3100; 0.4300] | 0.3820 [0.3300; 0.4300] | 0.1640 [0.1000; 0.2600] |
| 0.5 | pattern_support_error | 0.6740 [0.5889; 0.7282] | 0.6642 [0.6113; 0.7173] | 0.8983 [0.8620; 0.9213] |
| 0.5 | n_states | 162.8 [161.0; 164.0] | 162.8 [161.0; 164.0] | — |
| 0.5 | n_second_order | 0.0 | 0.0 | — |
| 0.5 | synthetic_mean_length | 7.1 [6.2; 7.6] | 10.8 [9.9; 12.0] | — |
| 0.5 | nobridge_density_error | 0.0619 [0.0600; 0.0650] | 0.0614 [0.0547; 0.0730] | 0.1462 [0.1081; 0.1735] |
| 0.5 | nobridge_hotspot_query_error | 0.2195 [0.0235; 0.3892] | 0.0555 [0.0000; 0.1927] | 0.3866 [0.0314; 0.8001] |
| 0.5 | nobridge_point_query_avre | 0.5045 [0.4792; 0.5338] | 0.3597 [0.2930; 0.4308] | 0.6813 [0.6454; 0.7049] |
| 0.5 | nobridge_coverage_kendall_tau | 0.5702 [0.5499; 0.5860] | 0.5784 [0.5268; 0.5986] | 0.3986 [0.3243; 0.4730] |
| 0.5 | nobridge_trip_error | 0.5461 [0.5385; 0.5534] | 0.5284 [0.5144; 0.5474] | 0.6062 [0.5908; 0.6216] |
| 0.5 | nobridge_pattern_f1 | 0.3260 [0.3100; 0.3400] | 0.3220 [0.2900; 0.3400] | 0.2540 [0.2100; 0.2700] |
| 0.5 | nobridge_pattern_support_error | 0.8525 [0.8102; 0.8886] | 0.7871 [0.7659; 0.8073] | 0.9271 [0.9007; 0.9509] |
| 0.5 | interpolated_share | 0.6371 [0.5953; 0.6594] | 0.3955 [0.3826; 0.4034] | 0.3709 [0.3117; 0.4206] |
| 1.0 | density_error | 0.0569 [0.0534; 0.0652] | 0.0432 [0.0411; 0.0466] | 0.0709 [0.0565; 0.0862] |
| 1.0 | hotspot_query_error | 0.0802 [0.0235; 0.1937] | 0.0199 [0.0013; 0.0314] | 0.1541 [0.0235; 0.3106] |
| 1.0 | point_query_avre | 0.3386 [0.2430; 0.4370] | 0.3886 [0.3746; 0.4162] | 0.5772 [0.4720; 0.6307] |
| 1.0 | coverage_kendall_tau | 0.6143 [0.5995; 0.6234] | 0.6458 [0.6408; 0.6578] | 0.5564 [0.5330; 0.5991] |
| 1.0 | trip_error | 0.5030 [0.4917; 0.5134] | 0.5063 [0.4961; 0.5121] | 0.5483 [0.5380; 0.5550] |
| 1.0 | diameter_error | 0.0960 [0.0871; 0.1015] | 0.1075 [0.1028; 0.1118] | 0.1947 [0.1597; 0.2303] |
| 1.0 | length_error | 0.1598 [0.1465; 0.1693] | 0.1082 [0.1041; 0.1138] | 0.1149 [0.0920; 0.1296] |
| 1.0 | pattern_f1 | 0.4160 [0.3300; 0.4700] | 0.4300 [0.3800; 0.4800] | 0.3320 [0.2300; 0.3800] |
| 1.0 | pattern_support_error | 0.5815 [0.5228; 0.6543] | 0.6806 [0.6489; 0.7043] | 0.8309 [0.7980; 0.8511] |
| 1.0 | n_states | 164.0 | 164.0 | — |
| 1.0 | n_second_order | 0.0 | 0.0 | — |
| 1.0 | synthetic_mean_length | 10.5 [8.6; 11.7] | 10.4 [9.8; 11.2] | — |
| 1.0 | nobridge_density_error | 0.0529 [0.0489; 0.0635] | 0.0490 [0.0471; 0.0512] | 0.0693 [0.0625; 0.0794] |
| 1.0 | nobridge_hotspot_query_error | 0.0602 [0.0235; 0.1991] | 0.0343 [0.0235; 0.0699] | 0.1567 [0.0235; 0.3106] |
| 1.0 | nobridge_point_query_avre | 0.2861 [0.1703; 0.3912] | 0.3488 [0.3170; 0.3954] | 0.5527 [0.4550; 0.6101] |
| 1.0 | nobridge_coverage_kendall_tau | 0.6041 [0.5894; 0.6162] | 0.6197 [0.6138; 0.6268] | 0.5528 [0.5371; 0.5819] |
| 1.0 | nobridge_trip_error | 0.5030 [0.4917; 0.5134] | 0.5063 [0.4961; 0.5121] | 0.5483 [0.5380; 0.5550] |
| 1.0 | nobridge_pattern_f1 | 0.3520 [0.3200; 0.3900] | 0.3620 [0.3500; 0.3800] | 0.3460 [0.3100; 0.3800] |
| 1.0 | nobridge_pattern_support_error | 0.7865 [0.7539; 0.8251] | 0.7767 [0.7532; 0.7923] | 0.8734 [0.8450; 0.8931] |
| 1.0 | interpolated_share | 0.5745 [0.5579; 0.5796] | 0.3539 [0.3483; 0.3621] | 0.3348 [0.2928; 0.3626] |
| 2.0 | density_error | 0.0482 [0.0457; 0.0504] | 0.0390 [0.0365; 0.0418] | 0.0539 [0.0488; 0.0631] |
| 2.0 | hotspot_query_error | 0.0294 [0.0131; 0.0595] | 0.0263 [0.0131; 0.0595] | 0.0788 [0.0235; 0.1630] |
| 2.0 | point_query_avre | 0.3272 [0.2930; 0.3720] | 0.4079 [0.3928; 0.4193] | 0.5402 [0.4863; 0.5630] |
| 2.0 | coverage_kendall_tau | 0.6407 [0.6305; 0.6540] | 0.6667 [0.6576; 0.6728] | 0.6220 [0.5980; 0.6361] |
| 2.0 | trip_error | 0.4844 [0.4742; 0.4898] | 0.4998 [0.4967; 0.5044] | 0.5196 [0.5157; 0.5226] |
| 2.0 | diameter_error | 0.0863 [0.0836; 0.0877] | 0.1235 [0.1200; 0.1327] | 0.1754 [0.1623; 0.1815] |
| 2.0 | length_error | 0.1446 [0.1350; 0.1527] | 0.1063 [0.1043; 0.1083] | 0.0861 [0.0756; 0.0913] |
| 2.0 | pattern_f1 | 0.4780 [0.4600; 0.4900] | 0.4560 [0.4400; 0.4700] | 0.3860 [0.3700; 0.4000] |
| 2.0 | pattern_support_error | 0.5906 [0.5637; 0.6183] | 0.6971 [0.6830; 0.7151] | 0.8030 [0.7954; 0.8129] |
| 2.0 | n_states | 164.0 | 164.0 | — |
| 2.0 | n_second_order | 5.4 [4.0; 7.0] | 4.2 [3.0; 6.0] | — |
| 2.0 | synthetic_mean_length | 10.4 [9.8; 11.1] | 9.8 [9.5; 10.3] | — |
| 2.0 | nobridge_density_error | 0.0441 [0.0428; 0.0459] | 0.0455 [0.0443; 0.0467] | 0.0527 [0.0496; 0.0550] |
| 2.0 | nobridge_hotspot_query_error | 0.0266 [0.0235; 0.0314] | 0.0343 [0.0235; 0.0699] | 0.0773 [0.0235; 0.1526] |
| 2.0 | nobridge_point_query_avre | 0.2769 [0.2329; 0.3288] | 0.3688 [0.3367; 0.3926] | 0.5202 [0.4923; 0.5326] |
| 2.0 | nobridge_coverage_kendall_tau | 0.6342 [0.6246; 0.6411] | 0.6351 [0.6277; 0.6398] | 0.6102 [0.6013; 0.6182] |
| 2.0 | nobridge_trip_error | 0.4844 [0.4742; 0.4898] | 0.4998 [0.4967; 0.5044] | 0.5196 [0.5157; 0.5226] |
| 2.0 | nobridge_pattern_f1 | 0.3900 [0.3700; 0.4000] | 0.3840 [0.3700; 0.4000] | 0.3420 [0.3300; 0.3500] |
| 2.0 | nobridge_pattern_support_error | 0.7784 [0.7550; 0.7903] | 0.7839 [0.7705; 0.7934] | 0.8481 [0.8394; 0.8589] |
| 2.0 | interpolated_share | 0.5084 [0.4999; 0.5210] | 0.3323 [0.3250; 0.3392] | 0.3222 [0.3131; 0.3436] |

**Regresija ponovne meritve:** stolpec `port` je v vseh 255 že obstoječih vrednostih (devet
metrik × 15 pogonov in dejstva porta) in stolpec `reference` v vseh 165 enak popoldanski
meritvi z dne 20. septembra 2026 do zadnje decimalke — isti žrebi šuma in iste mreže, ker
vrata delitve na zašumljeni vsoti pri 20.000 poteh niso prevrnila nobene celice (prag se
premakne za ~±0,1 okrog 27,8). Novo v tabeli sta torej tretji stolpec in blok brez mostov.

**Regresija ob ponovni meritvi maske (22. september 2026, PR #42):** iz commita `ca1eb7f` je
bilo ponovno pognanih vseh 15 pogonov stolpca `port` (8,2 min) in ponovno ocenjenih vseh 15
sintez izvirnika (5,2 min). Pri portu je vseh 420 že obstoječih vrednosti (15 pogonov × 28
ključev brez časov in poti do sinteze) do zadnje decimalke enakih datoteki
`results/privtrace_validation/port.json` iz PR #41; novi so samo trije ključi varovalke
(`max_redraws` = 20, `n_capped_walks` = 0 in `n_redrawn_walks` = 0 v vseh 15 pogonih). Pri
izvirniku je enakih vseh 315 vrednosti (15 pogonov × 21 ključev brez časov in poti do sinteze),
ker se koda ocenjevanja ni spremenila, ampak samo izpis tabele. Obe datoteki v `results/` zato
ostaneta zapis iz PR #41 (`git_commit ef9811c`); izhoda obeh regresijskih pogonov nista shranjena
v `results/`. Zamenjan je samo `port_masked.json` (`git_commit ca1eb7f`) skupaj s shranjenimi
sintezami v `port_masked_synthesis/`: datoteke maske iz PR #41 so s tem prepisane (kopija je
zunaj repozitorija), zato so številke tistega pogona, ki jih besedilo še navaja — 1.207 hoj do
varovalke pri semenu 1, povprečna dolžina 21,6 stanja, delež samoprehodov 0,0039 — citirane iz
preseženega zapisa in jih iz datotek na disku ni več mogoče ponoviti. Cel paket — ponovna
meritev z masko in obe regresiji — je tekel 21,7 min.

**Diagnostična tabela (ni del glavne primerjave):** kaj se z izvirnikom zgodi, če mu vzamemo
tri pogoje »ALI« v adaptivnem pravilu (popravek `scripts/privtrace_reference_no_or.patch`,
uporabljen samo za ta dva pogona in nato razveljavljen). `reference_s12` je glavni izvirnik,
ocenjen samo na semenih 1–2, da je primerjava enaka za enako; `reference_no_or` je izvirnik
brez teh treh pogojev, prav tako semeni 1–2. Prikazane so samo vrstice pri ε = 0,5, kjer je
diagnostika tekla (ogrodje izpiše tudi vrstice pri ε = 1 in ε = 2 iz datotek porta, a sta oba
stolpca izvirnika tam prazna; te vrstice so v glavni tabeli zgoraj). Delež vrinjenih celic pri
pravih poteh je tudi tu 0.0800:

| ε | metric | port | port_masked | reference_s12 | reference_no_or |
|---|---|---|---|---|---|
| 0.5 | density_error | 0.0630 [0.0586; 0.0679] | 0.0564 [0.0489; 0.0649] | 0.1722 [0.1558; 0.1885] | 0.1030 [0.0978; 0.1082] |
| 0.5 | hotspot_query_error | 0.1133 [0.0035; 0.3056] | 0.0254 [0.0000; 0.0474] | 0.6501 [0.3002; 1.0000] | 0.3801 [0.2160; 0.5442] |
| 0.5 | point_query_avre | 0.5436 [0.5108; 0.5828] | 0.3944 [0.3393; 0.4700] | 0.6792 [0.6750; 0.6834] | 0.6396 [0.6312; 0.6481] |
| 0.5 | coverage_kendall_tau | 0.5886 [0.5730; 0.6009] | 0.5963 [0.5468; 0.6234] | 0.3520 [0.3194; 0.3845] | 0.4596 [0.4513; 0.4678] |
| 0.5 | trip_error | 0.5461 [0.5385; 0.5534] | 0.5284 [0.5144; 0.5474] | 0.6163 [0.6111; 0.6216] | 0.5855 [0.5701; 0.6009] |
| 0.5 | diameter_error | 0.1108 [0.0944; 0.1291] | 0.0874 [0.0728; 0.0989] | 0.2681 [0.2347; 0.3015] | 0.2674 [0.2652; 0.2695] |
| 0.5 | length_error | 0.1468 [0.1389; 0.1579] | 0.1111 [0.1055; 0.1243] | 0.1810 [0.1709; 0.1912] | 0.1616 [0.1464; 0.1769] |
| 0.5 | pattern_f1 | 0.3540 [0.3100; 0.4300] | 0.3820 [0.3300; 0.4300] | 0.1150 [0.1000; 0.1300] | 0.2800 [0.2500; 0.3100] |
| 0.5 | pattern_support_error | 0.6740 [0.5889; 0.7282] | 0.6642 [0.6113; 0.7173] | 0.9158 [0.9103; 0.9213] | 0.8644 [0.8382; 0.8906] |
| 0.5 | n_states | 162.8 [161.0; 164.0] | 162.8 [161.0; 164.0] | — | — |
| 0.5 | n_second_order | 0.0 | 0.0 | — | — |
| 0.5 | synthetic_mean_length | 7.1 [6.2; 7.6] | 10.8 [9.9; 12.0] | — | — |
| 0.5 | nobridge_density_error | 0.0619 [0.0600; 0.0650] | 0.0614 [0.0547; 0.0730] | 0.1622 [0.1569; 0.1676] | 0.1041 [0.0975; 0.1107] |
| 0.5 | nobridge_hotspot_query_error | 0.2195 [0.0235; 0.3892] | 0.0555 [0.0000; 0.1927] | 0.5209 [0.3002; 0.7417] | 0.2618 [0.2095; 0.3141] |
| 0.5 | nobridge_point_query_avre | 0.5045 [0.4792; 0.5338] | 0.3597 [0.2930; 0.4308] | 0.6898 [0.6747; 0.7049] | 0.6384 [0.6234; 0.6533] |
| 0.5 | nobridge_coverage_kendall_tau | 0.5702 [0.5499; 0.5860] | 0.5784 [0.5268; 0.5986] | 0.3568 [0.3243; 0.3893] | 0.4532 [0.4438; 0.4626] |
| 0.5 | nobridge_trip_error | 0.5461 [0.5385; 0.5534] | 0.5284 [0.5144; 0.5474] | 0.6163 [0.6111; 0.6216] | 0.5855 [0.5701; 0.6009] |
| 0.5 | nobridge_pattern_f1 | 0.3260 [0.3100; 0.3400] | 0.3220 [0.2900; 0.3400] | 0.2400 [0.2100; 0.2700] | 0.3150 [0.3100; 0.3200] |
| 0.5 | nobridge_pattern_support_error | 0.8525 [0.8102; 0.8886] | 0.7871 [0.7659; 0.8073] | 0.9452 [0.9395; 0.9509] | 0.9073 [0.8935; 0.9212] |
| 0.5 | interpolated_share | 0.6371 [0.5953; 0.6594] | 0.3955 [0.3826; 0.4034] | 0.3877 [0.3547; 0.4206] | 0.3271 [0.3009; 0.3534] |

Kaj v izvirniku delajo ti trije pogoji (bralni pregled njegovih lastnih zašumljenih matrik
med pogonom; pregledovalna skripta ni v repozitoriju, ε = 0,5): pravilo članka (`degree_amount` **in** `degree_distribution`) izbere **0** stanj
2. reda od 159 pri semenu 1 in 0 od 164 pri semenu 2; pogoji »ALI« (velika izhodna stopnja,
teža začetka nad 2 %, teža konca nad 2 %) jih dodajo 0 / 13 / 27 oziroma 1 / 15 / 28, torej
34 in 35 vsiljenih stanj 2. reda, ki nosijo 35,4 % oziroma 34,1 % mase prehodov med pravimi
stanji in 59,2 % oziroma 62,0 % mase začetka. Po šumu in odrezu na cela števila je 52,1 %
oziroma 54,6 % njihovih vrstic praznih (vrnejo se na 1. red). Prevladujoč pogoj je teža
**konca**, ne začetka. Pri ε = 2 in semenu 1: pravilo članka 4 od 164, s pogoji »ALI« skupaj
20 (zgrajenih 17), 23,0 % mase, 54,5 % mase začetka, 54,1 % praznih vrstic. Izvirnik zgradi
tudi manj kažipotov, kot jih izbere (34 → 33, 20 → 17): drugi, nedokumentiran odpad. Eden ali
dva kažipota na pogon imata pokvarjen stolpec konca (`INT_MIN`, 0,7–2,5 % izhodne mase),
ker njegovo preračunavanje konca deli z nič — od tod `RuntimeWarning` v dnevnikih; taka
stanja hoje ne morejo končati in so odvisna od skoka iz slepe ulice. Pogona brez pogojev
»ALI« nimata nobenega takega opozorila in nobenega zavrnjenega sprehoda.

Dolžina sintetičnih poti (točk na pot): izvirnik 4,7 / 6,1 / 7,0 pri ε = 0,5 / 1 / 2
(po semenih 1 / 2: 4,22 / 4,42 pri ε = 0,5, 5,81 / 6,19 pri ε = 1, 7,10 / 7,09 pri ε = 2; brez
pogojev »ALI« 4,70 / 5,45), port 7,3 / 10,6 / 10,6 (stanj 7,1 / 10,5 / 10,4), port z masko
10,8 / 10,4 / 9,8 stanja (v PR #41, pred ponovnim žrebom, je bil pri ε = 0,5 dolg 13,1 stanja).
Prave poti Porta imajo na isti mreži s 164 stanji **12,04 strnjenega
stanja** (mediana 12, 90. percentil 19, največ 100), port brez šuma 8,57 (mediana 6) — to je
pristranskost, opisana pri odstopanju D-4.2. Pri semenu 1 je port dolg 6,17 stanja (mediana 4)
pri ε = 0,5 in 9,76 (mediana 7) pri ε = 2.

Maska je pri ε = 0,5 gnala hoje do varovalke, a samo pri enem semenu: v meritvi PR #41 je
**1.207 od 20.000 hoj** pri semenu 1 teklo do `max_len` = 200 stanj, pri semenih 2–5 pri istem
ε pa nobena (njihove najdaljše hoje imajo 148 / 112 / 176 / 115 stanj), pri ε = 2 prav tako
nobena. Vzrok je v modelu: zamaskirane vrstice ponekod ostanejo brez mase konca in z malo
dovoljenimi nasledniki, tako da hoja kroži po soseščini do varovalke; izvirnik prav to duši
z zavračanjem »postopajočih« hoj. Odstopanje D-4.3 tako hojo zdaj zavrže in jo ponovno izžreba
iz istega toka naključja, največ `max_redraws` = 20-krat. V ponovni meritvi 22. septembra 2026
se je varovalka sprožila v enem samem od 15 pogonov — ε = 0,5, seme 1, kjer je bilo
`n_redrawn_walks` = 1.287 in `n_capped_walks` = 0, torej ni bila obdržana nobena hoja, ki bi
varovalko dosegla; v ostalih 14 pogonih sta oba števca 0. Ponovnih žrebov je nekaj več kot
prej zajetih hoj (1.287 proti 1.207), ker lahko ponovno izžrebana hoja varovalko doseže še
enkrat in se žreb ponovi. Nobena hoja porta brez maske ne doseže varovalke pri nobenem ε, zato
tam varovalka nikoli ne sproži in žrebi ostanejo nespremenjeni: regresijska ponovitev stolpca
`port` iz commita `ca1eb7f` je do zadnje decimalke enaka meritvi PR #41.

Preskoki med celicama 1. plasti, ki nista 4-sosednji (delež vseh zaporednih korakov, seme 1):
prave poti 0,0082 (5.091 od 620.519), port 0,2367 pri ε = 0,5 in 0,0912 pri ε = 2, port brez
šuma 0,0248, port z masko 0 po konstrukciji, izvirnik 0,0139 / 0,0002 (semeni 1 / 2) pri
ε = 0,5, 0,0095 / 0,0048 pri ε = 1 in 0,0026 / 0,0017 pri ε = 2, izvirnik brez pogojev »ALI«
0,0084 / 0,0001. Samoprehodi v hojah: port 0,0008 / 0,0006 korakov pri ε = 0,5 / 2 (masa
diagonale 0,19 % / 0,06 % realnega bloka), z masko 0,0090 / 0,0018 (pri ε = 0,5 po ponovnem
žrebu: 1.648 od 182.681 korakov; v sintezi PR #41 s pobeglimi hojami je bil delež 0,0039, ker
so tiste dolge hoje s 412.201 koraki delež samo redčile), brez šuma 0.

Port brez šuma (ε = 10⁴, dve semeni; spodnja meja, ki jo določa struktura modela, ne
zasebnost): gostota 0,034, vroče točke 0,013, AvRE 0,46,
Kendall 0,69, potovanja 0,47, premer 0,088, dolžina 0,093, F1 0,53, podpora vzorcev 0,67,
133 stanj 2. reda, 8,6 stanja na pot.

Branje (merila kot pri LDPTrace, `docs/NACRT_LDPTRACE_VALIDACIJA.md` §6):

1. **Mreža in trend se ujemata.** Vse tri strani dobijo isto delitev (isto število stanj do
   nekaj enot, kar je žreb šuma) in pri vseh napake padajo in oceni rasteta z ε (edina
   izjema je portova dolžina, ki je ravna pri 0,15, glej 5). Pri ε = 2 so gostota (0,048
   proti 0,054), vroče točke (0,03 proti 0,08 pri široki razpršenosti) in Kendall (0,64 proti
   0,62) **znotraj razpona semen** — to je del mehanizma, ki ga članek določa (zašumljena
   mreža in Markov 1. reda), in tam se strani strinjata; pri ε = 1 se gostota in Kendall
   ravno še prekrivata, pri ε = 0,5 ne več.
2. **Del portove prednosti je bil umetnost točkovanja — izmerjena.** Premoščanje (kraljeva
   pot) vstavi pri pravih poteh 8 % celic verige, pri portu po članku pa 64 / 57 / 51 % pri
   ε = 0,5 / 1 / 2; port z masko ima 40 / 35 / 33 %, izvirnik 37 / 33 / 32 %. Tudi zadnja dva,
   ki oba ostajata pri 4-sosednosti 1. plasti, imata torej okrog tretjino vrinjenih celic:
   ena celica 1. plasti pokriva 3,3 celice ocenjevalne mreže 20 × 20, zato tudi dovoljen korak
   v sosednjo celico 1. plasti prečka več ocenjevalnih celic. Portovih dodatnih 51–64 % je
   plačilo za proste preskoke. Brez mostov portova podpora vzorcev pade s 0,674 na 0,853
   (ε = 0,5), z 0,582 na 0,787 (ε = 1) in z 0,591 na 0,778 (ε = 2), njegov F1 s 0,354 na 0,326,
   z 0,416 na 0,352 in z 0,478 na 0,390, napaka vročih točk pri ε = 0,5 pa z 0,113 na 0,220;
   izvirnik se premakne veliko manj (podpora 0,898 → 0,927, 0,831 → 0,873, 0,803 → 0,848;
   F1 0,164 → 0,254, 0,332 → 0,346, 0,386 → 0,342). Gostota, Kendall in potovanja se komaj
   premaknejo (potovanja so po konstrukciji enaka: berejo samo prvo in zadnjo celico).
3. **Kaj ostane, ko mostove odmislimo: port je še vedno boljši, a pri vzorčnih metrikah ne
   toliko, kot je kazala tabela z mostovi.** Brez mostov se ponovi sedem metrik in pri vseh
   sedmih je portovo povprečje
   pri vseh treh ε boljše od izvirnikovega; pri ε = 1 je prednost pri F1 tako majhna
   (0,352 [0,32; 0,39] proti 0,346 [0,31; 0,38]), da je znotraj razpona semen in je ne
   štejemo za razliko. Po enotnem merilu — ali se razpona čez pet semen prekrivata ali ne —
   je port pred izvirnikom **zunaj razpona semen** pri Kendallu, potovanjih, podpori vzorcev
   in poizvedbah po točkah pri vseh treh ε ter pri gostoti (0,062 proti 0,146 in 0,044 proti
   0,053) in F1 pri ε = 0,5 in ε = 2; pri ε = 1 se pri gostoti (0,053 proti 0,069) in F1
   razpona ravno še prekrivata. Vroče točke so pri vseh ε **znotraj** razpona semen, ker je
   razpršenost te metrike velika (pri ε = 0,5 port 0,024–0,389 proti izvirnikovim
   0,031–0,800). Poizvedba po točkah je zdaj del bloka brez mostov, ker se njena realna stran
   vzorči po celicah realnih verig; portova vrednost se brez mostov celo izboljša (0,544 →
   0,505 pri ε = 0,5, 0,339 → 0,286 pri ε = 1 in 0,327 → 0,277 pri ε = 2, izvirnik 0,674 →
   0,681, 0,577 → 0,553 in 0,540 → 0,520), portova prednost pa je pri vseh ε zunaj razpona
   semen. Iz surovih točk se računata samo premer in dolžina in ta dva se med prehodoma ne
   premakneta: pri premeru je port boljši pri vseh ε zunaj razpona semen, pri dolžini ne
   (točka 5). Prejšnji zapis »port boljši pri sedmih od devetih« je torej pri vzorčnih
   metrikah pretiraval.
4. **Zaostanek izvirnika pri ε = 0,5 je najprej v modelu, ne (samo) v sintezi.** Na
   njegovih lastnih zašumljenih matrikah pravilo članka pri ε = 0,5 izbere **nič** stanj
   2. reda (obe semeni), njegovi trije pogoji »ALI« pa jih vsilijo 34 oziroma 35 — nosijo
   35 % mase prehodov in 59–62 % mase začetka, po odrezu na cela števila pa je 52–55 %
   njihovih vrstic praznih. Ko te pogoje odstranimo (diagnostika zgoraj), se izvirnik glede
   na enako-za-enako kontrolo na semenih 1–2 izboljša pri **vseh devetih** metrikah z
   mostovi — tudi pri premeru, kjer je premik najmanjši (0,2681 → 0,2674) — in pri vseh
   sedmih brez mostov (gostota 0,162 → 0,104, vroče točke 0,521 → 0,262, poizvedbe po točkah
   0,690 → 0,638, Kendall 0,357 → 0,453, potovanja 0,616 → 0,586, F1 0,240 → 0,315, podpora
   0,945 → 0,907), hoje pa se mu podaljšajo (4,22 → 4,70 in 4,42 → 5,45 točke). Port kljub
   temu ostaja pred izvirnikom brez pogojev »ALI«, po istem merilu razponov: **zunaj razpona
   semen** pri gostoti (0,062 proti 0,104), Kendallu (0,570 proti 0,453), potovanjih (0,546
   proti 0,586), podpori (0,853 proti 0,907) in poizvedbah po točkah (0,505 proti 0,638),
   **znotraj razpona** pa pri vročih točkah (0,220 proti 0,262) in F1 (0,326 proti 0,315).
   Preostanek
   razlike je v izvirnikovi poti 1. reda — porazdelitev začetka iz reševalca `cvxpy` (razdalja
   L1 0,16–0,17 od njegove lastne zašumljene vrstice začetka), stolpec konca × 1,3, množilniki
   pri hoji in zavračanje hoj — teh nismo izklopili (odprto).
5. **Dolžina: portova šibka točka, ne izvirnikova prednost.** Prave poti imajo 12,0
   strnjenih stanj, port brez šuma 8,6 (30 % prekratko) — to je natanko pristranskost
   normalizacije 1/(L+1), ki jo članek popravi z reševalcem potovanj (§4.4) in ki jo
   odstopanje D-4.2 opusti. S šumom da port po članku 6,2 stanja pri ε = 0,5 in 9,8 pri ε = 2
   (seme 1), izvirnik 4,2–7,1 točke. Boljša dolžinska napaka izvirnika pri ε ≥ 1 (0,115 in
   0,086 proti 0,160 in 0,145) torej ni delujoč nadzor dolžine, ampak enakomerno prekratka
   porazdelitev, ki po naključju pade bliže: njegovi množilniki ×0,8 / ×0,5 / ×0,2 verjetnost
   konca **znižujejo** in hoje podaljšujejo, krajšata pa jih ×1,5 na masi konca stanj 2. reda
   in zavračanje hoj. (Prejšnji zapis je trdil, da je portova dolžina pri šumu pristranska
   navzgor; to ni res — port je brez šuma prekratek, s šumom pa se 12,0 približa po naključju
   šuma.) Odrez števcev 2. reda na cela števila pri ε ≤ 1 ne igra vloge (port tam nima stanj
   2. reda; pri ε = 2 jih ima 4–7). Port je pri ε = 2 blizu svoje meje brez šuma (gostota
   0,048 proti 0,034, potovanja 0,48 proti 0,47, premer 0,086 proti 0,088, F1 0,48 proti
   0,53), kar pove, da preostale napake pri ε = 2 določa model, ne šum.
6. **Maska sosednosti (D-4.6) kot enako-za-enako različica.** Pri ε ≥ 1 izboljša gostoto
   (0,043 proti 0,057 in 0,039 proti 0,048), vroče točke, Kendall (0,646 proti 0,614 in 0,667
   proti 0,641) in dolžino (0,108 in 0,106), poslabša pa poizvedbe po točkah (0,389 proti
   0,339 in 0,408 proti 0,327), premer (0,086 → 0,124 pri ε = 2) in podporo vzorcev z mostovi;
   brez mostov sta portovi različici pri ε ≥ 1 pri vseh sedmih metrikah bloka brez mostov
   znotraj razpona semen ena od druge, z dvema izjemama pri ε = 2, kjer je port po članku boljši
   zunaj razpona:
   potovanja (0,484 [0,474; 0,490] proti 0,500 [0,497; 0,504]; ta metrika je z mostovi in brez
   njih enaka) in poizvedba po točkah (0,277 [0,233; 0,329] proti 0,369 [0,337; 0,393]); pri
   ε = 1 se tudi ta dva prekrivata (potovanja 0,503 [0,492; 0,513] proti 0,506 [0,496; 0,512],
   poizvedba 0,286 [0,170; 0,391] proti 0,349 [0,317; 0,395]). Pri ε = 0,5 je bila
   nestabilnost, zapisana v PR #41, stvar enega samega semena: pri semenu 1 je 1.207 od 20.000
   hoj krožilo do varovalke, zato je imelo to seme povprečno dolžino 21,6 stanja, gostoto
   0,263, F1 0,00 in poizvedbo po točkah 1,45. Ponovni žreb (D-4.3) te hoje zamenja — 1.287
   ponovnih žrebov in nobena obdržana hoja pri varovalki — in seme 1 je zdaj videti kot ostala
   štiri (gostota 0,065, dolžina 10,1 stanja, mediana 6, najdaljša hoja 95 stanj). Z varovalko
   je zamaskirani port pri ε = 0,5 pri
   vsaki metriki boljši od porta po članku ali pa znotraj njegovega razpona semen: **zunaj
   razpona** (maska boljša) je pri poizvedbah po točkah (0,394 [0,339; 0,470] proti 0,544
   [0,511; 0,583]) in dolžini (0,111 [0,106; 0,124] proti 0,147 [0,139; 0,158]), brez mostov
   pa še pri poizvedbah po točkah (0,360 proti 0,505) in podpori vzorcev (0,787 [0,766; 0,807]
   proti 0,853 [0,810; 0,889]); **znotraj razpona** je pri gostoti, vročih točkah (povprečje
   je precej nižje, 0,025 proti 0,113, a se razpona prekrivata), Kendallu, potovanjih, premeru,
   F1 in podpori z mostovi. Njena povprečna dolžina 10,8 stanja je bliže pravim 12,0 kot
   portovih 7,1. Maska ostane privzeto izklopljena iz razloga, ki je veljal od začetka —
   Algoritem 1 v članku omejitve sosednosti nima — in ne zato, ker bi bila nestabilna; ponovni
   žreb je ožji portov sorodnik izvirnikovega zavračanja »postopajočih« hoj, saj zamenja samo
   hoje, ki dosežejo varovalko. Povedati je treba tudi ceno: ponovni žreb s pre-vzorčenjem
   skrije napako modela na strani maske pri nizkem ε (vrstice, ki izgubijo maso konca), in
   izžrebane hoje so pogojene s tem, da varovalke niso dosegle, česar točkovanje ne modelira.
7. **Kar ta primerjava še vedno ne dokaže.** Odstranitev pogojev »ALI« je bila edina
   diagnostika, ki jo je avtor odobril, in je bila izvedena; izvirnika z izklopljenimi filtri
   sinteze (množilniki, zavračanje hoj, skok iz slepe ulice, začetek iz `cvxpy`) nismo pognali,
   zato preostanek razlike pri ε = 0,5 ostaja pripisan, ne izmerjen. Kar je izmerjeno, je
   portova prednost v bloku brez mostov.

Sklep: port in izvirnik nad istim vhodom delita mrežo in smer z ε, pri ε = 2 pa se z mostovi
ujemata tudi pri gostoti, vročih točkah in Kendallu znotraj razpona semen (brez mostov se
Kendall pri ε = 2 loči). Portova prednost preživi točkovanje brez mostov, po enotnem merilu
prekrivanja razponov čez pet semen: zunaj razpona je pri Kendallu, potovanjih, podpori vzorcev
in poizvedbah po točkah pri vseh treh ε ter pri gostoti in F1 pri ε = 0,5 in ε = 2, medtem ko
so vroče točke pri vseh ε znotraj razpona; del prednosti, ki jo je kazala prva tabela, je bil
umetnost premoščanja. Zaostanek izvirnika pri
ε = 0,5 je najprej posledica stanj 2. reda, ki jih vsilijo njegovi trije pogoji »ALI« (to je
zdaj pokazano), nato njegove poti 1. reda (to ni izolirano). Portova lastna šibka točka je
dolžina (pristranskost D-4.2, brez šuma 30 % prekratko), ki jo izbirna maska — z varovalko
ponovnega žreba tudi pri ε = 0,5 — zamenja za premer. Port je zvesta izvedba članka, ne
kode; PrivTrace ostaja kandidat za baseline
(odločitev D5 je odprta), v poročilu kot zgornja meja uporabnosti pri zaupanja vrednem
zbiralcu.

### 2.4 Val 5 — horizont B (2. letnik)

A1 polni klasifikator lastnosti (Geolife nima demografskih oznak), M4 ujemanje
segmentov (edge recall/precision), M5 klasifikacijske metrike (vezane na A1), uvoznika
T-Drive in Porto, ujemalnik `fmm`, pogled `as_graph_path()`, PostGIS, MLflow,
federativni pristopi, diffusion generatorji. Vse se priključi prek obstoječih vmesnikov.

### 2.5 Manjše, tehnične

- **D5 — zvezkov ne poganja nobena avtomatika** (CI: ruff, mypy, pytest); po
  spremembah, ki vplivajo na izhode, jih je treba ročno ponovno izvesti
  (`docs/RUNNING.md` §3). **Odločeno 22. 9. 2026:** ostane ročno — zvezki berejo lokalne
  rezultate v `results/`, ki jih v CI ni. Postavka je zaprta.
- **Grafi na ravni poročila čez več zagonov ali čez ponovitve** (`results_master.csv`,
  `repetitions.csv`): funkcije v `reporting/plots.py` berejo vrstice enotne tabele,
  zato je priključitev poceni; `report.py` danes riše samo reidentifikacijski graf
  kompromisa na zagon. Zvezek 03 to pokriva ročno. **Odločeno 22. 9. 2026:** `report.py`
  se ne razširi; grafe čez mehanizme in semena da primerjalni zvezek 04. Postavka je zaprta.
- **Predpomnjenje sintetičnih izdaj** (`data/synthetic/`) in utility metrike nad
  sintezo: LiRA sprašuje model po verjetnosti poti, ne po vzorcih, zato ni bilo
  potrebno; odpre se s prvim korakom, ki ga potrebuje (npr. razdelek 7.3 poročila).
  `rnldp_eval` to pokriva na fixturih.
- **Neobvezno iz sheme rezultatov** (`docs/REZULTATI_SHEMA.md`): `.parquet` zrcalo
  glavne tabele; stolpca `exp_id` in `config_hash` v `repetitions.csv`. **Odločeno
  22. 9. 2026:** stolpca se dodata (majhen PR pred pogonom 182, ker primerjalni zvezek
  bere več eksperimentov skupaj); `.parquet` zrcala ne bo.
- **A2 (reidentifikacija nad sintetičnimi potmi)** je rešen v poročilu, ne v kodi:
  perturbacija se ocenjuje z reidentifikacijo, sinteza s sklepanjem o članstvu.
- **Strop memorizacije `markov`** je odvisen od stopnje (AUC ~1,0 pri 20, 0,54 pri 50,
  0,78 pri 182); v poročilu ga interpretiraj na stopnji, na kateri se poroča.
- **Ujemanje na zemljevid ni ponovljivo med procesi** (ugotovljeno 3. septembra 2026 pri
  zlatem izpisu za PR B2): nad fixturom `geolife_onroad` pot `006/20081206080000` enkrat
  dobi zadnji rob 387, enkrat ne (ocena ujemanja enaka, 0,9092), odvisno od naključnega
  semena zgoščevanja Pythona (`PYTHONHASHSEED`); s fiksnim semenom je izpis ponovljiv in
  stara in nova koda dasta isto. Vzrok je izenačenje kandidatov v knjižnici
  `leuvenmapmatching`, ne v najini kodi. Predpomnilnik bazena zagotavlja ponovljivost
  vseh zagonov nad enkrat izračunanim bazenom; dva sveža izračuna pa lahko pri
  izenačenjih odstopata za rob. **Odločeno 22. 9. 2026:** pravilo `PYTHONHASHSEED=0` je
  zapisano v `docs/RUNNING.md` §10; CLI se ne spreminja. Postavka je zaprta.
- **Točka na meji celice v načinu celic** (ugotovljeno 4. septembra 2026 v PR C): `Grid.cell_of`
  uporablja polodprte intervale, izvirnik LDPTrace zaprte s prvo zadeto celico; nad Portom
  meja lon −8,620002 zadene 0,5 % poti in da drugačno verigo. Ogrodje validacije
  (`reference_cells` v `experiments/ldptrace_eval.py`) uporablja izvirnikovo pravilo,
  orkestratorjev `_cell_pool` pa še `Grid.cell_of`; za MIA nad Portom to ni pomembno.
  **Odločeno 22. 9. 2026:** `_cell_pool` ostane pri `Grid.cell_of` — preklop bi spremenil
  hash predpomnilnika in zahteval ponovni pogon Porta brez vpliva na rezultate MIA.
  Postavka je zaprta.
- **Dolžinska pristranskost DTW v reidentifikaciji — preverjena in potrjena** (ugotovljeno
  4. septembra 2026 pri ZM-3, preverjeno isti dan na veji `claude/zm3-naive-baselines`,
  glej 2.3): časovno redčenje izdaje na 30 / 120 / 600 s dvigne `top1_acc` pri k = 3 z
  0,28 na 0,49–0,54 ob skoraj celem bazenu. Hipoteza: `geometry.dtw` vrne nenormirano
  vsoto po poravnavi, zato je razdalja med k znanimi točkami in galerijsko sledjo
  sorazmerna s številom njenih točk in kratke sledi zmagujejo. **Preverba:** skript zunaj
  repozitorija (koda napada se ni spremenila), ki bere samo predpomnjene bazene u20 s
  semenom 42 (surovi `data/processed/56dcf747ce5967f6`, 238 sledi, in tri izdaje redčenja
  v `data/protected/`) in ponovi zanko napada iz `attacks/reidentification.py` (sonde iz
  surovega bazena, `_evenly_spaced` k točk, galerija brez lastne sledi, ena razdalja na
  uporabnika) s tremi razdaljami iz enega prehoda dinamičnega programiranja: nenormirana
  `dtw`, `dtw / L` (L je dolžina optimalne poravnave, vračanje po matriki stroškov) in
  `dtw / max(n, m)`; `top1_acc` z bootstrapom 1.000 / seme 42 kot v pogonu; 59 s. Nenormirana
  razdalja reproducira izmerjeni zapis do zadnje decimalke, vključno z intervali (sidro).
  Napad dela nad ujetimi točkami (`matched_points`), ki jih je v povprečju 106 / 21 / 4,7 /
  1,4 na sled (mediana 64 / 15 / 4 / 1; največ 601) — manj kot izdanih točk (352 / 74 / 23 /
  6,5), a z isto težko desno repo.

  | Bazen | k | `dtw` (kot v pogonu) | `dtw / L` | `dtw / max(n, m)` |
  |---|---|---|---|---|
  | surovi | 3 | 0,283 [0,228; 0,338] | 0,523 [0,460; 0,586] | 0,523 [0,460; 0,586] |
  | surovi | 5 | 0,384 [0,325; 0,447] | 0,565 [0,506; 0,624] | 0,565 [0,506; 0,624] |
  | surovi | 10 | 0,489 [0,426; 0,557] | 0,603 [0,544; 0,667] | 0,603 [0,544; 0,667] |
  | redčenje 30 s | 3 | 0,485 [0,418; 0,549] | 0,591 [0,523; 0,654] | 0,591 [0,523; 0,654] |
  | redčenje 30 s | 5 | 0,473 [0,409; 0,536] | 0,612 [0,549; 0,675] | 0,608 [0,544; 0,667] |
  | redčenje 30 s | 10 | 0,570 [0,506; 0,633] | 0,595 [0,532; 0,658] | 0,586 [0,523; 0,646] |
  | redčenje 120 s | 3 | 0,544 [0,481; 0,608] | 0,574 [0,511; 0,641] | 0,574 [0,511; 0,641] |
  | redčenje 120 s | 5 | 0,536 [0,473; 0,599] | 0,570 [0,506; 0,633] | 0,565 [0,502; 0,629] |
  | redčenje 120 s | 10 | 0,557 [0,494; 0,624] | 0,570 [0,506; 0,637] | 0,557 [0,494; 0,624] |
  | redčenje 600 s | 3 | 0,485 [0,422; 0,549] | 0,481 [0,418; 0,544] | 0,481 [0,418; 0,544] |
  | redčenje 600 s | 5 | 0,494 [0,430; 0,557] | 0,489 [0,426; 0,553] | 0,494 [0,430; 0,557] |
  | redčenje 600 s | 10 | 0,498 [0,430; 0,561] | 0,498 [0,430; 0,561] | 0,498 [0,430; 0,561] |

  Diagnostika nad surovim bazenom (razmerje med številom točk najbližje galerijske sledi
  in mediano števila točk v galeriji; mediana / povprečje / delež sond, pri katerih je
  zmagovalec krajši od mediane): nenormirana 0,06 / 0,13 / 1,00 pri k = 3, 0,08 / 0,19 /
  0,98 pri k = 5, 0,23 / 0,37 / 0,92 pri k = 10 — zmagovalec je skoraj vedno ena najkrajših
  sledi v galeriji; normirana `dtw / L` 0,59 / 1,03 / 0,66, 0,91 / 1,26 / 0,57, 0,95 /
  1,58 / 0,51 — razmerje se premakne k 1. Vnaprej določeno merilo je izpolnjeno v vseh
  treh delih: (a) normirana razdalja surovi bazen dvigne na 0,52 / 0,57 / 0,60, torej na
  raven redčenih rok pod nenormirano razdaljo (0,47–0,57) ali nad njo; (b) prednost
  redčenih rok pred surovim bazenom pade v bootstrap interval surovega bazena v šestih od
  devetih celic, pri 30 s in k = 3 ostane tik nad njim (+0,07; 0,591 proti zgornji meji
  0,586), pri 600 s in k ≥ 5 se obrne (−0,08 / −0,10: galerija z 1–2 ujetima točkama
  normiranega napadalca ovira); (c) razmerje dolžin zmagovalcev gre od < 0,25 proti ≈ 1.
  Razdalji `dtw / L` in `dtw / max(n, m)` dasta praktično isto (pri k ≪ m je dolžina
  poravnave ≈ m); pri 600 s vse tri sovpadajo, ker galerijska sled z eno točko poravnavo
  fiksira.

  **Pomen.** Pristranskost je lastnost napadalca iz zasnove §6.1, ne mehanizma: v vsem
  izmerjenem zapisu S4 (stopnje 20 / 50 / 182, vse roke) nenormirani napadalec razvršča
  galerijo pretežno po številu ujetih točk in ne po geometriji, zato so vrednosti
  reidentifikacije nad surovim bazenom **podcenjene** (pri u20 0,28 → 0,52 pri k = 3) in
  redčenje »pomaga« samo zato, ker to pristranskost odpravi. Koda napada se ni spremenila,
  ker bi sprememba razdalje spremenila celoten izmerjeni zapis S4. **Odprta odločitev
  avtorja** z dvema možnostma: (1) normirana razdalja napadalca (`dtw / L` ali `dtw /
  max(n, m)` v `attacks/reidentification.py`, smiselno kot nova vrednost
  `attacker.distance`, da `dtw` ostane zapis S4) s ponovnim pogonom lestvice; ali (2)
  kontrola dolžine v poročilu (napadalec ostane, poleg vrstic pogona se poroča kontrola s
  sondami oziroma galerijo enake dolžine, redčenje pa se bere kot vzvod, ki napadalcu
  odpravi pristranskost). Do odločitve poročilo redčenja ne sme brati kot »zaščita, ki
  poveča tveganje«, temveč kot razkritje pristranskosti napadalca.

  **Odločeno 22. 9. 2026: kombinacija obeh možnosti.** V kodo pride nova vrednost
  `attacker.distance: dtw_norm` (`dtw / L`); `dtw` ostane privzeta, zato izmerjeni zapis
  S4 ostane veljaven kot zapis nenormiranega napadalca. Nove meritve mehanizmov (pogon
  182) poročajo obe razdalji; S4 v poročilu dobi opombo o pristranskosti in kontrolno
  vrstico z `dtw_norm` namesto ponovnega pogona lestvice.

---

## 3. Kje je zgodovina

- `arhiv/HANDOFF_2026-08-21.md` — celotna predaja: §0 dnevnik izvedbe (val 0–2 s
  commiti), §1.1–1.9 analiza vrzeli z recenzijo, §1.10 prvi pogon S4 v celoti,
  §1.11–1.12 (tu 1.3–1.4), §2 predlagano zaporedje valov z opombami izvedbe, §3–§4
  zgodovinski recenzijski prompt.
- `arhiv/HANDOFF_S4_POPRAVKI.md` — odločitve S4-1 do S4-5, razrez na tri PR-je in
  njihova izvedba (§3), merilo validacijskega pogona (§2) in njegov izid (§4; tu 1.2).
- `arhiv/IMPLEMENTATION_PLAN.md`, `arhiv/PROMPTS.md` — fazni načrt P0–P7 in prompti,
  vse izvedeno.
- `arhiv/CODEBASE_PHASE_GUIDE.md` — zgodovinski sprehod po kodi po fazah (stanje
  6. julija 2026).
