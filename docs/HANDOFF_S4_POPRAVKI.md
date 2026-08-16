# Predaja: popravki po prvem pogonu kampanje S4

Ta dokument je **načrt popravkov** za štiri vrzeli in eno opažanje iz prvega pogona
kampanje S4 (`docs/HANDOFF.md` §1.10, S4-1 do S4-5). Nastal je 16. avgusta 2026 v
seji, v kateri je avtor sprejel spodnje odločitve; zapisane so skupaj s konteksom in
izmerjenimi dejstvi iz kode, da jih implementacijskim sejam ni treba znova izpeljevati.

Razmerje do drugih dokumentov: `docs/HANDOFF.md` §1.10 ostaja **zapis stanja** po
pogonu in se tu ne podvaja. Povratni sklic iz §1.10 na ta dokument doda kasnejša
seja; tega ne počni v PR-jih spodaj. Vsak PR pa **v istem PR-ju** posodobi
dokumentacijo, ki jo vsebinsko spremeni (`docs/RUNNING.md`, `docs/REZULTATI_SHEMA.md`,
statusna vrstica v `CLAUDE.md`, po potrebi konfiguracijski komentarji), po pravilu
sledljivosti iz `docs/RUNNING.md` §7.3 (R3).

---

## 1. Sprejete odločitve

### S4-1 — populacija poročila in prag ujemanja

**Odločitev.** Poročilo meri **vozne sledi**, definirane **operativno**: populacija so
sledi, ki se na vozno cestno omrežje ujamejo z oceno `match_score ≥ prag`. Poročilo ob
tem prikaže porazdelitev ocen, tako da je meja populacije izmerjena, ne trjena.
Zemljevid ostane `network_type: "drive"`; oznake načina prevoza iz Geolife se **ne**
uvedejo (nalagalnik `datasets/geolife.py` jih danes ne bere) — ta možnost ostane
rezerva, če se izkaže, da noben razumen prag ne ohrani dovolj podatkov.

**Prag se zniža**, nova vrednost pa se izbere **z diagnostiko, ne na slepo**: trajna
celica v `notebooks/03_s4_sweep.ipynb` izriše histogram `match_score` čez očiščene
sledi pri `max_users: 20` (predpomnilnik čiščenja je topel) in tabelo
"prag → preživele sledi → pokriti uporabniki". Diagnostika teče na avtorjevem okolju;
podatkov v repozitoriju ni. Izbrani prag mora biti v poročilu zagovorljiv s to sliko.

**Izmerjeno stanje ob pragu 0,6:** od 1607 očiščenih sledi preživi 45 (2,8 %), pokritih
je 9 od 20 uporabnikov. Delež preživetja ni odvisen od `max_users`.

### S4-2 — varovalo veljavnosti in operativne točke napada na članstvo

**Odločitev.** Metrika `tpr@fpr` potrebuje vsaj `1/fpr` nečlanov. Ko je nečlanov manj,
napad zapiše **`NaN`** in v `run.json` doda opozorilo (trdo pravilo; nesmiselna
številka ne sme nastati — vrednost 0,067 iz prvega pogona je bila artefakt).
Operativne točke se razširijo na `fpr ∈ {0.001, 0.01, 0.1}`: točka 0,1 potrebuje samo
10 nečlanov in je merljiva že pri majhnih stopnjah, strožji točki oživita, ko podatki
zadoščajo.

**Dejstva iz kode.** Kandidati niso vzorčeni: člani so vse ujete sledi iz razreza
`train`, nečlani vse iz razreza `test` (`_mia_pool` v
`src/trajguard/experiments/orchestrator.py`, okoli vrstice 1070). Razmerje 15 : 3 iz
prvega pogona je zato neposredna posledica deležev `train: 0.5, test: 0.2` in
preživetja ujemanja. Groba projekcija: nečlani ≈ 0,2 × preživetje × očiščene sledi;
za `fpr = 0.01` (≥ 100 nečlanov) pri polnem obsegu zadošča zmerno preživetje, za
`fpr = 0.001` (≥ 1000) bi bilo potrebno preživetje nad ~34 % pri vseh 182 uporabnikih.

### S4-3 — predpomnjenje umerjanja v `rn_ldp_synth`

**Odločitev.** Faktor napihnjenosti dekodiranja se **predpomni po ključu
(zemljevid, parametri umerjanja)**, tako da ga 17 generatorjev iste veje izračuna
enkrat namesto sedemnajstkrat. Sprememba je lokalna v
`src/trajguard/synthesis/rn_ldp_synth.py`; vrednosti rezultatov se ne spremenijo.

**Zakaj je to varno (ključno dejstvo).** `_calibrate_inflation`
(`rn_ldp_synth.py:331`) uporablja fiksno javno seme (`np.random.default_rng(0)`) in
izključno javne strukture (graf, enakomerna jedra). Rezultat je za isti zemljevid in
iste parametre **deterministično enak**, zato je deljena vrednost identična
neodvisno izračunanim. Ključ predpomnilnika mora zajeti hash zemljevida in vse
parametre, ki na umerjanje vplivajo. Pričakovani učinek: ~65 s na vejo namesto
~1100 s; veja pade globoko pod proračun 300 s.

### Dopolnitev pravil `docs/RUNNING.md` §7.3

**Odločitev.** Lestvica krčenja obsega dobi **diagnostični korak 0**: pred krčenjem
preveri, ali je strošek prekoračitve sploh odvisen od podatkov (ali `max_users`
nanj vpliva). Če ni, je vzrok v zgradbi mehanizma ali napada in se rešuje tam;
lestvica zanj ne velja. Primer S4-3 se navede kot prvi znani protiprimer.

### S4-4 — popravek `trajguard report`

