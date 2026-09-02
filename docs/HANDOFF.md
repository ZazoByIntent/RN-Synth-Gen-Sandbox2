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
(`9005c2f`), korak 1c — rekonstrukcija v zanki orkestratorja (`4466008`), korak 1d —
`poi_inference` v zanki orkestratorja (`c24cb48`), korak 1e — `membership_inference` in
razdelek `synthetic_generators` v orkestratorju (`0608755`, `9388cc8`). S tem so O1, O2 in O3
zaprti in **val 1 je zaključen**: vsi štirje scenariji tečejo iz ene konfiguracije. Shema
`Rezultati_predloga` je dogovorjena in zapisana v `docs/REZULTATI_SHEMA.md` (5. avgust 2026);
**O4 iz vala 2 je izveden** (`0433079`, `6bfb35b`): vsak zagon zapiše `results.csv` po shemi,
`trajguard report` zlepi `reports/results_master.csv`. **O5 in O6 sta izvedena 5. avgusta
2026** (O5: `3c59167`, `b5fdf27`; O6: `34d5416`): vodilna metrika po družini vrti
`matrix.csv` in grafe kompromisa, štirje načrtovani grafi se rišejo iz enotne tabele,
pomnilniška špica se meri v stolpec `peak_memory_mb` — podrobnosti v bloku **[izvedba]**
pri valu 2. Avtor je še isti dan določil prag X = **300 sekund na en zagon napada** in
pravila za krčenje obsega so napisana (`834321f`): protokol v `docs/RUNNING.md` §7.3,
prekoračitve orkestrator označi v `run.json` — **val 2 je s tem v celoti zaključen**.
Naslednje delo je A3 iz vala 3 ali sistematični parametrski preizkusi (mejnik S4). Kjer se je med izvedbo izkazalo drugače, kot napoveduje
besedilo spodaj, je popravek vpisan na mestu in označen z **[izvedba]** (po istem vzorcu
kot **[recenzija]**).

**[izvedba, 15. avgust 2026] — analitična plast za mejnik S4.** Nov modul
`src/trajguard/reporting/results_io.py` bere enotno tabelo (`results.csv` /
`results_master.csv`) nazaj v `ResultRow` vrstice in združuje ponovitve čez semena
(povprečje + Studentov t interval; nikoli pomešan z bootstrap intervalom znotraj zagona);
nov zvezek `notebooks/03_s4_sweep.ipynb` nad tem riše štiri načrtovane grafe čez ponovitve
in pregleduje prekoračitve 300 s proračuna (`docs/RUNNING.md` §3.2). **Glava stolpcev
`results.csv` je s tem vmesnik s štirimi odjemalci — pred kakršnokoli spremembo sheme
preberi opozorilo v `docs/REZULTATI_SHEMA.md` (razdelek »Odjemalci sheme«).** Ob izvedbi
odkrita robna vrzel, ki ostaja odprta: `load_results` v `reporting/report.py` išče
`run.json` samo neposredno pod `results/<exp>/`, zato `trajguard report` pade, kadar so v
`results/` sami ponovitveni zagoni (`seed<N>/` podmape); zvezek to obide, ker glavno
tabelo zna zlepiti sam prek `merge_results_tables`.

