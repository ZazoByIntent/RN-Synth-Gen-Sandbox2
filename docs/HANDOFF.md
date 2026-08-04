# Predaja dela: vrzeli med dokumentacijo, poročilom IZV in kodo

**Nastalo:** 4. avgust 2026 · **Osnovano na commitu:** `aa5eb86` · **Veja:** `claude/review-attack-scenarios-c6byzc`
**Recenzirano in delno izvedeno:** 4. avgust 2026 · veja `claude/handoff-document-review-2fnmdo`
(končani so val 0 ter koraki 1a, 1b in 1c; glej razdelek 2)
**Viri:** `docs/Tehnicna_zasnova_eksperimentalno_okolje.md`, `docs/IMPLEMENTATION_PLAN.md`,
`docs/ARCHITECTURE.md`, koda pod `src/trajguard/`, zvezek `notebooks/02_pipeline_walkthrough.ipynb`
in poročilo `IZV_porocilo.docx` (delovni skelet, poglavja 1–3 izpolnjena).

---

## 0. Kako brati ta dokument — preberi preden karkoli spremeniš

**Recenzija je bila opravljena 4. avgusta 2026** (veja `claude/handoff-document-review-2fnmdo`):
od 24 postavk razdelka 1 je 20 potrjenih, štiri popravljene (O4, O5, O6 in razdelek 1.3 — vse
štiri so podcenjevale, kar v kodi že obstaja), ovržena ni nobena. Popravki so vpisani neposredno
v besedilo spodaj in označeni z **[recenzija]**. Recenzija je našla tudi eno spregledano
odvisnost — prepleteno seme, opisano pri O3 — ki spremeni sestavo vala 1 v razdelku 2.

**Stanje izvedbe (ista veja, 4. avgust 2026):** val 0 (`a2067b9`), korak 1a — ločitev semen in
`dataset.max_users` (`8fac2fb`), korak 1b — `trajguard repeat` s 95 % intervalom čez ponovitve
(`9005c2f`), korak 1c — rekonstrukcija v zanki orkestratorja (`4466008`). S tem sta O2 in O3
zaprta, O1 pa delno (rekonstrukcija da, `poi_inference` in `membership_inference` še ne).
Naslednji korak je **1d**.

**To je predlog, ne naročilo.** Nastal je v eni sami seji, iz ene same interpretacije poročila.
Prvotno besedilo ni bilo recenzirano; spodnja različica vključuje izid recenzije.

Pričakovani prvi rezultat naslednje seje **ni koda, ampak recenzija**: za vsako trditev v
razdelku 1 potrdi, ovrzi ali popravi, in za predlagano zaporedje v razdelku 2 povej, ali se z
njim strinjaš. Šele ko je recenzija predstavljena in potrjena, se lotimo prve spremembe.

Zakaj tako: vrzeli spodaj so bile ugotovljene s primerjavo besedila poročila s kodo. Poročilo je
delovni skelet z oznakami `[VSEBINA: …]` in `[REZULTAT: …]`, torej opisuje **namero**, ne
dokončanih zahtev. Nekaj postavk spodaj je zato lahko:

- **napačno branje namere** — poročilo zahteva nekaj, kar je bilo mišljeno drugače;
- **že rešeno drugje** — funkcionalnost obstaja, a pod drugim imenom ali v drugem modulu;
- **nepotrebno** — zahtevo v poročilu je ceneje spremeniti kot implementirati;
- **napačno prednostno razvrščeno** — vrstni red v razdelku 2 je ena od možnih poti.

Vsaka trditev nosi **mesto v kodi**, da je preverjanje poceni. Preveri jih; ne zaupaj temu
dokumentu na besedo.

### Vezni pogoji, ki veljajo ne glede na to recenzijo

Ta pravila prihajajo iz `CLAUDE.md` in jih ta dokument ne more povoziti:

- Netrivialno delo se začne v načrtovalnem načinu; načrt se pokaže in počaka na odobritev.
- Naloga, ki bi se dotaknila več kot približno petih datotek ali mešala nepovezane stvari, se
  **razdeli** — predlagaj razrez, ne izvedi vsega naenkrat.
