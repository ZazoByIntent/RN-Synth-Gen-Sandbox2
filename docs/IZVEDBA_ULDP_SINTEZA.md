# Izvedba 1: sinteza ULDP z moduli C3, C2, C1 (samostojna seja)

Seja zgradi skupne predpogoje vseh treh mehanizmov ULDP in mehanizem iz
`docs/NACRT_ULDP_SINTEZA.md`. Pred začetkom preberi `docs/IZVEDBA_ULDP_SKUPNO.md`,
kjer so pravila poteka, vloge, predloge pozivov, artefakt in konec seje. Algoritem
je v načrtu in se tu ne ponavlja.

**Vhod:** `main` vsebuje vse tri načrte, kode ULDP še ni.
**Izhod:** v `main` so predpogoji P0–P6 in P10–P12, generator `uldp_synth` z
rokami C3, C2, C1 in sestavljeno roko, izmerjeni u20 in u50, zapis v HANDOFF in
artefakt. Na tej kodi gradita seji 2 in 3.

## 1. Odločitve, ki zaprejo odprte točke načrta

Zapisane so za samostojno sejo. Avtor jih lahko spremeni tu, pred začetkom seje.

| Točka načrta | Odločitev |
|---|---|
| Ugotovitve F1–F9 (RANGI §10) | Uveljavijo se v kodi. F1: P1 zapiše postanke, P10 razreže seje. F2: oznaka C3 se vleče iz aposteriorne porazdelitve **ene** enakomerno izbrane poti. F3: P11. F5: za cone 3 × 3 se uporabi GRR, ne OLH. F6: roka samo C1 pri ε = 2 se poroča kot preverba. F7: vrata za vsak modul. F8: zamrznitev konstant. Številke šuma F4 se popravijo v SINTEZA §4.3, §4.4 in §5.1. |
| §7.1 točka 1, roke priorja | Ena skupna roka priorja (ε → 0) in ena roka orakla. Lastnih rok priorja po modulih ni. |
| §7.1 točka 2, dokaz uporabnosti | Referenca so zadržani testni uporabniki. Utež je po uporabnikih (RANGI §8, točka 8). Primarne metrike so: W1 trajanja, W1 povprečne hitrosti, krožna razlika ure odhoda, JSD matrike OD 3 × 3 in W1 trajanja znotraj obdobja odhoda (P12). Dobiček je (prior − roka) / (prior − orakelj), z bootstrap intervalom po uporabnikih. Metrika, kjer orakelj ne premaga priorja, se izpiše, a ne šteje kot dokaz. |
| §7.1 točka 3, enota zasebnosti | `fit` dobi vse učne uporabnike (P11). Kdor nima ujete poti, pošlje javno privzeto vrednost. n se šteje iz učnega dela. Kandidati MIA vstopijo v senčne prilagoditve pod svojim `user_id`. Število vprašanj je določeno s konfiguracijo. |
| §7.1 točka 4 | P8 se ne gradi (SKUPNO §2, točka 4). |
| §7.1 točka 5, dodeljevanje | Javni žreb deli uporabnike na tretjine C1, C2 in C3. Žreb uporablja javno seme nad urejenim seznamom vpisanih uporabnikov, ne podatkov. Mreža ε je {0.5, 2, 8}. Število vprašanj določa javno pravilo n·ε² iz §4.2. Popravki C1 se nanesejo na vse režime C3 enako. |
| §7.1 točka 6 | Pragov ni (SKUPNO §2, točka 5). V `run.json` se zapiše ε na ravni uporabnika. Za mehanizme na pot se zapiše še m·ε, kjer je m največje število ujetih poti na uporabnika. |
| §7.2 C3 | Pred kodo se izvede preverba P9a: ali graf `maps/beijing` vsebuje pešpoti in kolesarske steze. Katalog ima tri režime (hoja, kolo, motorni promet) s citiranimi hitrostmi. Če pešpoti v grafu ni, se režimi razlikujejo le po hitrosti; to se zapiše. |
| §7.2 C2 | Mreža con je 3 × 3 čez javni okvir zemljevida (`maps/beijing/meta.json`, bbox). Pasovi stroška in obdobja dneva so iz §4.4; manjkajoče meje se vzamejo iz citiranega vira. |
| §7.2 C1 | P9b: izvajalec poskusi dobiti celotno besedilo GeoPM-DMEIRL s spleta. Če ga ne dobi, C1 zgradi po §4.5 in v HANDOFF zapiše, da trditev o novosti ni preverjena. |
| P10, pravilo razreza | Postanek je vsaj 3 minute znotraj 150 m ali vrzel vsaj 3 minute s premikom pod 300 m (RANGI §8, točka 4). Razrez je možnost čiščenja (`cleaning.split_sessions`) in je privzeto izklopljen. |
| P6 | Simulacija obnovitve parametrov do n = 10 000 po §5.5. P7 (T-Drive) se ne gradi. |
| Imena | Generator je `@register("generator", "uldp_synth")` v `src/trajguard/synthesis/uldp_synth.py`. Javni model P3 je v `src/trajguard/synthesis/public_sim.py`, ker si ga delijo vsi trije mehanizmi. Gradniki LDP gredo v obstoječi `privacy/ldp.py`, če tam še niso. Imena so obvezna, ker se nanje sklicujeta seji 2 in 3. |

