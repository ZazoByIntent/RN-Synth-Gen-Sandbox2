# Načrt: kontrasti časov po odsekih znotraj poti pod LDP na ravni uporabnika (T3)

Stanje ob zapisu: 9. oktober 2026, izhodišče je commit `19e7555` z načrtom drugega kroga
(ta še ni združen v `main`, ki je na `5db5f56`). To je **načrt**: nič od opisanega še ni
implementirano. Povzema tretji krog ideacije istega dne; surovo angleško gradivo je v
`arhiv/brainstorm_2026-10-09/` in je zapis, ne navodilo za delo. Načrt dopolnjuje
`docs/NACRT_ULDP_SINTEZA.md` in `docs/NACRT_ULDP_RANGI.md` in ju ne nadomešča. *Zasnova §4*
tu pomeni izbrano zasnovo prvega kroga (en mehanizem z moduli C1, C2 in C3), *zasnova
K1 + K8* izbrano zasnovo drugega kroga (umerjanje z rangi); razdelki drugih dokumentov so
navedeni z imenom datoteke, gola oznaka § kaže na ta načrt. Seja prebere le razdelke, ki jih
našteje njen prompt (§9.3); najdeš jih z `grep -n '^#'`.

## Kazalo

- §0 Namen, stanje in odločitve
- §1 Raziskovalna vrzel in omejitve
- §2 Kako je izbor nastal
- §3 Banka kandidatov T1–T6 (3.1 tabela, 3.2 kdaj se vrniti k neizbranim)
- §4 Izidi preverjanja novosti (4.1 izbrana zasnova, 4.2 neizbrani kandidati, 4.3 meje iskanja)
- §5 Izbrana zasnova (5.1 poročilo, 5.2 strežnik, 5.3 sinteza, 5.4 verjetje, 5.5 zasebnost)
- §6 Kaj lahko Geolife pokaže in kako merimo (6.1 javna preverba, 6.2 šum pri n = 91,
  6.3 le simulacija, 6.4 kontrolne roke in metrike)
- §7 Tveganja in varovala
- §8 Odprte odločitve
- §9 Predpogoji in načrt sej (9.1 predpogoji, 9.2 vrstni red, 9.3 prompt za prvo sejo)
- §10 Viri

## 0. Namen, stanje in odločitve

**Glavna poanta.** Tretji zaščitni mehanizem bo **kontrast časov po odsekih znotraj poti**
(kandidat T3 tretjega kroga). Kot obe prejšnji zasnovi je mehanizem lokalne diferencialne
zasebnosti na ravni uporabnika (LDP: vsak uporabnik podatke naključno popači na svoji
napravi; zaščiten je cel uporabnik z vsemi potmi iz obdobja zbiranja), ki umerja javni
simulator poti P3 iz OpenStreetMap (OSM, odprti zemljevid) in citiranih konstant. Telefon
znotraj ene svoje poti primerja hitrost na 100 m dolgih kosih ulice s trgovinami in na
podobnih kosih iste poti brez njih, nekaj minut narazen in daleč od križišč, semaforjev in
postajališč; hitrost meri glede na javni model. Ker obe strani primerjave prevozi isti človek
na isti poti, se njegova lastna hitrost in način potovanja (hoja, avtobus, avto) izničita.
Pošlje enega od štirih odgovorov (počasneje, enako, hitreje, ni uporabnega para) z naključnim
odgovorom pri polnem zasebnostnem proračunu ε. Strežnik s točnim testom preveri, ali sta
»počasneje« in »hitreje« enako pogosta; če nista, oceni en faktor, za koliko ulica s
trgovinami upočasni gibanje, in ga uporabi za čase po odsekih in stroške usmerjevalnika
sintetičnih poti. To je edina izbira tretjega kroga, ki doda nekaj, česar nobeden od obeh
načrtov nima: zasebni popravek časovne zgradbe znotraj poti iz kontrasta znotraj ene poti
(zahteva R1); obe načrtovani zasnovi pri n = 91 popravita le raven hitrosti oziroma trajanje
cele poti.

**Stanje.** Tretji krog ideacije je bil zaključen 9. oktobra 2026; nič ni implementirano.
Mehanizem se začne graditi šele, ko vnaprej prijavljena javna preverba (odločitev 2, §6.1)
potrdi eno od dveh plasti fasade; pred tem pridejo skupni predpogoji, med njimi razrez sej
ob postankih (P10), ter nova P13 in P14 (§9.1).

**Odločitve avtorja, 9. oktober 2026.**

1. **Izbran je T3 v obliki po krogu ugovorov** (arhiv: `40_evaluation.md` §6,
   `41_rebuttals.md`, `45_digest.md`): ostane le kategorična parna oblika s fasado;
   spremenljivka križišč in številska oblika z zamudo v križiščih sta opuščeni (bližnja
   različica dela Roth in Avella-Medina 2025). Par sta dve 100 m okni sredi odseka brez
   križišč, enake dolžine, iz iste skupine razredov ceste in iste poti, največ 3 minute
   narazen, obrezani za 40 m ob vozliščih ter za 80 m pred semaforji in ob avtobusnih
   postajališčih; hitrost se meri glede na P3. Vsak uporabnik pošlje en odgovor (počasneje,
   enako, hitreje, ni uporabnega para) s posplošenim naključnim odgovorom (GRR) pri polnem ε;
   strežnik s točnim pogojnim binomskim testom preveri, ali fasada vpliva na čas, in šele ob
   zavrnitvi z urejenim probitom oceni en faktor upočasnitve ob fasadi za čase po odsekih in
   stroške usmerjevalnika sintetičnih poti (§5).
2. **Javna preverba pred zamrznitvijo je vnaprej prijavljena** (okoli ena ura, le P3, brez
   podatkov Geolife; P15, §6.1), kot jo je v krogu ugovorov zapisal predlagatelj T3, z
   dopolnili ocenjevalca: najprej razrez sej (P10); delež uporabnikov brez para se presoja v najslabšem
   primeru od 1 do 30 poti na uporabnika, ne pri povprečju Geolife 9 poti; obrez tudi ob
   avtobusnih postajališčih; za meritve je skupaj s preverbo vnaprej prijavljena placebo roka
   (§6.4); pravilo »obdrži, zamenjaj, ustavi« ima vnaprej določene pragove (najprej fasada s
   trgovinami, nato pozidana fasada v 30 m).
3. **Pravilo za umik je vnaprej prijavljeno** (tudi §8, točka 2). Če preverba pade za obe
   plasti fasade, postane T3 modul za velik n, prikazan le v simulaciji obnovitve parametrov
   (P6), mehanizem tretjega kroga pa postane T1 z vprašanjem T4 o relaciji obeh koncev poti
   (kombinacija K-α vrednotenja, §3); njegov načrt se tedaj napiše v novi seji.
4. **T1 je priporočen kot poceni vprašanje o cilju v zasnovi K1 + K8** (§3.2, §8). O tem
   odločajo seje K1; v `docs/NACRT_ULDP_RANGI.md` §8 je za to dodana točka 11.
5. **Nova metrika je predpogoj:** vnaprej prijavljena metrika hitrosti v oknih (P16, §6.4)
   se računa enako za vse roke. Novi predpogoji nadaljujejo številčenje za P12 (P13–P16).
6. **Poštenost.** Načrt in članek T3 imenujeta »K8, razširjen s kontrastov med potmi na
   kontraste znotraj poti po spremenljivki povezave« (»K8 extended from across-trip to
   within-trip contrasts on an edge covariate«); sodba novosti je NOVEL COMBINATION s srednjo
   zanesljivostjo, najbližje delo Roth in Avella-Medina (2025). Pri ε = 2 se vidi le
   upočasnitev za okoli 15 % ali več (1.6 do 2.5 standardnega odklona, SD, odvisno od deleža
   uporabnikov brez para). Napad s sklepanjem o članstvu (MIA) učinek vidi le šibko, prek
   stroškov usmerjevalnika; pravi preizkus bi bil časovno občutljiv napad (P8). Mehanizem je
   odvisen od razreza sej (P10); preverba novosti je imela omejitve (§4.3).
7. **Ne odpira se:** S1–S5, odločitve obeh prejšnjih načrtov, nabor leč tretjega kroga ter
   opuščena kandidata T5 in T6, katerih jedri sta objavljeni.
8. **Surovo gradivo je arhivirano** v `arhiv/brainstorm_2026-10-09/`. Kandidati tretjega
   kroga imajo oznake T1–T6, surove ideje se navajajo po leči in številki (R3-D.3 je »ura
   fasade«, frontage clock, jedro T3).

**Razmerje do prejšnjih načrtov.** T3 ne spremeni nobenega modula zasnove §4 in nobenega
vprašanja zasnove K1 + K8; je svoja roka s svojim poročilom in si z obema deli predpogoje
P0–P6 in P10–P12 (P8 neobvezno). Od drugega kroga prevzame *nosilec*, to je obliko
poročila in strežnika postavke K8 (en razred kontrasta z GRR, ravnotežje znakov kot točen test, urejeni probit za velikost);
nova je ocenjevana količina, kontrast med odseki iste poti po javni lastnosti ceste (§4.1).

**Izrazi.** *Roka* je nastavitev v konfiguraciji poskusa; *roka priorja* je isti generator
brez zasebnih poročil (ε → 0; manjši ε pomeni močnejšo zaščito), *roka orakla* isti
ocenjevalnik na točnih statistikah (ε = ∞); *prior* je model iz samih javnih virov; *stopnja*
je velikost populacije Geolife (u20, u50, u182). *Okno* je 100 m dolg kos ceste sredi
odseka med dvema križiščema; *fasada* je to, kar obdaja cesto (trgovine, stavbe, zidovi,
parki); *ostanek* okna je naravni logaritem razmerja med izmerjenim časom in časom javnega
modela, v *natih* (0.15 nata pomeni okoli 15 do 16 % več časa). *GRR* pošlje eno od k javnih
vrednosti, z znano verjetnostjo pravo, sicer naključno drugo; *HM* (hibridni mehanizem)
popači eno število z omejenim razponom; *PIT* (probability integral transform) je delež med
0 in 1, ki je pri pravilnem modelu enakomerno porazdeljen; *⊥* je odgovor »nimam podatka«.
Razlika okoli 2 SD je najmanjša, ki jo še ločimo od šuma; W1 (Wassersteinova razdalja) meri
razliko porazdelitev, manj je bolje; OD sta izvor in cilj poti; GPS so satelitsko izmerjene
točke položaja s časom. *Urejeni probit* je model za urejene kategorije (§5.2); *vrata* so
vnaprej prijavljeni test, ki obdrži prior, dokler ga podatki ne zavrnejo; *dvojčki* (iz K1) so
poti, ki jih javni simulator izdela za isti *kontekst* kot pravo pot (to, kar je o poti dano
vnaprej, na primer izvor in cilj); *Newtonov korak* je en popravek parametra po naklonu in
ukrivljenosti cilja; *izotonična prilagoditev* ohrani naraščanje ocene; *Dijkstrovo iskanje*
izračuna najkrajše poti v grafu.

## 1. Raziskovalna vrzel in omejitve

**Vrzel ob obeh načrtovanih zasnovah.** Zahteva R1 pravi, da ima vsaka sintetična pot čas na
vsakem cestnem odseku. Obe načrtovani zasnovi te čase vzameta iz javnega modela P3 in
zasebno popravita le njihovo raven: C1 pošlje uporabnikovo razmerje hitrosti, K1 umeri
trajanje cele poti in vse odseke pomnoži z istim razmerjem, K8 primerja dve različni poti
istega uporabnika (v konici in zunaj nje). Pri n = 91 nobena ne pove, kako se čas spreminja
*vzdolž* poti (C1 da faktorje hitrosti po razredu ceste šele pri velikem n, in to kot ravni,
ne kot kontrast). Poleg tega pri n = 91 vsa njuna vprašanja pri ε = 2 merijo isto količino, mešanico hoje
in vožnje v Geolife (nauk obeh prejšnjih vrednotenj). Kontrast znotraj ene poti to mešanico
za test izniči, ker obe okni prevozi isti človek z istim prevoznim sredstvom; velikost ocene
pa je pri fiksnih zamudah še vedno povprečje po načinih potovanja (§7).

