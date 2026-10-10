# Izvedba 2: umerjanje z rangi in pari K1 + K8 (samostojna seja)

Seja zgradi mehanizem iz `docs/NACRT_ULDP_RANGI.md`. Pred začetkom preberi
`docs/IZVEDBA_ULDP_SKUPNO.md`, kjer so pravila poteka, vloge, predloge pozivov,
artefakt in konec seje. Algoritem je v načrtu in se tu ne ponavlja.

**Vhod:** seja 1 je končana. V `main` so P0–P6, P10–P12, `public_sim.py` in
`uldp_synth`, kar potrjuje dnevnik v `docs/IZVEDBA_ULDP_SINTEZA.md`.
**Izhod:** v `main` je generator `uldp_rank` z rangom trajanja in parom, kontrolne
roke na ravni uporabnika, simulacija P6 za ta mehanizem, izmerjena u20 in u50 ob roki
C1 na istih uporabnikih, zapis v HANDOFF in artefakt.

**Vhodna preverba (blok 0).** Orkestrator prebere le dnevnik seje 1. Če kateri
predpogoj ni združen, ga najprej zgradi kot blok 0 po tabeli enot v
`IZVEDBA_ULDP_SINTEZA.md` §2 in z odločitvami iz njenega §1. Če manjka generator
`uldp_synth`, se primerjava s C1 (§3) izpusti in to se zapiše.

## 1. Odločitve, ki zaprejo odprte točke načrta

| Točka načrta (R §8) | Odločitev |
|---|---|
| 1, prior proti nasičenju | Doda se razred »precej počasneje«. Meje razredov so pri kvantilih priorja PIT 0.5, 0.95 in 0.999, zato so razredi štirje, s ⊥ pa pet. Ničelna hipoteza ostane točna. Mešanice hoje in vožnje v priorju ni. |
| 2, pravilo upravičenih parov | Okni konice sta 7.00–9.00 in 17.00–19.00 po lokalnem času, z citiranim virom za Peking. Razmerje javnih časov prostega toka obeh poti mora biti v [0.8, 1.25]. Če para ni, uporabnik pošlje ⊥. Pravilo se zamrzne, preden kdo pogleda Geolife (F8). |
| 3, metrika | P12 je zgrajen v seji 1. Dvorazsežna JSD za kopulo se doda le, če P12 ne loči roke s parom od roke brez para v simulaciji P6. |
| 4, razrez sej | Odločeno v SKUPNO §2, točka 3. |
| 5, uporabniki brez ujete poti | Rešeno s P11 v seji 1. |
| 6, gostitelj | `public_sim.py` (P3). |
| 7, vrstni red glede na C1 | Seja 1 je C1 že zgradila. Konfiguracija tega mehanizma vsebuje roko `uldp_synth` samo C1 pri istem ε, nad istimi uporabniki. |
| 8, utež | Po uporabnikih. |
| 9, vprašanja in dvojčki | Vprašanja so *dur*, *dep* in *len*; vsa so kategorična z GRR, zato HM ni potreben. Število dvojčkov je vrednost, ki jo priporoča R §5.1; če razdelek da le razpon, je 39. Raven vrat je α = 0.05. Število vprašanj določa javno pravilo n·ε² iz §5.1. |
| 10, časovni MIA | Ne gradi se (SKUPNO §2, točka 4). |
| 11, vprašanje *dest* (T1) | V tej seji se ne doda. V HANDOFF se zapiše kot naslednji korak, z opombo, da najprej potrebuje preverjen podatek o razdaljah poti v Pekingu. |
| Imena | `@register("generator", "uldp_rank")` v `src/trajguard/synthesis/uldp_rank.py`. Generator uporabi `public_sim.py` in gradnike iz `privacy/ldp.py` in jih ne podvaja. |

## 2. PR-bloki in enote

R = `NACRT_ULDP_RANGI.md`, S = `NACRT_ULDP_SINTEZA.md`.

