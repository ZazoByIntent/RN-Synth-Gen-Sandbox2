# Načrt: umerjanje simulatorja z rangi pod LDP na ravni uporabnika (K1 + K8)

Stanje ob zapisu: 7. oktober 2026, izhodišče `main` na commitu `5db5f56`. To je **načrt**:
nič od opisanega še ni implementirano. Povzema drugi krog ideacije istega dne; surovo
angleško gradivo je v `arhiv/brainstorm_2026-10-07_krog2/` in je zapis, ne navodilo za delo.
Načrt dopolnjuje `docs/NACRT_ULDP_SINTEZA.md` in ga ne nadomešča. *Zasnova §4* tu vedno
pomeni izbrano zasnovo iz tistega dokumenta (en mehanizem z moduli C1, C2 in C3); razdelki
drugih dokumentov so navedeni z imenom datoteke, gola oznaka § kaže na ta načrt. Seja
prebere le razdelke, ki jih našteje njen prompt (§9.3); najdeš jih z `grep -n '^#'`.

## Kazalo

- §0 Namen, stanje in odločitve
- §1 Raziskovalna vrzel in omejitve
- §2 Kako je izbor nastal
- §3 Banka kandidatov K1–K8 (3.1 tabela, 3.2 kdaj se vrniti k neizbranim)
- §4 Izidi preverjanja novosti (4.1 izbrana zasnova, 4.2 neizbrani kandidati)
- §5 Izbrana zasnova (5.1 poročilo, 5.2 strežnik, 5.3 sinteza, 5.4 verjetje, 5.5 zasebnost)
- §6 Kaj lahko Geolife pokaže (6.1 šum pri n = 91, 6.2 le simulacija, 6.3 kontrolne roke)
- §7 Tveganja in varovala
- §8 Odprte odločitve
- §9 Predpogoji in načrt sej (9.1 predpogoji, 9.2 vrstni red, 9.3 prompt za prvo sejo)
- §10 Ugotovitve za zasnovo iz NACRT_ULDP_SINTEZA §4
- §11 Viri

## 0. Namen, stanje in odločitve

**Glavna poanta.** Drugi zaščitni mehanizem bo **umerjanje z rangi med uporabniki in
znotraj njih** (kandidata K1 in K8, v gradivu kombinacija B). Kot zasnova §4 je mehanizem
lokalne diferencialne zasebnosti na ravni uporabnika (LDP: vsak uporabnik podatke naključno
popači na svoji napravi; zaščiten je cel uporabnik z vsemi potmi iz obdobja zbiranja), ki
umerja javni simulator poti iz OpenStreetMap (OSM, odprti zemljevid) in citiranih konstant.
Telefon za eno svojo pravo pot s simulatorjem izdela okoli 30 »dvojčkov« (29 do 50, §5.1):
poti z isto traso in istim odhodom, a s časi vožnje po simulatorju. Pošlje le, kam se prava
pot uvrsti med njimi: hitreje od večine, v sredini, počasneje. Drug uporabnik primerja
svojo pot v prometni konici s svojo potjo zunaj nje. Če je simulator pravilen, so rangi pri
vsakem uporabniku popolnoma uravnoteženi, ne glede na število poti in način potovanja;
strežnik zato simulator preizkusi z vnaprej prijavljenim testom in ga obdrži, če test ne
zavrne, sicer popravi njegove čase vožnje. Parna oblika meri učinek konice znotraj iste
osebe, neodvisno od tega, kdo potuje kdaj, česar LDP na posamezni poti ne zmore (§1).

**Stanje.** Drugi krog ideacije je bil zaključen 7. oktobra 2026; nič ni implementirano.
Najprej predpogoji z dvema novima skupnima popravkoma, nato rang trajanja, par in simulacija.

**Odločitve avtorja, 7. oktober 2026.**

1. **Izbran je mehanizem z rangi (K1 + K8),** prva izbira ocenjevalčevega povzetka, pod
   pogojema iz kroga ugovorov: ne postavlja vprašanj o momentih (povprečjih statistik poti,
   kot C1) ali glasov o režimu (kot C3), raven časa vožnje pri n = 91 pa pokaže v
   neposredni primerjavi s C1 na istih uporabnikih in istem simulatorju, ne kot novo
   ugotovitev. V praksi: na Geolife ne obljublja ničesar, česar ne bi zmogel C1; lastni
   prispevek (točen test, učinek znotraj osebe) pokaže simulacija (§6.2). Je samostojen
   mehanizem, ne le časovna vprašanja modula C1 (izpeljava pisca iz izbire in točke 4 kroga
   ugovorov; potrdi avtor).
2. **Dva skupna popravka sta predpogoja:** seje Geolife se ob postankih razrežejo na poti
   (P10), vsak učni uporabnik pa pošlje natanko eno poročilo, po potrebi z odgovorom »nimam
   ujete poti« (P11). V praksi: oba spremenita podatke ali ogrodje za vse roke (§10, F1, F3).
3. **Neizbrane končne izbire** (celi uporabniki s središči in raziskovanjem, K6 + K5;
   struktura poti, K4; »najprej čas«, K2 + K3) ostanejo v banki s pogoji za vrnitev (§3.2).
4. **Ugotovitve za zasnovo §4** so v §10 in v `NACRT_ULDP_SINTEZA.md` niso uveljavljene;
   tam nanje kaže le opomba v §0.
5. **Surovo angleško gradivo je arhivirano** v `arhiv/brainstorm_2026-10-07_krog2/`.

**Izrazi.** *Roka* je nastavitev v konfiguraciji poskusa; *roka priorja* je isti generator
brez zasebnih poročil (ε → 0; ε je zasebnostni proračun, manjši ε pomeni močnejšo zaščito);
*roka orakla* je isti ocenjevalnik na točnih statistikah (ε = ∞); *prior* je model iz samih
javnih virov; *stopnja* je velikost populacije Geolife (u20, u50, u182); *ablacija* je
primerjava različic, ki se razlikujejo le v enem delu. *Rang* pove, koliko dvojčkov je
hitrejših od prave poti; *PIT* (probability integral transform) je isti podatek kot delež
med 0 in 1, pri pravilnem modelu enakomerno porazdeljen. *GRR* (posplošeni naključni
odgovor) pošlje eno od k javnih kategorij, z znano verjetnostjo pravo, sicer naključno
drugo; *HM* (hibridni mehanizem) je gradnik LDP, ki popači eno število z omejenim razponom.
*Kopula* je model odvisnosti dveh spremenljivk. *Nat* je enota naravnega logaritma (premik
trajanja za 0.07 nata je okoli 7-odstoten). *OD* sta izvor in cilj poti. SD je standardni
odklon; W1 (Wassersteinova razdalja) in JSD (Jensen–Shannonova divergenca) merita razliko
porazdelitev, manj je bolje; MIA je napad s sklepanjem o članstvu.

## 1. Raziskovalna vrzel in omejitve

**Vrzel ob zasnovi §4.** Zasnova §4 umerja simulator z momenti poti (C1), deleži con (C2)
in glasom o režimu (C3), dvojega pa ne zmore. Prvič, nima testa napačnosti simulatorja, ki
bi ostal točen ne glede na število poti uporabnika: C1 pošilja odrezana povprečja v ročno
izbranih razponih, C3 pa potrebuje javni zakon števila poti na uporabnika, ki ga noben vir
ne da (§10, F2); rang med dvojčki za kontekst poti same (trasa in odhod) pa je pri pravilnem
priorju točno enakomeren pri vsakem uporabniku. Drugič, ne meri učinkov znotraj iste osebe,
na primer koliko počasneje isti človek potuje v konici. Ocena prek različnih uporabnikov ta
učinek pomeša s tem, kdo potuje kdaj; LDP na posamezni poti (vsaka pot se popači posebej)
takega kontrasta po konstrukciji ne da, LDP na ravni uporabnika pa ga lahko, ker obe poti
vstopita v isto poročilo.

**Trde zahteve R1–R3 in že sprejete odločitve S1–S5** (se ne odpirajo):