**Zakaj tretja zasnova.** Ideacija je iskala mehanizem, ki se od obeh načrtovanih bistveno
razlikuje. T3 se od K8 ne razlikuje po protokolu, ampak po ocenjevani količini in delu
modela, ki ga popravi, zato ga je treba predstaviti kot razširitev K8 (§4.1). V praksi
disertacija dobi zasebno korekcijo časovne zgradbe poti z ničelnim testom brez nejavnega
zakona populacije (ne števila poti na uporabnika ne izvorov in ciljev); cena je šibek signal
pri n = 91 (§6.2).

**Trde zahteve R1–R3 in sprejete odločitve S1–S5** (se ne odpirajo):

| | V preprostih besedah |
|---|---|
| R1 | Izhod so sintetične poti, veljavne po cestnem grafu OSM, vsaka s časom odhoda in časom na vsakem cestnem odseku. |
| R2 | Čisti ε-LDP na ravni uporabnika: enota so vsi podatki uporabnika v obdobju zbiranja; porazdelitev poročila se med katerimakoli dvema možnima uporabnikoma razlikuje največ za faktor e^ε. Mešalec (shuffler), varno seštevanje ali zaupanja vreden zbiralec so dovoljeni le kot neobvezna razširitev, ki je jamstvo ne potrebuje. |
| R3 | Eno poročilo na uporabnika in obdobje zbiranja; protokol v več krogih le z ločenimi skupinami uporabnikov. Poročilo sme združiti več delov, če se njihovi ε seštejejo v celotni ε, a obe prejšnji vrednotenji sta pokazali, da se delitev ε pri n = 91 nikoli ne izplača. |
| S1 | Javni prior vsebuje le OSM in citirane objavljene konstante, nič iz Geolife ali drugih podatkovij. |
| S2 | Dokaz za velik n (število poročajočih uporabnikov) da simulacija obnovitve parametrov do n = 10 000. Prave vrednosti smejo izvirati iz prilagoditve orakla na učnih uporabnikih Geolife in javnih odmikov, a rabijo le za generiranje podatkov, nikoli v priorju ali sproščenem modelu. |
| S3 | Benchmark je Geolife z okoli 91 poročajočimi učnimi uporabniki pri stopnji 182 in mrežo ε {0.5, 2, 8}. |
| S4 | Napad MIA kliče le `fit()` in `sequence_log_prob()`, zato mora mehanizem določiti verjetje poti kot zaporedja cestnih odsekov. |
| S5 | Sintetični izhod še nima časov; to je predpogoj v podatkovnem modelu (P1), ne ovira za zamisli. |

**Od česa se mora razlikovati:** od zasnove §4 in zasnove K1 + K8, od neizbranih kandidatov
C4–C10 in K2–K7 ter od 38 surovih idej prvih dveh krogov (20 in 18). K neizbranemu se sme
vrniti le nov pogled, ki izpolni pogoj iz §3.2 ustreznega načrta; noben kandidat tretjega
kroga ne obuja C4–C10 ali K2–K7, zato se ti pogoji nikjer ne uporabijo. Pet smeri drugega
kroga (najprej čas, celi sintetični uporabniki, ena vzorčena pot na uporabnika, večkrožni
protokoli, stisnjen lokalni opis) je raziskanih in se ne preobleče.

**Dejstva benchmarka, pomembna za T3.**

- **Seje, ne poti:** čiščenje Geolife ne reže ob postankih, zato je ena seja lahko vožnja z
  avtobusom in nato hoja; par oken iz dveh načinov bi pokvaril kontrast (P10, odločitev 2).
- **`fit` dobi le ujete učne poti** (ki so prestale ujemanje z zemljevidom); uporabnik brez
  njih danes ne pošlje ničesar (P11).
- **Malo uporabnikov:** pri u182 okoli 91 učnih uporabnikov z okoli 9 ujetimi potmi (od
  17 313 očiščenih trajektorij jih ujemanje prestane 1770, učenje teče na okoli 809), pri u50
  okoli 25, pri u20 okoli 10; zakon števila poti na uporabnika ni javen.
- **Redki časi:** točke so vsaj 5 s narazen, zato 100 m okno pri hitrem vozilu dobi le 1–2
  točki; vstop v okno in izstop iz njega se interpolirata iz `matched_points`. Ujemalnik
  vrzeli zapolni z najkrajšimi potmi, zato okno brez ujete točke ne šteje.
- **Semantike ni v tabelah zemljevida** (`length_m`, `highway`, `oneway`, `maxspeed`): raba
  tal in točke zanimanja zahtevajo nov izvoz iz istega posnetka OSM (P13); ali so semaforji
  in postajališča ohranjeni kot oznake vozlišč v datoteki grafa, preveri P13. Graf Pekinga
  ima 35 764 vozlišč.
- **Napad MIA** bere le verjetje zaporedja povezav, časov ne vidi; roka zgradi 17
  generatorjev (tarča in 16 senčnih), klic napada ima 300 s pri u20 in u50 ter 1200 s pri
  u182.

## 2. Kako je izbor nastal

Izhodiščni agent je najprej povzel, kaj sta pokrila prva dva kroga (obe zasnovi, 38 surovih
idej, kandidate C1–C10 in K1–K8, najbližja dela, pogoje za vrnitev, ugotovitve F1–F9), in za
vsako novo smer zapisal, kaj je še odprto. Pet predlagateljev je iskalo vsak v svoji »leči«:
R3-A najprej graf (cestni graf in njegove hierarhije nosijo poročilo), R3-B najprej napad
(poročilo, ki ne pomaga povezati posameznika), R3-C najprej uporabnost (statistika, ki določi
metrike disertacije), R3-D semantična plast OSM (raba tal, trgovine, stavbe) in R3-E
robustna statistika (mediane, kvantili, odrez). Dali so 20 idej, po štiri na lečo (R3-A.1
do R3-E.4); konsolidacija jih je združila v kandidate T1–T6 (14 idej je vstopilo, 6 je
izpadlo). Preverba novosti je kandidate v treh skupinah z 71 spletnimi iskanji primerjala z
literaturo. Ocenjevalec je točkoval po šestih merilih, na vseh kandidatih izvedel napad
»rdeče ekipe« (namerno iskanje šibkosti), sestavil kombinacije K-α, K-β in K-γ ter v krogu
ugovorov dobil odgovore predlagateljev T1, T3 in T2; njegove številke po tem krogu veljajo pred
prejšnjimi. Avtor je izbral T3 v obliki po ugovorih (§0).

**Ugotovitev kroga.** Nobena od treh končnih izbir ni povsem nov protokol: T1 uporablja
nosilec K1, T3 nosilec K8, le izenačeno poročilo T2 je nov nosilec, ta pa ima najšibkejši
signal. Prispevek tretjega kroga so nove statistike in ocenjevane količine na nosilcih
drugega kroga. Pri n = 91 vsaka možnost pri ε = 2 premakne največ eno število, pri ε = 0.5 pa
je vsaka enaka svojemu javnemu modelu.

**Opuščene surove ideje (6 od 20).** R3-A.4 (strani ovir: topološki razredi poti okoli velikih
ploskev grafa) pri n = 91 ne pokaže ničesar in se lahko vrne kot družina poti za velik n;
R3-B.1 (preusmerjanje po tipičnosti poti med dvojčki) in R3-B.2 (skupni nagib poti in časa)
sta preobleki K1; R3-B.3 (umerjanje po pokritosti galerije) je naprava K1 proti globalni
referenci in bi bila verjetno enaka svoji roki priorja; R3-E.3 (certificirana vrata) ni novo
poročilo, ampak pravilo izdaje za vse kandidate; R3-E.4 (zakon števila poti v poročilu) je
C3 s popravkom iz F2, njegova skupna postavka pa je pri ε = 2 šum.

## 3. Banka kandidatov T1–T6

### 3.1 Tabela

Novost je sodba preverbe, v oklepaju njena zanesljivost: EXISTS pomeni, da je jedro
objavljeno; CLOSE VARIANT, da se objavljeno delo razlikuje le v eni podrobnosti (tak kandidat
ne more biti izbran); NOVEL COMBINATION, da so kosi objavljeni, njihova kombinacija pa ne.
Točke: zasebnost in signal pri n = 91 štejeta dvojno, novost, uporabnost izhoda, prileganje
benchmarku in znanstvena zgodba enojno, vsako merilo 0–5, največ 40. Prvo število je ocena
pred krogom ugovorov, drugo po njem (`40_evaluation.md` §6.4, velja); prve tri izbire so
znotraj šuma točkovanja (±1). CH (contraction hierarchy, hierarhija krčenja) je javna
razvrstitev vozlišč po pomembnosti za iskanje najkrajših poti.

| | Kandidat (leča, jedro) | Poročilo | Kaj oceni | Novost (zanesljivost) | Točke /40 pred, po | Usoda |
|---|---|---|---|---|---|---|
| T1 | Zakon cilja po rangu priložnosti (R3-C; jedro R3-C.2, še R3-D.1, R3-B.4) | za eno upravičeno pot: v kateri tretjini javnega zakona leži število »priložnosti« (dolžina cest ali kraji OSM), ki so izvoru bližje od pravega cilja, ali ⊥; GRR nad 4 (pri ε = 8 nad 7); prvotno povprečje PIT vseh poti s HM | merilo dosega ρ: kako daleč ljudje potujejo glede na to, kar je okoli njih | NOVEL COMBINATION, ozka (srednja) | 26.5, 26.5; kot K-α 27.0, 27.0 | priporočen kot vprašanje o cilju v K1 (§3.2); rezerva po pravilu za umik kot K-α |
| T2 | Zakon poti pod stropom hierarhije (R3-A; jedro R3-A.1, še R3-A.2) | za eno pot: ali se je izognila najvišjemu pasu CH, ki ga uporabi dolžinsko najkrajša pot med istima koncema; po ugovorih bit z »izenačeno delovno točko«, ki ima v vsakem kontekstu isti javni verjetnosti, α brez stropa in β s stropom, in ⊥ | delež poti, ki se izognejo glavnim cestam; mešanica javnih usmerjevalnikov s stropi | NOVEL COMBINATION (srednja) | 26.0, 26.0 | neizbran; le če javni preverbi pokažeta, da hierarhija šteje |
| T3 | Kontrasti časov po odsekih znotraj poti (R3-D; jedro R3-D.3, še R3-A.3, R3-E.1) | razred mediane kontrasta »okna s fasado proti oknom brez« iste poti: počasneje, enako, hitreje, ⊥; GRR nad 4 | en faktor upočasnitve ob fasadi γ | NOVEL COMBINATION (srednja); številska oblika s križišči CLOSE VARIANT | 26.5, 27.5 | **izbran** (§5), pod pogojem javne preverbe |
| T4 | Semantične relacije koncev poti (R3-D; jedro R3-D.2, še R3-D.4) | relacija obeh koncev ene poti v javni hierarhiji ograjenih območij OSM: znotraj istega, v dveh iste vrste, med vrstama, zanka, ⊥; GRR nad 5 | dve konstanti relacije v zakonu cilja | NOVEL COMBINATION (srednja); postavke z vrsto cilja CLOSE VARIANT | 25.0, 25.0 (ni bil v krogu ugovorov) | neizbran; vprašanje o relaciji živi v K-α |
| T5 | Poročilo gradienta metrike (R3-C; jedro R3-C.1, še R3-C.3) | odvod uporabnikove povprečne energijske ocene (pravilnega pravila točkovanja) vzdolž ene javne smeri v prostoru parametrov simulatorja; HM | en Newtonov korak za 1–2 parametra pri ε ≤ 2 | kot zapisan NOVEL COMBINATION (nizka); jedro CLOSE VARIANT (srednje visoka) | 22.0, 22.0 | opuščen: objavljeno jedro |
| T6 | Porazdelitev trajanja pri absolutnih pragovih (R3-E; jedro R3-E.2, še R3-C.4) | za eno pot v javno izžrebanem obdobju odhoda: ali je bila krajša od javnega absolutnega praga (na primer 30 minut), ali ⊥; GRR nad 3 | porazdelitvena funkcija (CDF) trajanja po obdobjih z izotonično prilagoditvijo | jedro EXISTS (visoka); celota CLOSE VARIANT (visoka) | 23.0, 22.5 | opuščen: objavljeno jedro |