- Definicija dokončanosti: `ruff check` in `mypy` sta čista, obstaja test na fixturih, in
  **pokažeš dokaz** — natančen ukaz in njegov izpis. Ne trdi, da deluje.
- Vsak nov napad, mehanizem, generator ali metrika deduje od ustreznega abstraktnega razreda in
  se registrira z `@register(kind, name)`. Vmesnikov se ne obhaja.
- Ena faza = ena veja = en zahtevek za združitev.

---

## 1. Ugotovljene vrzeli

Stanje je po commitu `aa5eb86`. Stolpec »preveri« pove, kje trditev potrdiš ali ovržeš.

### 1.1 Ocenjevalni scenariji (napadi)

Implementirani in testirani so štirje: `reidentification`, `membership_inference`,
`reconstruction`, `poi_inference` (32 testov, tečejo v desetinki sekunde). Manjka naslednje.

| # | Vrzel | Zahteva | Preveri |
|---|---|---|---|
| A1 | `attribute_classifier` — polni klasifikator lastnosti | zasnova §6.4, poročilo §4.4 | v registru ga ni; razlog v `docs/IMPLEMENTATION_PLAN.md:150` — Geolife nima demografskih oznak |
| A2 | Reidentifikacija nad sintetičnimi podatki | poročilo §4.1 pravi »perturbacija IN sinteza« | `src/trajguard/attacks/reidentification.py` — `target_scope = {"raw", "protected"}` |
| A3 | Rekonstrukcija z omejitvijo cestnega omrežja | poročilo §7.4 (seriji »z/brez omrežja«), zasnova §6.3 | `src/trajguard/attacks/reconstruction.py` — Whittakerjev glajevalnik brez zemljevida |
| A4 | Rekonstrukcija z delno poznanimi vhodnimi vzorci (0 % / 10 %) | poročilo §6.3 | isti razred sprejme le `epsilon`, `unit_m`, `motion_m` |

**Kaj tu podvomi:** A2 je lahko nedoslednost v poročilu, ne v kodi — reidentifikacija nad
sintetičnimi potmi je konceptualno sporna, ker sintetične poti ne pripadajo nobeni resnični
osebi. Morda je ceneje popraviti poročilo. A4 je smiseln le, če se dogovorimo, kaj »poznan
vhodni vzorec« sploh pomeni; poročilo tega ne opredeli.

**[recenzija]** Dvom pri A2 je potrjen: rešuje se **v poročilu**, ne v kodi. Smiselno
zasebnostno vprašanje za sintezo je »ali si je generator zapomnil učne podatke«, kar že meri
napad s sklepanjem o članstvu (`membership.py`, obseg `{"synthetic"}`). Poročilo §4.1 naj pravi:
perturbacija se ocenjuje z reidentifikacijo, sinteza s sklepanjem o članstvu. A2 s tem odpade
iz načrta implementacije. A4 ostane blokiran, dokler avtor ne opredeli »poznanega vzorca«.

### 1.2 Metrike

| # | Vrzel | Zahteva | Preveri |
|---|---|---|---|
| M1 | TPR\@FPR, AUC, prostorska napaka, Hausdorff niso registrirane metrike | poročilo §7.3, §7.4 | `src/trajguard/evaluation/metrics.py:44` in `:58` — registrirani sta **samo** `top_k_accuracy` in `linkage_rate`; funkcije obstajajo v `evaluation/roc.py` in v poročevalskih funkcijah napadov, a jih iz YAML ni mogoče poimenovati |
| M2 | Točnost top-k POI | poročilo §7.5, §6.8 | ni je; `src/trajguard/representation/views.py:88` — `as_poi_visits()` sproži `NotImplementedError` |
| M3 | »Odstopanje statistik gibanja« | poročilo §7.5 | ni definirano niti v poročilu — **potrebna je odločitev, kaj to je** |
| M4 | Ujemanje segmentov (edge recall/precision) | zasnova §6.3 | ni implementirano |
| M5 | Balanced accuracy, F1, preciznost, priklic | zasnova §6.4 | vezano na A1 |