| | V preprostih besedah |
|---|---|
| R1 | Izhod so sintetične poti, veljavne po cestnem grafu OSM, vsaka s časom odhoda in časom na vsakem cestnem odseku. |
| R2 | Čisti ε-LDP na ravni uporabnika: enota so vsi podatki uporabnika v obdobju zbiranja; porazdelitev poročila se med katerimakoli dvema možnima uporabnikoma razlikuje največ za faktor e^ε. Mešalec (shuffler), varno seštevanje (secure aggregation) ali zaupanja vreden zbiralec so dovoljeni le kot neobvezna razširitev, ki je jamstvo ne potrebuje. |
| R3 | Eno poročilo na uporabnika in obdobje zbiranja; protokol v več krogih mora uporabiti ločene skupine uporabnikov (kohorte); poročilo sme združiti več delov, če se njihovi ε seštejejo v uporabnikov celotni ε. |
| S1 | Javni prior vsebuje le OSM in citirane objavljene konstante, nič iz Geolife ali drugih podatkovij. |
| S2 | Dokaz za velik n (število poročajočih uporabnikov) da simulacija obnovitve parametrov do n = 10 000. Prave vrednosti smejo izvirati iz prilagoditve orakla na učnih uporabnikih Geolife in javnih odmikov (`NACRT_ULDP_SINTEZA.md` §5.5), a rabijo le za generiranje podatkov, nikoli v priorju ali sproščenem modelu. |
| S3 | Benchmark je Geolife z okoli 91 poročajočimi učnimi uporabniki pri stopnji 182 in mrežo ε {0.5, 2, 8}. |
| S4 | Napad MIA kliče le `fit()` in `sequence_log_prob()`, zato mora mehanizem določiti verjetje poti kot zaporedja cestnih odsekov. |
| S5 | Sintetični izhod še nima časov; to je predpogoj v podatkovnem modelu, ne ovira za zamisli. |

**Od česa se mora razlikovati:** od zasnove §4 ter od kandidatov C4–C10 in 20 surovih idej
prvega kroga (arhiv, `00_baseline.md` §3); k neizbranemu kandidatu se sme vrniti le nov
pogled, ki izpolni pogoj iz `NACRT_ULDP_SINTEZA.md` §3.2.

**Dejstva benchmarka.**

- **Seje, ne poti (ocenjevalec je preveril v kodi):** Geolife da eno trajektorijo na
  datoteko `.plt`, čiščenje le odstrani točke nad 200 km/h, redči na najmanj 5 s in zahteva
  vsaj 20 točk in 500 m; nič ne reže ob postankih. Trajanja zato vsebujejo postanke in
  vrzeli v snemanju, seja dom–trgovina–dom pa je zanka. Kako pogosto je to, ni izmerjeno in
  se pred zamrznitvijo priorja na Geolife ne sme meriti.
- **`fit` dobi le ujete učne poti** (ki so prestale ujemanje z zemljevidom; preverjeno v
  `experiments/orchestrator.py`): uporabnik brez ujete poti ne pošlje ničesar (§10, F3).
- **Malo uporabnikov:** pri u182 okoli 91 učnih uporabnikov z okoli 9 ujetimi potmi (od
  17 313 očiščenih trajektorij ujemanje prestane 1770, učenje teče na okoli 809); pri u50
  okoli 25, pri u20 okoli 10. Napad MIA bere le verjetje zaporedja povezav, časov ne vidi;
  roka zgradi 17 generatorjev, klic napada ima 300 s pri u20 in u50 ter 1200 s pri u182.

## 2. Kako je izbor nastal

Izhodiščni agent je najprej povzel, kaj je pokril prvi krog. Pet predlagateljev je nato
iskalo vsak v svoji smeri (»leči«: R2-A najprej čas, R2-B celi sintetični uporabniki, R2-C
ena vzorčena pot na uporabnika, R2-D večkrožni protokoli z ločenimi skupinami, R2-E lokalna
sinteza s stisnjenim opisom) in dalo skupaj 18 idej. Konsolidacija jih je združila v osem
kandidatov K1–K8, zapisala 14 presečnih ugotovitev X1–X14 in šum preračunala s točno
formulo za n = 91. Preverba novosti je kandidate v treh skupinah s približno 145 spletnimi
iskanji primerjala z literaturo. Ocenjevalec je točkoval po osmih utežnih merilih, na štirih
najboljših izvedel napad »rdeče ekipe« (namerno iskanje šibkosti), sestavil tri kombinacije
in v enem krogu ugovorov s sedmimi točkami popravil ocene: zasebnost je postala prag, razrez
sej ob postankih pa skupni predpogoj. Avtor je izbral prvo izbiro, K1 + K8.

## 3. Banka kandidatov K1–K8

### 3.1 Tabela

Novost je sodba preverbe, v oklepaju njena zanesljivost: *nova kombinacija* pomeni
objavljene kose v neobjavljeni kombinaciji, *bližnja različica* pa, da se objavljeno delo
razlikuje le v eni podrobnosti (taka ne more biti izbrana). Prvo točkovanje ima osem utežnih
meril (novost, ločenost od zasnove §4, dokaz pri n = 91, vrednost za disertacijo, prileganje
benchmarku, velik n, zasebnost, strošek; največ 100); krog ugovorov je zasebnost spremenil v
prag in ponovno točkoval (največ 95), njegove točke veljajo; šum točkovanja je okoli ±3. Pri
centralni DP (diferencialni zasebnosti) šum doda zaupanja vreden zbiralec; EPR je model
individualne mobilnosti »raziskovanje in prednostno vračanje«.

| | Kandidat | Zamisel v enem stavku | Novost (zanesljivost) | Najbližje delo | Točke /100, /95 | Status |
|---|---|---|---|---|---|---|
| K1 | Umerjanje z rangom med dvojčki | naprava razvrsti eno svojo pot med 29–50 dvojčkov, ki jih javni simulator izdela za njen kontekst, in pošlje grobi rang; strežnik simulator preizkusi in popravi | nova kombinacija (srednja); zaporedna oblika sama je bližnja različica | Joseph et al. (NeurIPS 2019); Penso et al. (COPA 2025) | 60, 57 | izbran, del mehanizma |
| K2 | Prizme časovnega proračuna | pot se začne kot dva časa, trajanje in tesnost glede na najhitrejši javni čas; cilj pride iz obroča enake časovne oddaljenosti okoli izvora | nova kombinacija (srednja) | RATR (IEEE TDSC 2025); PCATS/FAMOS (2005), Yoon et al. (2012) | 57, 51 | neizbran; s K3 kombinacija T |
| K3 | Stanja hitrosti ob naključni sekundi | stanje hitrosti (stoji, hodi, počasi, hitro) ob eni naključni sekundi potovalnega časa poganja polmarkovsko uro hitrosti in usmerjevalnik, ki ji sledi | nova kombinacija, ozka (srednja) | Bian et al. (Google EIE, 2024); BerlinMOD (2009) | 53, 48 | neizbran; del T ali modul |
| K4 | Struktura poti prek vmesnih točk | ena vzorčena pot pove, iz koliko skoraj najkrajših kosov je in ali je zanka; usmerjevalnik veriži skoraj najkrajše sprehode prek javnih vmesnih vozlišč | nova kombinacija (srednja); sam model poti je objavljen | Knapen et al. (2016); DPMM (ACSAC 2022) | 66, 56 (po razrezu, A′) | neizbran; tretja končna izbira |
| K5 | Središča navad | uporabnik sporoči navado (celico, kjer se začne ali konča večina poti) namesto vzorca; strežnik ustvari uporabnike, ki se vračajo v svoje središče | nova kombinacija, ozka (srednja); »navada namesto vzorca« sama je bližnja različica | Wang et al. (AAAI 2018); DP-WHERE (2013) | 56, 52 | neizbran; del C |
| K6 | Uporabniki s podpisom mobilnosti | naprava strne obdobje v klasičen opisnik mobilnosti (število različnih krajev, polmer kroženja) in pošlje enega; strežnik umeri EPR in ustvari cele uporabnike | nova kombinacija (srednja) | DP-WHERE (2013); Kapp et al. (2022) | 62, 60 | neizbran; s K5 druga končna izbira |
| K7 | Namestni anketiranec | naprava prilagodi parametre simulatorja svojim potem in odgovori na en javno zasnovan hipotetični izbor; strežnik prek znanega kanala oceni strukturne parametre | nova kombinacija (nizka); obe izvedljivi obliki sta bližnji različici | LDP-DL (Zhuang et al. 2022); Zhou in Tan (AAAI 2021) | 53, 51 | zavrnjen |
| K8 | Kontrasti in povezave znotraj uporabnika | ena kategorija o razmerju med uporabnikovimi lastnimi potmi (konica proti zunaj konice, znak korelacije) umeri kontrast simulatorja brez vpliva tega, kdo potuje kdaj | nova kombinacija (srednja); postavka (d) sama je bližnja različica | Sopa, Avella-Medina, Rush (arXiv 2026, centralna DP) | 64, 62 | izbran, del mehanizma |

Kombinacija šteje le, če si deli eno poročilo (en javni žreb vprašanja, en gradnik s polnim
ε), en dokaz zasebnosti in ne ponovi zasnove §4. **B** = K1 + K8 (postavki a in c): 69 in
**70** točk, izbrana. **C** = K6 + K5: 65 in 62. **A** = K4, razširjen z deli seje med
postanki (iz K3 in K2) in z zankami: 72 in 61; drugo število velja za nerazrezane seje, ko
njen dodatni signal opisuje, kako so prostovoljci vklapljali snemanje, zato ni priporočena.
**A′** = K4 po razrezu: 56. **T** = K2 + K3: 54.