Kombinacije vrednotenja delijo uporabnike po zamrznjeni javni tabeli, nikoli ε.
**K-α** (jedro T1 in vprašanje T4 o relaciji, pogojeno na dejanski izvor, oboje na nosilcu
K1): 27.0 pred in po krogu ugovorov. **K-β** (T1 in T3 pod zamrznjeno delitvijo uporabnikov):
25.5, nato 26.0. **K-γ** (T2 s točno pogojno ničelno hipotezo): 25.5, umaknjena, ker je
izenačena delovna točka T2 boljša rešitev.

### 3.2 Kdaj bi se splačalo vrniti k neizbranim

Pogoji so poimenovani po kandidatu (R3-Cond-T…), kot v prejšnjih načrtih. Kandidata T5 in T6
se po odločitvi 7 ne odpirata; njuna pogoja sta zapisana le zaradi sledljivosti.

| Pogoj | Kdaj se splača vrniti in kaj mora biti prej narejeno |
|---|---|
| **R3-Cond-T1**, rang cilja med priložnostmi (26.5; kot K-α 27.0) | Priporočen je takoj, a kot poceni vprašanje o cilju (*dest*) na zamrznjenem seznamu vprašanj K1 ob *dur*, *dep* in *len* (okoli 2 seji; napad MIA ga vidi, ker ocena vstopi v verjetnost cilja pri danem izvoru), ne kot samostojen mehanizem: ocenjevalec ga po krogu ugovorov šteje za nosilec K1 z drugo statistiko, cilj ocene (kako verjetnost cilja pada z oddaljenostjo) pa je del modula C2. Kot mehanizem tretjega kroga se vrne le po pravilu za umik, kot K-α. V obeh primerih: (1) citirani podatek o razdaljah poti v Pekingu, ki postavi javno merilo zakona, je treba preveriti in zamrzniti s hashem (kandidat je poročilo CAUPD, China Academy of Urban Planning and Design, in Baidu o poteh na delo; nepreverjeno); (2) najprej P10, ker zanke, ki se končajo blizu izvora, oceno dosega potegnejo navzdol; (3) obvezna je primerjava s postavko pasov stroška iz C2 na istih uporabnikih, ker ocena pri ε = 2 lahko spet meri mešanico hoje in vožnje. Signal pri ε = 2: SD logaritma ocene dosega je 0.30 brez ⊥ in 0.38 pri deležu ⊥ 0.3; zakon, zgrešen za faktor 2.5 v masi priložnosti (okoli 1.6 v razdalji), je pri deležu ⊥ 0.3 oddaljen 2.3 SD, faktor 2 le 1.8 SD. Oblika zakona (zakon sevanja, Simini et al. 2012) ostaja največja nepreverjena odločitev priorja; preizkusi jo le W1 dolžin na Geolife. |
| **R3-Cond-T2**, strop v hierarhiji poti (26.0) | Le če dve javni preverbi pred kakršnokoli kodo pokažeta, da hierarhija šteje: ablacija (primerjava različic, ki se razlikujeta le v enem delu) »pasovi CH proti razredom cest OSM« in delež izogibanja glavnim cestam, ki ga da že javni model čez citirani razpon temperatur. Če se razredi OSM izenačijo s pasovi, ostane izenačeno poročilo z verjetjem gnezdenih stropov (novost okoli 2.5, smer C1 z drugim ocenjevalnikom), CH pa se ne gradi. Signal je šibek: pri javnih ciljnih verjetnostih (α, β) = (0.15, 0.9) veliko kontekstov izpade, SD ocenjenega deleža je 0.11 pri deležu ⊥ 0.3 in 0.17 pri 0.6, za 2 SD je potreben delež okoli 0.22–0.34. Pred kodo še: ali ujemalnik v repozitoriju vrzeli res zapolni z dolžinsko najkrajšimi potmi; točen izračun na pot z mejo korakov usmerjevalnika; varovalo GPS le na zapisu GPS; ali mešanica režimov C3 že napove delež izogibanja. Ocenjevanje pod desnim cenzuriranjem (znana je le spodnja meja vrednosti) pod LDP je objavljeno (Egéa in Escobar-Bach 2023), zato cenzurirana identifikacija pri ε = 8 sama ne nosi novosti; Kaplan–Meierjev produkt (ocena porazdelitve iz cenzuriranih opazovanj) je le citirano orodje. |
| **R3-Cond-T4**, relacije koncev poti (25.0) | Samostojno se ne vrne: pri n = 91 je notranji delež pri deležu ⊥ 0.3 oddaljen le okoli 1.6 SD, njegova ničelna vrednost pa je odvisna od nejavnega zakona izvorov (izvori Geolife ležijo v kampusih in zaprtih soseskah pekinškega okraja Haidian). Vprašanje o relaciji živi naprej v K-α, kjer se pošlje kot PIT razreda relacije pri dejanskem izvoru; vrata so tam točna za vsak zakon izvorov, velikost ocene pa še sloni na javnem zakonu izvorov. Postavke z vrsto cilja so CLOSE VARIANT in ostanejo zunaj. Potrebuje P9 (poti za pešce in servisne ceste v grafu) in izvoz ograjenih območij OSM. |
| **R3-Cond-T5**, poročilo gradienta metrike (22.0; opuščen) | Jedro je CLOSE VARIANT enokoračnega ocenjevalnika Duchija in Ruana (2024) in surove ideje B.1 prvega kroga. Novost bi prinesla le dokazana točna raven vrat pri neenakem številu poti in simulacijskih ponovitvah ter v P6 pri n = 10 000 pokazan dobiček zasnovane smeri pred smerjo vpliva in pred naključno koordinato; brez tega je pošten opis »enokoračni popravek Duchi–Ruan z oceno pravilnega pravila točkovanja v javni pilotni točki«. |
| **R3-Cond-T6**, porazdelitev trajanja pri absolutnih pragovih (22.5; opuščen) | Poročilo in ocenjevalnik sta objavljena (Liu, Hu in Kong 2024, preverjeno v celotnem besedilu); verjetje je pri vsakem ε enako priorjevemu, zato ga napad MIA ne vidi. Novost bi lahko nosila le izdaja iz R3-C.4 (posteriorna mediana porazdelitvene funkcije s certificirano mejo W1), kvečjemu kot NOVEL COMBINATION z nizko zanesljivostjo. Polno besedilo Liu, Hu in Kong (dodatek preverbe G3) nima ne metrike W1 ne posteriorja, sklepanje pa je točkovno na fiksni mreži; enakomernih pasov zaupanja preverba ni našla (nepreverjeno, ali obstajajo drugje). |
| **K-β**, T1 in T3 pod zamrznjeno delitvijo uporabnikov (26.0) | Cilji in časi po odsekih bi dobili zasebni popravek z ničelnima hipotezama brez zakona populacije, a sestavljeni mehanizem se pokaže le v P6, arhitektura (moduli, ki pod delitvijo uporabnikov umerjajo P3) pa je zasnova §4; okoli 6–7 sej. Ni v priporočilu vrednotenja. |

## 4. Izidi preverjanja novosti

Preverba je tekla v treh skupinah (G1: T1, T2; G2: T3, T4; G3: T5, T6). Večina del je
presojena po zadetkih iskalnika, povzetkih ali zapisih prvih dveh krogov; besedilo ali
posamezne razdelke so preverbe odprle le pri Roth in Avella-Medina (§6), Duchi in Ruan (§4.4,
§5.2, §6), Steinberger, Liu, Hu in Kong (celotno besedilo) ter Yang et al. 2014 (formula).
»Le povzetek« in »le izsek« označujeta dela, pri katerih je preverba to izrecno zapisala. DP
pomeni diferencialno zasebnost; pri *centralni* DP šum doda zaupanja vreden zbiralec, ne
naprava.

### 4.1 Izbrana zasnova (T3)

**Sodba: NOVEL COMBINATION, srednja zanesljivost.** Deli obstajajo ločeno: povprečenje
učinkov znotraj uporabnika pod LDP na ravni uporabnika, znakovni naključni odgovor z
Gaussovo inverzijo, primerjave skupin pod LDP, zasebne hitrosti odsekov in zasebni znakovni
testi pod centralno DP. Ni bilo najdeno: parni kontrast znotraj poti po javni lastnosti
povezave, poslan kot en razred GRR s točno simetrično ničelno hipotezo in uporabljen za
ponovno umerjanje časov po odsekih in stroškov usmerjevalnika sintetizatorja. Ocenjevalec je
novost po krogu ugovorov ohranil pri 3 od 5: nova ocenjevana količina in nov del sinteze na
nosilcu K8.

| Delo | Kaj naredi | Razlika od T3 |
|---|---|---|
| Roth, Avella-Medina, »Differential Privacy with Dependent Data«, arXiv 2025, https://arxiv.org/abs/2511.18583 | v §6 (razširitev na LDP) vsak uporabnik pod LDP na ravni uporabnika svoj regresijski naklon (posledica 6.10, longitudinalna regresija) ali svoje povprečje (posledica 6.8) omeji na interval, ki ga locira histogram naključnih odgovorov pri ε/2, in doda Laplaceov šum pri ε/2; strežnik povpreči | številsko poročilo z delitvijo ε in intervalom, lociranim iz podatkov; regresija prek vseh zapisov uporabnika, brez parov znotraj poti, brez točne ničelne hipoteze, brez cestnega grafa in sinteze. Številska oblika T3 z zamudo v križiščih je bila bližnja različica posledice 6.8 in je opuščena |
| Sopa, Avella-Medina, Rush, »Differentially Private Inference for Longitudinal Linear Regression«, arXiv 2026, https://arxiv.org/abs/2601.10626 | DP na ravni uporabnika z združevanjem regresij po uporabnikih, s sklepanjem; zaupanja vreden zbiralec | centralno in številsko; ista družina ocen (povprečen učinek znotraj uporabnika), brez lokalnega naključnika. Regresijo pod LDP na ravni uporabnika imata tudi Zhao et al. (2024) in Ma, Jia, Yang (ICML 2024), brez kontrasta znotraj enote |
| Kalinin, Steinberger, »Efficient Estimation of a Gaussian Mean with Local Differential Privacy«, arXiv 2024, https://arxiv.org/abs/2402.04840 | znakovni mehanizem: naključni odgovor o znaku razlike od središča, središče locira prva skupina uporabnikov | T3 centrira pri točni ničli 0 brez faze lociranja, doda razred »blizu nič« in ⊥, velikost pa dobi z urejenim probitom z javno lestvico šuma (ista zamisel obrata praga kot Joseph et al. 2019) |
| Ding, Nori, Li, Allen, AAAI 2018, https://ojs.aaai.org/index.php/AAAI/article/view/11301; Ohnishi, Awan, JMLR 26 (2025), https://www.jmlr.org/beta/papers/v26/23-1401.html | testi in ocene razlik med skupinami ali randomiziranimi kraki pod LDP | razlike med različnimi enotami z dodelitvijo; kontrast T3 je znotraj ene poti, »obravnava« pa je javna lastnost povezave |
| Rameshwar et al., arXiv 2024, https://arxiv.org/abs/2401.15906; Brown, Ohrimenko, Tamassia, »Haze«, ACM SIGSPATIAL 2013, https://arxiv.org/abs/1309.3515 | povprečne hitrosti avtobusov po celicah pod centralno DP na ravni uporabnika; hitrosti voznikov po odsekih, zbrane s kriptografijo in DP | ravni hitrosti po krajih, centralno ali kriptografsko, brez kontrasta in brez sinteze |
| Awan, Slavković (2018), https://arxiv.org/abs/1904.00459 (povezava: revijska različica); Couch et al. (2018), https://arxiv.org/abs/1809.01635 | znakovni test in Wilcoxonov test predznačenih rangov pod centralno DP | zaupanja vreden zbiralec; parnega znakovnega testa pod LDP preverba ni našla |