**[recenzija]** M1 ni mehansko opravilo: uvodni komentar `evaluation/roc.py:1-6` namerno
utemeljuje, zakaj metrike na zveznih ocenah (AUC, TPR@FPR) ne sodijo v razred `SampledMetric`,
ki predpostavlja binarne indikatorje po sondi. Registracija zahteva oblikovno odločitev o
razširitvi vmesnika `Metric` — zato M1 ne stoji sam, ampak se rešuje po družinah napadov ob
priključitvi v orkestrator (glej popravljeni val 1). Pri M3 je vrzel manjša, kot je zapisano:
`UTILITY_METRICS` že vsebuje `cell_js_divergence` in `length_dist_error`
(`evaluation/utility.py:118-121`); manjkata le analogiji za trajanje in hitrost po istem vzorcu.

### 1.3 Zaščitni mehanizmi

Implementirana sta `none` in `geo_indistinguishability`. Zasnova §7 in poročilo §6.1
predvidevata še: prostorsko zaokroževanje, časovno redčenje, naivni Gaussov šum, točkovni LDP,
SquareWave, segmentno perturbacijo, k-anonimnost in kombinirane mehanizme.

**[recenzija]** Prvotno besedilo je spregledalo `src/trajguard/privacy/ldp.py`: gradnika
točkovnega LDP poročanja (GRR in OUE) že obstajata in sta testirana (`tests/test_ldp.py`),
namenoma kot funkciji in ne kot mehanizma (`ldp.py:1-16`). Točkovni LDP in LDPTrace iz vala 4
sta zato cenejša od prvotne ocene.

### 1.4 Generatorji

Implementirana sta `markov` (nezaseben) in `rn_ldp_synth` (prototip v1). **LDPTrace** manjka,
čeprav ga poročilo §5.5 navaja kot osnovni mehanizem sinteze iz literature — brez njega se
razdelek 7.3 primerja samo proti nezasebnemu Markovu, kar je šibkejša trditev, kot jo poročilo
obljublja. Manjkajo tudi DPT, AdaTrace, Diff-RNTraj, ControlTraj (horizont B).

### 1.5 Podatki, ujemanje s cestami, pogledi

Uvoznik obstaja samo za Geolife; T-Drive in Porto manjkata (poročilo §5.1 ju obravnava kot
alternativi in izbiro argumentira — morda zadošča argument, ne implementacija). Ujemalnik je
`leuven`; `fmm` iz zasnove §8 manjka. Pogleda `as_graph_path()` in `as_poi_visits()` sta prazna
kavlja (`views.py:84` in `:88`).

### 1.6 Pogon eksperimentov — najbolj boleča skupina

| # | Vrzel | Zahteva | Preveri |
|---|---|---|---|
| O1 | Trije od štirih napadov niso v zanki orkestratorja | poročilo §7.1 zahteva izhodišče za **vse štiri** scenarije | `src/trajguard/experiments/orchestrator.py:47` — `_ORCHESTRATOR_ATTACKS = frozenset({"reidentification"})`; zavrnitev je namerna in dokumentirana v komentarju nad njo |
| O2 | Velikost vzorca (20 / 50 / 100 / 182 uporabnikov) | poročilo §6.4 | v razčlenjevalniku konfiguracije ni ustreznega ključa |
| O3 | Ponovitve na konfiguracijo (predlog 5, fiksna semena, povprečje + 95 % IZ) | poročilo §6.4 | orkestrator pozna eno samo `experiment.seed` |
| O4 | Enotna tabela rezultatov s stolpci iz `Rezultati_predloga` (ID konfiguracije, seme, verzija kode) | poročilo §5.7, §6.7 | `run.json` in `matrix.csv` obstajata, a nista preslikana na dogovorjeno shemo iz `IZV_nacrt_eksperimentov.xlsx` |
| O5 | Načrtovane vizualizacije (glede na ε, glede na predznanje, primerjava mehanizmov, računski čas) | poročilo §6.8, §7.2–7.5 | `src/trajguard/reporting/tradeoff.py` — obstaja samo `plot_tradeoff()` |
| O6 | Merjenje računske zahtevnosti (čas, pomnilniška špica) in pravila za krčenje obsega | poročilo §7.6, §6.6 | `runtime_s` se beleži na ravni napada; pomnilnika in pravil ni |