### 3.2 Kdaj bi se splačalo vrniti k neizbranim

- **C, celi uporabniki s središči in raziskovanjem (K6 + K5; 62/95; okoli 7–8 sej).** Na
  Geolife pokaže kvečjemu eno glavno 5-km celico pri ε = 2, če si jo deli okoli tretjina
  uporabnikov (ni izmerjeno). Vrnitev se splača, ko (1) benchmark dobi povezan izhod in
  metrike na ravni uporabnika (pogoj za C4 iz `NACRT_ULDP_SINTEZA.md` §3.2; pri u182 slonijo
  na okoli 36 testnih uporabnikih, pri u20 in u50 so neuporabne), (2) enourna javna
  simulacija pred kodo pokaže, da konstanta vračanja ρ sploh premakne W1 dolžine in JSD
  matrike OD 3 × 3, in (3) se zakon števila poti na uporabnika vpraša v poročilu, nikoli ne
  prilagodi na Geolife (S1). Tveganje: glavna celica se bere kot poročilo o domu in pri
  ε = 8 sprosti celice ob domovih.
- **A′, struktura poti (K4; 56/95; okoli 3–4 seje).** Statistiko (iz koliko skoraj
  najkrajših odsekov je pot) so objavili Knapen et al. (2016); nova so le razred zanke,
  zasebni zakon in točno verjetje, kar krog ugovorov šteje za eno podrobnost. Po razrezu sej
  Geolife verjetno ne odstopa od objavljenih deležev za potrebnih 0.15 (30–55 %
  avtomobilskih poti je znotraj 5 % najkrajšega časa; Zhu in Levinson 2015), večdelne poti
  pešcev pa so spet mešanica načinov potovanja. Vrnitev se splača, če je razumno
  pričakovati, da prior iz citiranih konstant zgreši delež za vsaj 0.15 (le tedaj ga
  postavka pri ε = 2 popravi); če bi avtor seje raje modeliral kot razrezal (kombinacija A);
  kot možnost usmerjevalnika zasnove §4, ki zank skoraj ne ustvari; ali z merilnim profilom
  okna (verjetnost, da je naključno okno poti skoraj najkrajše, po dolžini okna), edino
  oceno te družine brez predhodnika.
- **T, najprej čas (K2 + K3; 54/95).** V šumu točkovanja je enaka A′ in ima prednost le,
  če mora biti čas sam tisto, kar uporabniki sporočajo; obe postavki pri n = 91 merita
  mešanico načinov (X10). Ključni dokaz bi bila ablacija »izokronski obroč proti
  gravitaciji« (cilj iz krivulje enake časovne oddaljenosti namesto iz gravitacijskega
  modela, v katerem privlačnost cone pada z razdaljo); K3 je bolje predstaviti kot modul
  časa in postankov.
- **K7 (zavrnjen).** Obe izvedljivi obliki sta bližnji različici, odzivna ploskev pa
  potrebuje dva nejavna zakona populacije. Vrnitev le kot posredno sklepanje (indirect
  inference) pod LDP z zasnovanimi scenariji več družin pri n ≥ okoli 1000, če simulacija
  pokaže, da en zasnovan odgovor obnovi več parametrov kot zasebno poslana koordinata.
- **K1 in K8 sama** sta dela izbrane zasnove: K1 sam ocenjuje isto kot C1, K8 sam nima
  generatorja in se na benchmarku ne vidi.

## 4. Izidi preverjanja novosti

Preverba je tekla v treh skupinah (G1: K1, K7, K8; G2: K2, K3, K4; G3: K5, K6). Dela so bila
odprta (povzetek ali članek), razen kjer piše »le izsek« (sodba iz povzetka iskalnika).

### 4.1 Izbrana zasnova (K1 + K8)

**Sodba:** K1 in K8 sta vsak zase nova kombinacija s srednjo zanesljivostjo; ocenjevalec je
kombinaciji za novost dal 4 od 5, ker K8 prinaša novo ocenjevano količino (učinek znotraj
osebe). Najbližja sta Cormode in Markov (2023; zasebno umerjanje skupnega modela) ter Sopa
et al. (2026; ocene znotraj osebe, le centralna zasebnost).

| Delo | Kaj naredi | Razlika od izbrane zasnove |
|---|---|---|
| Joseph, Kulkarni, Mao, Wu, NeurIPS 2019, https://arxiv.org/abs/1811.08382 | dve skupini uporabnikov: groba ocena, nato binarni odgovor glede nanjo | zaporedna oblika K1 je njihov drugi krog s porazdelitvijo simulatorja namesto Gaussove, zato bližnja različica; jedro je enokrožno |
| Penso, Mahpud, Goldberger, Sheffet, COPA 2025, https://arxiv.org/abs/2505.15721 | ocena skladnosti podatkov z modelom, en bit naključnega odgovora na uporabnika v ločenih skupinah | K1 pošlje razred PIT, obnovi celo preslikavo, model je simulator, pogojen na kontekst |
| Cormode, Markov, PVLDB 16(11) 2023, https://arxiv.org/abs/2210.12526 | umerjanje skupnega modela iz histogramov pod LDP | za ocene klasifikatorjev, ne za PIT zvezne porazdelitve generatorja |
| Kuleshov, Fenner, Ermon, ICML 2018, https://arxiv.org/abs/1807.00263 | ponovno umerjanje napovedne porazdelitve | strežniška preslikava K1 je ta postopek, tam brez zasebnosti |
| Acharya, Canonne, Freitag, Tyagi, AISTATS 2019, https://proceedings.mlr.press/v89/acharya19b.html; Lam-Weil, Laurent, Loubes, https://arxiv.org/abs/2002.04254 | testi prileganja pod LDP | vrata K1 so tak test, uporabljen na PIT |
| Sopa, Avella-Medina, Rush, arXiv 2026, https://arxiv.org/abs/2601.10626 | ocene znotraj uporabnika pod DP na ravni uporabnika | centralno in zvezno; K8 je lokalna različica z eno kategorijo glede na prior |
| Kent, Berrett, Yu 2024, https://arxiv.org/abs/2405.11923; Acharya, Liu, Sun, AISTATS 2023, https://proceedings.mlr.press/v206/acharya23a.html | teorija LDP na ravni uporabnika | brez ocen znotraj uporabnika |
| Ding, Nori, Li, Allen, AAAI 2018, https://arxiv.org/abs/1803.09027 | primerjava povprečij skupin pod LDP | skupine različnih uporabnikov, ne poti istega |
| Couch et al. 2018, https://arxiv.org/abs/1809.01635 | parni test znotraj osebe | pod centralno DP (znakovni test, Awan in Slavković 2018, le izsek) |
| LoPub (Ren et al., IEEE TIFS 2018), https://arxiv.org/abs/1612.04350; Ghazi et al., NeurIPS 2023 (§11) | odvisnost med spremenljivkami pod LDP | znotraj enega zapisa ali med uporabniki, nikoli med zapisi istega uporabnika |

**Kaj mora zasnova trditi.** (1) PIT, pogojen na kontekst poti, naredi vsako poročilo pri
pravilnem javnem priorju točno enakomerno ne glede na število poti, mešanico kontekstov ali
način potovanja, zato se razlike med uporabniki ne morejo kazati kot napaka simulatorja; to
K1 loči od odrezanih momentov C1 in oznak C3. (2) Vnaprej prijavljen točen ničelni test
obdrži prior, dokler ga podatki ne zavrnejo; sestavljena gostota ostane normirana, poti
veljavne po cestah. (3) LDP na posamezni poti kontrasta znotraj osebe ne more dati; parni
rang s personaliziranimi dvojčki odstrani uporabnikovo raven hitrosti in ohrani kontrast;
zakon izbire upravičenih parov je javen, zato je ocenjevana količina dobro definirana;
oceni znotraj in prek uporabnikov se primerjata na simulirani populaciji, v kateri je čas
potovanja povezan s tem, kdo potuje. Po rdeči ekipi trditev o K8 preživi le z
identifikacijskim argumentom in primerjavo variance z ocenjevalnikom prek uporabnikov.

**Česa ne sme trditi:** »prvo umerjanje pod LDP« (Cormode in Markov 2023 za klasifikatorje);
»nov prilagodljiv protokol« (Joseph et al., Penso et al., Aamand et al. 2025); »nov test
prileganja pod LDP«; nov gradnik LDP; »prvi parni test« ali »prva kopula pod LDP«; »prvi
ocenjevalnik znotraj uporabnika pod DP na ravni uporabnika« (centralna različica obstaja);
»prvi generator trajektorij z LDP na ravni uporabnika« (PateGail, AAAI 2023; PateGAIL++, ICLR
2026, le povzetek); novosti metode »simuliraj, popači, ujemi« (Sakong in Zentefis, NBER 2024;
Xiong et al. 2023; Wang, Chang, Awan 2025); dobička uporabnosti pri n ≈ 91 razen premika
log-trajanja, ki ga premakneta tudi C1 in C3. Ker pri n = 91 meri mešanico načinov
potovanja, mora citirati Bian et al. (2024; Google EIE: način, razdalja in trajanje pod
centralno DP na ravni uporabnika) in poudariti čisti LDP. Recenzent lahko vpraša, zakaj ni
uporabljen ocenjevalnik Acharya, Liu, Sun (2023), ki ima »vzorči eno pot, nato GRR« za
izhodišče.