**Ozadje, ne grožnja.** Da je gibanje ob trgovski fasadi počasnejše (»stransko trenje«, side
friction), je znana nezasebna ugotovitev prometne stroke (ETASR; študija hitrosti GPS iz
Chennaija, leto nepreverjeno); nova je le zasebna zbirka te količine.

**Strogo branje.** Kdor bi za jedro vzel »učinek znotraj uporabnika, sproščen pod LDP na
ravni uporabnika in povprečen«, bi jedro imel za CLOSE VARIANT posledice 6.10 (razlika bi bila
le vrsta šuma in izbira parov). Sprejeta obramba: regresijski naklon po uporabniku ne izniči
ravni hitrosti vsake poti niti menjave načina znotraj uporabnika, nima točne ničelne hipoteze
in ne hrani sintetizatorja.

**Primerjava s prvima krogoma.** Oblika poročila je surova ideja R2-A.4 (postavka b K8, ki jo
je avtor v drugem krogu izločil: razlika log-razmerij hitrosti v treh razredih z GRR),
strežnik je postavka a K8 (ravnotežje znakov, urejeni probit); razlikuje se os kontrasta.
C1 (C.1, D.2, E.3), C8 (A.4) in K3 (R2-A.2) pošiljajo ravni hitrosti, nobena kontrasta
znotraj poti.

**Kaj mora zasnova trditi** (sprejeto v krogu ugovorov). (1) Novo ocenjevano količino v delu
modela, ki se ga noben prejšnji krog ne dotakne: časovno zgradbo odsekov znotraj poti (R1).
(2) Znotraj ene poti se način potovanja in lastna raven hitrosti poti izničita po zasnovi;
ničelna hipoteza testa drži za vsako mešanico načinov (ob enakem javnem času prostega toka na
meter v obeh oknih, §5.2), česar par dveh poti v K8 (morda v dveh načinih) ne zmore.
(3) Točna ničelna hipoteza ne potrebuje dvojčkov niti zakona števila poti na uporabnika. (4) Ocena spremeni čase odsekov in stroške usmerjevalnika, zato se
spremenijo tudi poti, K8 pa premakne le trajanja celih poti.

**Česa ne sme trditi:** nov protokol ali nov gradnik LDP (nosilec je K8); vzročnega učinka
fasade (fasada gre skupaj s parkiranjem, širino pasov in drugimi nekartiranimi lastnostmi
ulice); da je upočasnitev ob trgovinah nova ugotovitev; prvega zasebnega parnega testa
(centralni obstajata) ali prve ocene učinka znotraj uporabnika pod LDP na ravni uporabnika
(Roth in Avella-Medina 2025); dobička na metrikah P2 ali P12 ali vidnosti za napad MIA
onkraj stroškov usmerjevalnika; da pri n = 91 pokaže upočasnitev, manjšo od okoli 15 %. Pri
vsaki trditvi o mešanici načinov potovanja citira Bian et al. (2024), kjer so način, razdalja
in trajanje ocenjeni pod centralno DP na ravni uporabnika.

### 4.2 Neizbrani kandidati

| | Sodba (zanesljivost) | Najbližja dela | Bistvo razlike ali razlog za izpad |
|---|---|---|---|
| T1 | NOVEL COMBINATION, ozka (srednja) | Yang, Herrera, Eagle, González, Sci. Rep. 4:5662 (2014), https://doi.org/10.1038/srep05662 (razširjeni zakon sevanja z enim eksponentom); Simini et al., Nature 2012, https://arxiv.org/abs/1111.0586; Sakong in Zentefis (NBER); DP-WHERE (Mir et al., IEEE BigData 2013), https://doi.org/10.1109/BigData.2013.6691626; Gibbs et al., EPJ Data Sci. 2026, https://doi.org/10.1140/epjds/s13688-025-00611-4 (le povzetek); Canonne, Gentle, Singhal, ITCS 2026, https://arxiv.org/abs/2510.18379; Kent, Berrett, Yu 2024, https://arxiv.org/abs/2405.11923 | zakon cilja je objavljen; novi sta le poslana statistika (položaj cilja v vrstnem redu priložnosti okoli izvora) in ocenjevalnik, ki velja iz vsakega izvora; nobeno najdeno delo ne ocenjuje parametra izbire cilja iz poročil LDP. Test uniformnosti pod LDP na ravni uporabnika (Canonne et al.) je gradnik, ki ga morajo vrata citirati |
| T2 | NOVEL COMBINATION (srednja) | Ramaekers, Reumers, Wets, Cools, Netw. Spat. Econ. 2013, https://doi.org/10.1007/s11067-013-9184-8 (le povzetek); Yao in Bekhor, hEART 2020, https://arxiv.org/abs/2006.04536; DPMM (Haydari et al., ACSAC 2022), https://doi.org/10.1145/3564625.3567974; Yang et al., IEEE TSC 2020, https://arxiv.org/abs/2012.13807, in AHEAD (CCS 2021), https://arxiv.org/abs/2110.07505; Egéa in Escobar-Bach 2023, https://arxiv.org/abs/2311.01303; Geisberger et al., Transp. Sci. 2012, https://doi.org/10.1287/trsc.1110.0401 | nobeno zasebno delo ne poroča, kje v hierarhiji cest leži pot; nezasebna dela modelirajo razred ceste, ki ga pot uporabi. Statistika je enopotna različica razredov cest glede na najhitrejšo pot iz A.1 in E.3 (modul C1); če se razredi OSM izenačijo s pasovi CH, ostane razlika le v ocenjevalniku |
| T4 | NOVEL COMBINATION (srednja); postavke z vrsto cilja CLOSE VARIANT | Cunningham, Cormode, Ferhatosmanoglu, Srivastava, PVLDB 14 (2021), https://www.vldb.org/pvldb/vol14/p2283-cunningham.pdf; Sun et al. (PLTS), IEEE TIFS 19 (2024, prizorišče le iz izseka), https://research.polyu.edu.hk/en/publications/generating-location-traces-with-semantic-constrained-local-differ/; L-SRR (Wang et al., CCS 2022), https://arxiv.org/abs/2209.15091; NCHRP Report 684 (2011), https://nap.nationalacademies.org/read/14489/chapter/3 (stran ni bila odprta) | poročilo o relaciji koncev poti, ki ne imenuje nobenega konca, ni bilo najdeno; »notranji delež poti« je znana prometna količina, gravitacijski model z indikatorsko spremenljivko za isto cono pa učbeniški; načelo »relacije namesto krajev« je D.4 (C4) prvega kroga |
| T5 | kot zapisan NOVEL COMBINATION (nizka); jedro CLOSE VARIANT (srednje visoka) | Duchi in Ruan, Ann. Statist. 52(1), 2024, https://arxiv.org/abs/1806.05756; Steinberger, Ann. Statist. 2024, https://arxiv.org/abs/2301.10600; McKenna, Maity, Mazumdar, Miklau, PVLDB 13(11), 2020, https://arxiv.org/abs/2002.01582 | eno poslano projekcijo gradienta na uporabnika in en Newtonov popravek imata že Duchi in Ruan; vsaka razlika je ena modelska izbira; zasnovana smer je pri enem cilju njihova smer vpliva |
| T6 | jedro EXISTS (visoka); celota CLOSE VARIANT (visoka) | Liu, Hu, Kong, ICML 2024, https://proceedings.mlr.press/v235/liu24z.html (celotno besedilo); Hu in Liu, ICML 2026 (poster, le povzetek), https://icml.cc/virtual/2026/poster/64491; Aamand et al. 2025, https://arxiv.org/abs/2502.02990; Cormode, Kulkarni, Srivastava, PVLDB 12(10), 2019, https://www.vldb.org/pvldb/vol12/p1126-cormode.pdf | isto poročilo (en bit »vrednost pod pragom« z naključnim odgovorom), isti ocenjevalnik (izotonična prilagoditev), isti cilj; T6 doda le domeno, eno vzorčeno pot na uporabnika z ⊥ in preslikavo simulatorja |

### 4.3 Meje iskanja

- **Skupaj 71 spletnih iskanj** (G1 27, G2 22, G3 22) in več odprtih strani. Vse tri skupine
  so okoli 14:10–14:15 zadele omejitev seje spletnih orodij. G1 je po ponastavitvi od 15:11
  izvedla preostalih 7 iskanj za T2; G2 ni mogla izvesti treh načrtovanih iskanj za T4 in
  enega preverjalnega odpiranja strani; G3 je iskanje za T6 dokončala v dodatku od 15:29 do
  15:50 (7 iskanj in celotno besedilo Liu, Hu in Kong 2024).
- **Za T3** je vseh 14 iskanj teklo pred omejitvijo; odprte so bile štiri strani (pri Roth in
  Avella-Medina prebran §6, pri ostalih povzetki). Iskanje je zajelo celotnega kandidata pred
  krogom ugovorov; ožja oblika (le fasada, okna brez križišč) ni bila iskana posebej, sodba je
  ohranjena brez novega iskanja (nepreverjeno). Leto študije iz Chennaija je nepreverjeno, o
  stranskem trenju pa sta navedena le dva zgleda.
- **Ostalo nepreverjeno:** Gibbs et al. (stran je vrnila napako 403) in Ramaekers et al.
  (predtisk napako 503) sta presojena po povzetku; eksponent 0.84 zakona rangov (Noulas et
  al. 2012) je bil najden le v predavanjih; stran PLTS je preusmerila na prijavni portal,
  prizorišče je iz enega izseka; poročilo posterja Hu in Liu (2026); ali Bayesovski
  ocenjevalnik za podatke o trenutnem stanju (znano je le, ali je dogodek nastopil pred časom
  pregleda) pod LDP obstaja drugje; avtorji in prizorišče enega zadetka za T6 (iz spomina
  preverjevalca).

## 5. Izbrana zasnova

Gostitelj je skupni javni model P3 iz `NACRT_ULDP_SINTEZA.md` §4.1: Boltzmannov sprehod
proti cilju (na vsakem vozlišču izbere povezavo z verjetnostjo, ki eksponentno pada z
dodanim stroškom; po javni meji korakov konča po najkrajši poti), gravitacijski OD, javni
prior odhodov v pekinškem času (UTC+8) in čas na povezavi = čas prostega toka × javni faktor
obdobja × tresenje + javna zamuda zavoja. T3 doda en sam zasebni parameter, faktor
upočasnitve ob fasadi γ. Jedro izhaja iz surove ideje R3-D.3 (ura fasade); R3-A.3 je
prispevala spremenljivko križišč (opuščena), R3-E.1 pa izluščenje časov po odsekih in
izločanje postankov.

