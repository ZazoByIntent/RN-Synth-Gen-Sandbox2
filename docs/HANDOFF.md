# Predaja dela: stanje kampanje S4 in odprte postavke

**Različica:** 2. september 2026 (skrajšana). Celotna zgodovina predaje — analiza vrzeli
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

### 2.1 Odločitve avtorja (niso koda; blokirajo poročilo, ne repozitorija)

- **Pragovi zadostnosti zaščite** (poročilo §8.2): pri kateri vrednosti metrike
  mehanizem velja za zadostnega. Avtorjev predlog je vpisan v poročilo 24. avgusta
  2026 (po zapisu tiste seje; poročilo ni v gitu): reidentifikacija top-1 < 5 % pri
  k ≤ 10; MIA `tpr@fpr = 0.01` ≤ 0,02 in interval AUC vsebuje 0,5; rekonstrukcija
  povprečna napaka ≥ 500 m; dom/delo lokalizirana ≤ 10 %. **Čaka potrditev
  mentorice**; v repozitoriju pragovi niso kodirani.
- **Pomen »odstopanja statistik gibanja«** (M3, poročilo §7.5): `UTILITY_METRICS` že
  ima `cell_js_divergence` in `length_dist_error`; manjkata analogiji za trajanje in
  hitrost, a najprej mora biti jasno, kaj metrika sploh meri.
- **Definicija »poznanega vhodnega vzorca«** za rekonstrukcijo z delnim predznanjem
  (A4, poročilo §6.3). Dokler ni določena, je A4 blokiran.
- **Prekoračitve proračuna pri 182** (sedem klicev reidentifikacije na seme, glej 1.4)
  so sprejete po pravilu R1. Če bo poročilo zahtevalo klic `k10` pod proračunom, sta
  naslednja koraka lestvice (`docs/RUNNING.md` §7.3) opustitev `k10` ali nižja
  stopnja — oboje spremeni zasnovo in je avtorjeva odločitev.

### 2.2 Val 3 — dopolnitve znotraj obstoječih štirih scenarijev

- **A3 — rekonstrukcija z omejitvijo cestnega omrežja** (zasnova §6.3, poročilo §7.4):
  primerjava »z omrežjem proti brez omrežja« je empirični argument za omrežno
  zavednost. Danes je `attacks/reconstruction.py` Whittakerjev glajevalnik brez
  zemljevida. Brez blokad.
- **M2 — top-k točnost POI** (poročilo §7.5) skupaj s pogledom `as_poi_visits()`
  (`representation/views.py`, danes `NotImplementedError`). Predpogoj: v repozitoriju
  ni vira točk interesa in testi ne smejo na omrežje — potreben je fixture sloj POI.
- **A4** — glej 2.1.

### 2.3 Val 4 — širina mehanizmov in LDPTrace

- Mehanizmi iz zasnove §7, ki manjkajo: prostorsko zaokroževanje, časovno redčenje,
  Gaussov šum, točkovni LDP, SquareWave, segmentna perturbacija, k-anonimnost,
  kombinacije. Dodajaj po naraščajoči zahtevnosti; segmentna perturbacija zadnja
  (najbližja RN-LDP-Synth, zato najkoristnejša primerjava).
- **LDPTrace** prednostno: brez njega se razdelek 7.3 poročila primerja samo proti
  nezasebnemu Markovu. Točkovni LDP in LDPTrace gradita na `privacy/ldp.py` (GRR, OUE).
- **Načrt izvedbe (2. september 2026):** `docs/NACRT_MEHANIZMI.md`. Izbrani so štirje
  koraki, vsak ena seja in en PR: ZM-1 LDPTrace, ZM-2 točkovni LDP, ZM-3 naivna trojica
  (prostorsko zaokroževanje, časovno redčenje, Gaussov šum), ZM-4 PrivTrace. Odločitve,
  datoteke, testi in prompti za seje so v tistem dokumentu. Nabor baseline-ov za članek
  (odločitev D5 v projektu »Izbirni predmeti«) ostaja odprt; ti mehanizmi so kandidati.

**ZM-1 LDPTrace — zaključen (2. september 2026, veja `claude/zm1-ldptrace`).** Generator
`ldptrace` (`src/trajguard/synthesis/ldptrace.py`; dejanske odločitve v
`docs/NACRT_MEHANIZMI.md` §2, uvodni odstavek). Izmerjeno pri stopnji 20 s konfiguracijo
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
  neproblematične. Odprto (ločen PR): dekodiranje celic v odseke in roka `ldptrace` v
  `experiments/rnldp_eval.py`.
- **Validacija proti izvirni kodi** (metrike članka, način surovih koordinat na mreži
  v konfiguraciji, primerjalni pogon nad javnim Portom): načrt, predaja in prompt v
  `docs/NACRT_LDPTRACE_VALIDACIJA.md` (2. september 2026, še ni začeto). Ponovitev
  številk iz članka ni mogoča (izvirnik ne prilaga podatkov in nima semena); cilj je
  diferencialna primerjava port ↔ izvirnik nad istim vhodom.

### 2.4 Val 5 — horizont B (2. letnik)

A1 polni klasifikator lastnosti (Geolife nima demografskih oznak), M4 ujemanje
segmentov (edge recall/precision), M5 klasifikacijske metrike (vezane na A1), uvoznika
T-Drive in Porto, ujemalnik `fmm`, pogled `as_graph_path()`, PostGIS, MLflow,
federativni pristopi, diffusion generatorji. Vse se priključi prek obstoječih vmesnikov.

### 2.5 Manjše, tehnične

- **D5 — zvezkov ne poganja nobena avtomatika** (CI: ruff, mypy, pytest); po
  spremembah, ki vplivajo na izhode, jih je treba ročno ponovno izvesti
  (`docs/RUNNING.md` §3).
- **Grafi na ravni poročila čez več zagonov ali čez ponovitve** (`results_master.csv`,
  `repetitions.csv`): funkcije v `reporting/plots.py` berejo vrstice enotne tabele,
  zato je priključitev poceni; `report.py` danes riše samo reidentifikacijski graf
  kompromisa na zagon. Zvezek 03 to pokriva ročno.
- **Predpomnjenje sintetičnih izdaj** (`data/synthetic/`) in utility metrike nad
  sintezo: LiRA sprašuje model po verjetnosti poti, ne po vzorcih, zato ni bilo
  potrebno; odpre se s prvim korakom, ki ga potrebuje (npr. razdelek 7.3 poročila).
  `rnldp_eval` to pokriva na fixturih.
- **Neobvezno iz sheme rezultatov** (`docs/REZULTATI_SHEMA.md`): `.parquet` zrcalo
  glavne tabele; stolpca `exp_id` in `config_hash` v `repetitions.csv`.
- **A2 (reidentifikacija nad sintetičnimi potmi)** je rešen v poročilu, ne v kodi:
  perturbacija se ocenjuje z reidentifikacijo, sinteza s sklepanjem o članstvu.
- **Strop memorizacije `markov`** je odvisen od stopnje (AUC ~1,0 pri 20, 0,54 pri 50,
  0,78 pri 182); v poročilu ga interpretiraj na stopnji, na kateri se poroča.

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