**[izvedba, 15.–16. avgust 2026] — prvi zagon kampanje S4 na pravem Geolife.** Kampanja je
prvič tekla na resničnih podatkih (ne na fixturih) pri najnižji stopnji lestvice vzorcev,
`dataset.max_users: 20`. Celotna pot deluje od konca do konca in analitična plast iz bloka
zgoraj se je izkazala za uporabno, hkrati pa je zagon razkril **štiri nove vrzeli in eno
opažanje**. **Te odprte točke je treba urediti, preden kampanja napreduje na višjo stopnjo
lestvice vzorcev in preden gre katerakoli številka v poročilo** — prvi zagon je torej urejen
in delno uspešen, ne pa zaključen. Vse skupaj je
zapisano v novem razdelku **1.10**; tam so tudi natančne izmerjene vrednosti in mesta v
kodi. Na kratko: iz podatkov po ujemanju na ceste ostane premalo materiala (razdelek 1.10,
S4-1), zato napad na članstvo meri na osemnajstih kandidatih in ne pove ničesar (S4-2);
napad na članstvo proti `rn_ldp_synth` presega 300-sekundni proračun po sami zgradbi
mehanizma in lestvica krčenja iz `docs/RUNNING.md` §7.3 tega ne reši (S4-3); robna vrzel
`trajguard report` iz bloka zgoraj se je v resnični kampanji pokazala kot blokada
poročanja, ne kot robni primer (S4-4). **Delo na teh točkah je bilo namenoma odloženo v
ločeno sejo** — ta blok in razdelek 1.10 sta zapis stanja, ne načrt izvedbe.

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
  priskrbi (ali se zapiše v `docs/`). **[izvedba, 5. avgust 2026]** Pogoj je izpolnjen: shema
  je dogovorjena z avtorjem in zapisana v `docs/REZULTATI_SHEMA.md` (ena ploska tabela, osi
  vrtenja kot namenski stolpci, statistika veje in časi kot stolpci, vrstice po semenih) —
  val 2 ni več blokiran.
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

**[izvedba, 4. avgust 2026]** O1 je zaprt: vse štiri družine so v zanki orkestratorja
(`_ORCHESTRATOR_ATTACKS` v `orchestrator.py`). Vzorec priključitve je pri vseh treh novih
družinah enak — vsaka prinese svoje metrike prek svoje poročevalske funkcije v vrstice
`MetricValue`, torej v `metrics.csv`, `run.json` in samodejno v `trajguard repeat`. Vodilna
metrika iz opombe zgoraj pa ostaja trdo kodirana: `matrix.csv` in graf kompromisa še naprej
vrtita samo `top1_acc` reidentifikacije, nove družine tja niso vključene. »Vodilna metrika po
družini« torej ni bila del vala 1 in sodi v val 2 (poročanje).

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

**[izvedba, 5. avgust 2026]** Prag X je določen: **300 sekund na en zagon napada**. Pravila
za krčenje obsega so napisana (`834321f`) — protokol z lestvijo krčenja v `docs/RUNNING.md`
§7.3, samodejna oznaka prekoračitev v `run.json` (blok `over_budget`, ključ
`metrics.attack_time_budget_s`). Odprti ostajata odločitvi o pragovih zadostnosti zaščite
(§8.2) in o pomenu M3.

### 1.10 Prvi zagon kampanje S4 na pravem Geolife (15.–16. avgust 2026)

Ta razdelek je **zapis stanja po prvem zagonu na resničnih podatkih**, ne načrt. Ničesar od
spodnjega nisem popravljal: naloga te seje je bila pognati kampanjo in ugotovitve zapisati,
izvedbo in načrt pa se dogovori v ločeni seji na podlagi tega besedila.

**Kaj je bilo pognano.** Dve novi konfiguraciji, ker `max_users` ni os, ki bi se razširila
sama iz mreže parametrov, in da originalni konfiguraciji za polni obseg ostaneta nedotaknjeni:
`config/experiments/geolife_geoind_reid_u20.yaml` (pet semen, 1–5) in
`config/experiments/geolife_synth_mia_u20.yaml` (tri semena, 1–3). Obe imata
`dataset.max_users: 20`, svoj `experiment.id` in `output_dir` ter `metrics.memory: false`
(pravilo R0 iz `docs/RUNNING.md` §7.3: merjenje pomnilniške špice podvoji čas napada, zato
bi ga primerjava s pragom 300 s morala izključiti; posledica je, da je stolpec
`peak_memory_mb` v tej kampanji prazen). Razlogi so vpisani kot komentarji v obeh datotekah,
kot zahteva pravilo R3 o sledljivosti. Zagoni so v `results/geolife_geoind_reid_u20/seed{1..5}/`
in `results/geolife_synth_mia_u20/seed{1..3}/`, glavna tabela v `reports/results_master.csv`,
slike v `reports/s4_figures/`, izvedeni zvezek je `notebooks/03_s4_sweep.ipynb`. Nič od tega
ni v gitu (mape so ignorirane); v delovnem drevesu sta ostali samo novi konfiguraciji in
izveden zvezek, brez commita.

