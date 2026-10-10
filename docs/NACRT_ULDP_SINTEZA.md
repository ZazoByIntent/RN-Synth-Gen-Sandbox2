# Načrt: sinteza poti s časi pod LDP na ravni uporabnika (ULDP; moduli C1, C2, C3)

Stanje ob zapisu: 7. oktober 2026, izhodišče `main` na commitu `1886f36`. To je **načrt**:
nič od opisanega še ni implementirano. Povzema ideacijsko sejo istega dne; surovo angleško
gradivo je v `arhiv/brainstorm_2026-10-07/` in je zapis, ne navodilo za delo. Seja prebere
le razdelke, ki jih našteje njen prompt (§8.3, §8.4); najdeš jih z `grep -n '^#'`.

## Kazalo

- §0 Namen, stanje in odločitve
- §1 Raziskovalna vrzel in omejitve
- §2 Kako je izbor nastal
- §3 Banka kandidatov (3.1 tabela, 3.2 kdaj se vrniti k neizbranim)
- §4 Izbrana zasnova (4.1 simulator, 4.2 poročilo in delitev uporabnikov, 4.3 C3, 4.4 C2,
  4.5 C1, 4.6 zasebnost, 4.7 `sequence_log_prob`, 4.8 razširitve)
- §5 Kaj lahko Geolife pokaže (5.1 šum, 5.2 tri točke, 5.3 dokaz, 5.4 MIA, 5.5 simulacija)
- §6 Zasebnostna tveganja in varovala (6.1 tveganja, 6.2 varovala, 6.3 po modulih)
- §7 Odprte odločitve (7.1 mehanizem, 7.2 moduli)
- §8 Predpogoji in seje (8.1 P0–P5, 8.2 vrstni red, 8.3 prompt P0 + P1, 8.4 predloga)
- §9 Viri

## 0. Namen, stanje in odločitve

**Glavna poanta.** Naslednji zaščitni mehanizem bo **en** mehanizem z lokalno
diferencialno zasebnostjo na ravni uporabnika (ULDP). Lokalna diferencialna zasebnost
(LDP) pomeni, da vsak uporabnik podatke naključno popači na lastni napravi, zato strežniku
ni treba zaupati; »na ravni uporabnika« pomeni, da je zaščiten cel uporabnik z vsemi
potmi iz obdobja zbiranja. Vsak pošlje eno popačeno poročilo; strežnik z njimi umeri
javni simulator iz OpenStreetMap (OSM, odprti zemljevid) in citiranih konstant, ki ustvari
poti po cestah s časom odhoda in časi po odsekih. **C3** (glas o režimu) pove, kakšne
vrste popotnik je uporabnik (na primer pešec ali voznik), **C2** (deleži izvorov in
ciljev), kje se poti začnejo in končajo, **C1** (vedenjski momenti), kako se giblje glede
na najhitrejšo pot med istima krajiščema.

**Odločitve avtorja, 7. oktober 2026.**

1. **En mehanizem, trije moduli, eno poročilo na uporabnika.** Javni žreb dodeli modul,
   na katerega uporabnik odgovori s celotnim ε (zasebnostni proračun; manjši ε pomeni
   močnejšo zaščito); izvedba v vrstnem redu C3, C2, C1. V praksi: en dokaz zasebnosti, en
   ε na uporabnika, štiri roke (samo C1, samo C2, samo C3, sestavljena).
2. **Javni prior je OSM plus citirane konstante.** Prior je model iz samih javnih virov;
   hitrosti, profil odhodov, upad z razdaljo in katalog C3 imajo vir v OSM ali v citirani
   objavi in se zamrznejo s hashem commita pred prvim pogonom pri 182 uporabnikih. V
   praksi: nič se ne nastavlja po Geolife, ker smo njegove številke videli v kampanji S4.
3. **Dokaz za velik n (število poročajočih uporabnikov) zdaj s simulacijo obnovitve
   parametrov** (§5.5, P6) do 10 000 uporabnikov, brez novih podatkov. Nalagalnik za
   T-Drive (okoli 10 000 pekinških taksijev na istem grafu, P7) je velik in tvegan, zato
   pride na vrsto le, če simulacija ne bo zadoščala.
4. **Surovo angleško gradivo je arhivirano** v `arhiv/brainstorm_2026-10-07/`.

**Stanje.** Nič ni implementirano; najprej predpogoji P0–P5 (§8.1), nato C3, C2, C1,
sestavljena roka in simulacija (§8.2); odprte odločitve so v §7. **Izrazi:** *roka* je
nastavitev v konfiguraciji poskusa; *roka priorja* je isti generator brez zasebnih poročil
(ε → 0); *roka orakla* je isti ocenjevalnik na točnih statistikah brez šuma (ε = ∞),
nezasebni strop te družine modelov; *stopnja* je velikost populacije Geolife (u20, u50,
u182); SD je standardni odklon; JSD (Jensen–Shannonova divergenca) in W1 (Wassersteinova
razdalja dveh enorazsežnih porazdelitev) merita razliko porazdelitev, manj je bolje.

**Opomba (7. oktober 2026).** Drugi krog ideacije je za to zasnovo zapisal ločene ugotovitve
F1–F9 (seje namesto poti, zakon števila poti na uporabnika za C3, kdo poroča, točnejši šum za
§4.3, §4.4 in §5.1, izbira gradnika za C2, vrata »obdrži prior, razen če test zavrne«);
zbrane so v `docs/NACRT_ULDP_RANGI.md` §10 in tu še niso uveljavljene.

## 1. Raziskovalna vrzel in omejitve

**Vrzel.** Ni objavljenega mehanizma, ki bi sintetiziral cele poti po cestnem grafu s
časom odhoda in časi po odsekih tako, da sproščeni podatki izpolnjujejo čisti LDP na ravni
uporabnika. Zahteve: randomizacija na napravi brez zaupanja vrednega mešalca (shuffler)
ali varnega seštevanja (secure aggregation), ki smeta biti le neobvezni razširitvi; eno
poročilo po obdobju zbiranja (na primer mesecu), poznejša oddaja je nov uporabnik;
strežnik sme model posodabljati postopoma; arhitektura je prosta; čas je obvezen, izhod
pa veljaven po cestah po konstrukciji (vsaka naslednja povezava obstaja v javnem grafu).
Mehanizem mora biti nov: ne ponavljamo LDPTrace, PrivTrace, AdaTrace, DPT, DP-Star,
RetraSyn, Cunningham et al., zbiranja v slogu TrajLDP, modelov v slogu DP-FedAvg in
nezasebnih generatorjev (TS-TrajGen, Diff-RNTraj, DiffTraj, ControlTraj); kombinacija
znanih kosov šteje le, če reši problem, ki ga noben kos ne reši sam.

**Dejstva benchmarka, ki omejujejo zasnovo.**

- **Malo uporabnikov:** `fit` vidi le učni del, pri stopnji 182 okoli 91 uporabnikov z
  okoli 9 ujetimi potmi (potmi, ki so prestale ujemanje z zemljevidom), skupaj okoli 809
  poti; ker pride v `fit` le, kdor ima vsaj eno ujeto pot, jih je morda manj. Pri stopnji
  50 jih je okoli 25, pri 20 okoli 10.
  Napaka pod čistim LDP pada kot 1/(ε·√n), zato histogrami in prehodi po odsekih odpadejo.
- **Napad s sklepanjem o članstvu (MIA)** kliče le `fit` in `sequence_log_prob(edge_seq)`,
  ki mora biti končen za vsako zaporedje; `generate` in časov ne vidi. Roka zgradi 17
  generatorjev (tarčni in 16 senčnih, vsak z okoli 18 uporabniki in kandidatnimi potmi),
  zato se javni izračuni predpomnijo; klic napada ima na voljo 300 s pri u20 in u50 ter
  1200 s pri u182.
