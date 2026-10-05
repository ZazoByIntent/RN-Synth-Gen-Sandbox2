# Pregled rešitve trajguard — živi opis diagrama

**Stanje na dan:** 5. oktober 2026, veja `main` (merge commit `aefe2e9`, PR #54).
**Diagram:** `docs/img/trajguard_pregled.svg` (za prosojnice); generator
`scripts/gen_pregled_diagram.py`. Objavljena različica za deljenje:
<https://claude.ai/artifact/R1ToYDNfx5Xw26nf5r6BCQ>.

Ta dokument in diagram sta namenjena predstavitvi celotnega poteka rešitve (mentorici,
na predstavitvi) in se posodabljata ročno ob mejnikih. Brez izmerjenih številk — te so v
`docs/HANDOFF.md`. Kjer se koda in dokumenti razhajajo, velja koda; razhajanja so
zbrana v §7.

## Kako posodabljati

1. Spremeni stanje vozlišč v `scripts/gen_pregled_diagram.py` (vsako vozlišče ima status
   `meas` izmerjeno, `val` validirano, `prep` pripravljeno, `open` odprto; spodnji pas je
   seznam `rows`).
2. Poženi `uv run python scripts/gen_pregled_diagram.py` (SVG se zapiše v `docs/img/`);
   z `--html <mapa>` nastane še HTML-stran za objavo kot Artifact (ista povezava kot zgoraj,
   če se objavi iz seje, ki jo je ustvarila, ali z njenim URL-jem).
3. Uskladi tabele spodaj in vrstico »Stanje na dan«; dodaj vnos v §8.

![Pregled rešitve trajguard](img/trajguard_pregled.svg)

**Legenda:** zelena = izmerjeno; modra = validirano proti izvirni kodi avtorjev (in
izmerjeno); rumena = pripravljeno, a neizmerjeno; sivo črtkano = odprto / načrtovano;
puščica = tok podatkov.

## 1. Viri in priprava

| Gradnik | Registrsko ime | Vloga | Stanje |
| --- | --- | --- | --- |
| Nabor Geolife (Peking) | `geolife` | surovi `.plt` iz `data/raw/`, `native_region = beijing` | izmerjeno |
| Nabor Porto | `ldptrace_dat` | `.dat` brez zemljevida, samo celična predstavitev, samo za validacijo LDPTrace | validirano |
| Zemljevid | `osm` | OpenStreetMap → `RoadNetwork`; orkestrator zavrne pogon, če `map.region != native_region` | izmerjeno |
| Čiščenje | — | filter hitrosti in dolžine, prevzorčenje → `CleanTrajectory` | izmerjeno |
| Delitev | — | enkrat, po uporabniku, s `split_seed`, na `train / test / shadow / attack`; oznaka `split` spremlja vse izpeljanke | izmerjeno |
| Map-matching | `leuven` | → `MatchedTrajectory`; privzeta pot `segments` | izmerjeno |
| Celična veriga | `Grid.chain` | pot `cells` (`dataset.representation: cells`): brez zemljevida, dovoljen le napad na članstvo | validirano (Porto) |

## 2. Zaščita

Perturbacijski mehanizmi (`PrivacyMechanism`) vrnejo eno izdano pot na vhodno
(`ProtectedTrajectory`, vez `source_traj_id`). Sintetični generatorji
(`SyntheticGenerator`) se naučijo na delu `train` in izdajo nove poti
(`SyntheticTrajectory`, `trained_on_split`).

| Oznaka | Registrsko ime | Vrsta | Jamstvo | Mreža rok (konfiguracije) | Stanje |
| --- | --- | --- | --- | --- | --- |
| — | `none` | perturbacijski (kontrola) | brez | — | izmerjeno |
| S4 | `geo_indistinguishability` | perturbacijski, planarni Laplace | geo-ind | `epsilon` | izmerjeno (20/50/182) |
| ZM-2 | `point_ldp` | perturbacijski, naključni odziv nad celico 20×20 | LDP na točko | `epsilon` | izmerjeno (u20) |
| ZM-3 | `spatial_rounding` | naivni osnovni | brez | `cell_m` | izmerjeno (u20) |
| ZM-3 | `temporal_downsampling` | naivni osnovni | brez | `interval_s` | izmerjeno (u20) |
| ZM-3 | `gaussian_noise` | naivni osnovni | brez | `sigma_m` | izmerjeno (u20) |
| — | `markov` | sintetični, nezasebni osnovni | brez | `order` | izmerjeno (20/50/182) |
| ZM-1 | `ldptrace` | sintetični, celice 12×12 | ε-LDP na pot | `epsilon` | validirano (Porto) + izmerjeno (u20) |
| ZM-4 | `privtrace` | sintetični, prilagodljiva mreža + Markov | centralni DP | `epsilon` | validirano (Porto) + izmerjeno (u20) |
| lastni | `rn_ldp_synth` | sintetični, omejen na cestno omrežje, prototip v1 | ε-LDP na pot | `epsilon` | izmerjeno (20/50/182) |

## 3. Napadi

| Registrsko ime | Obseg (`target_scope`) | Pristop | Stanje |
| --- | --- | --- | --- |
| `reidentification` | raw, protected | napadalec pozna `known_points` ∈ {3, 5, 10} točk tarče; galerija `rematched` (izdaja znova pripeta na omrežje, privzeto) ali `release` (surove izdane točke, le `protected`); razdalja `dtw` (privzeto) ali `dtw_norm` (deljeno z dolžino poravnave) | `rematched`+`dtw` izmerjeno; `release` in `dtw_norm` pripravljena, neizmerjena |
| `membership_inference` | synthetic | LiRA-lite: 16 senčnih generatorjev, člani = `train`, nečlani = `test` | izmerjeno |
| `reconstruction` | protected (roke geo-ind) | Whittakerjev glajevalnik brez zemljevida | izmerjeno; A3 (z omrežjem) in A4 (delno predznanje) odprta |
| `poi_inference` | protected (+ synthetic, le formalno) | točke postanka → dom (noč) / služba (dan) | izmerjeno; M2 (top-k POI) odprto |

## 4. Metrike

- Reidentifikacija: `top1_acc`, `topk_acc` (k = 5), `linkage_rate`.
- Napad na članstvo: `auc`, `tpr@fpr` ∈ {0.001, 0.01, 0.1}; razpon čez semena, brez bootstrapa.
- Rekonstrukcija: `hausdorff_m`, `dtw_m`, `mean_spatial_error_m`.
- Točke interesa: `home_error_m`, `work_error_m`, `home_localised`, `work_localised`.
- Uporabnost izdaje (`UTILITY_METRICS`, surovo proti izdaji, parni bootstrap, le
  perturbacijski mehanizmi): `cell_js_divergence`, `length_dist_error` (izmerjeno);
  `duration_dist_error`, `speed_dist_error` (M3, v konfiguracijah za 50 in 182, neizmerjeno).
- Pragovi zadostne zaščite (poročilo §8.2): predlog avtorja, čaka potrditev mentorice.

## 5. Eksperimenti in stanje po stopnjah

| Scenarij (konfiguracije) | 20 | 50 | 182 | Porto |
| --- | --- | --- | --- | --- |
| S4 reidentifikacija, geo-ind (`geolife_geoind_reid*`) | izmerjeno | izmerjeno | izmerjeno (poročevalski pogon) | — |
| S4 napad na članstvo (`geolife_synth_mia*`: `markov`, `rn_ldp_synth`) | izmerjeno | izmerjeno | izmerjeno | — |
| Mehanizmi, reidentifikacija (`geolife_mech_reid_u*`) | izmerjeno (en pogon, `release` ne) | pripravljeno — naslednji korak | pripravljeno — po stopnji 50 | `privtrace_validation` |
| Mehanizmi, napad na članstvo (`geolife_mech_mia_u*`) | izmerjeno | pripravljeno — naslednji korak | pripravljeno — po stopnji 50 | `porto_cells_mia`, `ldptrace_validation` |

Vrstni red naslednjih pogonov: `geolife_mech_mia_u50` → `geolife_mech_reid_u50` →
`geolife_mech_mia_u182` → `geolife_mech_reid_u182` (HANDOFF §2, točka 6). Izhod:
`results/` → `trajguard report` → `reports/`.

## 6. Odprto in načrtovano

- A3 rekonstrukcija z omejitvijo cestnega omrežja; A4 rekonstrukcija z delnim
  predznanjem (HANDOFF §2.2).
- M2 top-k točnost točk interesa in pogled `as_poi_visits()` (potreben fixture sloj POI).
- Primerjalni zvezek `notebooks/04` nad stopnjama 50 in 182 (NACRT_MEHANIZMI §1.6).
- Pragovi §8.2 (mentorica); odločitev D5 o osnovah za članek (projekt »Izbirni predmeti«).
- Val 5 / horizont B: nalagalnika T-Drive in Porto, `fmm`, PostGIS, MLflow, difuzijski
  generatorji (HANDOFF §2.4).

## 7. Znana razhajanja med kodo in dokumenti

Trenutno nobeno. Razhajanja, ki jih je našel prvi pregled (opis rekonstrukcije in seznam
metrik uporabnosti v `ARCHITECTURE.md`, zastareli status PR-jev in datum v `HANDOFF.md`,
seznam metrik v `NACRT_MEHANIZMI.md` §1.6), so popravljena v PR #54 (merge commit
`aefe2e9`, 5. oktober 2026). Nova razhajanja se vpišejo sem, dokler niso popravljena.

## 8. Dnevnik posodobitev

- 5. oktober 2026 — prva različica po združitvi PR #51–#54 v `main`
  (stanje na dan: `main` pri `aefe2e9`).