**Odločitev.** `load_results` v `src/trajguard/reporting/report.py` (vrstica 197:
`glob("*/run.json")`) najde tudi ponovitvene zagone v podmapah `seed<N>/`, poročilo
pa čez semena **združuje** z obstoječo, testirano logiko iz
`src/trajguard/reporting/results_io.py` (ta že uporablja rekurzivni `rglob` in
Studentov t interval). Izhod: **ena vrstica na roko poskusa** (povprečje + interval),
ne ena vrstica na seme — sicer matrika tveganj ni berljiva. S tem poročilo in zvezek
`03_s4_sweep.ipynb` povesta isto.

### S4-5 — ničelni intervali pri vejah brez šuma

**Odločitev.** Samo dokumentacija, brez kode: kratek odstavek v `docs/RUNNING.md`
§7.1 (ali `docs/REZULTATI_SHEMA.md`), da veji `raw` in `protected:none` čez semena
nimata vira naključnosti (seme premakne šum mehanizma in senčne podmnožice, ne
napadalčevih enakomerno izbranih točk), zato je njun interval širine nič in to ni
napaka. Samodejno opombo v `report.md` dodamo šele, če se pri pisanju poročila
izkaže za motečo.

---

## 2. Merilo uspeha validacijskega pogona (pri `max_users: 20`)

Po združitvi PR-jev spodaj se kampanja **ponovi pri `max_users: 20`** (poceni, topel
predpomnilnik) z istima konfiguracijama in semeni kot prvi pogon (geoind 5 semen,
MIA 3 semena). Pogon je uspešen, ko velja oboje:

1. **nečlanov je vsaj 11** (projekcija 11 × 182/20 ≈ 100 pomeni, da pri polnem
   obsegu oživi `fpr = 0.01`), in
2. **galerija reidentifikacije pokrije vsaj 15 od 20 uporabnikov**.

Ob tem mora veja `rn_ldp_synth` pasti pod proračun 300 s (dokaz popravka S4-3) in
`trajguard report` mora uspešno izdelati `report.md` in `risk_matrix.csv` (dokaz S4-4).

**Če merilo pade,** je zaporedje vzvodov dogovorjeno: najprej poskus pri
`max_users: 50` (stopnja 20 za MIA morda ni smiselna); šele če pade tudi tam, se
spremeni delež razrezov v konfiguraciji MIA (npr. večji `test`), z izrecnim
zapisom v poročilu, da manjši `train` pomeni šibkejši ciljni generator in s tem
manjšo memorizacijo, ki jo napad meri. Če noben razumen prag ne ohrani dovolj
podatkov, se odpre rezervna možnost iz S4-1 (filtriranje po oznakah prevoza) —
to je nova avtorjeva odločitev, ne implementacijska.

---

## 3. Razrez dela in pot naprej

En PR = en poseg; vsaka seja začne v načrtovalnem načinu (pravila `CLAUDE.md`).

- **PR 1 — poročilo in varovalo (neodvisen, takoj):** popravek S4-4; varovalo
  `NaN` + opozorilo iz S4-2; razširitev `fprs` na `{0.001, 0.01, 0.1}` v
  konfiguracijah MIA; odstavek S4-5 v dokumentaciji rezultatov. Testi proti fixturam
  za rekurzivno odkrivanje, združevanje in varovalo. **Izvedeno 16. avgusta 2026**
  (veja `claude/s4-pr1-report-aggregation-mia-guard`); poleg dogovorjenega varovala
  ob izračunu poročilo shranjene neveljavne vrednosti `tpr@fpr` iz starejših zagonov
  zamolči še retroaktivno (isti predikat) in jih izpiše v razdelku Warnings, zato
  `trajguard report` že deluje nad rezultati prvega pogona.
- **PR 2 — mehanizem in pravila (neodvisen, takoj):** predpomnjenje umerjanja
  (S4-3) s testom determinističnosti (dva generatorja istega zemljevida delita
  vrednost; različna parametra je ne delita); korak 0 v `docs/RUNNING.md` §7.3.
  **Izvedeno 16. avgusta 2026** (veja `claude/s4-pr2-inflation-cache`): faktor se
  predpomni v procesnem predpomnilniku po ključu (vsebinski hash zemljevida —
  vozlišča, tabela povezav, uteženi seznam povezav grafa — ter `n_rows`,
  `n_cols`, `l_max`; `epsilon`, `budget_split` in seme v umerjanje ne vstopajo
  in v ključ ne sodijo). Testi dokazujejo en sam izračun z deljenjem, ločevanje
  po parametrih in po zemljevidu ter enakost predpomnjene vrednosti neodvisno
  izračunani; korak 0 je dodan v §7.3, opomba o deljenju v
  `docs/RN_LDP_SYNTH_DESIGN.md` §7.
- **Diagnostika praga (avtorjevo okolje, vzporedno s PR 1 in 2):** trajna celica v
  `notebooks/03_s4_sweep.ipynb` (histogram + tabela prag → sledi → uporabniki);
  avtor iz nje izbere novi prag.
- **PR 3 — populacija (po diagnostiki):** novi `min_match_score` v konfiguracijah;
  operativna definicija populacije in merilo iz razdelka 2 v dokumentaciji;
  izvedena diagnostična celica kot dokaz izbire.
- **Validacijski pogon pri 20** (merilo v razdelku 2) → **stopnja 50** (prvič
  izmeri, kako se podatkovno odvisni del cene MIA skalira, in da napoved proračuna
  za polni obseg) → **stopnja 182** (poročevalski pogon).

Seja, ki zaključi validacijski pogon, vpiše izid v ta dokument, doda povratni
sklic v `docs/HANDOFF.md` §1.10 in posodobi statusno vrstico v `CLAUDE.md`.