**Kaj bi novost dvignilo.** Pri K1 (nobena sprememba ga ne naredi »novega«): skupni
zaporedni PIT odhoda in trajanja, poslan kot ena skupna postavka odhod × trajanje z 9
celicami pri ε = 8, za kar ni bilo najdeno nič podobnega, in dokaz, da vrata ohranijo raven
pri katerem koli zakonu števila poti. Pri K8: ocenjevalnik s fiksnimi učinki znotraj
uporabnika (model, ki vsakemu uporabniku dovoli lastno raven in oceni le razlike znotraj
njega) pod LDP s primerjavo variance proti ocenjevalniku prek uporabnikov bi kot metoda lahko
dosegel sodbo »nova«, a je statistični prispevek, ne mehanizem, in se pokaže šele pri
tisočih uporabnikih.

**Razlika od zasnove §4 in C4–C10.** Razliko od C1 in C3 opisujeta §1 in trditev 1. Od
surovih idej družine C1 (A.1, B.1, C.1, D.2, E.3) je najbližja C.1 (»centrirano na
pričakovanje priorja«), ki pa pošlje povprečje z odrezom in brez ničelnega testa. Od C5 se
loči, ker so dvojčki zamenljivi s pravo potjo in niso knjižnica; od C7, ker nima ploskve
gumbov ali dvoboja (zaporedna oblika pa ima obliko C7). C4 ni obujen: par dveh poti
identificira en učinek modela nepovezanih poti, za povezave pa je potrebna skupna metrika
(pogoj, podoben pogoju za C4).

### 4.2 Neizbrani kandidati

| | Sodba (zanesljivost) | Najbližja dela | Česa ne sme trditi |
|---|---|---|---|
| K2 | nova kombinacija (srednja) | RATR (Zhang et al., IEEE TDSC 2025), https://research.polyu.edu.hk/en/publications/ratr-optimized-trajectory-release-with-temporal-local-differentia/; Brauer et al., »Time will not tell« (CEUS 112, 2024), https://doi.org/10.1016/j.compenvurbsys.2024.102154 (celotno besedilo nedostopno); FAMOS/PCATS (Pendyala et al., TRR 1921, 2005), https://itspubs.ucdavis.edu/publication_detail.php?id=127; Yoon et al. (Transportation 39(4), 2012, le izsek), https://ideas.repec.org/a/kap/transp/v39y2012i4p807-823.html | izbire cilja, omejene s prizmo ali proračunom; »časovnega LDP za trajektorije« kot prvega; prostorskega dobička brez ablacije obroča proti gravitaciji |
| K3 | nova kombinacija, ozka (srednja) | Bian et al. 2024 (Google EIE), https://arxiv.org/abs/2407.03496; BerlinMOD (Düntgen, Behr, Güting, VLDB Journal 18, 2009), https://docs.mobilitydb.com/MobilityDB-BerlinMOD/master/ch02s07.html; Balau et al. (SAE 2015-01-0488); Acharya, Liu, Sun 2023 | časovno uteženih deležev, markovske sinteze hitrosti, postankov po razredu ceste, časov po načinu pod DP na ravni uporabnika |
| K4 | nova kombinacija (srednja), sam model poti je objavljen | Knapen et al. (Transportation Research Part B 90, 2016; tabele za plačljivim zidom), https://ideas.repec.org/a/eee/transb/v90y2016icp156-171.html; DPMM (Haydari et al., ACSAC 2022), https://its.berkeley.edu/node/5589; Abraham et al. (ACM JEA 18, 2013), https://www.microsoft.com/en-us/research/?p=165224; Fischer (2020), https://arxiv.org/abs/1909.08801; Manley, Addison, Cheng (2015), https://ideas.repec.org/a/eee/jotrge/v43y2015icp123-139.html; Zhu in Levinson (PLoS ONE 2015), https://pmc.ncbi.nlm.nih.gov/articles/PMC4534461/ | hipoteze o nekaj staknjenih najkrajših poteh, razgradnje, vmesnih vozlišč, lokalne optimalnosti in sider; Knapen et al. morajo biti imenovani kot najbližje delo |
| K5 | nova kombinacija, ozka (srednja); »navada namesto vzorca« sama je bližnja različica | Wang et al. (AAAI 2018), https://ojs.aaai.org/index.php/AAAI/article/view/11285; DP-WHERE (Mir et al., IEEE BigData 2013), https://doi.org/10.1109/BigData.2013.6691626; Cho, Myers, Leskovec (KDD 2011), https://cs.stanford.edu/people/jure/pubs/mobile-kdd11.pdf; Vanhoof, Lee, Smoreda (2018), https://arxiv.org/abs/1809.09911 | »poročaj navado« kot novega načela; da modalna celica ni sidro (je standardni detektor doma); da so središča pri ε = 8 v praksi varna (pari dom–delo imajo po Golle in Partridge 2009 mediano anonimnostne množice 1) |
| K6 | nova kombinacija (srednja) | DP-WHERE (2013); Kapp et al. (2022), https://arxiv.org/abs/2209.08921; Sakong in Zentefis (NBER 2024); PateGail (AAAI 2023), https://ojs.aaai.org/index.php/AAAI/article/view/26700; DITRAS (Pappalardo in Simini 2018), https://arxiv.org/abs/1607.05952, s Song et al. (2010), https://arxiv.org/abs/1010.0436 | novosti opisnikov in njihove zasebne izdaje, metode »simuliraj, popači, ujemi«, plasti kopij in metrik koherence; »prvega generatorja celih uporabnikov z LDP« |
| K7 | nova kombinacija (nizka) | LDP-DL (Zhuang, Li, Chang 2022), https://arxiv.org/abs/2202.02971; Zhou in Tan (AAAI 2021), https://arxiv.org/abs/2010.06709; Hausman, Abrevaya, Scott-Morton (1998), https://dspace.mit.edu/handle/1721.1/63829, in Zhang et al. (ICML 2025), https://proceedings.mlr.press/v267/zhang25x.html; lokalno zasebno vzorčenje (Husain et al. 2020, Park et al. 2024, Zamanlooy et al. 2025); PATE (Papernot et al. 2017) | »prve poizvedbe lokalnega modela pod LDP«; možnosti pri ε = 8 kot novega vzorčevalnika; večparametrskih trditev pri n ≈ 91 |

## 5. Izbrana zasnova

Gostitelj je skupni javni model P3 iz `NACRT_ULDP_SINTEZA.md` §4.1, predpogoj obeh
mehanizmov in ne modul zasnove §4: Boltzmannov sprehod proti cilju (na vsakem vozlišču
izbere povezavo z verjetnostjo, ki eksponentno pada z dodanim stroškom) po gravitacijskem
OD (privlačnost cone pada z razdaljo), javni prior odhodov in čas na povezavi = čas prostega
toka × javni faktor × tresenje. Namesto modulov ima mehanizem družine vprašanj z enim
poročilom in enim dokazom; javno pravilo n·ε² (zamrznjena tabela, ki iz števila uporabnikov
in ε določi, kdo dobi katero vprašanje) deli uporabnike, nikoli ε. K1 izvira iz idej R2-C.1
in R2-D.1, K8 iz R2-C.3, R2-A.4 in R2-E.4.

### 5.1 Poročilo uporabnika

Javni žreb, neodvisen od podatkov, izbere vprašanje iz zamrznjenega seznama. Vsak učni
uporabnik pošlje natanko eno poročilo; kdor nima ujete poti ali upravičenega para, pošlje
kategorijo ⊥ (»nimam«), ki je del vsake domene. Dvojčki nikoli ne zapustijo naprave.