## 2. PR-bloki in enote

Stolpec »Razdelki« pove, kaj izvajalec prebere. Orkestrator teh razdelkov ne bere.
S = `NACRT_ULDP_SINTEZA.md`, R = `NACRT_ULDP_RANGI.md`.

| Blok | Enota | Cilj | Razdelki |
|---|---|---|---|
| A podatki | P0 | dejstva o `user_id` v `fit`, test nad fiksturo, dejstva vpisana v S §7.1 točka 3 | S §7.1, §8.1 (P0); R §10 F3 |
| A | P1 | časovni sintetični payload z vstopom in izstopom na povezavo (postanki), UTC+8, Parquet | S §8.1 (P1); R §10 F1 |
| A | P10 | razrez sej ob postankih kot možnost čiščenja; novi ključ predpomnilnika | R §8 točka 4, §9.1, §9.3 |
| A | P11 | vsak učni uporabnik pošlje natanko eno poročilo; test z uporabnikom, čigar poti nehajo prestajati ujemanje | R §9.1 (P11), §10 F3; S §4.2 |
| B metrike | P2 + P12 | metrike uporabnosti v orkestratorju, posodobljen `REZULTATI_SHEMA.md` in test, ki ga pripenja | S §5.3, §8.1 (P2); R §8 točki 3 in 8; `docs/REZULTATI_SHEMA.md` |
| C model | P3 | javni model, roki priorja in orakla, predpomnilnik po hashu | S §4.1, §4.7 |
| C | P4 + P5 | razrez `encode_user` / `server_fit`, zasebnostni testi 1–4 s pozitivno kontrolo, ε na uporabnika v `run.json` | S §4.6, §6.2, §7.1 točka 3 |
| D moduli | C3 | P9a, nato modul C3 z vrati F7 | S §4.3, §6.3, §7.2; R §10 F2, F4, F7 |
| D | C2 | modul C2 z GRR nad 3 × 3 | S §4.4, §6.3; R §10 F5, F7 |
| D | C1 | P9b, nato modul C1 z Boltzmannovim sprehodom | S §4.5, §6.3; R §10 F6, F7 |
| D | sestavljena | sestavljena roka z žrebom tretjin | S §4.2, §7.1 točka 5 |
| E dokaz | P6 | simulacija obnovitve parametrov | S §5.5 |
| E | konfiguracija | `config/experiments/geolife_uldp_mia_u20.yaml` in `_u50.yaml` (§3) | S §5.3; SKUPNO §2 |
| E | validacija | pogoni in primerjave iz §3 (validator) | — |
| E | dokumenti | HANDOFF, CLAUDE.md, S §8.2 in popravek številk F4 v S | SKUPNO §9 |

Enote bloka A tečejo zaporedno, ker vse posegajo v čiščenje ali orkestrator. Moduli
C3, C2 in C1 tečejo zaporedno, ker si delijo datoteko generatorja.

**Posebne točke za recenzenta.**

- Ali kdo poroča in koliko vprašanj dobi, ni odvisno od zasebnih podatkov.
- Žreb modula je javen.
- Nobena konstanta nima vira v Geolife.
- Zamrznjene konfiguracije so bajt za bajtom nespremenjene (`git diff main -- config/`).
- Pri vratih velja pravilo, da roka obdrži prior, razen če test zavrne.

## 3. Validacija na pravih podatkih