- **Manjka:** časovni payload (`SyntheticTrajectory` nosi le povezave ali celice; P1) in
  metrike sintetične uporabnosti v orkestratorju (JSD celic in napaka dolžine sta le v
  `rnldp_eval`; P2). Sintetični `user_id` niso potrebni, ker so poti nepovezane.
- **Mreža ε je {0.5, 2, 8}.** Obstoječe roke ščitijo posamezno pot: uporabnik z 9 potmi
  pri ε = 0.5–2 na pot je dejansko pri 4.5–18, z 95 potmi pri 0.5 pri okoli 47.
- **Orodja:** brez globokih generatorjev (PyTorch, grafični procesor); prototip
  `rn_ldp_synth` (poročila na pot, brez časov) ni predloga.

## 2. Kako je izbor nastal

Pet predlagateljev z različnimi pogledi (statistik za LDP, prometni strokovnjak, strojno
in federativno učenje, zasebnostni napadalec, prosta domišljija) je dalo po štiri ideje;
konsolidacija je 20 idej združila v družine C1–C10 in šum preračunala na n ≈ 91 (nekateri
so računali z n ≈ 180, zato so bile njihove napake okoli √2-krat premajhne). Preverba
novosti je družine s približno sto spletnimi iskanji primerjala z literaturo. Ocenjevalec
je točkoval po šestih merilih z novostjo kot pragom, na štirih najboljših izvedel napad
»rdeče ekipe« (namerno iskanje puščanja zasebnosti) in izbral C1, C3 in C2; v krogu
ugovorov (sedem točk koordinatorja) je popravil račun šuma in predlagal en mehanizem s
tremi moduli. Vse številke tu so ocenjevalčeve, popravljene v krogu ugovorov, za n ≈ 91.

## 3. Banka kandidatov

### 3.1 Tabela

Točke so vsota šestih ocenjevalčevih meril po 1–5 (novost, zasebnost, dobiček nad
priorjem, prileganje benchmarku, napor in tveganje, zgodba); novost vsaj 3 je prag, zato
*bližnja različica* (objavljeno delo se razlikuje le v eni podrobnosti) ne more biti
izbrana, *nova kombinacija* pa pomeni objavljene kose v neobjavljeni kombinaciji (vse
preverbe imajo srednjo zanesljivost). OD je izvorno-ciljna matrika (koliko poti gre iz
cone i v cono j); PM in HM sta odsekovni in hibridni mehanizem za eno omejeno število; GRR
je posplošeni naključni odgovor (pošlje eno od k kategorij, z znano verjetnostjo pravo,
sicer naključno drugo); OLH je optimizirano lokalno zgoščevanje za velike domene; pri
centralni DP (diferencialni zasebnosti) šum doda zaupanja vreden zbiralec.

| | Kandidat | Mehanizem v enem stavku | Novost; najbližje delo | Točke | Status |
|---|---|---|---|---|---|
| C1 | Vedenjski momenti | ena koordinata uporabnikovega povprečja statistik poti in časa, centriranih na najhitrejšo pot, s PM ali HM; strežnik z ujemanjem momentov umeri usmerjevalnik | nova kombinacija; GeoPM-DMEIRL (FGCS 2024), PUTS (TKDE 2023) | 25 | izbran: modul C1 |
| C2 | Gravitacijsko regularizirana inverzija OD | en element robnih deležev (cona krajišča, pas stroška, obdobje) z GRR ali OLH, inverzija prek gravitacijskega priorja | nova kombinacija, ocenjevanje samo je bližnja različica L-SRR (CCS 2022) | 24 | izbran: modul C2, brez kordonov |
| C3 | Glas o javnem katalogu vedenj | ena oznaka režima iz zamrznjenega kataloga celotnih generatorjev z GRR; strežnik oceni uteži mešanice | nova kombinacija v obliki uteži; dvoboj je bližnja različica Gopi et al. (COLT 2020) | 23 | izbran: modul C3 |
| C6 | Spektralno polje na grafu | koeficienti nizkih lastnih vektorjev Laplaceove matrike cestnega grafa s PM | nova kombinacija, ozka; Duchi et al. (JASA 2018), Chedemail et al. (2022) | 20 | odložen |
| C5 | Glas o javni knjižnici poti | ena lastna pot, preslikana v najbližji arhetip javne knjižnice, z GRR | bližnja različica; Private Evolution (ICLR 2024), PrE-Text (ICML 2024) | 20 | zavrnjen |
| C4 | Aktivnostna sidra in urniki | ena reža opisa dom, delo in urnik s PM ali GRR | nova kombinacija; DP-WHERE (BigData 2013), OnTheMap (ICDE 2008) | 19 | odložen |
| C9 | N-grami žetonov manever × razred ceste | bigrami lokacijsko neodvisnih žetonov s frekvenčnim orakljem | bližnja različica; LDPTrace (PVLDB 2023), Cunningham et al. (PVLDB 2021) | 17 | zavrnjen |
| C7 | Regresija dobička verjetja z enim bitom | en bit o dobičku log-verjetja pri javno dodeljeni nastavitvi priorja | bližnja različica; Zhou in Tan (AAAI 2021) | 16 | zavrnjen |
| C8 | Prilagodljivo sito cestnih koridorjev | par ključ–vrednost (vozlišče cestne hierarhije, bit hitrosti) s PCKV, korelirano perturbacijo parov ključ–vrednost; spust po skupinah | nova kombinacija; AHEAD (CCS 2021), PCKV (USENIX Security 2020) | 15 | odložen do T-Drive |
| C10 | Orakelj tokov med conami | povprečni tok čez cone z Duchijevim mehanizmom na ℓ₂-krogli, projekcija na ohranitev toka | bližnja različica; LDPTrace (PVLDB 2023) | 13 | zavrnjen |

### 3.2 Kdaj bi se splačalo vrniti k neizbranim

- **C6:** odloči ga ena ura računanja na javnem grafu: ali nizki lastni vektorji pokrijejo
  mesto. Če ga pokrijejo, je ablacija (primerjava različic, ki se razlikujejo le v enem
  delu) »spektralni načini proti conam« v C2 (ena seja) ali zamenja cone C2; če sedijo na
  robnih delih grafa, je le znani Duchijev ocenjevalnik.
- **C4:** nov (poročila le o relacijah, na primer o razredu razdalje dom–delo, brez
  koordinat), a benchmark nepovezanih poti ne vidi koherentnih uporabnikov; sidra pri
  okoli 9 poteh niso definirana, taksiji pa jih nimajo. Smiseln šele ob vrednotenju
  povezanih sintetičnih uporabnikov; do takrat so poročila o relacijah tema za razpravo.
- **C5:** Private Evolution (zapis glasuje za najbližji javni vzorec) s šumom na napravi.
  Pri n ≈ 91 prevesi le 4–8 grobih tipov poti (dolžina, del dneva), geografije ne;
  izhodišče »javni prior plus en glas« že da roka C3 z enakomernimi utežmi. Vrnitev le
  kot poceni pošten naslednik v1 ali pri n ≈ 10 000 (64–256 arhetipov).
- **C7:** bližnja različica LDP Bayesove optimizacije in za parametre eksponentne družine
  manj učinkovita od ujemanja momentov v C1; pri n ≈ 91 oceni en ali dva gumba, ocena pa
  pogosto pristane na robu območja. Smiselna le za nelinearne gumbe (utež glavnih cest,
  ura konice) pri n ≈ 5000, kjer zmore 6–8 gumbov.