**Kaj tu podvomi:** O3 je morda rešljiv zunaj kode — pet zagonov iste konfiguracije z različnimi
semeni in združevanje v skripti. Presodi, ali je vgradnja v orkestrator res boljša od tanke
skripte, preden se lotiš posega v jedro.

**[recenzija]** Popravki k tej skupini:

- **O3 — tanka skripta da, a šele po ločitvi semen.** Eno samo `experiment.seed` danes hkrati
  krmili delitev uporabnikov (`orchestrator.py:503` in razpršilni ključ `:341`), šum mehanizma
  (`:696`) in znanje napadalca (`:719`). Ponovitve z različnimi semeni bi torej vsakič na novo
  razdelile uporabnike (kršitev zlatega pravila o enkratni delitvi), pomešale varianco delitve
  z varianco šuma in ob vsakem semenu razveljavile predpomnilnik ujetih poti. Predpogoj je
  ločitev semena delitve od semena zagona v orkestratorju (poseg v eno datoteko); zanka
  ponovitev in združevanje potem sodita v tanko skripto — precedens je `experiments/rnldp_eval.py`.
  Pri združevanju ločuj dve vrsti intervalov zaupanja: bootstrap znotraj enega zagona in
  interval čez ponovitve (varianca med semeni).
- **O4 — sestavine že obstajajo.** `run.json` že beleži seme, verzijo kode (`git_commit`) in
  podpis konfiguracije (`config_hash`) (`orchestrator.py:864-887`); manjka le pripenjanje teh
  stolpcev vrsticam rezultatov. Ciljne sheme ni mogoče preveriti, ker `IZV_nacrt_eksperimentov.xlsx`
  in `IZV_porocilo.docx` **nista v repozitoriju** — val 2 je blokiran, dokler avtor sheme ne
  priskrbi (ali se zapiše v `docs/`).
- **O5 — spregledan je `reporting/report.py`.** Ukaz `trajguard report` že združuje vse zagone
  v tabele, matriko tveganj in Markdown poročilo (`report.py:224`, `:304`, `:512`). Manjkajo
  štirje načrtovani grafi, izhodišče pa je bistveno boljše od »obstaja samo `plot_tradeoff()`«.
- **O6 — čas se beleži na dveh ravneh:** po napadu (`AttackResult.runtime_s`) in za celoten
  zagon (`orchestrator.py:875`). Pomnilniške špice in pravil za krčenje obsega res ni.
- **Dodatno (spregledano v prvotnem besedilu):** vodilna metrika je trdo kodirana —
  `matrix.csv` in graf kompromisa vrtita samo `top1_acc` (`orchestrator.py:39`); priključitev
  drugih družin zahteva vodilno metriko po družini, preslikava v `report.py:23-28` že obstaja.
  Velikost vzorca (O2) mora v razpršilni ključ predpomnilnika, sicer si različne velikosti
  delijo isti predpomnjeni bazen.

### 1.7 Infrastruktura (namerno odloženo, horizont B)

PostGIS, sledenje poskusov z MLflow, federativni pristopi, več zemljevidov hkrati.

### 1.8 Neskladja v dokumentaciji (poceni, brez kode)

| # | Neskladje | Mesto |
|---|---|---|
| D1 | Trditev, da je `RNLDPSynth` kavelj z `NotImplementedError`, je zastarela — generator deluje | `docs/ARCHITECTURE.md:194` in zlato pravilo v `CLAUDE.md:54` |
| D2 | Tabela navaja za `poi_inference` obseg »protected, synthetic«, sintetična veja pa v praksi ne deluje (Markov vrača zaporedja segmentov brez koordinat in časov) | `docs/ARCHITECTURE.md:143`; opozorilo je pravilno zapisano le v dokumentacijskem nizu razreda |
| D3 | Zvezek `notebooks/02_pipeline_walkthrough.ipynb` ni omenjen nikjer v dokumentaciji | `docs/RUNNING.md` opisuje samo `01_matching_sanity.ipynb` |
| D4 | V zvezku ena kodna celica (indeks 49, slika `tradeoff.png`) nima shranjenega izhoda | `notebooks/02_pipeline_walkthrough.ipynb` |
| D5 | Zvezkov ne izvaja nobena avtomatika, zato tiho zastarevanje ni zaznano | `.github/workflows/ci.yml` poganja `ruff`, `mypy`, `pytest` |