**Časi za oceno naslednjih stopenj lestvice.** Prvi zagon geoind 811 s (hladen predpomnilnik,
večina na čiščenje in ujemanje), naslednji štirje po približno 105 s (topel predpomnilnik
bazena). Vsak zagon napada na članstvo približno 42 minut. Predpomnilnik bazena je vezan tudi
na `max_users`, zato bo prva stopnja pri 50 uporabnikih spet plačala celotno čiščenje in
ujemanje.

**S4-1 — po ujemanju na ceste ostane 2,8 odstotka podatkov.** Od 1607 očiščenih trajektorij
dvajsetih uporabnikov jih prag `map_matching.min_match_score: 0.6` prestane **45**, in te
pokrivajo samo **devet** uporabnikov (`n_matched`, `n_dropped` in `arms.*.n_gallery_users` v
`results/geolife_geoind_reid_u20/seed1/run.json`). Vse številke reidentifikacije so torej nad
galerijo devetih ljudi. Zakaj to ni presenečenje: Geolife vsebuje veliko hoje, kolesarjenja in
vožnje s podzemno železnico, ki ne sledijo voznemu omrežju, del sledi pa pade zunaj očrtnega
pravokotnika iz konfiguracije. Zakaj vseeno šteje kot vrzel: pri tako majhnem preživelem
bazenu nobena od štirih družin nima statistične teže, in ker odstotek preživetja ni odvisen od
`max_users`, se z višjimi stopnjami lestvice vzorcev **ne bo popravil sam**. Odločitev, ki je
odprta, je vsebinska in ne tehnična — kaj je populacija, ki jo poročilo meri (samo vozne sledi,
ali tudi ostale načine prevoza), in šele iz tega sledi, ali se premakne prag ujemanja, tip
cestnega omrežja pri gradnji zemljevida ali obseg podatkovne množice.

**S4-2 — napad na članstvo meri na osemnajstih kandidatih, od tega treh nečlanih.** V
`results/geolife_synth_mia_u20/seed1/results.csv` so `n_pool = 18`, `n_members = 15`,
`n_nonmembers = 3`. Posledici sta dve in obe sta resni: ploščina pod krivuljo (AUC) nad tremi
negativnimi primeri skoraj ne nosi informacije, `tpr@fpr=0.001` pa **po definiciji ne more**
razločiti stopnje lažnih alarmov pod 1/3, zato je izmerjena vrednost 0,067 artefakt
zaokroževanja in ne meritev. To se vidi tudi v intervalih čez semena: spodnja meja pri ε = 8
je −0,099, kar je znak, da Studentov t interval nad tremi ponovitvami pri teh velikostih ni
smiseln. Vzrok je sestavljen — S4-1 zmanjša bazen na 45 poti, razrez `train: 0.5, test: 0.2`
pa iz tega naredi 15 članov proti 3 nečlanom. Odprto je torej, ali je to zgolj posledica S4-1
in izgine z večjim bazenom, ali pa sestava kandidatnega nabora pri majhnih bazenih potrebuje
svoje pravilo; presoditi je treba tudi, ali sta pri tako majhnem številu nečlanov obe
operativni točki iz `fprs` sploh smiselni.

**S4-3 — napad na članstvo proti `rn_ldp_synth` presega proračun po zgradbi mehanizma, ne po
velikosti vzorca.** Vseh devet klicev (tri veje ε krat tri semena) je trajalo med **755 in 866
sekundami** proti pragu 300 s, medtem ko je vsak drug napad v kampanji pod 11 sekundami — to
je razmerje okoli 1 : 1000 in je najbolj vidno na sliki `reports/s4_figures/runtime.png`.
Izmerjen vzrok: konstruktor `RNLDPSynthGenerator` (`src/trajguard/synthesis/rn_ldp_synth.py`,
metoda `_calibrate_inflation`, klicana iz `__init__`) umeri faktor napihnjenosti dekodiranja s
približno 300 Dijkstrovimi iskanji čez celoten graf, kar na zgrajenem pekinškem omrežju
(35.764 vozlišč, 80.652 povezav) traja **65 sekund na en generator**; napad zgradi
`n_shadow + 1 = 17` generatorjev na vejo, ker `_train_shadows` kliče `shadow_factory` za vsak
senčni model posebej. **Bistveno za naslednjo sejo:** lestvica krčenja obsega iz
`docs/RUNNING.md` §7.3 tega primera ne reši, kar je prvi znani protiprimer njenim pravilom.
Korak 1 (nižji `max_users`) na to ceno ne vpliva niti za sekundo, ker je umerjanje odvisno
samo od zemljevida in konfiguracije, ne od podatkov; korak 2 (prepolovitev `n_shadow` na 8) bi
dal še vedno okoli 400 sekund, torej še vedno čez prag; korak 3 bi pomenil izločitev vseh vej
`rn_ldp_synth` iz kampanje, kar bi odstranilo prav tisto, kar naj bi kampanja izmerila.
Odprto je oboje: kaj storiti s samim mehanizmom (podatek, da je umerjanje odvisno izključno od
javnih struktur, je pri tem ključen, ker pomeni, da se med generatorji istega zemljevida
podvaja) in ali pravila §7.3 potrebujejo še eno vejo za primere, kjer strošek ni v podatkih.