- **C8:** spust po hierarhiji v slogu AHEAD (prilagodljiva hierarhična razgradnja) pri
  n ≈ 91 ne steče, ker je skupina uporabnikov ena sama; bazen poti ne da končnega
  verjetja; koridorji zahtevajo nov izvoz imen cest iz OSM. Vrnitev le s T-Drive, kjer
  razloči koridorje nad 2–5 % prometa z njihovimi hitrostmi.
- **C9:** nova je le abeceda; pri n ≈ 91 podvaja vprašanja C1 o razredih cest in zavojih s
  šibkejšim generatorjem, brez vleka proti cilju pa sprehodi tavajo. Pri n ≈ 10 000
  postanejo pogosti bigrami merljivi; do takrat je abeceda le možna družina vprašanj C1.
- **C10:** SD na lok med conama je 0.4 pri ε = 2 ob tokovih 0.1–0.5, torej je pod ε ≈ 4
  enak priorju na vsaki stopnji Geolife; pri n ≈ 5000 dajo cone 3 × 3 SD 0.06–0.09.
  Kvečjemu roka za T-Drive; ohranimo le zamisel sprehoda, ki ohranja tok in zato ne rabi
  modela dolžine.

## 4. Izbrana zasnova: en mehanizem, trije moduli

### 4.1 Javni simulator (P3)

Vsi moduli umerjajo isti javni model poti iz OSM in citiranih konstant. Pri ε = 0 je to
roka priorja, z istim ocenjevalnikom brez šuma roka orakla; člani kataloga C3 so njegove
nastavitve, C2 mu da matriko OD, C1 umeri parametre poti in časa.

- **Usmerjevalnik:** Boltzmannov sprehod proti cilju: na vsakem vozlišču izbere povezavo z
  verjetnostjo, ki eksponentno pada z dodanim stroškom; preostali strošek do cilja da eno
  iskanje najkrajših poti nazaj od cilja (obratni Dijkstra). Po javni meji korakov se pot
  zaključi po najkrajši poti, zato je veljavna po cestah po konstrukciji.
- **Povpraševanje in čas:** izvor po javni masi dolžine cest, cilj po gravitacijskem
  modelu (privlačnost cone pada z razdaljo); odhod iz javnega priorja v pekinškem času
  UTC+8 (enakomeren, razen ob citiranem dnevnem profilu); čas na povezavi = čas prostega
  toka (OSM `maxspeed` ali privzeta hitrost razreda) × javni faktor × tresenje (AR(1),
  samoregresijski šum reda 1, ali lognormalno) + javna zamuda na zavoj.
- **Verjetje** je točno; javna spodnja meja verjetnosti na vsakem koraku pokrije
  nedosegljive cilje, vrzeli med povezavami in mejo korakov. **Predpomnilnik** po hashu
  zemljevida in konfiguracije je skupen 17 generatorjem roke (prevedena rutina najkrajših
  poti za okoli 1100 ciljev za vsako roko).

### 4.2 Poročilo uporabnika in delitev uporabnikov namesto ε

Poročilo je par (id modula, odgovor). Javni žreb, neodvisen od podatkov, izbere modul in
vprašanje v njem; uporabnik odgovori s celotnim ε. Vsak vpisani uporabnik pošlje natanko
eno poročilo fiksne velikosti, tudi brez ujete poti (javna privzeta vrednost). Javno
pravilo iz n·ε² določi delež uporabnikov po modulih in število vprašanj; pri majhnem n·ε²
gredo vsi v en modul. Koda se deli na `encode_user(views, public, rng) -> Report` na
napravi in `server_fit(reports, public) -> params` na strežniku, ki pogledov na poti ne
dobi (P4). Vsak modul najprej izide kot svoja roka, nato pride sestavljena.

**Zakaj delimo uporabnike in ne ε.** Odgovor na vse tri module z ε/3 bi stal okoli 3-krat
več variance kot delitev uporabnikov pri ε ≤ 2 in 7.5-krat (števila) do 85-krat (oznaka s
tremi vrednostmi) pri ε = 8; trije neodvisni mehanizmi nad istimi uporabniki bi po osnovni
kompoziciji stali 3ε, delitev pa da en dokaz v treh vrsticah in en ε na uporabnika. Napor
je kot za tri mehanizme (P3 že vsebuje sestavljeni model) in ena seja za pravilo
dodeljevanja; recenzent bere en sistem z ablacijami po modulih kot zasnovo, ne kot tri
okuse ene ideje. Sklopljenost (ena napaka pokvari vse roke) blažijo ločene roke modulov;
manjše število prispevkov nadomesti metoda vrednotenja (roki priorja in orakla, strukturna
revizija zasebnosti), ki jo trdimo kot samostojen prispevek.

### 4.3 Modul C3: glas o režimu iz javnega kataloga (prvi)

Oblika z utežmi mešanice (B.4, C.2 v gradivu); dvoboj (D.3) je objavljen kot lokalno
zasebna izbira hipoteze.

- **Na napravi:** oceni vse uporabnikove poti pod K javnimi celotnimi generatorji, ki se
  razlikujejo po poteh, hitrosti, profilu odhodov in upadu z razdaljo (pri n ≈ 91 trije
  režimi, na primer hoja ali kolo, mestna in hitra motorna vožnja), in iz aposteriorne
  porazdelitve po režimih izžreba eno oznako.
- **Popačenje:** GRR s celotnim ε (OLH pri K > 3e^ε + 2); žreb oznake je lokalna
  naključnost in proračuna ne troši; meja je končna javna domena oznak.
- **Strežnik:** odstrani pristranskost, skrči deleže proti enakomernim in z algoritmom
  pričakovanje–maksimizacija (EM) odstrani učinek matrike zamenjav (kako pogosto uporabnik
  režima i izžreba oznako j), simulirane enkrat na javnem grafu pod javnim številom poti
  na uporabnika.
- **Pot s časi:** izžrebaj režim, nato izvor po javni masi, cilj po upadu režima, odhod,
  pot in čase iz njegovega profila, usmerjevalnika in hitrosti.
- **Pri n ≈ 91:** trije deleži z SD 0.136 (ε = 1) oziroma 0.073 (ε = 2) pred
  dekonvolucijo (odstranitvijo učinka matrike zamenjav), točno pri deležih blizu 1/3
  (ugotovitev F4 v `NACRT_ULDP_RANGI.md` §10; prejšnji vrednosti 0.12 in 0.05 veljata le za
  izginjajoče deleže); dobiček v obliki porazdelitev trajanja in
  hitrosti (dvovrhost hoja proti vozilu, ki je ena hitrostna številka ne zajame);
  geografija ostane na priorju.
- **Pri velikem n (5000–10 000):** 24–48 razredov (regija, delavnik) in popravki po
  režimih (oznaka in en bit javno izbrane koordinate v enem GRR nad 2K vrednostmi); za
  taksije je zgodba šibka, ker so en sam način prevoza.
- **Benchmark in tveganje:** verjetja članov se izračunajo enkrat (K-krat okoli 1100
  dreves najkrajših poti za vsako roko) za vseh 17 generatorjev; roka z enakomernimi
  utežmi je izhodišče »javni prior plus ena oznaka«. Napačni režimi (avtobus z
  ustavljanjem je podoben kolesu) dajo skoraj ravno matriko zamenjav, ki ojača šum.

### 4.4 Modul C2: deleži izvorov in ciljev z gravitacijsko inverzijo (drugi)

Oblika z robnimi deleži con (B.2); kordonov (A.3) ni, ker se prekrivajo z objavljenim
ε-DP merjenjem prometa med točkama.