### 1.9 Odprte odločitve — niso koda in blokirajo poročilo, ne repozitorija

Poročilo ima tri mesta »MESTO ZA ODLOČITEV«: prag računskega časa X (§6.6) ter konkretne pragove
zadostnosti zaščite (§8.2). To so odločitve avtorja oziroma mentorice. Prav tako je odprto, kaj
pomeni »odstopanje statistik gibanja« iz M3.

---

## 2. Predlagano zaporedje — recenziraj, preden ga sprejmeš

Vodilo pri razvrščanju: **najprej tisto, kar odklene poglavje 7 poročila**, ker je to najbližji
rok, in šele nato širina iz zasnove. Vsak val je zaokrožena celica dela za eno vejo in en
zahtevek za združitev.

**Val 0 — dokumentacijski popravki (D1–D4, nekaj ur). [recenzija: opravljeno v tej veji.]**
Uskladi zastarele trditve, dodaj opozorilo o sintetični veji, vpiši pregledni zvezek v
`RUNNING.md`, shrani manjkajoči izhod celice v zvezku 02. Poceni in prepreči delo po
napačnem opisu. Nima odvisnosti.

**Val 1 — pogon eksperimentov. [recenzija: sestava spremenjena.]** Prvotni predlog
(M1 + O2 + O3, nato O1) je zamenjan, ker M1 kot samostojen korak registrira metrike brez
odjemalca (mrtvo ogrodje, kršitev pravila o navpičnih rezinah) in ker ima O3 predpogoj —
ločitev semen (glej popravek pri O3 zgoraj). Nova sestava, vsak korak svoj zahtevek za
združitev:

- **1a — izvedeno (`8fac2fb`)** — ločitev semena delitve od semena zagona v orkestratorju +
  velikost vzorca (O2): ključa `experiment.split_seed` in `dataset.max_users`, oba v
  razpršilnem ključu predpomnilnika, ter `trajguard run <config> --seed N`;
- **1b — izvedeno (`9005c2f`)** — tanka skripta za ponovitve: `trajguard repeat <config>
  --seeds …` v `experiments/repeat.py`, združevanje v povprečje in 95-odstotni interval
  zaupanja po Studentovi t čez ponovitve, zapis v `repetitions.csv` (ostanek O3);
- **1c — izvedeno (`4466008`)** — rekonstrukcija v zanki orkestratorja: teče nad vsako
  geo-ind vejo z `epsilon`/`unit_m` iz veje (napadalec pozna mehanizem, zasnova §6.3),
  poroča `hausdorff_m`, `dtw_m`, `mean_spatial_error_m` z bootstrap intervali;
- **1d — naslednji korak** — `poi_inference` v zanko orkestratorja: potrebuje preusmeritev
  čistih GPS bazenov (`clean_by_id` namesto `matched`) in prenos svojih metrik (razdalja
  dom/delo v metrih, delež lokaliziranih uporabnikov) v `metrics.csv`; brez znanih blokad;
- **1e** — `membership_inference` v zanko orkestratorja: največji od treh, ker konfiguracija
  danes sploh nima razdelka za generatorje (`RunConfig`, `orchestrator.py`); prinese svoji
  metriki AUC in TPR pri nizkem FPR iz `evaluation/roc.py`; zgled priprave je obstoječi
  samostojni pogon `experiments/rnldp_eval.py`.

Šele ko to stoji, je razdelek 7.1 izvedljiv iz ene konfiguracije. Val se ujema z mejnikom S4.