**S4-4 — `trajguard report` na tej kampanji pade; iz robne vrzeli je postala blokada.** Vrzel
je bila zabeležena že 15. avgusta v razdelku 0 kot robni primer: `load_results` v
`src/trajguard/reporting/report.py` išče `run.json` samo neposredno pod `results/<exp>/`, ne
pa v podmapah `seed<N>/`. V resnični kampanji so **vsi** zagoni ponovitveni, zato ukaz pade z
`FileNotFoundError` in nedosegljivi ostanejo `report.md`, `risk_matrix.csv` ter
`metrics_long.csv`/`.parquet` — torej celoten izhod razdelka §8 iz `docs/RUNNING.md`. Zvezek
`03_s4_sweep.ipynb` to obide, ker `merge_results_tables` išče rekurzivno (`rglob`), tako da je
`reports/results_master.csv` pravilna in slike nastanejo; manjka pa vse ostalo. Popravka
nisem izvedel, ker razdelek 0 tega dokumenta zanj izrecno predvideva odločitev avtorja.

**S4-5 (opažanje, morda ne potrebuje kode).** Surova veja in identitetna veja `protected:none`
dasta v vseh petih semenih popolnoma enake vrednosti, zato je njun interval čez ponovitve
širine nič (`top1_acc` pri desetih znanih točkah je 0,500 z intervalom [0,500, 0,500]). To ni
napaka: seme zagona premakne samo šum mehanizma in izbor senčnih podmnožic, napadalčevih
enakomerno razporejenih znanih točk (`_evenly_spaced` v `attacks/reidentification.py`) pa ne,
zato pri vejah brez šuma ponovitve nimajo česa premakniti. Vredno je zapisati zato, ker bo
tabela v poročilu po §7.1 pri teh dveh vrsticah kazala interval brez razpona in bo to videti
kot napaka, če ni pojasnjeno.

**Kaj kampanja kljub temu pokaže.** Da ne bo videti kot sam neuspeh: cevovod od konca do konca
teče, vzorci pa so vsebinsko pravilni. Rekonstrukcija pada s šumom (povprečna prostorska napaka
657 → 92 → 16 metrov pri ε = 0,1 → 1 → 10) in vse tri vrednosti so pod povprečnim premikom šuma
`2·unit_m/ε`, kar je pričakovano. Sklepanje o domu in službi vrne pri identitetni veji točno
ničelno napako in stoodstotno lokalizacijo, kar je pravi zdravstveni znak merilne verige.
Reidentifikacija pade s 0,500 na nezaščitenih na 0,277 pri ε = 10 in na nič pri ε = 1 in
ε = 0,1, kjer šum uniči vse poti pri ponovnem ujemanju. Pri napadu na članstvo `markov` doseže
AUC točno 1,000 v vseh treh semenih — strop memorizacije stoji tako, kot mora — `rn_ldp_synth`
pa je pri 0,585 / 0,556 / 0,578 za ε = 0,5 / 2 / 8, torej blizu naključnega ugibanja; te tri
vrednosti so ob upoštevanju S4-2 uporabne kvečjemu kot znak, da merilna veriga teče, ne kot
rezultat.