- **Na napravi:** deleži krajišč poti po Z javnih conah (9 = 3 × 3 pri n ≈ 91, 36–144 pri
  n ≥ 5000) ter deleži poti po šestih pasovih stroška prostega toka, petih obdobjih dneva
  in treh hitrostnih režimih: Z + 14 števil, neodvisno od velikosti grafa.
- **Popačenje:** eno vprašanje o enem lokalno izžrebanem krajišču ali poti: cona z OLH
  (verjetnost 0.4), pas, obdobje ali režim z GRR (po 0.2); celoten ε.
- **Strežnik:** s točno znano kovarianco šuma V reši T = argmin KL(T ‖ Q) + ½‖AT − t̂‖²,
  uteženo z V⁻¹ (KL je Kullback–Leiblerjeva divergenca, Q gravitacijski prior na stroških
  prostega toka med 144 conami, A preslika T v robne deleže t̂), s trosmernim Furnessovim
  skaliranjem (iterativnim proporcionalnim prilagajanjem po vrsticah, stolpcih, pasovih).
- **Pot s časi:** izžrebaj obdobje in par con, vozlišči po javni masi, pot z javnim
  usmerjevalnikom (za poti se proračun ne troši), čase po obdobju in razredu ceste.
- **Pri n ≈ 91:** pri ε = 2 deleži 3 × 3 z SD 0.06, če odgovarjajo vsi, in 0.10, če 40 %,
  ter upad z razdaljo; pri ε = 1 je SD 0.19, kar je mejno. Številke so ocenjevalčeve
  (konsolidacija je za 9 con pri ε = 2 navedla okoli 0.14). Metrike: JSD obiskov celic
  (edina že obstoječa sintetična metrika), W1 dolžin in JSD matrike OD 3 × 3.
- **Pri velikem n:** 36 con z SD 0.03–0.04 pri ε = 1 in OD po obdobjih s sklopitvijo
  izvor–cilj (jutranji dotok proti večernemu odtoku), klasična raba za taksije.
- **Benchmark in tveganje:** člen poti je javen in skupen 17 generatorjem, razlikuje se le
  tabela OD z največ 144 celicami; prispevek je le gravitacijsko sklopljena inverzija
  robnih deležev na ravni uporabnika kot stran povpraševanja časovnega generatorja.
  Krajišča Geolife morda niso dovolj zgoščena glede na maso dolžine cest (okvir zemljevida
  je morda obrezan na Geolife), zato dobička na JSD celic pri ε ≤ 2 morda ne bo; tega še
  nihče ni preveril.

### 4.5 Modul C1: vedenjski momenti in usmerjevalnik (tretji)

Najprej različica z Boltzmannovim sprehodom (C.1, D.2, E.3), ki se predpomni čez 17
generatorjev; točni rekurzivni logit (RL, model izbire poti z največjo entropijo; A.1,
B.1) bi zahteval 17 redkih faktorizacij z zasebnimi parametri in ogrozil proračun 300 s.

- **Na napravi:** za vsako ujeto pot nekaj odrezanih statistik (deleži razredov cest,
  zavoji na kilometer, obvoz ali dolžina, razmerje hitrosti do hitrosti prostega toka,
  harmoniki ure odhoda), večinoma kot razlika do javne reference iste poti (najhitrejše
  poti med istima krajiščema, hitrosti iz OSM); povprečje čez vse poti je
  x_u ∈ [−1, 1]^d, pri n ≈ 91 z d = 3–8, neodvisno od velikosti grafa.
- **Popačenje:** javni žreb izbere eno koordinato; številko pošlje PM, HM ali Duchijev
  enobitni mehanizem, kategorijo GRR, s celotnim ε. Povprečje je v javnem okviru ne glede
  na število poti; centriranje okvir zoži, trikrat ožji okvir pa potrebuje devetkrat manj
  uporabnikov.
- **Strežnik:** nepristranska povprečja z znano varianco projicira na dopustno množico,
  skrči proti javnemu priorju θ₀ in prilagodi peščico parametrov (stroški razredov, kazen
  za zavoj, temperatura obvoza ali upad z razdaljo, gostota odhodov, raven hitrosti), da
  se pričakovane statistike modela ujemajo z ocenjenimi; pravilo n·ε² določi število
  vprašanih koordinat.
- **Pot s časi:** izvor po javni masi, cilj po gravitaciji, Boltzmannov sprehod, odhod iz
  prilagojene krožne gostote ali deležev obdobij; čas na povezavi = čas prostega toka ×
  prilagojeni faktor hitrosti × tresenje (+ zamuda na zavoj).
- **Pri n ≈ 91:** pri ε = 2 se premakneta dve števili, razmerje hitrosti do OSM in merilo
  dolžine (W1 trajanja, hitrosti in dolžine); pri ε = 8 do okoli osem. Okusi izbire poti
  (obvoz, razred ceste, zavoji) ostanejo pri ε ≤ 2 na priorju in deloma opisujejo
  ujemalnik z zemljevidom, ki daje prednost najkrajšim potem, zato so momenti poti
  trditev za velik n.
- **Pri velikem n:** okoli 10–25 števil pri ε = 1–2 (ne »100 in več«), na primer faktorji
  hitrosti po razredu in obdobju (W1 trajanja po uri odhoda, napaka časa vožnje po
  razredu). T-Drive zabeleži točko le na okoli 3 minute, zato naj trditve slonijo na
  času, OD in dolžinah, ne na statistikah poti, ki so tam večinoma delo ujemalnika.
- **Novost pod vprašajem:** GeoPM-DMEIRL je presojan le po povzetkih iskalnikov. Če popači
  značilke na uporabnika in ne lokacij, je C1 bližnja različica in vodi le kot vedenjski
  modul; ostanejo mu statistika, centrirana na zemljevid, časovni model iz istega poročila
  in točno, navzdol omejeno verjetje z veljavnostjo po cestah.

### 4.6 Zasebnostni argument celotnega mehanizma

**Trditev:** mehanizem je čisti ε-LDP na ravni uporabnika: za katerakoli dva nabora poti
istega uporabnika (tudi prazen) se verjetnost kateregakoli poročila razlikuje največ za
faktor e^ε. **Dokaz:** (1) modul in vprašanje izbere javni žreb, neodvisen od podatkov;
(2) odgovor je standardni ε-LDP gradnik (GRR, OLH, PM, HM, Duchi) na javno omejeni
funkciji vseh uporabnikovih poti ali na eni poti, izbrani z od podatkov neodvisno
naključnostjo; (3) poročilo je eno, zato kompozicije ni, vse naprej je naknadna obdelava.
**Lahki del:** gradniki so standardni, meja je vgrajena v konstrukcijo, število poti ne
spremeni oblike poročila. **Subtilni del:** nič »javnega« (okvirji, referenčne hitrosti,
cone, katalog, pravilo števila vprašanj) ne sme izvirati iz učnih podatkov ali iz števila
uporabnikov z ujetimi potmi; nedefinirana statistika dobi javno privzeto vrednost; izhodi
se zaokrožijo na javno mrežo; C3 pošlje le oznako; strežnik se prilagaja le med ločenimi
skupinami uporabnikov; časovni model je v dokazu zajet, a ga napad MIA ne preizkusi (§6).

### 4.7 Kako se računa `sequence_log_prob`