**Val 2 — zajem rezultatov in slike (O4, O5, O6).** Preslikava na shemo `Rezultati_predloga`,
merjenje časa in pomnilnika, štirje načrtovani grafi. Brez tega se rezultati prepisujejo ročno,
kar je pri petih ponovitvah krat šest vrednosti ε krat pet stopenj predznanja vir napak.
**[recenzija]** Blokiran, dokler shema `Rezultati_predloga` ni na voljo (datoteki
`IZV_nacrt_eksperimentov.xlsx` in `IZV_porocilo.docx` nista v repozitoriju); gradi na
obstoječem `reporting/report.py`, ne od začetka.

**Val 3 — dopolnitve znotraj obstoječih štirih scenarijev (M2, A3, A4).** Top-k POI skupaj z
`as_poi_visits()` odklene razdelek 7.5; rekonstrukcija z omejitvijo omrežja je vsebinsko najbolj
zanimiva za članek, ker je primerjava »z omrežjem proti brez omrežja« empirični argument za
omrežno zavednost. **[recenzija]** M2 ima podatkovni predpogoj: v repozitoriju ni nobenega vira
točk interesa, testi pa ne smejo na omrežje — potreben je fixture sloj POI. A4 blokiran na
odločitvi avtorja (definicija »poznanega vzorca«); A3 nima blokad.

**Val 4 — širina mehanizmov (1.3) in LDPTrace (1.4).** Mehanizme dodajaj po naraščajoči
zahtevnosti: prostorsko zaokroževanje in časovno redčenje sta skoraj trivialna in takoj dodata
točke na krivuljo kompromisa; sledita Gaussov šum in točkovni LDP; segmentna perturbacija je
zadnja, ker je najbližja RN-LDP-Synth in zato najbolj koristna kot primerjava. **LDPTrace
obravnavaj prednostno znotraj tega vala**, ker brez njega razdelek 7.3 nima primerjave iz
literature. **[recenzija]** Točkovni LDP in LDPTrace gradita na obstoječih gradnikih v
`privacy/ldp.py` — če postane razdelek 7.3 časovno kritičen, se LDPTrace lahko izvleče pred
preostanek vala.

**Val 5 — horizont B (A1, M4, M5, 1.5, 1.7).** Drugo leto; priključi se prek obstoječih
vmesnikov brez posegov v jedro. **[recenzija]** A2 je izločen iz tega vala — rešuje se s
popravkom poročila (glej razdelek 1.1), ne z implementacijo.

### Naslednji konkreten korak

**[recenzija — prvotni predlog M1 + O2 + O3 je umaknjen** iz razlogov, opisanih pri valu 1.]
Val 0 ter koraki 1a, 1b in 1c so izvedeni (glej oznake zgoraj). Naslednji je korak **1d**:
`poi_inference` v zanko orkestratorja, po zgledu razreza 1c — validacija konfiguracije v
`_attack_specs` (napad ima svoje parametre `dwell_s`, `radius_m`, ure, `tz_offset_h` in prag
`threshold_m` za delež lokaliziranih), ločena priprava vhodov (čisti GPS bazeni: cilj je
izdana veja, resnica surovi `clean_by_id`), prenos metrik iz `attribute_report` v
`MetricValue` vrstice — razrez: `experiments/orchestrator.py`, `tests/test_orchestrator.py`,
konfiguracija pod `config/experiments/` in `docs/RUNNING.md` — znotraj pravila o petih
datotekah.

---

## 3. Kaj sem pričakoval od recenzije — **opravljeno**

Ta razdelek je zgodovinski: vse štiri točke so bile izpolnjene 4. avgusta 2026, izidi so
vpisani v razdelka 1 in 2 z oznako **[recenzija]**. Ohranjen je zato, da je razvidno, kaj je
bilo naročeno. Za nadaljevanje dela glej razdelek 4.

Naročilo se je glasilo:

1. **Za vsako postavko iz razdelka 1:** potrjeno / ovrženo / popravljeno, z mestom v kodi, ki to
   dokazuje. Ovržene postavke naj se iz načrta izločijo, ne tiho preskočijo.
2. **Za zaporedje iz razdelka 2:** strinjanje ali protipredlog, s kratko utemeljitvijo. Zlasti
   presodi dvom pri O3 (ali ponovitve res sodijo v orkestrator) in pri A2 (ali ni ceneje
   popraviti poročila).