Novi konfiguraciji sta sestrski kopiji `geolife_mech_mia_u20.yaml` oziroma `_u50.yaml`.
Populacija, delitev, napad in proračun ostanejo enaki. Vklopljen je razrez sej
(`cleaning.split_sessions: true`).

Roke so:

- roka priorja in roka orakla;
- C3, C2, C1 in sestavljena roka pri ε ∈ {0.5, 2, 8};
- kontrolne roke `markov` (red 1), `rn_ldp_synth` in `ldptrace` z istimi nastavitvami
  kot v `geolife_mech_mia_u*`.

V glavi konfiguracije je komentar, ki pojasni, zakaj je to sestrska datoteka.

Validator izvede tri preverbe:

1. **Regresija.** Na končni kodi požene nespremenjeni `geolife_mech_mia_u20.yaml` in
   `geolife_mech_mia_u50.yaml` (semena 1–3, pod začasnim imenom, SKUPNO §7.2).
   Vrstice morajo biti bit za bitom enake obstoječim v `results/geolife_mech_mia_u20/`
   in `results/geolife_mech_mia_u50/`. Če niso, je to kritična napaka bloka, ki je
   spremenil privzeto vedenje.
2. **Nova pogona.** `uv run trajguard repeat config/experiments/geolife_uldp_mia_u20.yaml
   --seeds 1 2 3`, nato isto za u50. Validator poroča AUC in `tpr@fpr=0.1` napada MIA
   ter primarne metrike uporabnosti po rokah, z intervali.
3. **Učinek razreza.** Kontrolne roke z razrezom primerja z istimi rokami brez njega
   (iz preverbe 1). Razlika se zapiše v HANDOFF kot učinek razreza.

## 4. Artefakt

Velja SKUPNO §8. Na strani so trije moduli kot tri veje istega drevesa: vprašanje
telefona, naključni odgovor, ocenjevalnik na strežniku in parameter simulatorja, ki ga
spremeni. Prikazan je tudi javni žreb, ki uporabnike deli med module. Številke so
histogrami poročil, izid vrat po modulih in dobiček proti priorju in orakelju pri u50.

## 5. Prompt za začetek seje

Model orkestratorja je Opus 5.5 z naporom *high* (`/model opus`, `/effort high`).
Sejo poženi v samodejnem načinu dovoljenj (*auto mode*), da je pozivi za dovoljenja
ne ustavljajo. Prilepi:

```
Implementacijska seja 1 od 3 v repozitoriju trajguard: mehanizem ULDP sinteza (moduli
C3, C2, C1) skupaj s skupnimi predpogoji. Delaš kot orkestrator popolnoma samostojno, od
začetka do konca, brez plan mode in brez vprašanj meni; avtor je načrt vnaprej potrdil.
Preberi CLAUDE.md (že naložen), nato v celoti docs/IZVEDBA_ULDP_SKUPNO.md in
docs/IZVEDBA_ULDP_SINTEZA.md. Ta dva dokumenta imata prednost pred CLAUDE.md in skillom
orchestrate, kjer si nasprotujejo. Načrtov NACRT_ULDP_* ne beri sam; razdelke
berejo podagenti. Kode, diffov in dnevnikov pogonov ne beri; drži kontekst nizek po
SKUPNO §4. Najprej preveri dnevnik izvedbe na dnu IZVEDBA_ULDP_SINTEZA.md: če ni
prazen, nadaljuj tam, kjer se je ustavil. Pojdi skozi bloke A–E, vsak blok svoj PR, ki
ga po zeleni recenziji sam združiš v main. Na koncu pošlji risarja za artefakt (SKUPNO §8)
in mi poročaj po SKUPNO §9, v slovenščini, brez nepojasnjenih kratic.
```

## Dnevnik izvedbe