Napad vidi le zaporedje povezav, zato časovni model ne vstopa. Za en režim je log-verjetje
log P(O, D) + vsota log-verjetnosti korakov sprehoda + javni člen za vrzeli; P(O, D) da
tabela OD (prior ali C2), koraki parametre poti (prior ali C1). Za mešanico C3 je
log Σ_k π̂_k · P_k(seq) z ocenjenimi utežmi π̂_k; kako se popravki C1 nanesejo na režime
C3, gradivo ne določa (odloči seja sestavljene roke). Funkcija bere le parametre in
predpomnilnike s ključem iz zemljevida in konfiguracije, strošek do cilja računa leno za
vsak poizvedovani cilj po isti poti kode za člane in nečlane, končnost pa zagotovi javna
spodnja meja verjetnosti.

### 4.8 Neobvezne razširitve

Prilagodljivo dodeljevanje pri velikem n (poznejše, ločene skupine po javnem pravilu k
modulu z najbolj negotovimi parametri); model mešalca (shuffle) kot ojačitev, a zunaj
jedra, ker zahteva zaupanja vreden mešalec; ablacija »spektralni načini proti conam« v C2,
če preverba C6 uspe; ravnovesje zastojev za C1 pri n ≈ 10 000 s funkcijo zamude BPR
(Bureau of Public Roads; čas vožnje glede na pretok), ki potrebuje objavljene zmogljivosti
cest; abeceda C9 kot družina vprašanj C1 pri velikosti T-Drive.

## 5. Kaj lahko Geolife pokaže in kako merimo

### 5.1 Šum pri n = 91

SD ocene ene koordinate pri n = 91 kot delež polovice razpona, s hibridnim mehanizmom HM
(nad ε ≈ 0.6 boljši od Duchijevega); d je število vprašanj, med katera se razdelijo
uporabniki. Prva vrednost je le šum, druga doda razpršenost med uporabniki 0.4 polovice
razpona, ki šteje šele pri ε = 8.

| d | ε = 0.5 | ε = 2 | ε = 8 |
|---|---|---|---|
| 1 | 0.43 | 0.11 / 0.12 | 0.017 / 0.045 |
| 2 | 0.61 | 0.15 / 0.16 | 0.023 / 0.064 |
| 4 | 0.86 | 0.21 / 0.23 | 0.033 / 0.090 |
| 8 | 1.21 | 0.30 / 0.33 | 0.047 / 0.13 |

**Pravilo: dobiček zahteva napako priorja okoli dveh SD.** Pri ε = 0.5 pogon z 91
uporabniki ne pokaže ničesar. Pri ε = 2 je dobiček le pri d ≤ 2 in napakah priorja okoli
0.3 polovice razpona ali več (d = 4 le za eno napako blizu 0.45); deluje tudi eno
kategorično vprašanje: trije deleži z SD 0.073 ali devet z 0.079 (0.11 za delež blizu
0.5), če odgovarjajo vsi, oziroma 0.126 ali 0.137, če tretjina; to velja točno pri
deležih blizu 1/k (ugotovitev F4 v `NACRT_ULDP_RANGI.md` §10; prejšnje vrednosti 0.05,
0.06, 0.08 in 0.11 veljajo le za izginjajoče deleže). Številke v tabeli zgoraj so
najslabši primer HM pri n = 91 in ostanejo. Pri ε = 8 deluje d ≤ 8 za napake od 0.1 do 0.25. Pri
stopnji 20 (n = 10) ima ena številka pri ε = 2 SD 0.42 (Duchijev mehanizem), zato je tam
vsak kandidat enak priorju in je stopnja le dimni test; pri n ≈ 5000 proračun kupi okoli
10–25 števil pri ε = 1–2.

### 5.2 Zgodba Geolife v treh točkah

Pošten odgovor je »ε = 8 za majhen model, ε = 2 za eno družino vprašanj, nikoli ε = 0.5«:
pri **ε = 0.5** je izhod enak priorju (negativni rezultat, ki ga teorija LDP napove); pri
**ε = 2** se sprašuje ena družina, zato so roke samo C1, samo C2 in samo C3 ablacija; pri
**ε = 8** se sprašuje majhna sestavljena roka. Pravilo dodeljevanja mora zato pri majhnem
n·ε² dati vse uporabnike enemu modulu; ε = 8 na ravni uporabnika postavimo ob 4.5–18, ki
ga roke na pot (ε = 0.5–2) dajo uporabniku z devetimi potmi; momenti poti C1 so le
trditev za velik n. Večina izmerjenega dokaza na Geolife bo iz C3 in C2 pri ε = 2.

### 5.3 Kaj šteje kot dokaz

Ves razdelek je predlog ocenjevalca; definicija dobička, referenca, seznam metrik in
pravilo izpusta so odprti v §7.1, točka 2.

- **Dokaz uporabe zasebnih podatkov** je dobiček nad zamrznjeno roko priorja kot delež
  vrzeli med priorjem in oraklom, (m_prior − m_roka) / (m_prior − m_orakelj) za metriko
  m, kjer je manj bolje: 0 je »ne bolje od priorja«, 1 »kot nezasebni strop«.
- **Metrike** (P2), ki naj se prijavijo vnaprej: časovno občutljive W1 trajanja, povprečne
  hitrosti in krožne ure odhoda; prostorske JSD celic, W1 dolžine in JSD matrike OD 3 × 3.
- **Referenca** naj bodo zadržani testni uporabniki. Ocenjevalnik na ravni uporabnika
  cilja povprečnega uporabnika, v referenci, uteženi po poteh, pa prevladujejo uporabniki
  z mnogo potmi, kar lahko delujoč ocenjevalnik prikaže slabšega od priorja; zato P2
  ponudi tudi utež po uporabnikih. Intervali so čez semena in testne uporabnike
  (bootstrap, to je ponovno vzorčenje s ponavljanjem, ki pokaže negotovost ocene).
- **Metrike, kjer niti orakelj ne premaga priorja,** naj se izpustijo; to ni neuspeh
  mehanizma.

### 5.4 Zakaj napad MIA ne razvrsti kandidatov

ε-LDP na ravni uporabnika omeji vsak test članstva s TPR ≤ e^ε · FPR (TPR in FPR sta
deleža pravih in lažnih zadetkov), zato je predlagani prag TPR ≤ 0.02 pri FPR 0.01
zajamčen le za ε ≤ ln 2 ≈ 0.69. Eno poročilo med 91 komaj premakne oceno, zato bodo vse
roke blizu naključja, kot že v1; tudi nezasebni strop `markov` je šibek (AUC, ploščina pod
krivuljo ROC, ki kaže TPR proti FPR pri vseh pragovih napada; 0.5 je ugibanje: 0.776 in
TPR 0.027 pri FPR 0.01 pri u182, AUC 0.542 pri u50). Pri ε = 8 AUC ni 0.5 po
konstrukciji (pri d = 4 eno poročilo premakne povprečje
koordinate za do 0.09 polovice razpona), zato signal nad naključjem ni samodejno napaka,
preverimo pa, da AUC z rastočim ε ne pada. Namesto razvrščanja dokazujemo strukturo
(§6.2): revizija naključnika, kanarček (umetno dodan uporabnik z ekstremno potjo), test,
da `sequence_log_prob` bere le parametre in zemljevid, ter pozitivna kontrola, ki pokaže,
da napad zazna namerno vgrajeno puščanje.

### 5.5 Simulacija obnovitve parametrov (P6)

- **Resnica:** θ* je prilagoditev roke orakla na učnih uporabnikih u182, rabljena le za
  generiranje, nikoli kot prior ali v sproščenem modelu; dodata se dva javna odmika od
  θ₀, da izid ni odvisen od tega, kje Geolife slučajno leži.
- **Sintetični uporabniki:** θ_u = θ* plus razpršenost med uporabniki iz orakla; število
  poti prevzorčeno iz u182; poti ustvari skupni model na pekinškem grafu, po cestah in s
  časi; teče ista koda `encode_user` in `server_fit` kot na pravih podatkih.