**[izvedba, 17. avgust 2026]** Vrzeli S4-1 do S4-4 so obravnavane: odločitve, razrez na tri
PR-je in njihova izvedba so v `docs/HANDOFF_S4_POPRAVKI.md` (razdelka 1 in 3), opažanje S4-5
je pokrito z odstavkom v `docs/RUNNING.md` §7.1. Validacijski pogon pri `max_users: 20` z
istimi konfiguracijami in semeni kot zgoraj je **uspel — vseh pet meril je izpolnjenih**
(nečlani 15 ≥ 11, galerija 16/20 ≥ 15/20, `rn_ldp_synth` ~20 s < 300 s, `trajguard report`
izdela poročilo z eno vrstico na roko, varovalo `tpr@fpr` deluje). Izmerjene vrednosti in
opombe za načrtovanje vzpona so v `docs/HANDOFF_S4_POPRAVKI.md`, razdelek 4.

### 1.11 Prva izmeritev stopnje 50 (17. avgust 2026)

Prvi pogon stopnje `max_users: 50` po lestvici iz `docs/HANDOFF_S4_POPRAVKI.md` §3
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
- **1d — izvedeno (`c24cb48`)** — `poi_inference` v zanki orkestratorja: čisti GPS bazeni
  (`clean_by_id` namesto `matched`; cilj je izdana veja, resnica surova, ujemanje po
  `user_id`) in prenos njegovih metrik (razdalja dom/delo v metrih, delež lokaliziranih
  uporabnikov) z bootstrap intervali v `metrics.csv`;
- **1e — izvedeno (`0608755`, `9388cc8`)** — `membership_inference` v zanki orkestratorja:
  nov razdelek `synthetic_generators` (mreža parametrov kot pri mehanizmih), strogi LiRA
  protokol po odločitvi avtorja (senčni modeli: razrez shadow + poizvedovane kandidatne
  poti; člani iz train, ne-člani iz test), senčni modeli istega razreda po zgledu
  `rnldp_eval`; metriki AUC in TPR pri nizkem FPR kot točkovni vrednosti brez intervala
  znotraj zagona (interval čez ponovitve da `trajguard repeat`).

Šele ko to stoji, je razdelek 7.1 izvedljiv iz ene konfiguracije. Val se ujema z mejnikom S4.

**[izvedba, 4. avgust 2026] — popravki in spoznanja iz izvedbe korakov 1d in 1e:**

- **1e je bil cenejši od napovedi »največji od treh«: posega v `attacks/membership.py` ni
  bilo.** Strogi protokol (senčni modeli napadalca ne smejo videti učne množice) se izrazi
  že s sestavo senčnega bazena v orkestratorju: bazen je razrez shadow plus kandidatne poti,
  ki jih napadalec upravičeno pozna, ker po njih sprašuje; enakomerno podvzorčenje vsakega
  kandidata samodejno uvrsti v približno polovico senčnih modelov (skupina IN). Sestavo
  preverja enotski test `test_mia_pool_builds_the_strict_shadow_protocol`.
- **Odločitve, sprejete v pogovoru z avtorjem (4. avgust 2026), ki jih to besedilo prej ni
  določalo:** strogi protokol namesto zgleda iz `rnldp_eval` (tam senčni modeli vidijo del
  učne množice, kar napadalca precenjuje); v konfiguraciji oba generatorja (markov in
  rn_ldp_synth); AUC in TPR pri nizkem FPR kot točkovni vrednosti brez intervala znotraj
  zagona — interval čez ponovitve da `trajguard repeat`; točke FPR nastavljive s ključem
  `fprs` (privzeto 0.001 in 0.01).
- **Tehnične podrobnosti, na katere naj računa nadaljnje delo:** konstruktorji generatorjev
  se razlikujejo, zato orkestrator omrežje in seme vbrizga glede na podpis konstruktorja
  (`_generator_ctor`); senčni modeli so istega razreda s parametri veje in semeni
  `seed + 1000 + k`; parametri generatorjev se — drugače kot pri mehanizmih — ne
  pretvarjajo v decimalke, ker gredo surovi v konstruktorje (Markov `order` mora ostati
  celo število), predpomnilniški ključ pa od njih ne odvisi.
