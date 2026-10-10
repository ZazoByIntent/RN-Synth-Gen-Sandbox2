# Izvedba 3: kontrasti časov po odsekih znotraj poti T3 (samostojna seja)

Seja zgradi mehanizem iz `docs/NACRT_ULDP_ODSEKI.md`. Pred začetkom preberi
`docs/IZVEDBA_ULDP_SKUPNO.md`, kjer so pravila poteka, vloge, predloge pozivov,
artefakt in konec seje. Algoritem je v načrtu in se tu ne ponavlja.

**Vhod:** seji 1 in 2 sta končani; to potrjujeta dnevnika v
`docs/IZVEDBA_ULDP_SINTEZA.md` in `docs/IZVEDBA_ULDP_RANGI.md`.
**Izhod je odvisen od javne preverbe P15.**

- **Preverba prestane** za eno od dveh plasti fasade: v `main` je generator
  `uldp_segment` s placebo roko, izmerjena sta u20 in u50, v HANDOFF je zapis, na
  voljo je artefakt.
- **Preverba pade** za obe plasti: velja umik (blok F). T3 ostane le modul v
  simulaciji P6, v HANDOFF je zapisan umik, artefakt se vseeno naredi.

**Vhodna preverba (blok 0).** Orkestrator prebere le dnevnika sej 1 in 2. Če kateri
od P0–P6 ali P10–P12 ni združen, ga najprej zgradi po `IZVEDBA_ULDP_SINTEZA.md` §2.
Seja 2 za ta mehanizem ni nujna. Če ni končana, se to zapiše in seja nadaljuje.

## 1. Odločitve, ki zaprejo odprte točke načrta

| Točka načrta (O §8) | Odločitev |
|---|---|
| 1, plast fasade | Odloči P15 po vnaprej prijavljenem pravilu iz O §6.1. Najprej se preizkusi fasada s trgovinami, nato pozidana fasada v 30 m. Pragov se ne spreminja. |
| 2, umik | Če P15 pade za obe plasti, se izvede blok F. Načrta K-α seja ne piše; v HANDOFF ga zapiše kot naslednji korak, ki ga začne avtor. |
| 3, T1 | V tej seji se ne gradi (enako kot v seji 2). |
| 4, konstante oken in parov | Veljajo vrednosti iz O §8 točka 4: okno 100 m; obrez 40 m ob vozliščih ter 80 m pred semaforji in ob postajališčih; največ 3 minute med oknoma; izločitev prvih in zadnjih 200 m in postankov nad 60 s; K = 10; vsaj trije različni pari; meje ±0.1 nata; pragova fasade 0.5 in 0.1; raven testa α = 0.05. Viri za popravke ob semaforjih se citirajo. Konstante se zamrznejo s hashem commita pred P15. |
| 5, lestvica šuma | Iz tresenja P3, kot je zapisano v `public_sim.py`. |
| 6, oblika pri ε = 8 | Enaki štirje odgovori kot pri drugih ε. Šestih vrednosti in delitve po konici ni. |
| 7, utež | Po uporabnikih, enako kot v seji 1. |
| 8, časovni MIA | Ne gradi se (SKUPNO §2, točka 4). |
| 9, pravila izdaje | Javna zgornja meja vpliva enega poročila na sproščeno verjetje se zgradi. V P6 se doda roka zastrupitve z 0, 2, 5 in 10 lažnimi uporabniki; prag zloma se le poroča. |
| 10, vrstni red | Ta mehanizem je tretji, po sejah 1 in 2. |
| 11, razrez | Odločeno v SKUPNO §2, točka 3; konfiguracije T3 imajo razrez vklopljen. |
| Posnetek OSM | P13 izvozi plast iz istega posnetka kot zemljevid (`maps/beijing/meta.json`, `osm_timestamp` 2026-07-12, isti bbox). Če točno tega posnetka ni mogoče dobiti, uporabi poizvedbo Overpass z datumskim filtrom tega trenutka in to zapiše. Rezultat je regenerabilen predpomnilnik ob zemljevidu, ključ je hash zemljevida in pravila. |
| Imena | `@register("generator", "uldp_segment")` v `src/trajguard/synthesis/uldp_segment.py`. Koda oken in parov (P14) je ena sama in jo kličejo naprava, preverba in metrika; mesto predlaga izvajalec. |

## 2. PR-bloki in enote

O = `NACRT_ULDP_ODSEKI.md`, S = `NACRT_ULDP_SINTEZA.md`.