- **Mreža:** n = 10, 25, 91, 300, 1000, 3000 in 10 000; ε ∈ {0.5, 2, 8}; vsaj 20 semen.
- **Merimo** napako in pokritost intervalov po parametrih, število parametrov, katerih
  interval izključi prior, in delež vrzeli prior–orakelj na metrikah uporabnosti proti
  zadržanim simuliranim uporabnikom (vrednotenje omenja »pet metrik«, ne da bi jih
  naštelo, P2 jih predvideva šest; izbor je del §7.1, točka 2).
- **Prikaz:** panel na metriko, n na logaritemski osi, simulirani pasovi po ε, prave
  vrednosti u20, u50 in u182 kot točke z intervali; če padejo v pasove, je simulacija
  potrjena, njen konec pri n = 10 000 pa pokaže isti ocenjevalnik na populaciji,
  umerjeni po Geolife.
- **Meje:** en napačno specificiran pogon (simuliraj iz mešanice C3, prilagodi C1); učinki
  ujemalnika in vedenje taksijev niso zajeti; to bi dodal šele nalagalnik T-Drive.

## 6. Zasebnostna tveganja in varovala

Ugotovitve »rdeče ekipe«. Napad MIA bi večino teh puščanj spregledal, zato jih zapirata
konstrukcija in testi.

### 6.1 Skupna tveganja

- **Sodelovanje:** `fit` vidi le uporabnike z ujeto potjo; v resnični rabi bi »poslal je
  poročilo« razkrilo »ima ujeto pot«. Vsak vpisani uporabnik zato pošlje natanko eno
  poročilo fiksne velikosti; kdor nima poti, pošlje javno privzeto vrednost.
- **Metapodatki:** poročilo ne razkrije števila poti (več poti ne pomeni več vprašanj ali
  obeh krajišč vsake poti, meja vzorčenja ni iz porazdelitve poti na uporabnika),
  časovnega razpona zbiranja ali tega, ali uporabnik sploh poroča.
- **Naključnost in vrednosti:** naključnost naprave ni odvisna od podatkov (ne seme iz
  `traj_id`) in je strežnik ne vidi; vrednosti pred šumom ne pridejo v dnevnik, `run.json`
  ali predpomnilnik; izhodi PM in Laplacea se zaokrožijo na javno mrežo, sicer nizki biti
  števila s plavajočo vejico razkrijejo pravo vrednost.
- **Čas ni napaden:** model odhodov ali hitrosti na surovih časih bi bil nezaščitena
  izdaja, ki je nobena številka benchmarka ne bi razkrila.

### 6.2 Skupna varovala (P4)

- **Razrez** na `encode_user(views, public, rng) -> Report` in
  `server_fit(reports, public) -> params`; strežniški del pogledov ne dobi.
- **Javni deli brez pogledov:** katalog, OD-prior, mase con, stroški povezav in ključi
  predpomnilnika nastanejo iz zemljevida in konfiguracije s konstruktorji, ki ne sprejmejo
  nobenega pogleda na poti; vse je zajeto v `params_hash`.
- **Štirje testi:** (1) parametri ostanejo enaki, ko se surovi pogledi spremenijo,
  poročila pa ne; (2) revizija naključnika: empirično log-razmerje frekvenc izhodov dveh
  skrajnih uporabnikov je največ ε v mejah vzorčne tolerance; (3) kanarček, uporabnik z
  ekstremno potjo; (4) `sequence_log_prob` bere le parametre in predpomnilnike s ključem
  iz zemljevida in konfiguracije.
- **Pozitivna kontrola:** namerno puščajoča roka C1 (na primer strošek »domačnosti«
  povezav iz učnih poti) dokaže, da napad ta razred puščanja zazna.

### 6.3 Po modulih: puščanje, napad, zapora

- **C1.** *Puščanje:* preskok pri nedefinirani statistiki; referenčna hitrost ali okvir iz
  učnih podatkov (na primer mediana učnih hitrosti namesto OSM `maxspeed`); pri ε ≥ 4 k
  odgovorov z ε namesto z ε/k; več vprašanj za uporabnike z več potmi; pravilo števila
  vprašanj iz števila uporabnikov z ujetimi potmi. *Napad:* člen domačnosti ali velikosti
  poti (path-size) iz učnih poti dvigne verjetnost redkih povezav članov, LiRA (napad MIA
  z razmerjem verjetij) pa jih loči pri nizkem FPR, kot pri `markov`; podobno deluje
  predpomnilnik stroška do cilja le za učne cilje, saj nečlani gredo skozi nadomestno pot
  kode in dobijo drugačne log-verjetnosti. *Zapora:* stroški povezav le iz zemljevida in
  parametrov; strošek do cilja leno za vsak cilj z eno javno funkcijo; testa 1 in 4.
- **C2.** *Puščanje:* obe krajišči vsake poti (m·ε); cone, pasovi ali obdobja na kvantilih
  podatkov; meja vzorčenja iz porazdelitve poti na uporabnika; upad z razdaljo, prilagojen
  na Geolife. *Napad:* vozlišče v coni po empirični masi učnih krajišč namesto po masi
  dolžine cest, zato P(vozlišče | cona) dobi špico na krajiščih članov, `generate` pa
  oddaja poti z domov članov. *Zapora:* mase v conah, cone, pasovi, obdobja, upad in utež
  KL (moč vleka proti priorju) iz zemljevida in konfiguracije, zajeti v `params_hash`;
  utež KL nikoli s prečnim preverjanjem na učnih podatkih; testi 1–4.
- **C3.** *Puščanje:* razlika verjetij ali cela aposteriorna porazdelitev namesto oznake;
  konstante kataloga ali število režimov iz statistik S4 ali po ogledu prilagoditev;
  matrika zamenjav iz razvrščanja pravih učnih poti namesto simulacije iz javnih članov.
  *Napad:* »realističen« član kataloga, prilagojen na učne poti (na primer Markovov model
  nad povezavami), da mešanici pomnilno komponento, ki jo LiRA prebere neposredno.
  *Zapora:* le javni modeli s citiranimi konstantami, zamrznjeni s hashem commita pred
  prvim pogonom pri 182; simulirana matrika zamenjav; samo oznaka v poročilu; testi 1–4.

## 7. Odprte odločitve

### 7.1 Na ravni mehanizma

Ocenjevalčev seznam v vrstnem redu, v katerem blokira delo; vire priorja in zamrznitev je
zaprla odločitev 2, pot do dokaza za velik n odločitev 3, sestavljeno roko odločitev 1.
Termini ob točkah (»pred P3« in podobni) niso ocenjevalčevi: vrednotenje daje le vrstni
red, termine je iz vrstnega reda sej (§8.2) izpeljal pisec tega načrta.

1. **Katere roke priorja:** ali poleg skupne roke priorja vodimo še lastno roko ε → 0
   vsakega modula za trditev, da so bili zasebni podatki uporabljeni; v praksi: koliko
   rok priorja ima konfiguracija. Pred P3.
2. **Dokaz uporabnosti:** referenca (predlog: zadržani testni uporabniki), utež po
   uporabnikih ali po poteh, vnaprej prijavljene primarne metrike, definicija dobička
   (§5.3), izpust metrik, kjer niti orakelj ne premaga priorja; v praksi: kaj implementira
   P2. Pred koncem P2, primarne metrike najkasneje pred prvim pogonom pri 182.