3. **Karkoli, kar sem spregledal** — vrzel, ki je v tem dokumentu ni, ali odvisnost med valovi,
   ki je nisem opazil.
4. **Predlog prvega zahtevka za združitev** z razrezom po datotekah, v načrtovalnem načinu.

Če se recenzija bistveno razlikuje od tega dokumenta, je pravilen izid **popravljen ta dokument**
v istem zahtevku za združitev, ne tiho odstopanje od njega.

---

## 4. Prompt za novo sejo

Besedilo spodaj je mišljeno za lepljenje v svežo sejo. Prvotni recenzijski prompt je opravil
svoje (recenzija je vpisana v ta dokument); spodnja različica nadaljuje izvedbo. Če se izkaže
za koristnega trajno, sodi v `docs/PROMPTS.md`.

```
Preberi CLAUDE.md in docs/HANDOFF.md.

HANDOFF je recenziran in delno izveden načrt: val 0 ter koraki 1a, 1b in 1c so
končani na veji claude/handoff-document-review-2fnmdo (seznam commitov je v
razdelku 0). Ločena semena (experiment.split_seed), velikost vzorca
(dataset.max_users), ponovitve (trajguard repeat) in rekonstrukcija v
orkestratorju že obstajajo — ne implementiraj jih znova; prepričaj se v kodi.

Tvoja naloga je korak 1d: priključi poi_inference v zanko orkestratorja, po
zgledu koraka 1c (glej _reconstruction_values v experiments/orchestrator.py).
Zaporedje in razrez sta bila potrjena v recenziji, zato
načrtovalni način ni potreben; če med izvedbo naletiš na odločitev, ki je
HANDOFF ne pokriva, se ustavi in vprašaj.

Vsebina koraka 1d:
- validacija v _attack_specs: napad ima svoje parametre (dwell_s, radius_m,
  home_hours, work_hours, tz_offset_h) in prag threshold_m za delež
  lokaliziranih uporabnikov; reid-style ključa known_points/distance zavrni;
- priprava vhodov: cilj je izdana (zaščitena) veja kot čisti GPS bazen
  (pool.clean_by_id), resnica surovi clean_by_id; ujemanje je po user_id,
  ne po poteh, ujetih na ceste;
- metrike družine iz attribute_report (home/work_error_m, home/work_localised)
  z bootstrap intervali v MetricValue vrstice — v metrics.csv, run.json in
  s tem samodejno v trajguard repeat;
- konfiguracija pod config/experiments/ in razdelek v docs/RUNNING.md s
  pričakovanim izidom.

Pazi na dve pasti iz kode: (1) geo-ind veja z močnim šumom lahko pusti prazen
re-matched bazen, a poi_inference tega ne potrebuje — bere clean_by_id, ki hrani
celotno izdajo; (2) identitetna veja (mechanism none) vrne surove točke, zato je
njen rezultat sanity vrednost blizu ničelne napake, ne prava zaščita — v testu
to izkoristi. Fixture podatki imajo kratke poti; parametre napada (dwell_s,
radius_m) v testni konfiguraciji prilagodi, da nastane vsaj en stay-point —
zgled je tests/test_attribute.py.

Commitaj na isto vejo (claude/handoff-document-review-2fnmdo) in ob koncu
posodobi oznako stanja v docs/HANDOFF.md (razdelka 0 in 2).

Velja definicija dokončanosti iz CLAUDE.md: ruff check in mypy čista, test na
fixturih, in dokaz z natančnim ukazom ter njegovim izpisom. Ne trdi, da deluje —
pokaži. Če bi se korak dotaknil več kot ~5 datotek, predlagaj razrez namesto
da ga izvedeš naenkrat.
```

Za korak **1e** (`membership_inference`) prompt namenoma še ni napisan: pred njim je treba
odločiti, kako konfiguracija sploh opiše generatorje (`synthetic_generators` v YAML), kar je
oblikovna odločitev in ne mehanska priključitev. Napiši ga takrat, ko bo 1d končan.