| Blok | Enota | Cilj | Razdelki |
|---|---|---|---|
| A plast | P13 | semantična plast OSM: trgovine, stavbe, semaforji, postajališča; x(e) na povezavo; preverba pokritosti po conah 3 × 3 | O §9.1 (P13), §5.1 |
| B okna | P14 | okna in pari: ena koda za `matched_points`, poti P3 in sintetične poti | O §5.1, §9.1 (P14) |
| C preverba | P15 | javna preverba nad P3 brez Geolife (okoli ena ura, zažene jo validator); izid »obdrži«, »zamenjaj« ali »ustavi« gre v dnevnik in HANDOFF | O §6.1 |
| D mehanizem | P16 | metrika hitrosti oken s podporo za placebo roko | O §6.4, §9.1 (P16) |
| D | T3 | `encode_user` (okna, pari, razred, GRR) in `server_fit` (popravek šuma, pogojni binomski test, urejeni probit, zaokrožitev); sinteza s časi po odsekih; `sequence_log_prob` s petimi tabelami stroškov | O §5.2–§5.4; S §4.7 |
| D | zasebnost | testi 1–4 iz zasebnostnega kompleta za ta generator in test natanko enega poročila | O §5.5, §7; S §6.2 |
| E dokaz | P6 | simulacija obnovitve γ in roka zastrupitve | O §6.3, §8 točka 9 |
| E | konfiguracija | `config/experiments/geolife_uldp_segment_mia_u20.yaml` in `_u50.yaml` (§3) | O §6.4 |
| E | validacija | pogoni in primerjave iz §3 (validator) | — |
| E | dokumenti | HANDOFF, CLAUDE.md, O §9.2 | SKUPNO §9 |
| F umik | P6-T3 | samo če P15 vrne »ustavi«: T3 kot modul v simulaciji P6, brez konfiguracije Geolife; HANDOFF zapiše umik in izid preverbe | O §0 odločitev 3, §6.3 |

Bloka A in B se smeta prekrivati, ker se ne dotikata istih datotek. Blok C se začne
šele, ko sta A in B združena. Če P15 vrne »ustavi«, se bloka D in E preskočita, izvede
se blok F in seja gre na artefakt.

**Posebne točke za recenzenta.**

- Okna se izluščijo z isto kodo na napravi, v preverbi in v metriki.
- Plast fasade ne uporablja Geolife.
- Pri P15 se pravilo »obdrži, zamenjaj, ustavi« izvaja s pragovi iz O §6.1, ki jih
  koda ne sme nastavljati.
- Placebo roka res nima učinka.
- Zamrznjene konfiguracije so nespremenjene.

## 3. Validacija na pravih podatkih (samo po bloku D)

Konfiguraciji kopirata populacijo, delitev, napad in proračun iz `geolife_uldp_mia_u*`
seje 1. Roke so:

- prior in orakelj;
- `uldp_segment` pri ε ∈ {0.5, 2, 8};
- placebo roka (okna z naključno javno oznako namesto fasade);
- `uldp_synth` sestavljena in `uldp_rank` rang s parom pri ε = 2, če obstajata;
- `markov` (red 1).

Validator izvede tri preverbe:

1. **Regresija.** Ponovno požene `geolife_uldp_mia_u20.yaml` (pod začasnim imenom).
   Vrstice morajo biti bit za bitom enake rezultatom seje 1.
2. **Nova pogona.** u20 in u50, semena 1–3. Validator poroča AUC in `tpr@fpr=0.1`,
   metriko hitrosti oken (P16) in primarne metrike seje 1.
3. **Izid testa.** Pri vsakem ε poroča delež uporabnikov brez para, izid binomskega
   testa z vrednostjo p in γ̂ z intervalom. Placebo roka mora dati γ̂ blizu 0.

## 4. Artefakt

Velja SKUPNO §8. Na strani je odsek ene poti (iz fiksture ali simulacije, ne iz
Geolife) z označenimi okni, obrezi ob vozliščih in semaforjih ter fasado. Sledi par
oken, izračun ostanka v natih, razred, ki ga pošlje telefon, in naključni odgovor.
Na strani strežnika so prikazani števci »počasneje« proti »hitreje«, binomski test,
γ̂ in to, kako γ̂ spremeni čase po odsekih sintetične poti. Prikazan je tudi izid P15 s
pragovi. Ob umiku stran pokaže, zakaj je preverba padla.

## 5. Prompt za začetek seje

Model orkestratorja je Opus 5.5 z naporom *high*, v samodejnem načinu dovoljenj. Prilepi:

```
Implementacijska seja 3 od 3 v repozitoriju trajguard: mehanizem ULDP s kontrasti časov
po odsekih znotraj poti (T3). Delaš kot orkestrator popolnoma samostojno, od začetka do
konca, brez plan mode in brez vprašanj meni; avtor je načrt vnaprej potrdil. Preberi
CLAUDE.md (že naložen), nato v celoti docs/IZVEDBA_ULDP_SKUPNO.md in
docs/IZVEDBA_ULDP_ODSEKI.md. Ta dva dokumenta imata prednost pred CLAUDE.md in skillom
orchestrate, kjer si nasprotujejo. Iz IZVEDBA_ULDP_SINTEZA.md in IZVEDBA_ULDP_RANGI.md
preberi le dnevnika izvedbe na dnu (vhodna preverba). Načrtov NACRT_ULDP_* ne beri sam;
razdelke berejo podagenti. Kode, diffov in dnevnikov pogonov ne beri; drži kontekst
nizek po SKUPNO §4. Če dnevnik na dnu IZVEDBA_ULDP_ODSEKI.md ni prazen, nadaljuj tam,
kjer se je ustavil. Pojdi skozi bloke (0), A–E oziroma F po izidu preverbe P15, vsak blok
svoj PR, ki ga po zeleni recenziji sam združiš v main. Na koncu pošlji risarja za
artefakt (SKUPNO §8) in mi poročaj po SKUPNO §9, v slovenščini, brez nepojasnjenih kratic.
```

## Dnevnik izvedbe

(prazno; prvi vnos naredi orkestrator seje 3)