3. **Enota zasebnosti v ogrodju:** zasnova zahteva, da poroča vsak vpisani uporabnik
   (tisti brez ujete poti s privzeto vrednostjo; §4.2, §6.1); pri tem je odprto le, kako
   orkestrator doseže uporabnike brez ujete poti. Odprto je še, ali kandidati MIA
   vstopajo v senčne prilagoditve kot uporabniki z eno potjo ali pod svojim `user_id` in
   ali je število vprašanj fiksirano s konfiguracijo, da imajo tarča in sence enako
   strukturo modela. Po P0, ki prinese dejstva, in pred P5.

   **Dejstva (preverjeno s P0, 10. 10. 2026; test `tests/test_uldp_user_wiring.py`).**
   Odločitve so že sprejete (F3 in P11: `fit` dobi vse učne uporabnike, uporabnik brez
   ujete poti pošlje javno privzeto vrednost, n se šteje iz učnega dela, kandidati MIA
   vstopijo v senčne prilagoditve pod svojim `user_id`, število vprašanj fiksira
   konfiguracija); spodaj je, kako ogrodje deluje danes, preden to izvedeta P5 in P11.
   - Tarčni `fit` dobi en pogled na vsako ujeto učno pot, vsak z izpolnjenim `user_id` in
     `split == "train"`, v obeh predstavitvah (segmenti in celice): pogled ovije čisto
     pot (`experiments/orchestrator.py:647–651`, klic `:1503`), `user_id` pa se bere iz
     nje (`representation/views.py:123`). Združevanje pogledov po `user_id` da natanko
     učne uporabnike fiksture.
   - Poti brez uspešnega ujemanja (pod `min_match_score`) v `fit` ne pridejo:
     `clean_by_id` obdrži le ujete poti (`orchestrator.py:921–922`), bazen MIA pa bere le
     njih (`:1437–1440`). Uporabnik, ki mu ne uspe nobena pot, danes ne pošlje ničesar
     (F3 drži). Pri celicah se nič ne izpusti. Poti, ki jih zavrže čiščenje
     (`:911`), ne dobijo niti oznake delitve.
   - Senčne prilagoditve LiRA dobijo gola zaporedja (`attacks/membership.py:141`,
     `:189–191`): vsak kandidat, član ali nečlan, vstopi kot anonimno zaporedje z eno
     potjo, brez `user_id`, `traj_id` in oznake delitve. Če bi pogledi kandidatov nosili
     čisto pot, bi varovalo v `fit` (na primer `synthesis/markov.py:55`) zavrnilo nečlane
     z oznako `test`; P5 mora `user_id` zato prenesti brez te oznake.
   - n danes šteje poti, ne uporabnikov: noben generator ne bere `user_id` (v
     `synthesis/` ga ni nikjer), `ldptrace` šteje `n = len(seqs)` (`ldptrace.py:257`), in
     `split_counts` v `run.json` šteje poti po delih (`orchestrator.py:918`). Število
     učnih uporabnikov po P11 je treba šteti iz delitve (`datasets/split.py:14`), ne iz
     ujetih poti.
4. **Časovno občutljiv napad MIA:** časovni model je največja nova zasebna izdaja in ga
   noben napad ne preizkusi; če da, se doda P8 (napor M). Pred prvimi meritvami modulov,
   da je nabor napadov fiksen vnaprej.
5. **Pravilo dodeljevanja:** javno pravilo števila vprašanj (n·ε²), razdelitev uporabnikov
   med C1, C2 in C3, ali ostane mreža ε {0.5, 2, 8} in kako se popravki C1 nanesejo na
   režime C3. Število vprašanj pred sejo modula, razdelitev in sestava pred sejo
   sestavljene roke.
6. **Pragovi uporabnosti in pretvorba ε:** prage uspeha dogovori z mentorjem; določi tudi,
   kako se mehanizmi na pot v primerjalnih grafih pretvorijo v ε na ravni uporabnika
   (m·ε). Pred primerjalnim zvezkom in poročilom.

### 7.2 Na ravni modulov (pred sejo modula)

- **C3:** katalog treh režimov s citiranimi konstantami; ali pekinški graf vsebuje pešpoti
  in kolesarske steze (P9), ker od tega zavisi, ali se režimi razlikujejo po poteh ali le
  po hitrosti.
- **C2:** mreža con (predlog 3 × 3 čez javni okvir zemljevida), pasovi stroška, obdobja.
- **C1:** seznam statistik, javno pravilo števila vprašanj za vsak par (n, ε) in branje
  celotnega besedila GeoPM-DMEIRL (P9) pred prvo vrstico kode.

## 8. Predpogoji P0–P5 in načrt sej

### 8.1 Predpogoji

Napor: S majhen, M srednji, L velik; seja je en delovni blok z AI pomočnikom. P0–P5 so
pred prvim modulom in skupaj stanejo približno toliko kot en mehanizem (4–6 sej).

| # | Predpogoj | Napor | Blokira |
|---|---|---|---|
| P0 | Preveri uporabniško napeljavo: ali ima vsak pogled v `fit` (tarča in sence) izpolnjen `user_id`, kateri `user_id` nosijo kandidati MIA v senčnih prilagoditvah in ali poti brez uspešnega ujemanja pridejo v `fit`. Test nad fiksturo preveri `all(v.user_id for v in train_views)`, preveri, da združevanje po `user_id` da učne uporabnike fiksture, in zabeleži `user_id` kandidatov v eni senčni prilagoditvi | S (manj kot ura) | vse na ravni uporabnika |
| P1 | Časovni sintetični payload: identifikatorji povezav, čas odhoda in čas vstopa na vsako povezavo, v lokalnem času UTC+8 (izrecno zapisano), serializiran v Parquet | S | vse tri module |
| P2 | Neparne metrike sintetične uporabnosti v orkestratorju: JSD celic in W1 dolžine prestavi iz `rnldp_eval`, dodaj W1 trajanja, povprečne hitrosti in krožne ure odhoda ter JSD matrike OD 3 × 3; utež po uporabnikih kot možnost, zadržana referenca, intervali bootstrap; posodobi shemo rezultatov in njen pripeti dokument | M (1–2 seji) | vse tri |
| P3 | Skupni javni model iz §4.1 (Boltzmannov sprehod s točnim, navzdol omejenim verjetjem, gravitacijski OD, prior odhodov, hitrosti prostega toka s tresenjem, predpomnilnik po hashu zemljevida in konfiguracije); pri ε = 0 roka priorja, na statistikah brez šuma roka orakla, osnova kataloga C3 | M (1–2 seji) | vse tri |
| P4 | Zasebnostni komplet: razrez `encode_user` / `server_fit` in testi 1–4 iz §6.2 | S–M (1 seja) | vse tri |
| P5 | Preverbe ogrodja iz §7.1, točka 3, in ε na ravni uporabnika v `run.json` za vsako roko | S | pogone MIA |

Pozneje ali ob strani: **P6** simulacija obnovitve (S–M, §5.5); **P7** nalagalnik T-Drive
(L, 2–4 seje; tveganje, da ujemalnik odpove pri redkih točkah; le po potrebi); **P8**
neobvezni časovno občutljivi napad MIA (M); **P9** dve enourni preverbi: razredi cest v
grafu (pred C3) in celotno besedilo GeoPM-DMEIRL (pred C1).

### 8.2 Vrstni red sej (navpične rezine)

Vsak korak je ena veja in en PR in se konča z izidom, ki ga je mogoče preveriti.