- **1e namenoma ne generira sintetičnih izdaj in ne računa utility metrik nad sintezo:**
  LiRA sprašuje naučeni model po verjetnosti poti (`sequence_log_prob`), ne njegovih
  vzorcev. Predpomnjenje sintetičnih izdaj (`data/synthetic/`) zato ostaja odprto za prvi
  korak, ki ga bo zares potreboval (npr. utility nad sintezo za razdelek 7.3 poročila;
  samostojni `rnldp_eval` to zaenkrat pokriva na ravni fixture podatkov).
- **Testna omejitev:** fixture populacija ima 2 uporabnika, zato v end-to-end testih
  orkestratorja razrez shadow ostane prazen (1 uporabnik train, 1 test) in senčni bazen
  sestavljajo samo kandidati; polni protokol z bazo pokriva zgornji enotski test. Za
  end-to-end test s polno bazo bi bila potrebna večja fixture populacija (3+ uporabniki).
- **1d je potekel po napovedi;** edina širitev obsega je bil popravek zastarele trditve v
  dokumentacijskem nizu razreda v `attacks/attribute.py` (šesta datoteka), ki je trdila,
  da napad ni priključen v orkestrator.

**Val 2 — zajem rezultatov in slike (O4, O5, O6).** Preslikava na shemo `Rezultati_predloga`,
merjenje časa in pomnilnika, štirje načrtovani grafi. Brez tega se rezultati prepisujejo ročno,
kar je pri petih ponovitvah krat šest vrednosti ε krat pet stopenj predznanja vir napak.
**[recenzija]** Blokiran, dokler shema `Rezultati_predloga` ni na voljo (datoteki
`IZV_nacrt_eksperimentov.xlsx` in `IZV_porocilo.docx` nista v repozitoriju); gradi na
obstoječem `reporting/report.py`, ne od začetka. **[izvedba, 5. avgust 2026]** Shema je
zdaj v `docs/REZULTATI_SHEMA.md` — blokada je odpravljena. Sem sodi tudi vodilna metrika po
družini iz opombe pri 1.6.

**[izvedba, 5. avgust 2026] — O4 izveden (`0433079`, `6bfb35b`). Kaj in zakaj:**

- **`results.csv` ob vsakem zagonu** po shemi iz `docs/REZULTATI_SHEMA.md`. Shema kot koda
  živi v novem modulu `reporting/results_schema.py` (`RESULTS_COLUMNS`, `ResultRow`,
  `write_results_csv`); vrstice se zapisujejo imensko, ne pozicijsko, zato stolpec ne more
  pristati na napačnem mestu. Zakaj: ročno prepisovanje rezultatov je pri 5 ponovitvah × 6 ε
  × 5 stopenj predznanja vir napak, ki ga ta tabela odpravi.
- **Stolpci se polnijo pri izvoru** iz strukturiranih specifikacij (nova `_arm_infos` +
  družinske funkcije v orkestratorju vračajo `ResultRow`), nikoli z razčlenjevanjem oznak
  nazaj. Ob tem se je začelo zapisovati troje, kar se je prej izmerilo in zavrglo ali sploh
  ni obstajalo: `attack_runtime_s` ob vsaki vrstici napada, ε/`unit_m` veje tudi kadar ju
  YAML ni izrecno navedel (bereta se z instance mehanizma), ter MIA števca
  `n_members`/`n_nonmembers` (brez njih se `tpr@fpr` ne da brati).
- **En blok porekla** (`exp_id`, `config_hash`, `git_commit`, obe semeni, `max_users`,
  časovni žig) se deli med `run.json` in `results.csv`. Zakaj: dva izvora iste resnice bi
  se lahko razšla.
- **`reports/results_master.csv`**: `trajguard report` čisto zlepi vse zagonske tabele
  (tudi ponovitve pod `seed<N>/`); tabela s tujo glavo stolpcev je glasna napaka, ne tiho
  zamaknjeni stolpci. Obstoječi izhodi (`metrics.csv`, `matrix.csv`, `run.json`,
  `repetitions.csv`) so nespremenjeni, zato `trajguard repeat` in stari odjemalci delajo
  naprej.