| Blok | Enota | Cilj | Razdelki |
|---|---|---|---|
| A rang | dvojčki | izdelava dvojčkov za isti kontekst nad P3, deterministično s semenom | R §5.1, §5.3 |
| A | rang trajanja | `encode_user` (rang, razred, GRR) in `server_fit` (popravek šuma, vrata, preslikava kvantilov); `sequence_log_prob` | R §5.1, §5.2, §5.4; S §4.7 |
| A | zasebnost | testi 1–4 iz zasebnostnega kompleta (P4) za ta generator in test natanko enega poročila | R §5.5, §7; S §6.2 |
| B par | par in znak | K8 a in c s pravilom upravičenih parov iz §1 | R §5.1, §5.2, §8 točka 2 |
| C kontrole | kontrolne roke | `ldptrace` in `rn_ldp_synth`, dvignjeni na raven uporabnika | R §6.3 |
| C | P6 | simulacija: raven vrat pri zakonih števila poti {1, 3, 9, 30} na uporabnika; populacija, v kateri je čas potovanja povezan s tem, kdo potuje | R §6.2; S §5.5 |
| D dokaz | konfiguracija | `config/experiments/geolife_uldp_rank_mia_u20.yaml` in `_u50.yaml` (§3) | R §6.3 |
| D | validacija | pogoni in primerjave iz §3 (validator) | — |
| D | dokumenti | HANDOFF, CLAUDE.md, R §9.2 | SKUPNO §9 |

**Posebne točke za recenzenta.**

- Dvojčki ne uporabijo nobenega podatka, ki ni v kontekstu poti.
- Meje razredov so iz priorja, ne iz podatkov.
- Vrata so vnaprej prijavljena: roka obdrži prior, razen če test zavrne.
- Pod ničelno hipotezo je test točen. Izvajalec to pokaže s testom nad simuliranimi
  rangi.
- Zamrznjene konfiguracije so nespremenjene.

## 3. Validacija na pravih podatkih

Konfiguraciji kopirata populacijo, delitev, napad in proračun iz `geolife_uldp_mia_u*`
seje 1, z razrezom sej. Roke so:

- prior in orakelj;
- `uldp_rank` samo rang ter rang s parom pri ε ∈ {0.5, 2, 8};
- `uldp_synth` samo C1 pri istem ε;
- kontrolni roki na ravni uporabnika in `markov` (red 1).

Validator izvede tri preverbe:

1. **Regresija.** Ponovno požene `geolife_uldp_mia_u20.yaml` (pod začasnim imenom).
   Vrstice morajo biti bit za bitom enake rezultatom seje 1. Isto preveri za
   `geolife_mech_mia_u20.yaml` proti `results/geolife_mech_mia_u20/`.
2. **Nova pogona.** u20 in u50, semena 1–3. Validator poroča AUC in `tpr@fpr=0.1` ter
   primarne metrike uporabnosti, posebej W1 trajanja znotraj obdobja odhoda.
3. **Izid vrat.** Pri vsakem ε poroča izid vrat (zavrne ali ne zavrne, z vrednostjo p)
   in primerjavo z rokama C1 in prior na istih uporabnikih.

## 4. Artefakt

Velja SKUPNO §8. Na strani je ena prava pot (iz fiksture, ne iz Geolife), njenih
dvojčkov in mesto prave poti med njimi. Sledi razred, ki ga pošlje telefon, in
histogram razredov čez vse uporabnike ob enakomernem histogramu ničelne hipoteze.
Prikazani so tudi izid vrat in premik porazdelitve trajanj. Ločeno je prikazan par
konica proti času zunaj konice. Številke so iz pogona u50.

## 5. Prompt za začetek seje

Model orkestratorja je Opus 5.5 z naporom *high*, v samodejnem načinu dovoljenj. Prilepi:

```
Implementacijska seja 2 od 3 v repozitoriju trajguard: mehanizem ULDP z rangi in pari
(K1 + K8). Delaš kot orkestrator popolnoma samostojno, od začetka do konca, brez plan
mode in brez vprašanj meni; avtor je načrt vnaprej potrdil. Preberi CLAUDE.md (že
naložen), nato v celoti docs/IZVEDBA_ULDP_SKUPNO.md in docs/IZVEDBA_ULDP_RANGI.md. Ta
dva dokumenta imata prednost pred CLAUDE.md in skillom orchestrate, kjer si nasprotujejo.
Iz docs/IZVEDBA_ULDP_SINTEZA.md preberi le dnevnik izvedbe na dnu (vhodna preverba).
Načrtov NACRT_ULDP_* ne beri sam; razdelke berejo podagenti. Kode, diffov in dnevnikov
pogonov ne beri; drži kontekst nizek po SKUPNO §4. Če dnevnik na dnu
IZVEDBA_ULDP_RANGI.md ni prazen, nadaljuj tam, kjer se je ustavil. Pojdi skozi bloke
(0), A–D, vsak blok svoj PR, ki ga po zeleni recenziji sam združiš v main. Na koncu
pošlji risarja za artefakt (SKUPNO §8) in mi poročaj po SKUPNO §9, v slovenščini, brez
nepojasnjenih kratic.
```

## Dnevnik izvedbe

(prazno; prvi vnos naredi orkestrator seje 2)