1. **P0 + P1** (ena seja; prompt v §8.3).
2. **P2** (1–2 seji): metrike, brez katerih noben modul ne more pokazati dobička.
3. **P3** (1–2 seji): javni model; z njim obstajata roki priorja in orakla.
4. **P4 + P5** (okoli ena seja): zasebnostni komplet in preverbe ogrodja.
5. **C3** (2 seji; prompt po §8.4): prva merljiva roka; začne s preverbo razredov cest.
6. **C2** (2 seji).
7. **C1** (3–4 seje), po branju GeoPM-DMEIRL, z Boltzmannovim sprehodom.
8. **Sestavljena roka s pravilom dodeljevanja** (1 seja).
9. **Simulacija obnovitve parametrov P6** (S–M).
10. **Meritve** pri stopnjah 20, 50 in 182 (stopnja 20 je le dimni test), z zamrznitvijo
    priorja pred prvim pogonom pri 182 in zapisom izmerjenega v `docs/HANDOFF.md`.

Po ocenah vrednotenja je to okoli 12–15 sej pred simulacijo in meritvami.

### 8.3 Prompt za prvo sejo (P0 + P1)

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_ULDP_SINTEZA.md SAMO §0, §1, §7.1 (točka 3) in §8.1 (vrstici P0 in P1); arhiva
arhiv/ ne odpiraj. Za branje kode o tem, kako orkestrator in napad MIA kličeta fit (kateri
pogledi pridejo v tarčni in senčne fit, s katerim user_id, ali tudi poti brez uspešnega
ujemanja z zemljevidom), uporabi svežega podagenta general-purpose, ki vrne kratek
povzetek; glavni kontekst naj ostane čist.

Naloga P0: test nad fiksturo v tests/, ki preveri all(v.user_id for v in train_views) in
da združevanje po user_id da učne uporabnike fiksture ter v eni senčni prilagoditvi
zabeleži user_id kandidatov; ugotovitve vpiši v §7.1, točka 3, kot dejstva, ne odločitve.
Naloga P1: časovno opremljen sintetični payload (identifikatorji povezav, čas odhoda in
čas vstopa na vsako povezavo v lokalnem času UTC+8, izrecno zapisano, ker Geolife hrani
čas v GMT), serializiran v Parquet; test, da payload prestane zapis in branje brez izgube
in s pravim časovnim pasom. Obstoječi generatorji ostanejo nespremenjeni.

Postopek: začni v plan mode in počakaj na mojo potrditev. Naloga je majhna, zato skill
orchestrate ni potreben; če bi presegla ~5 datotek ali mešala teme, najprej predlagaj
razrez. Ustvari vejo claude/uldp-p0-p1. Definicija končanega: uv run ruff check ., uv run
mypy src in uv run pytest -q čisti; prilepi ukaz in zadnjih ~10 vrstic izpisa. Proračun
izpisa: pytest -q, nikoli -v, ob napaki ponovi le padli test; dolge izpise skrajšaj s
| tail -20; najprej git diff --stat. V istem PR posodobi vrstico stanja v CLAUDE.md in
označi P0 in P1 kot zaključena v §8.1 načrta. Koda, identifikatorji, docstringi in testi
v angleščini; pogovor z mano v slovenščini, brez nepojasnjenih kratic.
```

### 8.4 Predloga prompta za sejo modula

Pred rabo zamenjaj oznake v lomljenih oklepajih; odločitve prepiši iz §7.2, ko jih avtor
potrdi.

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_ULDP_SINTEZA.md SAMO §4.1, §4.2, <§4.3 | §4.4 | §4.5> (modul <Cx>), §4.6, §4.7,
§6 in §7.2; arhiva arhiv/ ne odpiraj. Predpogoji P0–P5 so v main: skupni javni model (P3)
in zasebnostni komplet (P4) uporabi, ne podvajaj.

Naloga: implementiraj modul <Cx> (<ime modula>) kot par encode_user / server_fit nad
skupnim javnim modelom in ga izpostavi kot roko »samo <Cx>« generatorja, ki podeduje
SyntheticGenerator in je registriran z @register("generator", "<ime>"); imena in poti
modula načrt ne določa, predlagaj ju v planu. Potrjene odločitve iz §7.2: <seznam>. Kjer
bi od načrta odstopil, to najprej predlagaj. Konfiguracija: roka priorja (ε → 0), roka
orakla in roke <Cx> pri ε ∈ {0.5, 2, 8}; vsaka javna konstanta ima v konfiguraciji citat.

Postopek: začni v plan mode in počakaj na mojo potrditev. Seja modula je večja naloga,
zato jo vodi skill orchestrate (orkestrator, sveži izvajalci, en recenzent); če bi korak
presegel ~5 datotek ali mešal teme, najprej predlagaj razrez. Ustvari vejo
claude/uldp-<cx>. Testi: testi 1–4 iz §6.2 za ta modul in končnost sequence_log_prob nad
fiksturo. Definicija končanega: uv run ruff check ., uv run mypy src in uv run pytest -q
čisti; prilepi ukaz in zadnjih ~10 vrstic izpisa. Proračun izpisa: pytest -q, nikoli -v;
dolge izpise skrajšaj s | tail -20; dolgi pogoni tečejo v ozadju, prebereš le run.json in
zadnje vrstice dnevnika. Če imam lokalno Geolife in maps/beijing, poženi roke pri u20 kot
dimni test in vrstice zapiši v docs/HANDOFF.md. V istem PR posodobi vrstico stanja v
CLAUDE.md in označi korak kot zaključen v §8.2 načrta. Koda, identifikatorji, docstringi
in testi v angleščini; pogovor z mano v slovenščini, brez nepojasnjenih kratic.
```

## 9. Viri

Obvezni citati po modulih iz preverb novosti; povezave in citati za neizbrane kandidate so
v arhivu (`30_novelty_*.md`). Kjer gradivo ne navaja prizorišča, sta navedena avtor in
leto.

- **Priporočen okvirni vir za vse module (ni obvezen citat):** Kent, Berrett, Yu, *Rate
  optimality and phase transition for user-level local differential privacy*, arXiv
  2405.11923 (2024, revidirano 2026): teorija LDP na ravni uporabnika.
- **C1:** Du et al., LDPTrace (PVLDB 2023) z RetraSyn (Hu, Du et al., ICDE 2024),
  izhodišče LDP-sinteze, katerega tabele velikosti zemljevida C1 nadomesti; Huang et al.,
  GeoPM-DMEIRL (Future Generation Computer Systems 2024), LDP z inverznim spodbujevalnim
  učenjem največje entropije in prvi ugovor »to je že narejeno«; Sun et al., PUTS (IEEE
  TKDE 2023) z MTNet (Wang et al., PVLDB 2022), časovna sinteza na cestnem omrežju pod
  centralno DP; Wang et al. (ICDE 2019; PM, HM in vzorčenje koordinat) z Ziebart et al.
  (2008, inverzno spodbujevalno učenje z največjo entropijo) in Fosgerau, Frejinger,
  Karlström (2013, rekurzivni logit). Priporočeno še DP-WHERE (Mir et al., IEEE BigData
  2013), centralni prednik zasnove »nekaj vedenjskih gumbov poganja simulator«.
- **C2:** L-SRR (Wang, Hong, Xiong, Qin, Hong; ACM CCS 2022); LDPTrace (PVLDB 2023); Van
  Zuylen in Willumsen (1980) z Wilsonom (1967) za entropijsko oziroma gravitacijsko
  inverzijo; DPMM (Haydari et al., ACSAC 2022) za zasebni OD z usmerjanjem po cestah.
- **C3:** Gopi et al., *Locally private hypothesis selection* (COLT 2020) s Kamath et al.
  (arXiv 2509.16180, 2025); Lin et al., Private Evolution (ICLR 2024) s Sim-PE (delavnica
  ICLR 2025); Greene in Hensher (Transportation Research Part B, 2003), modeli izbire z
  latentnimi razredi.