| Vprašanje | Kaj naprava izračuna | Kaj pošlje | Kdaj |
|---|---|---|---|
| *dur*, rang trajanja (K1) | eno ujeto pot izbere enakomerno naključno; javni simulator za isto zaporedje povezav in isti odhod izdela 29–50 dvojčkov s časi vožnje; rang je število hitrejših dvojčkov, izenačenja razbije naključno | razred ranga: trije razredi z enako verjetnostjo pod priorjem (hitreje od večine, sredina, počasneje), po odločitvi še »precej počasneje«, in ⊥; GRR s polnim ε | pri n = 91 vsi uporabniki pri ε ≤ 2 (pri ε = 0.5 vrata obdržijo prior); pri ε = 8 okoli polovica (§6.1) |
| *dep*, rang odhoda (K1) | točen PIT ure odhoda pod javnim dnevnim profilom, brez dvojčkov | razred ranga | ε = 8 ali velik n |
| skupna postavka odhod × trajanje (K1) | oba PIT iste poti | ena od 9 celic po GRR | ε = 8 ali velik n |
| *a*, par konica–zunaj konice (K8) | po javnem pravilu en upravičen par (predlog gradiva: pot v konici ob 7–9 h ali 17–19 h in pot zunaj nje med 6 in 22 h, časa prostega toka v razmerju največ 1.5); vsako trajanje razvrsti med 29 dvojčkov, premaknjenih za uporabnikovo povprečno log-razmerje hitrosti (izračunano lokalno) | razred razlike rangov d = rang v konici − rang zunaj nje: d < −10, d med −10 in 10, d > 10, ⊥; GRR nad 4 | velik n |
| *c*, znak povezanosti (K8) | Spearmanova korelacija (povezanost vrstnih redov) dveh lastnosti uporabnikovih poti, na primer dolžine in odhoda v konici, pri vsaj 3 poteh | negativna, je ni, pozitivna (prag ±0.3); GRR, pri ε = 8 HM na odrezani vrednosti | velik n |

Pri ε = 8 se lahko namesto razreda pošlje rang u ∈ [0, 1] s HM (razpon [0, 1] je dan sam po
sebi). Prostorska vprašanja K1 (*len*, oddaljenost cilja; *radial*; *route*, presenečenje
trase, ki meri tudi ujemalnik z zemljevidom) so le možnost pri velikem n. Po pogoju avtorja
ostaneta zunaj postavki K8 (b), razlika povprečnih log-hitrosti (momentno vprašanje), in
(d), kvadrant dveh rangov glede na mediane prejšnje skupine (oblika prek uporabnikov, le
primerjava v simulaciji). Jedro je enokrožno; zaporedna oblika (binarni odgovor o mediani,
nato druga skupina, ki simulator ponovno centrira) je bližnja različica Joseph et al. in je
le ablacija.

### 5.2 Strežnik

- **Popravek šuma:** iz histograma poročil se odstrani znani šum GRR; deleži med
  upravičenimi uporabniki so ŝ_c / (1 − ŝ_⊥).
- **Vrata »obdrži prior, razen če test zavrne«:** popravljeni test hi-kvadrat proti
  enakomerni porazdelitvi s kritično vrednostjo, simulirano vnaprej; če ne zavrne, ostane
  prior. Ker ⊥ ni del ničelne hipoteze, ostanejo vrata točna.
- **Preslikava kvantilov (*dur*):** nova gostota trajanja je prior × g(F_prior(x | kontekst)),
  kjer je F_prior porazdelitvena funkcija priorja za kontekst poti, g pa stopničasta funkcija
  iz deležev razredov; normiranje je točno, ker je E_prior[g(U)] = 1. Trije razredi dajo
  premik in razpršenost log-trajanja, ne dvovrhosti; obliko repa obdrži prior.
- **Par (K8a):** ravnotežje znakov (delež d > 10 proti d < −10) je točen test faktorja
  konice v priorju, ker sta PIT obeh poti zamenljiva, ko uporabnikov lastni učinek obe
  premakne enako (ocenjevalec je to preveril). Urejeni probit (model za urejene kategorije)
  z javno lestvico tresenja da napako log-hitrosti v konici μ̂.
- **Znak (K8c):** iz deležev se oceni parameter Gaussove kopule, skrčen proti 0.

### 5.3 Sinteza poti s časi

- **Trasa:** iz P3 (po javni meji korakov zaključek po najkrajši poti), zato je veljavna po
  cestah po konstrukciji; izvor, cilj in trasa ostanejo priorjevi.
- **Čas odhoda:** iz javnega dnevnega profila; rang *dep* ga popravi le pri ε = 8 ali
  velikem n.
- **Časi po odsekih:** javni čas prostega toka (OSM `maxspeed` ali privzeta hitrost razreda
  ceste) × faktor × tresenje; skupni čas se preslika po kvantilih iz rangov trajanja (pri
  n = 91 iz poročil), vsi odseki pa se skalirajo z istim razmerjem. Pri velikem n se doda
  faktor konice znotraj osebe, exp(μ̂ · 1[konica]); pari (obdobje, razred razdalje) se
  vlečejo iz ocenjene kopule. Zapis časov v izhodu zahteva P1 (S5).

### 5.4 `sequence_log_prob`

Kot v `NACRT_ULDP_SINTEZA.md` §4.7: log P(O, D) + vsota log-verjetnosti korakov sprehoda +
javni člen za vrzeli; čas ne vstopa. Pri n ≈ 91 se sprašuje le *dur*, zato je verjetje enako
priorjevemu in je napad MIA slep po konstrukciji. Postavki K8 a in c verjetja ne spremenita
(marginalizacija obdobja vrne P(O, D)). Le ablacija *len* pri velikem n doda člen
log g(F_ℓ(ℓ(seq) | O, D)); zanj se dvojčki sejejo s hashem (O, D, zemljevid, konfiguracija),
porazdelitev pa se oceni s simulacijo Monte Carlo. Ena pot kode za člane in nečlane, okoli
40 ms na poizvedovani cilj, predpomnilniki skupni 17 generatorjem roke.

### 5.5 Zasebnostni argument na ravni uporabnika