- 2026-10-10 · blok A · enota P0 · zeleno · 2 datoteki · pytest 552 passed · kode ni bilo treba spreminjati; `fit` dobi `user_id` za vsako ujeto pot; senčne prilagoditve LiRA kandidatov `user_id` ne dobijo (prenos na P5, brez oznake `test`); n danes šteje poti, ne uporabnikov
- 2026-10-10 · ODLOČITEV SEJE · P0: senčni kandidati dobijo `user_id` šele v P5, ker bi sprememba zdaj spremenila vhod napada
- 2026-10-10 · blok A · enota P1 · zeleno · 4 datoteke · pytest 560 passed · `LinkVisit` (vstop, izstop, `dwell_s`) in `TimedRoute` kot payload, `datamodel/timed_io.py` za Parquet
- 2026-10-10 · ODLOČITEV SEJE · P1: časi so sekunde Unix v UTC (float64, kot točke Geolife); zamik UTC+8 je obvezno polje `utc_offset_s` in zapis v metapodatkih Parquet, ne časovni pas Arrow
- 2026-10-10 · ODLOČITEV SEJE · P1: postanek je del obiska povezave (`dwell_s`); vrzeli med obiski so dovoljene, prekrivanja ne
- 2026-10-10 · blok A · enota P10 · zeleno · 4 datoteke · pytest 567 passed · `cleaning.split_sessions` (privzeto izklopljeno), `clean_trips()`, hash predpomnilnika ob izklopu nespremenjen (`abe8b341d8bfb1ca`)
- 2026-10-10 · ODLOČITEV SEJE · P10: razrez teče na že očiščenih točkah; »znotraj 150 m« je ≤ 150 m, »pod 300 m« je < 300 m; pragovi citirajo RANGI §8 točka 4, oblika pravila Li et al. 2008 (zaznava postankov)
- 2026-10-10 · ODLOČITEV SEJE · P10: hoja počasneje od ~0,8 m/s se šteje kot postanek; pogostost na Geolife ni izmerjena (zapis za HANDOFF)
- 2026-10-10 · blok A · enota P11 · zeleno · 3 datoteke · pytest 571 passed · zastavica `needs_user_roster`, `set_user_roster()`, `views_by_user()`; seznam `train_users` iz delitve pred ujemanjem v `meta.json` sklada; ključ predpomnilnika nespremenjen
- 2026-10-10 · ODLOČITEV SEJE · P11: uporabniki, ki jim čiščenje odstrani vse poti, nimajo oznake delitve in niso na seznamu (nespremenjeno vedenje); seznam za senčne prilagoditve in ε v `run.json` prideta v P5
- 2026-10-10 · blok A · PR #60 · recenzija: merge (ruff, mypy čisto, pytest 571 passed, `config/` nespremenjen) · manjše opombe prenesene v blok C: pri vklopljenem razrezu uporabnik izpade, če noben kos ne prestane čiščenja (odvisno od zasebnih postankov); generator z zastavico `needs_user_roster` naj javi napako, če seznama ni
- 2026-10-10 · blok A · PR #60 · združeno c636d74
- 2026-10-10 · blok B · enota P2 + P12 · zeleno · 5 datotek · pytest 582 passed · `evaluation/timed_utility.py` (9 metrik, `gain`, `utility_gain`), vklop s ključem `metrics.timed_utility` (privzeto izklopljen), brez novih stolpcev v `results.csv`
- 2026-10-10 · ODLOČITEV SEJE · P12: obdobja dneva noč 00–07, jutranja konica 07–09, sredina dneva 09–17, popoldanska konica 17–19, večer 19–24; konici pripisani letnemu poročilu Pekinškega inštituta za promet (北京交通发展年报); avtor naj vir preveri (en novičarski vir navaja večerno konico 17:30–20:00)
- 2026-10-10 · ODLOČITEV SEJE · P2: referenca so ujete poti testnih uporabnikov; interval dobička vzorči le uporabnike, raztros med semeni ostane `repeat`; dobiček še ni v `results.csv`, ker roki priorja in orakla prideta v P3
- 2026-10-10 · blok B · PR #61 · recenzija 1: fix first (manjkata JSD celic in W1 dolžine; dolžina referenc iz GPS namesto iz omrežja) · popravek zelen · 7 datotek · pytest 584 passed
- 2026-10-10 · ODLOČITEV SEJE · P2: obe strani se opišeta iz zaporedja povezav (dolžina, cone, celice iz omrežja), trajanje in odhod iz točk GPS; mreža celic je obstoječa `metrics.utility_grid` čez `map.bbox`
- 2026-10-10 · blok B · PR #61 · recenzija 2: merge (pytest 584 passed, `config/` nespremenjen) · opombi za blok C: generator se za metrike prilagodi dvakrat (ponovna uporaba prilagojenega cilja); `rnldp_eval` še računa svoje metrike (»premik« je le dodatek)