### 5.1 Poročilo uporabnika

**Javni podatki** (zamrznjeni s hashem commita pred prvim pogonom pri 182). Plast fasade
x(e) za vsako povezavo je delež 30-metrskega pasu ob povezavi, ki ga pokrivajo trgovska ali
maloprodajna raba tal ali točke trgovin in storitev OSM (`shop`, `amenity`); okno ima
*visoko* fasado pri x ≥ 0.5 in *nizko* pri x ≤ 0.1. Rezervna plast je *pozidana fasada*:
ali je v 30 m kakršnakoli stavba OSM, nasproti zidov, parkov in ograj; med plastema izbira
javna preverba (§6.1). Javni čas okna τ₀ da P3 (čas prostega toka × faktor obdobja ×
citirani popravki za semaforje in dostope). Javni so tudi skupine razredov ceste OSM,
pravila oken in parov, število parov K = 10, meje razredov, mreža vrednosti γ in lestvica
šuma para.

| Korak | Kaj naprava izračuna |
|---|---|
| 1. Okna | na vsaki ujeti poti 100 m okna sredi odsekov brez križišč, obrezana za 40 m ob vsakem vozlišču ter za 80 m pred semaforjem in ob avtobusnem postajališču; okno ima vsaj eno ujeto točko GPS (zapolnjene vrzeli ne štejejo), ne leži v prvih ali zadnjih 200 m poti in ne vsebuje postanka nad 60 s (postanek ni upočasnitev); čas vstopa in izstopa se interpolira iz `matched_points` |
| 2. Ostanek | za vsako okno ρ = log(t_izmerjen / τ₀), to je za koliko natov je bil uporabnik v oknu počasnejši od javnega modela |
| 3. Pari | eno okno z visoko in eno z nizko fasado iz iste skupine razredov ceste v isti poti, z vstopoma največ 3 minute narazen in z enakim javnim časom prostega toka na meter (isti `maxspeed` ali ista privzeta hitrost razreda in enak citirani popravek za dostope; dopolnilo recenzije, ni iz gradiva, §5.2); naprava z lastno naključnostjo izbere K = 10 parov z vračanjem iz vseh svojih poti; c je mediana razlik ρ_visoka − ρ_nizka |
| 4. Vrednost | c > 0.1 je »počasneje ob fasadi«, c med −0.1 in 0.1 »enako«, c < −0.1 »hitreje«; manj kot trije različni pari dajo ⊥ (»ni uporabnega para«) |
| 5. Pošiljanje | GRR nad štirimi vrednostmi (2 bita) pri polnem ε; pri ε = 8 šest vrednosti (pet razredov z mejami ±0.1 in ±0.3 nata ter ⊥); vsak učni uporabnik pošlje natanko eno poročilo (P11) |

V praksi: če je uporabnik povsod, na primer, dvakrat počasnejši od modela, ker hodi, se to v
razliki obeh ostankov odšteje. Poročilo zato ne pove, kako hitro kdo potuje, ampak le, ali
je bil na ulici s trgovinami počasnejši kot na podobni ulici brez njih na isti poti.

**Kaj ni del izbrane oblike.** Spremenljivka križišč (zamuda tam, kjer se srečata pasova
hierarhije) in številska oblika s povprečno zamudo v križiščih po HM sta opuščeni (odločitev
1). Ravni hitrosti po razredih ceste s HM pri ε = 8 (možnost iz R3-E.1 v gradivu) so
številska oblika ravni in po odločitvi 1 prav tako niso del zasnove (izpeljava pisca).

### 5.2 Strežnik

- **Popravek šuma:** iz histograma poročil se odstrani znani šum GRR; deleži med uporabniki
  s parom so ŝ_c / (1 − ŝ_⊥).
- **Vrata, točen pogojni binomski test.** Ničelna hipoteza pravi, da sta okni z visoko in
  nizko fasado iste poti zamenljivi, torej da fasada časa ne spremeni. Ker sta obe okni
  daleč od križišč in semaforjev, to velja za vsako mešanico fiksnih in sorazmernih zamud in
  za vsak način potovanja, a le, če imata okni enak javni čas prostega toka na meter
  (dopolnilo recenzije, ni iz gradiva): čas pešca ni sorazmeren τ₀, zato bi pri različnih
  omejitvah hitrosti razlika njegovih ostankov merila razmerje omejitev, ne fasade, in test bi
  na Geolife, kjer je hoje veliko, zavrnil brez učinka fasade. Pogoj je zato dodan pravilu
  parov (§5.1) in preverbi P15 (§6.1). GRR pošlje vsak lažen odgovor z isto verjetnostjo q,
  zato je pod ničelno hipotezo število odgovorov »počasneje« med m odgovori »počasneje« ali »hitreje«
  natanko binomsko porazdeljeno, Binomial(m, ½), ne glede na deleža »enako« in ⊥, število
  poti na uporabnika ali zakon izvorov; dvojčkov test ne potrebuje. Če test na vnaprej
  prijavljeni ravni ne zavrne, je γ̂ = 0 in ostane prior. Asimetrije, ki jih javni model
  nima (vrste, daljše od obreza, trend hitrosti blizu koncev poti, prehodi za pešce,
  zgoščeni ob fasadi), lahko test zavrnejo brez učinka fasade; njihov vpliv na raven testa
  izmeri javna preverba (§6.1).
- **Velikost, urejeni probit.** Če test zavrne, strežnik γ̂ oceni z urejenim probitom (model
  za urejene kategorije: c je približno normalno porazdeljen okoli γ z javno razpršenostjo
  para iz tresenja P3; poišče γ, ki najbolje pojasni deleže treh razredov) in ga zaokroži na
  javno mrežo {0, 0.1, 0.2, 0.3, 0.5}. Od javne lestvice šuma je odvisna velikost, ne test.
  Kadar je upočasnitev ob fasadi fiksna zamuda (prehodi, parkiranje, postajališča), je γ̂
  povprečje po načinih potovanja, uteženo z njihovim deležem.
- **Pri ε = 8** (šest vrednosti) test primerja oba razreda »počasneje« z obema razredoma
  »hitreje«; Binomial(m, ½) še velja, ker ima GRR za vsako lažno vrednost isto verjetnost q
  (izpeljava pisca, gradivo tega ne navaja).
- **Pri velikem n:** γ po skupini razreda ceste × obdobju × vrsti fasade, okoli 12 števil
  (prilagoditev pisca: gradivo ima »× spremenljivka«, fasada ali križišča; brez križišč je
  števil lahko manj).

### 5.3 Sinteza poti s časi

- **Izvor, cilj in odhod:** iz P3 (gravitacijski OD, javni profil odhodov v UTC+8); T3 jih ne
  spreminja.
- **Trasa:** Boltzmannov sprehod P3 s stroški povezav c_γ(e) = E_t τ(e, t) + javna zamuda
  zavoja, kjer je E_t τ pričakovani čas povezave prek javnega profila odhodov; po javni meji
  korakov sledi zaključek po najkrajši poti, zato je pot veljavna po cestah po konstrukciji.
  Pri γ̂ > 0 se poti nekoliko izogibajo počasnim trgovskim ulicam. `generate` in
  `sequence_log_prob` uporabljata iste stroške, ker morata po pravilu repozitorija opisovati
  isti model povezav.
- **Časi po odsekih:** τ(e, t) = τ₀(e, t) · exp(γ̂ · x(e)) · tresenje. Odsek s polno fasado
  (x = 1) je exp(γ̂)-krat počasnejši, pri γ̂ = 0.1 torej za okoli 10 %; odsek brez fasade
  ostane pri javnem modelu. Čas vstopa na vsako povezavo se dobi s seštevanjem vzdolž poti in
  se zapiše v časovni payload (P1, S5).

### 5.4 `sequence_log_prob`

Kot v `NACRT_ULDP_SINTEZA.md` §4.7, le s stroški c_γ: log P(O, D) + vsota log-verjetnosti
korakov sprehoda + javni člen za vrzeli; čas ne vstopa. Stroški do cilja (eno obratno
Dijkstrovo iskanje na poizvedovani cilj, okoli 40 ms) se računajo leno po eni poti kode za
člane in nečlane, s ključem hasha zemljevida in konfiguracije, zato nobena tabela ne nastane
le za učne cilje (to bi napadu izdalo članstvo). Ker je γ̂ zaokrožen na pet javnih vrednosti,
obstaja največ pet tabel stroškov: okoli 5 × 1100 × 40 ms ≈ 220 s javnega računanja, skupnega
17 generatorjem roke (vsak ima svoj γ̂). Verjetje je končno za vsako zaporedje zaradi javnega
spodnjega praga P3. Edini zasebni vhod je γ̂; napad MIA ga vidi le prek izbire poti, kjer vrata
ne zavrnejo, pa je verjetje enako priorjevemu (§6.2).

### 5.5 Zasebnostni argument na ravni uporabnika

**Trditev:** T3 je čisti ε-LDP na ravni uporabnika. Dokaz v petih korakih:

1. **Kaj spremeni en uporabnik.** Enota so vsi njegovi podatki iz obdobja zbiranja: vse ujete
   poti, vsa okna in vsi časi. Naprava iz vseh izračuna eno vrednost x iz javne domene štirih
   vrednosti (počasneje, enako, hitreje, ⊥; pri ε = 8 šestih). Ko se uporabnikovi podatki v
   celoti zamenjajo, se x lahko spremeni v katerokoli drugo vrednost domene, a nikamor drugam.
   Občutljivost je torej »katerakoli vrednost v katerokoli« in jo v celoti pokrije razmerje
   verjetnosti v koraku 2; številskega odreza ne potrebuje.
2. **Naključnik.** GRR nad k vrednostmi pošlje pravo vrednost z verjetnostjo
   p = e^ε / (e^ε + k − 1) in vsako drugo z verjetnostjo q = 1 / (e^ε + k − 1). Za vsak izhod
   y in vsaki vrednosti x, x' je P(y | x) / P(y | x') ≤ p / q = e^ε. Pri k = 4 in ε = 2 je
   p = 0.711 in q = 0.096 (p − q = 0.615).
3. **Naključnost naprave ne izdaja podatkov.** Izbira parov (K = 10 z vračanjem) in vsa druga
   naključnost prihajata iz semenskega generatorja naprave, neodvisno od podatkov in po
   javnem zakonu. Zato za katerakoli uporabnika s podatki D in D' in vsak izhod y velja
   P(y | D) ≤ max_x P(GRR(x) = y) ≤ e^ε · min_x P(GRR(x) = y) ≤ e^ε · P(y | D') (lema o dvigu
   iz drugega kroga): kako je bil x izračunan, ni pomembno.
4. **Kompozicije ni.** Eno poročilo na uporabnika in obdobje, pri polnem ε, brez delitve ε in
   brez drugih poročil. Test, ocena γ̂, sinteza in `sequence_log_prob` so naknadna obdelava in
   zasebnosti ne porabijo.
5. **Brez skrite odvisnosti od podatkov.** Vse, kar določa x ali domeno (plast fasade iz OSM,
   τ₀ iz P3 in citiranih konstant, pravila oken, parov in obreza, K, meje razredov, mreža γ,
   lestvica šuma, raven testa, pravilo za ⊥), je javno in zamrznjeno s hashem commita pred
   prvim pogonom pri 182; javna preverba (§6.1) teče le na P3, brez Geolife. Vsak učni
   uporabnik pošlje natanko eno poročilo (P11; ⊥, če nima uporabnega para), n je javno število
   učnega dela, zato to, kdo poroča, ni odvisno od podatkov. Konstant ni mogoče uglasiti na
   ravni hitrosti v Geolife, ker se raven v kontrastu odšteje.

