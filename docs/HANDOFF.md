# Predaja dela: vrzeli med dokumentacijo, poročilom IZV in kodo

**Nastalo:** 4. avgust 2026 · **Osnovano na commitu:** `aa5eb86` · **Veja:** `claude/review-attack-scenarios-c6byzc`
**Viri:** `docs/Tehnicna_zasnova_eksperimentalno_okolje.md`, `docs/IMPLEMENTATION_PLAN.md`,
`docs/ARCHITECTURE.md`, koda pod `src/trajguard/`, zvezek `notebooks/02_pipeline_walkthrough.ipynb`
in poročilo `IZV_porocilo.docx` (delovni skelet, poglavja 1–3 izpolnjena).

---

## 0. Kako brati ta dokument — preberi preden karkoli spremeniš

**To je predlog, ne naročilo.** Nastal je v eni sami seji, iz ene same interpretacije poročila,
in ni bil recenziran. Naslednja seja naj ga obravnava kot **osnutek kolega, ki ga je treba
recenzirati**, ne kot potrjen načrt dela.

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

### 1.2 Metrike

| # | Vrzel | Zahteva | Preveri |
|---|---|---|---|
| M1 | TPR\@FPR, AUC, prostorska napaka, Hausdorff niso registrirane metrike | poročilo §7.3, §7.4 | `src/trajguard/evaluation/metrics.py:44` in `:58` — registrirani sta **samo** `top_k_accuracy` in `linkage_rate`; funkcije obstajajo v `evaluation/roc.py` in v poročevalskih funkcijah napadov, a jih iz YAML ni mogoče poimenovati |
| M2 | Točnost top-k POI | poročilo §7.5, §6.8 | ni je; `src/trajguard/representation/views.py:88` — `as_poi_visits()` sproži `NotImplementedError` |
| M3 | »Odstopanje statistik gibanja« | poročilo §7.5 | ni definirano niti v poročilu — **potrebna je odločitev, kaj to je** |
| M4 | Ujemanje segmentov (edge recall/precision) | zasnova §6.3 | ni implementirano |
| M5 | Balanced accuracy, F1, preciznost, priklic | zasnova §6.4 | vezano na A1 |

### 1.3 Zaščitni mehanizmi

Implementirana sta `none` in `geo_indistinguishability`. Zasnova §7 in poročilo §6.1
predvidevata še: prostorsko zaokroževanje, časovno redčenje, naivni Gaussov šum, točkovni LDP,
SquareWave, segmentno perturbacijo, k-anonimnost in kombinirane mehanizme.

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

**Val 0 — dokumentacijski popravki (D1–D3, nekaj ur).** Uskladi zastarele trditve, dodaj
opozorilo o sintetični veji, vpiši pregledni zvezek v `RUNNING.md`. Poceni in prepreči delo po
napačnem opisu. Nima odvisnosti.

**Val 1 — pogon eksperimentov (M1, O2, O3, nato O1).** Po vrsti: registriraj manjkajoče metrike
kot razrede `Metric`; dodaj velikost vzorca in seznam semen z združevanjem v povprečje in
interval zaupanja; nato priključi preostale tri napade v zanko orkestratorja, vsakega s svojo
pripravo vhodov. Šele ko to stoji, je razdelek 7.1 izvedljiv iz ene konfiguracije. Ta val se
ujema z mejnikom S4, ki je v `CLAUDE.md` že označen kot naslednji korak.
*Opozorilo o obsegu:* O1 se dotakne priprave vhodov za tri različne družine napadov in ga
verjetno ni mogoče spraviti v isti zahtevek za združitev kot M1/O2/O3 — predvidi razrez.

**Val 2 — zajem rezultatov in slike (O4, O5, O6).** Preslikava na shemo `Rezultati_predloga`,
merjenje časa in pomnilnika, štirje načrtovani grafi. Brez tega se rezultati prepisujejo ročno,
kar je pri petih ponovitvah krat šest vrednosti ε krat pet stopenj predznanja vir napak.