**Trditev:** mehanizem je čisti ε-LDP na ravni uporabnika. **Dokaz v preprostih besedah**
(lema o dvigu, X1 v konsolidaciji): vse, kar naprava izračuna (izbira poti ali para,
dvojčki, rang, razred), je le pot do ene vrednosti x iz majhne javne domene, napravo pa
zapusti samo izhod GRR. Za vsak izhod y so verjetnosti P(GRR(x) = y) pri vseh x znotraj
faktorja e^ε, zato za katerakoli dva uporabnika s podatki D in D' velja P(y | D) ≤ max_x
P(GRR(x) = y) ≤ e^ε · min_x P(GRR(x) = y) ≤ e^ε · P(y | D'), ne glede na to, kako je bil x
izračunan. Poročilo je eno, kompozicije ni, vse naprej je naknadna obdelava.

**Pogoji.** Domene, razredi, število dvojčkov, pravilo parov, tabela n·ε², kritična vrednost
testa in pravilo razreza sej so javni in zamrznjeni s hashem commita pred prvim pogonom pri
182 (§10, F8). Izbira poti je za zasebnost brezplačna, a določi, kaj se ocenjuje, zato mora
strežnik poznati zakon izbire. Vsak učni uporabnik pošlje natanko eno poročilo; n je javno
število učnega dela (okoli 91, 25 in 10), ne število uporabnikov z ujeto potjo (§10, F3).
Zaporedna oblika potrebuje javno naključno delitev v skupine, določeno pred prvim
poročilom, nastavitve za skupino t pa le iz prejšnjih, ločenih skupin. Povezava dveh poti gre
v eno kategorično poročilo: dva bita z ε = 1 (skupaj ε = 2) bi zanjo delovala kot en bit pri
ε ≈ 0.43. Rdeča ekipa na zasebnost jedra ni našla napada.

## 6. Kaj lahko Geolife pokaže in kako merimo

### 6.1 Šum pri n = 91

SD so točne vrednosti po popravku šuma, s členom vzorčenja, iz vrednotenja in konsolidacije;
*razpršenost* je SD log-trajanja ene poti pod priorjem (0.42 nata).

| ε | Kaj se premakne | Šum |
|---|---|---|
| 0.5 | nič; vrata obdržijo prior, roka je enaka roki priorja | ±0.28 na delež razreda (3 razredi), ±0.21 za binarni odgovor, ki zazna le prior, zgrešen za vsaj 1.5 razpršenosti |
| 2 | raven časa vožnje; vsi uporabniki dobijo *dur* (pravilo n·ε²), zato je na Geolife mehanizem enak K1. Proti priorju z avtomobilskimi hitrostmi padejo poti pešcev, avtobusov in seje s postanki v zgornji razred; trije razredi dajo tedaj kvečjemu raven in razpršenost, ne dvovrhosti hoje in vožnje, zato je to ista mešanica, ki jo premakneta C1 in C3 (X10, domneva konsolidacije; zdravila v §8, točka 1, in P10) | ±0.073 na delež pri 3 razredih, ±0.074 pri 4; premik log-trajanja na ±0.17 razpršenosti, to je ±0.07 nata, če je pravi premik znotraj okoli ene razpršenosti; sicer en krog pove le »vsaj 1.3 nata v to smer« |
| 8 | dve vprašanji po okoli 45 uporabnikov (iz točke 6 kroga ugovorov sledi, da sta to rang trajanja in rang odhoda) ali skupna postavka odhod × trajanje | HM na rangu ±0.045 nata (binarni odgovor ±0.055); 9 celic skupne postavke ±0.033 na celico |

Ali rang raven hitrosti oceni bolje kot C1, je po konsolidaciji odvisno od tega, ali C1
razpon zoži po režimih (potem doseže ±0.06); zato je primerjava s C1 pogoj (odločitev 1).
Učinek konice znotraj osebe (K8a) se na Geolife ne vidi: upočasnitev za 0.2 nata ob tresenju
priorja 0.42 nata premakne delež »pot v konici je za več kot 10 od 29 rangov počasnejša« z
0.22 na okoli 0.36, nasprotni delež pa na okoli 0.12; če bi na par odgovarjali vsi in bi
bilo upravičenih okoli 40 od 91, bi bila razlika okoli 1.1 SD pri ε = 2 in 2.3 SD pri ε = 8
(račun preverjen, velikost učinka in delež upravičenih sta domnevi). Ker pri n = 91 vsi
dobijo *dur*, para ne sprašujemo. Odgovor ⊥ ima ceno: SD deležev med uporabniki s podatki se
pomnoži z 1/√(1 − s_⊥), kjer je s_⊥ delež ⊥ (× 1.05 pri s_⊥ = 0.1, × 1.2 pri s_⊥ = 0.3),
glede na današnje ogrodje, ki uporabnike brez poti izpusti, in z 1/(1 − s_⊥) glede na
populacijo samih informativnih uporabnikov.

**Napad MIA** pri n = 91 vidi le prior (AUC, ploščina pod krivuljo ROC, je 0.5 po
konstrukciji). Meja ε-LDP je TPR ≤ e^ε · FPR (TPR in FPR sta deleža pravih in lažnih
zadetkov); pri FPR 0.01 da 0.017 pri ε = 0.5 in 0.074 pri ε = 2, pri ε = 8 je brez vsebine.

### 6.2 Kaj pokaže le simulacija obnovitve (P6)

- Vrata ohranijo svojo stopnjo napake pri katerem koli zakonu števila poti na uporabnika
  (mreža n in ε ter koda `encode_user` in `server_fit` kot v `NACRT_ULDP_SINTEZA.md` §5.5).
- Učinek konice znotraj osebe ostane pravilen, ko se ljudje, ki potujejo v konici,
  razlikujejo od ostalih; populacija mora vsebovati tako povezavo, da se oceni znotraj in
  prek uporabnikov (oblika K8 (d)) vidno razlikujeta.
- Preslikave po kontekstih (obdobje × razred dolžine), skupni PIT, 5–10 razredov z
  naključnim zamikom robov, kopula 3 × 3, kontrasti po obdobju in razredu ceste ter
  delovnik proti vikendu, vse pri n do 10 000.
- Napačno specificiran pogon (podatki z drugačno obliko tresenja, kot jo predpostavi prior)
  in zaporedna oblika pri velikem n (8–10 skupin po okoli 1000 uporabnikov, SD 0.021).

### 6.3 Kontrolne roke in metrike

- **Roki priorja in orakla:** dobiček je delež vrzeli med njima (`NACRT_ULDP_SINTEZA.md` §5.3).
- **C1 na istih uporabnikih in istem simulatorju** (pogoj avtorja); recenzent bo verjetno
  zahteval prav PM v C1 (odsekovni mehanizem za eno število) na isti statistiki. Po X10 je
  smiselna tudi C3, ki meri isto mešanico.
- **»ldptrace, dvignjen na raven uporabnika«** (X7): ena enakomerno izbrana ujeta pot na
  uporabnika s polnim ε skozi LDPTrace, sprehod po mreži celic pripet na OSM z javnim
  usmerjevalnikom, odhod in časi iz priorja; enako dvignjen `rn_ldp_synth` kot druga
  kontrola. Mehanizem mora premagati obe in svojo roko priorja.
- **Ablacije:** vrata vklopljena in izklopljena; ena skupina proti dvema; simulacijske
  primerjave iz §6.2.
- **Metrike:** W1 trajanja, povprečne hitrosti in ure odhoda (P2) ter nova W1 trajanja
  znotraj vsakega obdobja odhoda (P12), brez katere par in kopula nimata vidnega učinka;
  prostorske metrike morajo ostati pri priorju. Zasebnost se dokazuje strukturno s kompletom
  P4 in z dodatnim testom iz P11.

## 7. Tveganja in varovala

Napad MIA večine teh tveganj ne bi opazil, zato jih zapirata konstrukcija in testi.

| Tveganje | Kaj se zgodi | Varovalo |
|---|---|---|
| Nasičenje (najmočnejši napad rdeče ekipe) | hoja, avtobusi in seje s postanki padejo v zgornji razred; trije razredi dajo le raven in razpršenost | prior z mešanico načinov ali razred repa (§8, točka 1); razrez sej (P10) |
| Podvajanje zasnove §4 | na Geolife meri isto mešanico hoje in vozil kot C1 in C3; recenzent ga lahko bere kot ocenjevalni sloj zasnove §4 | brez vprašanj o momentih in glasov; primerjava s C1 na istih uporabnikih; lastni prispevek dokazan v simulaciji |
| Slepota benchmarka | čas ni v verjetju povezav, napad MIA vidi prior; dobiček je viden le na W1 trajanja in hitrosti; nobena metrika P2 ni pogojena na obdobje | strukturni testi P4; metrika P12; odločitev o časovnem napadu (§8, točka 10) |
| Seje namesto poti | trajanja vsebujejo postanke in vrzeli v snemanju, zato je rang »počasneje« pogosto artefakt | P10 pred zamrznitvijo priorja |
| Kdo poroča | danes poroča le, kdor ima ujeto pot; »ni poročila« proti izhodu GRR se razlikuje neomejeno, n pa poveže vprašanje vsakega uporabnika z drugimi | P11: vsi učni uporabniki, ⊥, n iz učnega dela, test |
| Izbira upravičenih parov | izbere uporabnike s potmi v obeh obdobjih (efektivno okoli 30–45 uporabnikov, podobnih vozačem na delo); ocena velja le zanje | javno pravilo, zamrznjeno pred podatki; delež ⊥ pove velikost skupine |
| Šum znotraj osebe | isti človek ima ob različnih dneh različne namene in načine (okoli polovica variance časa vožnje, le izsek) | personalizirani dvojčki odstranijo raven, ne tega šuma; učinek pričakujemo le pri velikem n |
| Ena preslikava na vprašanje | predpostavlja, da napaka simulatorja ni odvisna od konteksta | pri velikem n preslikave po obdobju × razredu dolžine |
| Ujemalnik z zemljevidom | rang *route* meri tudi ujemalnik, ki daje prednost najkrajšim potem | *route* ni v jedru in se pri n = 91 ne sprašuje |
| Kontaminacija priorja | razredi, pravilo parov, število dvojčkov ali tabela n·ε², nastavljeni po številkah Geolife (na primer okoli 9 ujetih poti na uporabnika), so nezaščitena izdaja | vse iz OSM in citiranih virov, zamrznjeno s hashem commita (F8) |
| Zaporedna oblika | potrebuje citiran zakon razpršenosti med uporabniki (±0.3 nata, S1) in je bližnja različica | le ablacija |
| Kopula | predpostavlja Gaussovo odvisnost | le pri velikem n |

## 8. Odprte odločitve

Točke 1–3 imenuje ocenjevalčev povzetek, ostale odpira vrednotenje; »izpeljava« ali
»opažanje pisca« pomeni, da gradivo točke ne navaja. Termini so izpeljani iz §9.2.

| # | Odločitev | Kaj pomeni v praksi | Kdaj |
|---|---|---|---|
| 1 | Prior proti nasičenju: javni prior z mešanico hoje in vožnje ali dodaten razred »precej počasneje« (neenaki razredi po kvantilih priorja, na primer pri PIT 0.5, 0.95 in 0.999; ničelna hipoteza ostane točna) | mešanica naredi iz PIT razvrščevalnik načina potovanja in mehanizem približa C3; dodaten razred skoraj nič ne stane (pri ε = 2 je SD na delež 0.073 pri treh in 0.074 pri štirih kategorijah); druga skupina za ponovno centriranje stane faktor √2 v SD in je bližnja različica Joseph et al. | pred P3 |
| 2 | Pravilo upravičenih parov: okna konice in zunaj nje, razmerje časov prostega toka, kdaj se pošlje ⊥ | pravilo določi, čigav učinek merimo; ocene upravičenosti (0.3–0.6 uporabnikov) so ugibanje ob številki iz Geolife in pravila ne smejo oblikovati (F8) | pred sejo para |
| 3 | Nova metrika: W1 časa vožnje znotraj vsakega obdobja odhoda (P12), po potrebi dvorazsežna JSD za kopulo | brez nje benchmark ne nagradi ničesar, kar prinese par | pred koncem P2 |
| 4 | Pravilo razreza sej (P10): pragovi postanka in vrzeli iz citiranih virov (zgled iz vrednotenja: vsaj 3 min znotraj 150 m ali vrzel vsaj 3 min s premikom pod 300 m) in ali razrez velja za vse roke | razrez spremeni podatke S4 in številke vseh rok, tudi zasnove §4; brez njega trajanja vsebujejo postanke | pred P10 |
| 5 | Kako uporabniki brez ujete poti pridejo v `fit` (P11), na primer s čistimi pogledi za neujete trajektorije (X6) | odločitev je skupna z `NACRT_ULDP_SINTEZA.md` §7.1, točka 3 | po P0 |
| 6 | Gostitelj: vrednotenje navaja P3 ali usmerjevalnik kombinacije A | ker A ni izbrana, ostane P3 (izpeljava pisca, potrdi avtor) | pred P3 |
| 7 | Vrstni red glede na zasnovo §4 | primerjava s C1 potrebuje roko C1 na istih uporabnikih, v zasnovi §4 pa pride C1 zadnji; ali se ta mehanizem pri u182 meri po C1 ali ob najmanjši roki »PM v C1 na isti statistiki«, gradivo ne določa | pred meritvami |
| 8 | Utež: ocena, utežena po uporabnikih (ena pot na uporabnika, privzeto), ali po poteh z zgornjo mejo (X4) | skupno z `NACRT_ULDP_SINTEZA.md` §7.1, točka 2 | pred koncem P2 |
| 9 | Seznam vprašanj in tabela n·ε², povezava pri K8c, število dvojčkov (29–50), raven vrat | vse zamrznjeno pred prvim pogonom pri 182; kako se ⊥ pošlje pri številskem odgovoru HM, gradivo ne pove (opažanje pisca) | pred sejo ranga trajanja |
| 10 | Časovno občutljiv napad MIA (`NACRT_ULDP_SINTEZA.md` §7.1, točka 4; P8) | ta mehanizem spreminja le čase, ki jih napad ne vidi (§5.4), zato je odločitev tu še pomembnejša | pred prvimi meritvami |

## 9. Predpogoji in načrt sej

### 9.1 Predpogoji

P0–P6 so oznake iz `NACRT_ULDP_SINTEZA.md` §8.1 (napor S majhen, M srednji); vsak se naredi
enkrat in služi obema mehanizmoma. Novi predpogoji nadaljujejo številčenje, ker so P7–P9 tam
že zasedeni; njihovega napora gradivo ne ocenjuje.

| # | Predpogoj | Napor | Vloga za ta mehanizem |
|---|---|---|---|
| P0 | preverba uporabniške napeljave: `user_id` v pogledih, kandidati MIA, ali neujete poti pridejo v `fit` | S | dejstva za P11 |
| P1 | časovni sintetični payload: povezave, odhod, čas vstopa na povezavo v UTC+8, Parquet | S | izhod R1; ocenjevalec priporoča še zapis postanka (§10, F1) |
| P2 | neparne metrike uporabnosti: W1 trajanja, povprečne hitrosti in ure odhoda ter prostorske metrike | M | dokaz dobička |
| P3 | skupni javni model (simulator) | M | gostitelj in dvojčki; prior proti nasičenju (§8, točka 1) |
| P4 | zasebnostni komplet: razrez `encode_user` / `server_fit`, testi 1–4, pozitivna kontrola | S–M | strukturni dokaz; dobi test iz P11 |
| P5 | preverbe ogrodja, ε na ravni uporabnika v `run.json` | S | pogoni MIA |
| P6 | simulacija obnovitve parametrov | S–M | §6.2 |
| P10 | javni razrez sej Geolife ob postankih kot možnost čiščenja | ni ocenjen | trajanja brez postankov; pravilo po §8, točka 4 |
| P11 | vsak učni uporabnik pošlje natanko eno poročilo (⊥, če nima ujete poti), n iz učnega dela; test, da uporabnik, čigar poti nehajo prestajati ujemanje, še vedno pošlje natanko eno poročilo | ni ocenjen | jamstvo R2 in R3 v izvedbi |
| P12 | W1 trajanja znotraj vsakega obdobja odhoda (po potrebi dvorazsežna JSD) | ni ocenjen | vidnost para in kopule |

### 9.2 Vrstni red sej (navpične rezine)

Vsak korak je ena veja in en PR in se konča z izidom, ki ga je mogoče preveriti.

1. **P0 + P1** (prompt v `NACRT_ULDP_SINTEZA.md` §8.3), če še nista v `main`.
2. **P10**, razrez sej (prompt v §9.3); od P0 in P1 neodvisen, lahko teče tudi pred njima
   (izpeljava pisca).
3. **P11**, eno poročilo na učnega uporabnika (po P0; test sodi v komplet P4).
4. **P2 + P12**, metrike.
5. **P3**, javni model s priorjem proti nasičenju; z njim obstajata roki priorja in orakla.
6. **P4 + P5**, zasebnostni komplet in preverbe ogrodja.
7. **Rang trajanja** (K1 *dur*, enokrožno, z vrati in preslikavo kvantilov; okoli 2 seji).
8. **Par in znak** (K8 a in c) s pravilom upravičenih parov in tabelo n·ε².
9. **Simulacija P6**: raven vrat pri različnih zakonih števila poti; populacija s povezavo
   med časom potovanja in tem, kdo potuje.
10. **Meritve** pri u20 (dimni test), u50 in u182; prior zamrznjen pred prvim pogonom pri
    182; primerjava s C1 na istih uporabnikih (§8, točka 7); zapis v `docs/HANDOFF.md`.

Vrednotenje ocenjuje mehanizem na okoli 4–5 sej; gradivo ne pove, ali so predpogoji všteti
(pri kombinaciji A so izrecno izvzeti).

### 9.3 Prompt za prvo sejo (P10)

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_ULDP_RANGI.md SAMO §0, §1 (dejstva benchmarka), §8 (točka 4) in §9.1 (vrstica
P10); arhiva arhiv/ ne odpiraj. Za branje kode (kako datasets/geolife.py in
datasets/cleaning.py naredita trajektorije, kako attacks/attribute.py najde točke postanka
in kako je sestavljen ključ predpomnilnika očiščenih podatkov) uporabi svežega podagenta
general-purpose, ki vrne kratek povzetek; glavni kontekst naj ostane čist.

Naloga P10: javni razrez posnetih sej Geolife na poti ob postankih in vrzelih v snemanju,
kot možnost čiščenja v konfiguraciji. Pragove (razdalja in trajanje postanka, dolžina
vrzeli) predlagaj v planu s citiranim virom, nikoli po Geolife; potrdim jih jaz. Dokler ne
odločim, ali razrez velja za vse roke, je možnost privzeto izklopljena, zato se obstoječe
konfiguracije in številke S4 ne spremenijo. Ključ predpomnilnika mora vključiti pravilo
razreza. Ne meri, koliko sej Geolife razrez zadene: pred zamrznitvijo priorja se to ne sme.
Testi nad fiksturo: seja s postankom se razreže v dve poti, seja brez postanka ostane cela,
izid je determinističen, izklopljena možnost da enak izhod kot danes.

Postopek: začni v plan mode in počakaj na mojo potrditev. Naloga je majhna, zato skill
orchestrate ni potreben; če bi presegla ~5 datotek ali mešala teme, najprej predlagaj
razrez. Ustvari vejo claude/uldp-rangi-p10. Definicija končanega: uv run ruff check .,
uv run mypy src in uv run pytest -q čisti; prilepi ukaz in zadnjih ~10 vrstic izpisa.
Proračun izpisa: pytest -q, nikoli -v, ob napaki ponovi le padli test; dolge izpise
skrajšaj s | tail -20; najprej git diff --stat. V istem PR posodobi vrstico stanja v
CLAUDE.md in označi P10 kot zaključen v §9.1 načrta. Koda, identifikatorji, docstringi in
testi v angleščini; pogovor z mano v slovenščini, brez nepojasnjenih kratic.
```

## 10. Ugotovitve za zasnovo iz NACRT_ULDP_SINTEZA §4

Ocenjevalec drugega kroga je zapisal tudi ugotovitve za zasnovo §4; tu so zapisane, v
`NACRT_ULDP_SINTEZA.md` pa niso uveljavljene in o njih odloči avtor. Številke razdelkov se
nanašajo na `NACRT_ULDP_SINTEZA.md`; »preverjeno« pomeni preverjeno v kodi ali z računom.

| | Ugotovitev | Predlog ocenjevalca |
|---|---|---|
| F1 | **Seje, ne poti** (preverjeno, novo). Na Geolife je model poti zasnove §4 napačno specificiran: razmerje hitrosti in momenti odhoda C1 vsebujejo postanke in vrzeli; seja s povratkom ima cilj ob izvoru, ki ga gravitacija C2 in Boltzmannov sprehod skoraj ne ustvarita; C3 lahko sejo z avtom in dolgim postankom označi kot hojo ali kolo. | Pred zamrznitvijo priorja izberi javni razrez sej kot možnost podatkov (spremeni vse roke in številke S4) ali modeliranje sej; krog ugovorov priporoča razrez kot skupni predpogoj. V obeh primerih naj P1 zapiše postanek (čas vstopa in izstopa na povezavo), sicer postane absurdno počasna povezava. |
| F2 | **Zakon števila poti na uporabnika ni javen** (preverjeno z razmislekom). §4.3 simulira matriko zamenjav C3 »pod javnim številom poti na uporabnika«, ki ga noben citiran vir ne da; določita ga čiščenje in okoli 10-odstotni delež ujemanja. | Najceneje: oznako C3 vleči iz aposteriorne porazdelitve ENE enakomerno izbrane poti, da je matrika zamenjav javna po konstrukciji (cena: bolj ploska matrika, majhna, ko se režimi po hitrosti razlikujejo vsaj trikrat). Drugače: razred števila poti v isti postavki, oblika z rangom (K1) ali analiza občutljivosti v simulaciji. Povprečja C1 in vzorčeno krajišče C2 so za oceno, uteženo po uporabnikih, nepristranska tudi brez tega zakona. |
| F3 | **Kdo poroča, ne sme biti odvisno od podatkov** (preverjeno za ogrodje, novo). `fit` vidi le ujete učne poti, zato uporabnik brez ujete poti ne pošlje ničesar, n v pravilu n·ε² pa šteje uporabnike z ujetimi potmi; oboje je funkcija zasebnih podatkov (»ni poročila« in izhod GRR se razlikujeta neomejeno, n pa poveže vprašanje vsakega uporabnika z drugimi). Pri n = 91 je to v praksi drobno, a jamstvo iz §4.2 (»vsak vpisani uporabnik pošlje eno poročilo«) v izvedbi ne drži. | V `fit` predaj vse učne uporabnike (na primer s čistimi pogledi za neujete trajektorije); kdor nima ujete poti, pošlje javno privzeto vrednost; n beri iz učnega dela; v P4 dodaj test, da uporabnik, čigar poti nehajo prestajati ujemanje, še vedno pošlje natanko eno poročilo. |
| F4 | **Številke šuma v načrtu** (preverjeno). Vrednosti v §4.3 (C3: 0.12 pri ε = 1, 0.05 pri ε = 2), §4.4 (C2: 0.06 ob vseh, 0.10 pri 40 % uporabnikov, 0.19 pri ε = 1) in §5.1 (trije deleži 0.05, devet 0.06; s tretjino uporabnikov 0.08 in 0.11) veljajo le za izginjajoče deleže. | Točno pri deležih blizu 1/k: trije deleži 0.136 (ε = 1) in 0.073 (ε = 2); devet deležev 0.206 (ε = 1), 0.079 (ε = 2), 0.11 za delež blizu 0.5; pri 40 % uporabnikov 0.125; s tretjino 0.126 in 0.137; z OLH (optimizirano lokalno zgoščevanje), ki ga §4.4 predpiše za cone, okoli 0.095 (vsi) in 0.15 (40 %). Nobena sodba o modulu se ne obrne; meje zaznave se skrčijo za 15–40 %. |
| F5 | **Izbira gradnika** (preverjeno). Za cone C2 3 × 3 je pri ε ≥ 1 GRR boljši od OLH (k = 9 < 3e^ε + 2, kar je 10.2 pri ε = 1 in 24 pri ε = 2; okoli 0.079 proti 0.095 pri ε = 2). | Za cone 3 × 3 GRR; OLH šele od 36 con naprej. |
| F6 | **C1 bo na Geolife podvojil C3** (domneva). Pri n = 91 razmerje hitrosti in glas o režimu merita isto mešanico načinov. | Roko samo C1 pri ε = 2 poročaj kot preverbo, ne kot ločen dobiček (načrt že pričakuje večino dokaza iz C3 in C2). |
| F7 | **Vrata za vsak modul** (predlog). Zasnova §4 nima izjave o dokazu tam, kjer se nič ne premakne. | Surovi histogram poročil modula primerjaj s histogramom, ki ga prior napove skozi znani naključnik (točno pod ničelno hipotezo, brez dodatnih uporabnikov), in prior obdrži, razen če vnaprej prijavljen test zavrne; rangi K1 to razširijo na zvezne postavke brez zakona števila poti. |
| F8 | **Zamrzni tudi konstante zasnove** (nauk 7 prvega kroga). Robovi razredov in pravila upravičenosti, zgrajeni ob predpostavki okoli 9 ujetih poti na uporabnika, uporabljajo številko iz Geolife. | Pravilo zamrznitve s hashem naj jih zajame tako kot cone in katalog. |
| F9 | **Dela, ki naj jih zasnova §4 citira.** | Zasebno umerjanje skupnega modela ali simulatorja: Cormode in Markov (PVLDB 2023, LDP), Chopra et al. (AAMAS 2024, varno večstransko računanje). »Simuliraj, popači, ujemi« ni novo: Sakong in Zentefis (NBER 2024), Xiong et al. 2023, Wang, Chang, Awan 2025. Način, razdalja in trajanje pod centralno DP na ravni uporabnika: Bian et al. 2024 (Google EIE), za mešanico načinov C3. LDP na ravni uporabnika z več vzorci na uporabnika: Acharya, Liu, Sun 2023; Kent, Berrett, Yu 2024 (ena vzorčena postavka C2 je njihovo izhodišče). Generatorji celih uporabnikov pod DP: PateGail (AAAI 2023), PateGAIL++ (ICLR 2026); nikoli »prvi generator trajektorij z LDP na ravni uporabnika«. Lokalno zasebno vzorčenje: Husain et al. 2020, Park et al. 2024, Zamanlooy et al. 2025; »vleci iz aposteriorne, nato GRR« v C3 je lokalno zasebni vzorčevalnik, ki ga je vredno primerjati z optimalnim vzorčevalnikom Parka et al. Prilagodljive skupine (§4.8): Joseph et al. 2019, Aamand et al. 2025, Penso et al. 2025, Wang et al. (AAAI 2018). Konstante strukture poti kot javni prior za usmerjevalnik C1: Knapen et al. 2016, Zhu in Levinson 2015. Postanki po razredu ceste na OSM: BerlinMOD. |

Za ta načrt sta F1 in F3 že sprejeta kot predpogoja P10 in P11 (odločitev 2), F7 pa je
jedro tega mehanizma.

## 11. Viri

Najbližja dela s povezavami so v tabelah §4.1 in §4.2, tu so ostali citati za izbrano
zasnovo; poizvedbe in vsi zadetki so v arhivu (`30_novelty_G1.md` do `30_novelty_G3.md`).
Kjer gradivo povezave ne navaja, sta navedena le avtor in leto.

- **Umerjanje in prilagodljivi protokoli:** Chopra et al., AAMAS 2024,
  https://arxiv.org/abs/2404.12983 (umerjanje simulatorja z varnim večstranskim računanjem);
  Maddock, Cormode, Maple 2025, https://arxiv.org/abs/2510.01987; Aamand et al., ICML 2025,
  https://arxiv.org/abs/2502.02990; Liu, Hu 2026, https://arxiv.org/abs/2607.05312; Talts
  et al. 2018 (umerjanje na podlagi simulacij), https://arxiv.org/abs/1804.06788.
- **LDP na ravni uporabnika in odvisnost:** Zhao et al. 2024,
  https://arxiv.org/abs/2405.17079; Roth, Avella-Medina 2025,
  https://arxiv.org/abs/2511.18583; Joseph, Roth, Ullman, Waggoner, NeurIPS 2018,
  https://arxiv.org/abs/1802.07128; Ghazi et al., NeurIPS 2023,
  https://proceedings.neurips.cc/paper_files/paper/2023/hash/5642b9811a9ac5281be1cc84c275f251-Abstract-Conference.html.
- **Dela, zaradi katerih zasnova nečesa ne trdi:** Bian et al. 2024 (Google EIE),
  https://arxiv.org/abs/2407.03496; PateGail, AAAI 2023,
  https://ojs.aaai.org/index.php/AAAI/article/view/26700, in PateGAIL++, ICLR 2026 (le
  povzetek); Sakong, Zentefis, NBER 2024,
  https://www.nber.org/books-and-chapters/data-privacy-protection-and-conduct-applied-research-methods-approaches-and-new-findings/simulation-based-method-estimating-economic-models-privacy-protected-data;
  Xiong, Ju, Zhang 2023, https://arxiv.org/abs/2310.12781; Wang, Chang, Awan 2025.
- **Ozadje, ni bilo odprto:** Rosenblatt 1952; Diebold et al. 1998; Hamill 2001 (PIT in
  umerjanje napovedi). **Iz konsolidacije, brez povezave:** Dawid 1984 (PIT); Blomqvist 1950
  (koeficient odvisnosti).