**Kaj poročilo razkrije.** Moč lociranja (za koliko resnično poročilo poveča verjetnost, da
uporabnikov dom leži v neki coni) je 1 po konstrukciji: isti razred se lahko pojavi na kateri
koli poti v mestu, zato poročilo ne pove ničesar o domu, delu ali drugem kraju. Pri ε = 8
skoraj resničen razred razkrije lastnost (»trgovine me upočasnijo«), ne kraja. Iz ε-LDP na
ravni uporabnika sledi za napad MIA meja na delež pravih zadetkov pri danem deležu lažnih
(§6.2). Rdeča ekipa v
nobenem jedru tretjega kroga ni našla zasebnostne napake; odprta tveganja so postopkovna
(zamrznitev konstant, §7).

## 6. Kaj lahko Geolife pokaže in kako merimo

### 6.1 Javna preverba pred zamrznitvijo (P15)

Preverba je vnaprej prijavljena (odločitev 2), traja okoli eno uro računanja, teče le na
javnem modelu P3 in ne bere podatkov Geolife. Pred njo morata obstajati razrez sej (P10) in
predlog plasti fasade ter pravil oken (P13, P14); časi oken se izluščijo z isto kodo kot na
napravi.

| Del | Vsebina |
|---|---|
| Kaj simulira | 20 000 poti P3 nad javnim okvirjem zemljevida Pekinga (gradivo piše »pravokotnik okoli Geolife«; okvir iz točk Geolife bi v zamrznjeno odločitev vnesel podatek iz Geolife, zato po recenziji javni okvir), v režimu hoje in v režimu vožnje, združenih v uporabnike z m ∈ {1, 3, 9, 30} potmi, ker zakon števila poti na uporabnika ni javen. Časi vključujejo citirane čakalne dobe na semaforjih, prelivanje vrst in delež avtomobilov od 0 do 100 %, poleg tega pa asimetrije, ki jih simetrično tresenje P3 nima: vrste, daljše od obreza, trend hitrosti blizu koncev poti in prehode za pešce, zgoščene ob fasadi (dopolnilo ocenjevalca; brez njih bi preverba prestala trivialno), ter hojo, katere čas ni sorazmeren τ₀, na oknih z različnimi omejitvami hitrosti (dopolnilo recenzije, §5.2). |
| Kaj izmeri | delež uporabnikov brez para (⊥) in število različnih parov pri vsakem m; delež lažnih zavrnitev testa pri n = 91 za vsak delež avtomobilov; isto z ohranjenimi conami križišč kot negativno kontrolo, pri kateri mora delež lažnih zavrnitev z deležem avtomobilov rasti (sicer preverba ne bi zaznala niti znane napake); moč testa pri γ ∈ {0.05, 0.10, 0.15}. |
| Pravilo »obdrži, zamenjaj, ustavi« | fasada s trgovinami (raba tal OSM in točke `shop`/`amenity`) ostane, če je delež ⊥ v najslabšem primeru čez m od 1 do 30 največ 0.5 in delež lažnih zavrnitev pri vsakem deležu avtomobilov največ 0.06. Sicer se enkrat zamenja z bolje kartirano pozidano fasado (katerakoli stavba OSM v 30 m, nasproti zidov, parkov in ograj) pod istima pragoma. Če ne prestane nobena plast, velja pravilo za umik (odločitev 3): T3 ostane le modul za velik n v P6, mehanizem tretjega kroga pa postane K-α. |
| Opažanje pisca | ker delež uporabnikov brez para z več potmi na uporabnika le pada, je najslabši primer v praksi m = 1 (uporabnik z eno samo potjo); pravilo je zato strogo, kar je namen dopolnila, a povečuje verjetnost umika. |

### 6.2 Šum pri n = 91

SD so po popravku šuma, iz vrednotenja; ⊥ je delež uporabnikov brez para. Vsako trditev »k
SD« je treba računati med vsemi uporabniki z deležem ⊥, ne le med tistimi s parom.

| ε | Kaj se premakne | Šum in prag zaznave |
|---|---|---|
| 0.5 | nič; vrata obdržijo prior, roka je v praksi enaka roki priorja | šum na delež pri GRR okoli 0.28–0.41 (splošna tabela izhodišča) |
| 2 | en sam faktor γ̂, če fasada upočasni za okoli 15 % ali več | ravnotežje »počasneje« minus »hitreje« ±0.134 brez ⊥ (±0.17 med uporabniki s parom pri ⊥ 0.3); γ = 0.15 nata 1.6–2.5 SD; γ = 0.10 nata pod 2 SD; γ = 0.05 nata se ne vidi |
| 8 | šest vrednosti; gradivo predvideva kvečjemu dve števili (na primer γ v konici in zunaj nje) | ocenjevalec ni preračunal (nepreverjeno) |
| velik n | pri n = 10 000 okoli 12 števil: γ po skupini razreda ceste × obdobju × vrsti fasade (prilagoditev pisca, §5.2) | le v simulaciji (§6.3) |

**Skica variance pri ε = 2.** GRR nad štirimi vrednostmi ima p − q = 0.615 in q = 0.096.
Če sta prava deleža »počasneje« in »hitreje« π₊ in π₋, sta opažena deleža
f± = q + π± · (p − q), ravnotežje π₊ − π₋ pa ima po popravku šuma
SD = √((f₊ + f₋ − (f₊ − f₋)²) / n) / (p − q). Pri n = 91, π₊ = π₋ = 0.35 in deležu »enako«
0.3 je f± = 0.311 in SD = 0.134. Kolikšno je ravnotežje, ko fasada res upočasni: posamezen
par ima SD okoli 0.5 nata (100 m okno pri točkah vsaj 5 s narazen dobi 1–2 točki), mediana
desetih parov okoli 0.20 nata; z razpršenostjo med uporabniki 0.15 nata je c pri γ = 0.15
približno normalen s sredino 0.15 in SD 0.24 (vrednost ocenjevalca; točno je
√(0.20² + 0.15²) = 0.25, kar da ravnotežje 0.42 kot v konsolidaciji, vsebinsko enako).
Tedaj je P(c > 0.1) = 0.58 in P(c < −0.1) = 0.15, ravnotežje 0.43 (okoli 0.31 pri uporabnikih s samo tremi različnimi
pari). To je 2.5 SD pri deležu ⊥ 0.3 in 2.0 SD pri 0.5. Po obrezu ob vozliščih, semaforjih in
postajališčih je različnih parov manj, zato ocenjevalec realistično pričakuje 1.6 do 2.5 SD;
γ = 0.10 nata ostane pod 2 SD (okoli 1.7 SD pri deležu ⊥ 0.3 že pred obrezom). Pravi delež ⊥
na Geolife ni znan in se pred zamrznitvijo na Geolife ne meri; javno ga oceni preverba
(§6.1).

**Napad MIA** učinek vidi le šibko: γ̂ vstopi le v stroške usmerjevalnika, čas sam v verjetju
ni. Kjer vrata ne zavrnejo (pri ε = 0.5 v praksi vedno, pri ε = 2 morda), je verjetje enako
priorjevemu in je napad slep po konstrukciji; izid vrat se zato poroča za vsak ε posebej
(izpeljava pisca iz pripombe za T1). Napad bo pri vseh kandidatih tretjega kroga sedel pri
naključju, zato zasebnost med njimi ne loči. Meja ε-LDP je TPR ≤ e^ε · FPR (TPR in FPR sta
deleža pravih in lažnih zadetkov): pri FPR 0.01 da 0.017 pri ε = 0.5 in 0.074 pri ε = 2, pri
ε = 8 je brez vsebine. Pravi preizkus učinka bi bil časovno občutljiv napad (P8, §8).

### 6.3 Kaj pokaže le simulacija obnovitve (P6)

Mreža kot v `NACRT_ULDP_SINTEZA.md` §5.5: n = 10, 25, 91, 300, 1000, 3000 in 10 000, ε ∈
{0.5, 2, 8}, vsaj 20 semen na celico, ista koda `encode_user` in `server_fit` kot pri
Geolife. Prave vrednosti smejo izvirati iz prilagoditve orakla na učnih uporabnikih Geolife
in javnih odmikov (S2), a rabijo le za generiranje podatkov.

- Raven pogojnega binomskega testa pri vsaki mešanici hoje in vožnje in pri vsakem zakonu
  števila poti na uporabnika ter njegova moč pri γ ∈ {0.05, 0.10, 0.15} v odvisnosti od n.
- Ali γ̂ obnovi pravi γ pri sorazmerni upočasnitvi in koliko se velikost premakne proti
  povprečju po načinih, ko je del upočasnitve fiksna zamuda (prehodi, parkiranje,
  postajališča).
- En napačno specificiran pogon z zapolnjevanjem vrzeli, kakršnega dela ujemalnik, in z
  interpoliranimi časi oken; pri velikem n plast z okoli 12 števili (skupina razreda ceste ×
  obdobje × vrsta fasade; prilagoditev pisca, §5.2).
- Če javna preverba pade za obe plasti, T3 živi samo tu, kot modul za velik n (odločitev 3).

### 6.4 Kontrolne roke in metrike

Kot dokaz šteje dobiček nad lastno roko priorja in nad placebo roko v sloju fasade in v
razpršenosti znotraj poti, brez dobička v kontrolnih slojih; zasebnost se dokazuje strukturno.

| Roka ali metrika | Vsebina |
|---|---|
| Roki priorja in orakla | dobiček je delež vrzeli med njima, ki ga mehanizem zapre (`NACRT_ULDP_SINTEZA.md` §5.3) |
| Placebo roka (dopolnilo ocenjevalca) | isti γ̂, uporabljen na zamrznjenem naključnem naboru povezav z enakim deležem fasade; T3 jo mora premagati, sicer bi bil dobiček na razpršenosti le dodana varianca kjerkoli |
| Dvignjeni kontroli drugega kroga | `ldptrace` in `rn_ldp_synth`, dvignjena na raven uporabnika z eno enakomerno izbrano ujeto potjo pri polnem ε; vsak nov mehanizem mora premagati obe in svojo roko priorja |
| Metrika hitrosti oken (P16, odločitev 5) | zamrznjena pred vsakim rezultatom in računana enako za vse roke (roko priorja, placebo, T3 ter roke K1, C1 in drugih mehanizmov, ki dajo čase): W1 med hitrostmi v 100 m oknih sredi odseka v sintetičnih časih (P1) in v zadržanih ujetih poteh testnega dela, z bootstrapom po uporabnikih (ponovnim vzorčenjem uporabnikov za interval zaupanja); poroča se po skupini razreda ceste OSM, s semaforji ali brez in po zamrznjenem razredu fasade. Drugo število je W1 razpršenosti log-hitrosti oken znotraj poti, ki je nobeno enakomerno skaliranje cele poti (kot pri K1) ne premakne |
| Kontrolni sloji | sloja razreda ceste in semaforjev sta vgrajeni kontroli: T3 mora roko priorja premagati le v sloju fasade in v razpršenosti znotraj poti, dobiček v kontrolnih slojih bi kazal na artefakt. Zadržane hitrosti oken nosijo šum interpolacije, sintetični časi pa ne, zato se oboje izlušči enako pri enakem razmiku točk ali pa se roke primerjajo le po razlikah |
| Obstoječe metrike | W1 trajanja (P2) in W1 trajanja znotraj obdobij odhoda (P12) se premakneta malo, za okoli γ krat delež časa ob fasadi, to je 1–2 %; prostorske metrike se premaknejo le, kolikor se poti izognejo počasnim ulicam |
| Zasebnost | dokazuje se strukturno s kompletom P4 in z dodatnim testom iz P11, ne z napadom |