**Val 3 — dopolnitve znotraj obstoječih štirih scenarijev (M2, A3, A4).** Top-k POI skupaj z
`as_poi_visits()` odklene razdelek 7.5; rekonstrukcija z omejitvijo omrežja je vsebinsko najbolj
zanimiva za članek, ker je primerjava »z omrežjem proti brez omrežja« empirični argument za
omrežno zavednost.

**Val 4 — širina mehanizmov (1.3) in LDPTrace (1.4).** Mehanizme dodajaj po naraščajoči
zahtevnosti: prostorsko zaokroževanje in časovno redčenje sta skoraj trivialna in takoj dodata
točke na krivuljo kompromisa; sledita Gaussov šum in točkovni LDP; segmentna perturbacija je
zadnja, ker je najbližja RN-LDP-Synth in zato najbolj koristna kot primerjava. **LDPTrace
obravnavaj prednostno znotraj tega vala**, ker brez njega razdelek 7.3 nima primerjave iz
literature.

**Val 5 — horizont B (A1, A2, M4, M5, 1.5, 1.7).** Drugo leto; priključi se prek obstoječih
vmesnikov brez posegov v jedro.

### Predlagan prvi konkreten korak

Če iščeš en sam, jasno omejen zahtevek za združitev: **M1 + O2 + O3** — registracija metrik ter
velikost vzorca in ponovitve. Dotakne se `evaluation/metrics.py`, `evaluation/roc.py`,
`experiments/orchestrator.py` in dveh konfiguracij, torej ostane znotraj pravila o petih
datotekah, in odklene vse tabele v poglavju 7, ki potrebujejo stolpca »velikost vzorca« in
»95 % interval zaupanja«.

---

## 3. Kaj pričakujem od recenzije

Preden se karkoli implementira, naj naslednja seja predstavi:

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

Besedilo spodaj je mišljeno za lepljenje v svežo sejo. Če se izkaže za koristnega trajno, sodi v
`docs/PROMPTS.md`, kjer so zbrani prompti za posamezne faze.

```
Preberi CLAUDE.md in docs/HANDOFF.md.

HANDOFF je osnutek kolega iz prejšnje seje in NI potrjen načrt dela. Tvoja prva naloga
ni implementacija, ampak recenzija.

Naredi naslednje, v tem vrstnem redu:

1. Za vsako postavko v razdelku 1 dokumenta HANDOFF (A1–A4, M1–M5, O1–O6, D1–D5 in
   opisne razdelke 1.3, 1.4, 1.5, 1.7) preveri v kodi, ali trditev drži. Vsako označi
   kot potrjeno, ovrženo ali popravljeno in navedi mesto v kodi (datoteka:vrstica), ki
   to dokazuje. Ne zanašaj se na besedilo HANDOFF-a.

2. Posebej presodi dvoma, ki ju HANDOFF sam izpostavi:
   - O3: ali ponovitve eksperimenta res sodijo v orkestrator ali zadošča tanka skripta;
   - A2: ali je reidentifikacija nad sintetičnimi podatki sploh smiselna, ali je ceneje
     popraviti poročilo.

3. Povej, ali se strinjaš s predlaganim zaporedjem valov 0–5 v razdelku 2. Če ne,
   predlagaj drugačno in utemelji.

4. Navedi vse, kar je HANDOFF spregledal: vrzeli, ki jih ne omenja, ali odvisnosti med
   valovi.

5. Šele nato, v načrtovalnem načinu, predlagaj prvi zahtevek za združitev z razrezom po
   datotekah. Počakaj na mojo odobritev, preden karkoli spremeniš.

Velja definicija dokončanosti iz CLAUDE.md: ruff in mypy čista, test na fixturih, in
dokaz z natančnim ukazom in izpisom. Naloge, ki bi se dotaknile več kot ~5 datotek,
razdeli namesto da jih izvedeš naenkrat.
```