- **Mimogrede odkrita in odpravljena latentna napaka:** razčlenjevalnik `result_id` v
  `report.py` je zahteval pripono `:k<N>`, zato bi se `trajguard report` sesul na vsakem
  zagonu z rekonstrukcijo, POI ali MIA (družine iz 1c–1e). Popravljeno z regresijskim
  testom; napaka je hkrati konkreten dokaz, zakaj shema prepoveduje razčlenjevanje nizov.
- **Testi skladnosti s shemo:** `tests/test_results_schema.py` pribije vrstni red stolpcev,
  pravila praznih celic in — prek testa sinhronizacije z dokumentom — da je vsak stolpec,
  ki ga koda zapisuje, imenovan v `docs/REZULTATI_SHEMA.md`; end-to-end testi preverjajo
  tabelo na fixture zagonih za vse družine ter enakost glavne tabele z zagonsko.
- **Ni del tega koraka:** O5 (štirje grafi in vodilna metrika po družini v `matrix.csv` /
  grafu kompromisa), O6 (pomnilniška špica, pravila krčenja obsega) ter neobvezni dopolnitvi
  `.parquet` zrcalo glavne tabele in stolpca porekla v `repetitions.csv`.

**[izvedba, 5. avgust 2026] — O5 izveden (`3c59167`, `b5fdf27`), O6 izveden (`34d5416`).
Kaj in zakaj:**

- **Vodilna metrika po družini (`3c59167`).** Preslikava družina → vodilna metrika je zdaj
  ena sama: javna `HEADLINE_PREFERENCE` v novem modulu `reporting/plots.py`, ki jo uvažata
  tako `report.py` kot orkestrator — poročilo in zagon se ne moreta razhajati. `matrix.csv`
  je postal rezina matrike tveganj za en zagon: vrstica na vejo, stolpec na družino
  (`<družina>:<vodilna metrika>`, reidentifikacija pri največjem predznanju); pogled po
  `known_points` ostaja v `results.csv` in na grafu `by_knowledge`. Graf kompromisa se riše
  za vsako družino z utility vrednostmi na vejah — reidentifikacija obdrži ime
  `tradeoff.png`, druge družine dobijo `tradeoff_<družina>.png`; sklepanje o članstvu na ta
  graf ne more, ker se utility meri samo nad protected vejami (sintetične veje nimajo osi x).
  Validacijska zahteva po `top1_acc` je odpadla; nadomesti jo družinski izbor z rezervo
  (prednostna metrika, sicer prva prisotna po abecedi).
- **Štirje grafi (`b5fdf27`).** `by_epsilon_<družina>.png` (vodilna metrika glede na ε,
  logaritemska os, črta na vejo in pri reidentifikaciji na stopnjo predznanja),
  `by_knowledge_<družina>.png` (glede na `known_points`, črta na vejo),
  `mechanisms_<družina>.png` (vodoravni stolpci z bootstrap intervali, primerjava vej) in
  `runtime.png` (čas na zagon napada, logaritemska os, barva po družini). Vse funkcije v
  `reporting/plots.py` berejo vrstice enotne tabele — iste `ResultRow`, ki gredo v
  `results.csv` — brez razčlenjevanja `result_id`. Vklop v `reporting.plots`; graf brez
  ustreznih vrstic ne zapiše datoteke, graf, katerega os za dano konfiguracijo sploh ne more
  obstajati, je zavrnjen že ob branju konfiguracije. Vzorčna konfiguracija
  `geolife_geoind_reid.yaml` vklaplja vseh pet grafov.
- **O6 — pomnilniška špica (`34d5416`).** Orkestrator ovije vsak klic `attack.run` s
  `tracemalloc` (standardna knjižnica, brez nove odvisnosti) in zapiše vršno porabo novih
  alokacij v stolpec `peak_memory_mb`; opis stolpca je v `docs/REZULTATI_SHEMA.md` v istem
  commitu. Past za nadaljnje delo: sledenje približno podvoji čas napada, zato
  `attack_runtime_s` ob vklopljenem merjenju nosi pribitek — ključ `metrics.memory: false`
  merjenje izklopi (privzeto je vklopljeno). Testna zbirka ga v skupni fixture konfiguraciji
  izklaplja, da ostane hitra; privzeto (vklopljeno) pot pokriva namenski test.