## 7. Tveganja in varovala

Napad MIA večine teh tveganj ne bi opazil, zato jih zapirajo konstrukcija, preverbe in testi.
Edina usodna ugotovitev rdeče ekipe za T3, da je številska oblika z zamudo v križiščih bližnja
različica objavljenega dela, je rešena z opustitvijo te oblike (odločitev 1). Pet tveganj
(premalo parov, šibek signal, fiksne zamude, večnačinske seje, slepota benchmarka) povzetek
ocenjevalca šteje za resna; ostale vrstice so manjše ali postopkovne točke iz rdeče ekipe, iz
odgovora predlagatelja T3 in iz ugotovitve Y8 ocenjevalca (zasebnostna tveganja vseh jeder so
postopkovna). Nobeno ni usodno.

| Tveganje | Kaj se zgodi | Varovalo |
|---|---|---|
| Premalo parov (glavno odprto vprašanje) | če veliko uporabnikov nima vsaj treh različnih parov, se signal razredči (2.5 SD pri deležu ⊥ 0.3, 2.0 SD pri 0.5); kartiranje trgovin in rabe tal v Pekingu je lahko redko | javna preverba s pravilom »obdrži, zamenjaj, ustavi« in najslabšim primerom čez 1–30 poti; rezervna plast pozidane fasade; pravilo za umik (§6.1) |
| Šibek signal | pri ε = 2 se vidi le upočasnitev za okoli 15 % ali več, pri ε = 0.5 nič | vrata obdržijo prior; trditve omejene na prag zaznave; moč pokaže P6 |
| Fiksne zamude | ko je upočasnitev ob fasadi fiksna zamuda (prehodi, parkiranje, postajališča), je velikost γ̂ povprečje po načinih; test ostane točen | obrez ob postajališčih; velikost se poroča kot povprečje; P6 pokaže odmik |
| Večnačinske seje | seja z avtobusom in nato hojo po trgovski ulici v 3 minutah da par iz dveh načinov | razrez sej P10 pred preverbo (odločitev 2) |
| Asimetrije zunaj javnega modela | vrste, daljše od obreza, trend hitrosti blizu koncev poti in prehodi, zgoščeni ob fasadi, lahko zavrnejo test brez učinka fasade | vključene v javno preverbo; izločitev prvih in zadnjih 200 m; obrez 40 m in 80 m |
| Zmeda s skritimi lastnostmi ulice | fasada gre skupaj s parkiranjem in širino pasov; test je točen za upočasnitev, ki fasado spremlja, ne za vzročno | za sintezo neškodljivo; vzročnosti ne trdimo (§4.1) |
| Šumni časi oken | 1–2 točki na okno, interpolacija in pripenjanje ujemalnika | vsaj ena ujeta točka v oknu, brez zapolnjenih vrzeli; mediana desetih parov; enako izluščenje pri metriki |
| Slepota benchmarka | napad MIA vidi učinek le prek stroškov usmerjevalnika; P2 in P12 se skoraj ne premakneta | metrika P16 s kontrolnimi sloji; odločitev o časovno občutljivem napadu P8 (§8) |
| Metrika po meri mehanizma | dobiček na metriki, ki jo je predlagal predlagatelj kandidata | zamrznjena pred rezultati, enaka za vse roke, placebo roka |
| Kontaminacija priorja | pravila oken, pragovi fasade, meje razredov ali lestvica šuma, nastavljeni po Geolife, so nezaščitena izdaja | vse iz OSM in citiranih virov, zamrznjeno s hashem commita pred prvim pogonom pri 182; preverba le na P3 |
| Velikost odvisna od lestvice šuma | γ̂ (ne test) sloni na javnem tresenju P3 | lestvica iz citiranih virov, zamrznjena; občutljivost v P6 |
| Protokol drugega kroga | recenzent T3 prebere kot K8 na novi osi | oznaka iz odločitve 6 v načrtu in članku; trditev stoji na novi ocenjevani količini |

**Presečna pravila, ki jih načrt privzame** (iz odločitev avtorja in povzetka ocenjevalca):
vse javne konstante se zamrznejo s hashem commita pred prvim pogonom pri 182, vzete iz
objavljenih virov in nikoli nastavljene po Geolife; delež uporabnikov s pari se na Geolife pred
zamrznitvijo ne meri, plast izbere le javna preverba (izpeljava pisca iz S1); vsak učni
uporabnik pošlje natanko eno poročilo (P11); vsaka trditev »k SD« se računa ob deležu ⊥ med
vsemi uporabniki; metrika P16 in placebo roka sta vnaprej prijavljeni in enaki za vse roke.

## 8. Odprte odločitve

Točke 1–3 izhajajo iz odločitev avtorja in povzetka ocenjevalca, ostale iz vrednotenja,
gradiva in recenzije načrta (točka 11); »opažanje pisca« pomeni, da gradivo točke ne navaja.
Termini se nanašajo na §9.2.

| # | Odločitev | Možnosti in trenutni nagib | Kdaj |
|---|---|---|---|
| 1 | Plast fasade | fasada s trgovinami, pozidana fasada v 30 m ali ustavitev. Nagib: odloči javna preverba po vnaprej prijavljenem pravilu, najprej fasada s trgovinami (§6.1). Ocenjevalec je kot drugo možnost ponudil presojo deleža ⊥ pri m = 3; avtor je izbral strožji najslabši primer. | P15, pred kodo mehanizma |
| 2 | Umik, če preverba pade za obe plasti | odločeno vnaprej (odločitev 3): T3 postane modul za velik n, prikazan le v P6; mehanizem tretjega kroga postane K-α (T1 z vprašanjem T4 o relaciji), njegov načrt se napiše v novi seji. Odprto je le, kdaj se ta seja začne. | takoj po P15 |
| 3 | T1 v zasnovi K1 + K8 | (a) vprašanje *dest* na seznamu K1 (priporočeno, okoli 2 seji, napad MIA ga vidi); (b) mehanizem tretjega kroga kot K-α, le po umiku; (c) nič. Nagib: (a); odločijo seje K1 (`NACRT_ULDP_RANGI.md` §8, točka 11). V vsakem primeru je treba najprej preveriti in zamrzniti citirani podatek o razdaljah poti v Pekingu (§3.2), T1 pa potrebuje P10. Če velja umik, gradivo ne določa, ali T1 ostane tudi na seznamu K1. | v sejah K1, pred zamrznitvijo seznama vprašanj |
| 4 | Konstante oken, parov in fasade | dolžina okna 100 m, obrez 40 m ob vozliščih ter 80 m pred semaforji in ob postajališčih, največ 3 minute med oknoma, enak javni čas prostega toka na meter v obeh oknih (dopolnilo recenzije, §5.2), izločitev prvih in zadnjih 200 m in postankov nad 60 s, K = 10, vsaj trije različni pari, meje ±0.1 (±0.3) nata, mreža γ, pragova visoke (0.5) in nizke (0.1) fasade, pravilo pozidane fasade, skupine razredov ceste, raven testa. Nagib: vrednosti iz gradiva kot predlog, viri za popravke za semaforje in dostope se citirajo; nobena se ne nastavi po Geolife. | predlog pred P15 (preverba jih uporablja), dokončno pred prvim pogonom pri 182 |
| 5 | Lestvica šuma para za urejeni probit | iz tresenja P3; vpliva na velikost γ̂, ne na test. Nagib: iz citiranih virov, kot vse konstante P3. | s P3 |
| 6 | Oblika pri ε = 8 | šest vrednosti (meje ±0.1 in ±0.3 nata) ali javna delitev uporabnikov za γ v konici in zunaj nje. Nagib: gradivo ne izbere; številke pri ε = 8 niso preračunane (nepreverjeno). | pred zamrznitvijo |
| 7 | Utež ocene | T3 povpreči vse poti uporabnika (vsak uporabnik šteje enako), metrike P2 in P12 pa so utežene po poteh; skupno z `NACRT_ULDP_SINTEZA.md` §7.1, točka 2, in `NACRT_ULDP_RANGI.md` §8, točka 8. | pred koncem P2 |
| 8 | Časovno občutljiv napad MIA (P8) | T3 spreminja predvsem čase, ki jih napad ne vidi, zato je odločitev tu še pomembnejša kot pri K1 + K8; skupno z `NACRT_ULDP_SINTEZA.md` §7.1, točka 4, in `NACRT_ULDP_RANGI.md` §8, točka 10. | pred prvimi meritvami |
| 9 | Pravila izdaje iz konsolidacije | javna omejitev vpliva enega poročila na sproščeno verjetje, prag zloma proti lažnim uporabnikom in roka zastrupitve v P6 z 0, 2, 5 in 10 lažnimi uporabniki, ki jih konsolidacija predlaga za vse kandidate. Nagib: gradivo ga ne navaja. | pred P6 |
| 10 | Vrstni red glede na drugi dve zasnovi | vsi trije mehanizmi potrebujejo P3; ali se T3 gradi pred moduli zasnove §4 in pred K1 + K8 ali za njimi, gradivo ne določa (opažanje pisca). | pred P3 |
| 11 | Razrez sej P10 za vse roke | ali razrez velja za vse roke (spremeni številke S4 vseh rok), odloča `NACRT_ULDP_RANGI.md` §8, točka 4; T3 ga potrebuje vklopljenega (odločitev 2). | pred P10 |

## 9. Predpogoji in načrt sej

### 9.1 Predpogoji

P0–P9 so oznake iz `NACRT_ULDP_SINTEZA.md` §8.1, P10–P12 iz `NACRT_ULDP_RANGI.md` §9.1 (napor
S majhen, M srednji); vsak se naredi enkrat in služi vsem mehanizmom. Novi predpogoji
nadaljujejo številčenje s P13; imena in vrstni red je predlagal pisec, napora gradivo ne
ocenjuje.

| # | Predpogoj | Napor | Vloga za T3 |
|---|---|---|---|
| P0 | preverba uporabniške napeljave: `user_id` v pogledih, kandidati MIA, ali neujete poti pridejo v `fit` | S | dejstva za P11 |
| P1 | časovni sintetični payload: povezave, odhod, čas vstopa na povezavo v UTC+8, Parquet; zapis postankov (čas vstopa in izstopa) | S | izhod R1; metrika bere sintetične čase oken |
| P2 | neparne metrike uporabnosti (W1 trajanja, hitrosti, ure odhoda, prostorske metrike) | M | okvir metrik, ob katerem stoji P16 |
| P3 | skupni javni model (simulator) | M | gostitelj, τ₀, javna preverba, lestvica šuma |
| P4 | zasebnostni komplet: razrez `encode_user` / `server_fit`, testi, pozitivna kontrola | S–M | strukturni dokaz (§5.5) |
| P5 | preverbe ogrodja, ε na ravni uporabnika v `run.json` | S | pogoni MIA |
| P6 | simulacija obnovitve parametrov | S–M | §6.3; edini dom T3 po morebitnem umiku |
| P8 | neobvezni časovno občutljiv napad MIA | M | pravi preizkus učinka T3 (§8, točka 8) |
| P10 | javni razrez sej Geolife ob postankih | ni ocenjen | pari v enem načinu potovanja; pred javno preverbo (odločitev 2) |
| P11 | vsak učni uporabnik pošlje natanko eno poročilo (⊥ brez uporabnega para), n iz učnega dela, s testom | ni ocenjen | jamstvo R2 in R3 v izvedbi |
| P12 | W1 trajanja znotraj vsakega obdobja odhoda | ni ocenjen | primerjava s K1; T3 jo premakne malo |
| **P13** (nov) | **semantična plast OSM:** iz istega posnetka OSM kot zemljevid izvoz trgovske in maloprodajne rabe tal in točk `shop`/`amenity` (fasada s trgovinami), stavb (pozidana fasada v 30 m, nasproti zidov, parkov in ograj), semaforjev in avtobusnih postajališč; delež fasade x(e) na povezavo v 30-metrskem pasu; ključ po hashu zemljevida in pravila; enourna preverba pokritosti po conah 3 × 3, le iz OSM | ni ocenjen | spremenljivka x(e) in obrez ob semaforjih in postajališčih |
| **P14** (nov) | **okna in pari:** javno pravilo oken in parov iz §5.1 in ena koda, ki izlušči čase oken iz `matched_points` (naprava), iz simuliranih poti P3 (preverba) in iz sintetičnih poti s časi (metrika) | ni ocenjen | poročilo, preverba in metrika merijo isto (izpeljava pisca iz zahteve po enakem izluščenju, §6.4) |
| **P15** (nov) | **javna preverba pred zamrznitvijo** (§6.1): okoli ena ura računanja na P3, brez Geolife; izid je »obdrži, zamenjaj ali ustavi« | ni ocenjen | odloči, ali se T3 gradi (odločitvi 2 in 3) |
| **P16** (nov) | **metrika hitrosti oken** (§6.4): W1 po slojih razreda ceste, semaforjev in fasade ter W1 razpršenosti znotraj poti, bootstrap po uporabnikih, podpora za placebo roko | ni ocenjen | vidnost γ̂ na benchmarku (odločitev 5) |

### 9.2 Vrstni red sej (navpične rezine)

Vsak korak je ena veja in en PR in se konča z izidom, ki ga je mogoče preveriti.

1. **P0 + P1** (prompt v `NACRT_ULDP_SINTEZA.md` §8.3), če še nista v `main`; P1 mora
   zapisati tudi postanke.
2. **P13**, semantična plast OSM (prompt v §9.3); od ostalih korakov neodvisna, zato lahko
   teče tudi prva (opažanje pisca).
3. **P10**, razrez sej (prompt v `NACRT_ULDP_RANGI.md` §9.3), pred javno preverbo.
4. **P11**, eno poročilo na učnega uporabnika (po P0; test sodi v komplet P4).
5. **P3**, skupni javni model; če ga je zgradil že drug mehanizem, se uporabi isti.
6. **P14**, okna in pari.
7. **P15**, javna preverba: »obdrži« ali »zamenjaj« vodi naprej; »ustavi« pomeni umik
   (odločitev 3), T3 pa se nadaljuje le kot modul v P6 (korak 11).
8. **P2 + P12 + P16**, metrike.
9. **P4 + P5**, zasebnostni komplet in preverbe ogrodja.
10. **Mehanizem T3:** `encode_user` (okna, pari, razred, GRR), `server_fit` (popravek šuma,
    pogojni binomski test, urejeni probit, zaokrožitev), sinteza s časi po odsekih in
    `sequence_log_prob` s petimi tabelami stroškov.
11. **P6**, simulacija obnovitve (§6.3).
12. **Meritve** pri u20 (dimni test), u50 in u182 s placebo in kontrolnimi rokami; prior in vse
    konstante zamrznjeni pred prvim pogonom pri 182; zapis v `docs/HANDOFF.md`.

Ocenjevalec ocenjuje T3 na okoli 4 seje (potrebuje P1 s postanki, čase oken na napravi,
plast fasade, pet tabel stroškov in novo metriko); gradivo ne pove, ali so skupni predpogoji
všteti.

### 9.3 Prompt za prvo sejo (P13)

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_ULDP_ODSEKI.md SAMO §0, §5.1 (javni podatki) in §9.1 (vrstica P13); arhiva
arhiv/ ne odpiraj. Za branje kode (kako maps/osm.py in maps/build.py zgradita zemljevid
Pekinga iz OSM, od kod pride posnetek OSM, katere oznake vozlišč ostanejo v datoteki grafa
in kako je sestavljen hash zemljevida) uporabi svežega podagenta general-purpose, ki vrne
kratek povzetek; glavni kontekst naj ostane čist.

Naloga P13: iz ISTEGA posnetka OSM, iz katerega je zgrajen zemljevid, izvozi javno
semantično plast za povezave: (1) fasado s trgovinami, to je delež 30-metrskega pasu ob
povezavi, ki ga pokrivajo trgovska ali maloprodajna raba tal ali točke shop/amenity;
(2) pozidano fasado, to je ali je v 30 m kakršnakoli stavba (zidovi, parki in ograje so
nasprotje); (3) semaforje (highway=traffic_signals) in (4) avtobusna postajališča. Shrani
kot Parquet s ključem hasha zemljevida in pravila plasti. Dodaj javno preverbo pokritosti
po conah 3 × 3 (le OSM, nikoli Geolife). Pragove (visoka fasada vsaj 0.5, nizka največ 0.1)
vzemi iz načrta kot predlog; ničesar ne nastavljaj po Geolife, dokončno jih zamrzne avtor
pred prvim pogonom pri 182. Testi brez omrežja, nad majhno ročno sestavljeno fiksturo
poligonov in točk ob obstoječi fiksturi zemljevida: povezava ob poligonu trgovine dobi
pričakovani delež, povezava brez ničesar dobi 0, izid je determinističen, ključ
predpomnilnika se spremeni ob spremembi pravila.

Postopek: začni v plan mode in počakaj na mojo potrditev. Naloga je majhna, zato skill
orchestrate ni potreben; če bi presegla ~5 datotek ali mešala teme, najprej predlagaj
razrez. Ustvari vejo claude/uldp-odseki-p13. Definicija končanega: uv run ruff check .,
uv run mypy src in uv run pytest -q čisti; prilepi ukaz in zadnjih ~10 vrstic izpisa.
Proračun izpisa: pytest -q, nikoli -v, ob napaki ponovi le padli test; dolge izpise
skrajšaj s | tail -20; najprej git diff --stat. Nova odvisnost potrebuje enovrstično
utemeljitev v opisu PR. V istem PR posodobi vrstico stanja v CLAUDE.md in označi P13 kot
zaključen v §9.1 načrta. Koda, identifikatorji, docstringi in testi v angleščini; pogovor z
mano v slovenščini, brez nepojasnjenih kratic.
```

## 10. Viri

Vsa dela, navedena v načrtu, po temah; najbližja dela so z opisom v tabelah §4.1 in §4.2.
Poizvedbe in vsi zadetki so v arhivu (`30_novelty_G1.md` do `30_novelty_G3.md`). Kjer gradivo
leta ne navaja ali ga ni preverilo, je to zapisano.

| Tema | Dela (leto, povezava) |
|---|---|
| LDP na ravni uporabnika in učinki znotraj uporabnika | Roth, Avella-Medina 2025, https://arxiv.org/abs/2511.18583; Sopa, Avella-Medina, Rush 2026, https://arxiv.org/abs/2601.10626; Zhao et al. 2024, https://arxiv.org/abs/2405.17079; Ma, Jia, Yang, ICML 2024, https://proceedings.mlr.press/v235/ma24c.html; Kent, Berrett, Yu 2024, https://arxiv.org/abs/2405.11923; Canonne, Gentle, Singhal, ITCS 2026, https://arxiv.org/abs/2510.18379 |
| Znakovni odgovori, testi in primerjave | Kalinin, Steinberger 2024 (AISTATS 2025), https://arxiv.org/abs/2402.04840; Joseph, Kulkarni, Mao, Wu, NeurIPS 2019, https://arxiv.org/abs/1811.08382; Ding, Nori, Li, Allen, AAAI 2018, https://ojs.aaai.org/index.php/AAAI/article/view/11301; Ohnishi, Awan, JMLR 26 (2025), https://www.jmlr.org/beta/papers/v26/23-1401.html; Awan, Slavković 2018, https://arxiv.org/abs/1904.00459 (povezava: revijska različica); Couch et al. 2018, https://arxiv.org/abs/1809.01635 |
| Zasebne hitrosti in mešanica načinov | Rameshwar et al. 2024, https://arxiv.org/abs/2401.15906; Brown, Ohrimenko, Tamassia (Haze), ACM SIGSPATIAL 2013, https://arxiv.org/abs/1309.3515; Bian et al. 2024 (Google EIE), https://arxiv.org/abs/2407.03496 |
| Stransko trenje (nezasebno ozadje) | »Critical Analysis of Road Side Friction on an Urban Arterial Road«, ETASR, https://etasr.com/index.php/ETASR/article/view/5603 (leto ni navedeno); študija hitrosti GPS na arterijskih cestah Chennaija, https://trid.trb.org/View/777779 (leto nepreverjeno) |
| Zakon cilja (T1) | Simini, González, Maritan, Barabási, Nature 2012, https://arxiv.org/abs/1111.0586; Yang, Herrera, Eagle, González 2014, https://doi.org/10.1038/srep05662; Noulas et al., PLoS ONE 2012, https://doi.org/10.1371/journal.pone.0037027; Gibbs, Musolesi, Cheshire, Eggo 2026, https://doi.org/10.1140/epjds/s13688-025-00611-4; DP-WHERE (Mir et al., IEEE BigData 2013), https://doi.org/10.1109/BigData.2013.6691626; Sakong, Zentefis, NBER (osnutek 2024–26), https://www.nber.org/books-and-chapters/data-privacy-protection-and-conduct-applied-research-methods-approaches-and-new-findings/simulation-based-method-estimating-economic-models-privacy-protected-data; poročilo CAUPD in Baidu o poteh na delo (kandidat za javno merilo T1, nepreverjeno, brez povezave) |
| Hierarhija poti (T2) | Ramaekers, Reumers, Wets, Cools 2013, https://doi.org/10.1007/s11067-013-9184-8; Yao, Bekhor 2020, https://arxiv.org/abs/2006.04536; Haydari et al. (DPMM), ACSAC 2022, https://doi.org/10.1145/3564625.3567974; Yang et al., IEEE TSC 2020, https://arxiv.org/abs/2012.13807; AHEAD, CCS 2021, https://arxiv.org/abs/2110.07505; Egéa, Escobar-Bach 2023, https://arxiv.org/abs/2311.01303; Geisberger et al. 2012, https://doi.org/10.1287/trsc.1110.0401 |
| Semantične relacije (T4) | Cunningham, Cormode, Ferhatosmanoglu, Srivastava 2021, https://www.vldb.org/pvldb/vol14/p2283-cunningham.pdf; Sun et al. (PLTS) 2024, https://research.polyu.edu.hk/en/publications/generating-location-traces-with-semantic-constrained-local-differ/; Wang et al. (L-SRR), CCS 2022, https://arxiv.org/abs/2209.15091; NCHRP Report 684 (2011), https://nap.nationalacademies.org/read/14489/chapter/3 |
| Gradient metrike (T5) | Duchi, Ruan 2024, https://arxiv.org/abs/1806.05756 (DOI 10.1214/22-AOS2227); Steinberger 2024, https://arxiv.org/abs/2301.10600; McKenna, Maity, Mazumdar, Miklau 2020, https://arxiv.org/abs/2002.01582 |
| Porazdelitev trajanja (T6) | Liu, Hu, Kong, ICML 2024, https://proceedings.mlr.press/v235/liu24z.html; Hu, Liu, ICML 2026 (poster), https://icml.cc/virtual/2026/poster/64491; Aamand et al. 2025, https://arxiv.org/abs/2502.02990; Cormode, Kulkarni, Srivastava 2019, https://www.vldb.org/pvldb/vol12/p1126-cormode.pdf |