- **Namenoma ni narejeno:** pravila za krčenje obsega (drugi del O6) — takrat blokirana
  na odločitvi o pragu X; **[izvedba, isti dan]** avtor je prag določil (300 s na zagon
  napada) in pravila so napisana (`834321f`): deterministična lestev v `docs/RUNNING.md`
  §7.3 (`max_users` po lestvi §6.4 → družinski gumb → zabeležena izločitev), orkestrator
  prekoračitve označi v `run.json` in z opozorilom na konzoli; samodejnega krčenja
  namenoma ni, ker bi tiho spreminjalo poskus. Dalje ni narejeno: risanje istih grafov v
  `trajguard report` čez več zagonov ali čez ponovitve (`results_master.csv`,
  `repetitions.csv`) — funkcije so pisane nad vrsticami enotne tabele, zato je priključitev
  poceni, ko jo bo kdo potreboval; posplošitev report-level grafov kompromisa (`report.py`
  še naprej riše reidentifikacijskega na zagon); shranjeni izhod zvezka 02 kaže staro
  obliko `matrix.csv` (zvezkov nič ne poganja — znano neskladje D5).

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
Val 0, celoten val 1 (koraki 1a–1e) in **celoten val 2** (O4, O5, O6 vključno s pravili
krčenja pri pragu X = 300 s) so izvedeni (glej oznake zgoraj): razdelek 7.1 poročila je
izvedljiv iz ene konfiguracije, rezultati se samodejno zapisujejo v enotno tabelo po
`docs/REZULTATI_SHEMA.md` (s časom in pomnilniško špico na napad), en zagon nariše vseh
pet grafov (kompromis po družinah ter glede na ε, predznanje, mehanizme in računski čas),
prekoračitve časovnega proračuna pa so označene v `run.json` s protokolom krčenja v
`docs/RUNNING.md` §7.3. Naslednje delo brez blokad je A3 iz vala 3 (rekonstrukcija z
omejitvijo cestnega omrežja) ali sistematični parametrski preizkusi (mejnik S4), za
katere je zajem rezultatov zdaj pripravljen. Izbira je avtorjeva.

**[izvedba, 15.–16. avgust 2026]** Kampanja S4 je bila prvič pognana na pravem Geolife pri
`max_users: 20` (podrobnosti in izmerjene vrednosti v razdelku **1.10**). S tem se naslednji
konkreten korak premakne: pred širjenjem kampanje na višje stopnje lestvice vzorcev je treba
obravnavati štiri vrzeli, ki jih je zagon razkril (S4-1 do S4-4). Med njimi je ena vsebinska
odločitev avtorja, ki blokira vse ostalo — kaj je populacija, ki jo poročilo meri (S4-1) —
ker sta S4-2 in deloma tudi statistična teža celotne kampanje njena posledica. S4-3 in S4-4
sta neodvisna od te odločitve in ju je mogoče obravnavati vzporedno. **Načrt in razrez po
zahtevkih za združitev nista določena**; nastaneta v seji, ki se te skupine loti, po pravilih
iz razdelka »Vezni pogoji« (načrtovalni način, razrez pri več kot približno petih datotekah).

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

**[izvedba, 16. avgust 2026] — prompt spodaj je zastarel.** Nanaša se na korak 1d, ki je
opravljen (`c24cb48`), in ga puščam samo kot zgled oblike. Seja, ki se loti skupine S4-1 do
S4-4, naj izhaja iz razdelka **1.10** in iz bloka pri »Naslednji konkreten korak«. Novega
prompta namenoma ne pišem: naloga te seje je bila kampanjo pognati in ugotovitve zapisati,
naročilo za nadaljevanje pa oblikuje avtor.

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

Korak **1e** je bil izveden brez posebnega prompta: oblikovne odločitve (oblika razdelka
`synthetic_generators`, strogi LiRA protokol, metrike brez intervala znotraj zagona) je avtor
sprejel v pogovoru 4. avgusta 2026 in so povzete v razdelkih 0 in 2. Prompt za morebitni
naslednji korak napiši ob izbiri med valom 2 in valom 3.
