# Shema enotne tabele rezultatov (»Rezultati_predloga«)

**Status:** dogovorjena predloga, 5. avgust 2026 — še ni implementirana. Ta dokument je
merodajni opis sheme za val 2 (O4 iz `docs/HANDOFF.md`): avtomatsko zapisovanje rezultatov
v obliko, ki gre brez ročnega prepisovanja v Excel in v poglavje 7 poročila. Ob implementaciji
se morebitna odstopanja popravijo tukaj, v istem zahtevku za združitev.

## Odločitve, na katerih shema stoji (avtor, 5. avgust 2026)

1. **Ena ploska tabela** — ena vrstica na izmerjeno vrednost metrike; metapodatki zagona se
   ponovijo v vsaki vrstici (prijazno do vrtilnih tabel v Excelu).
2. **Oznaka veje + ključni stolpci** — enoznačna oznaka veje ostane, osi vrtenja (ε,
   `unit_m`, `known_points`, `n_shadow`) pa dobijo namenske stolpce; brez JSON stolpca.
3. **Obseg** — poleg metrik napadov tudi utility metrike (kot vrstice), statistika veje
   (kot stolpci) in čas izvajanja.
4. **Vrstice po semenih** — glavna tabela vsebuje surove vrednosti enega zagona (z bootstrap
   intervalom znotraj zagona); povprečja in intervale čez semena še naprej daje ločena
   `repetitions.csv`, da se dve vrsti intervalov ne moreta pomešati.

## Datoteke

- `results/<exp_id>/results.csv` — na zagon; pri ponovitvah `results/<exp_id>/seed<N>/results.csv`.
- `reports/results_master.csv` — `trajguard report` zlepi vse zagone pod `results/` v eno
  glavno tabelo (po želji še `.parquet` zrcalo za pandas/DuckDB).
- `repetitions.csv` ostane nespremenjena (raven čez semena); val 2 ji lahko doda stolpca
  `exp_id` in `config_hash`, da je samostojno berljiva.

Vrednosti, ki niso končna števila (NaN/inf pri degeneriranih vejah), se zapišejo kot prazna
celica — enako kot danes v `metrics.csv`.

## Stolpci

Prazna celica pomeni »za to družino/vejo ni smiselno«. Imena stolpcev so angleška (kot vsa
koda), vsebina dokumentacije slovenska.

### Poreklo zagona (ponovljeno v vsaki vrstici)

| stolpec | tip | pomen | vir danes |
|---|---|---|---|
| `exp_id` | niz | ID konfiguracije (`experiment.id`) | `run.json` |
| `config_hash` | niz (16 hex) | podpis predpripravnega cevovoda (zemljevid, čiščenje, ujemanje, vzorec, delitev) | `run.json` |
| `git_commit` | niz (40 hex) | verzija kode | `run.json` |
| `seed` | celo | seme zagona (šum, znanje napadalca, bootstrap) | `run.json` |
| `split_seed` | celo | seme populacije (podvzorec uporabnikov + delitev) | `run.json` |
| `max_users` | celo/prazno | omejitev velikosti vzorca; prazno = vsi uporabniki | `run.json` |
| `created_at` | ISO-8601 UTC | časovni žig zagona | `run.json` |

Opomba: `config_hash` pokriva samo predpripravni del. Parametri napadov, ki niso izpostavljeni
v stolpcih spodaj (npr. `dwell_s` pri POI, `motion_m` pri rekonstrukciji), so enolično določeni
z `exp_id` + `git_commit` → konfiguracijska datoteka v `config/experiments/`.

### Identiteta vrstice

| stolpec | tip | pomen |
|---|---|---|
| `family` | enum | `reidentification` \| `reconstruction` \| `poi_inference` \| `membership_inference` \| `utility` |
| `scope` | enum | `raw` \| `protected` \| `synthetic` |
| `arm_id` | niz/prazno | registrsko ime mehanizma ali generatorja (`none`, `geo_indistinguishability`, `markov`, `rn_ldp_synth`); prazno pri `raw` |
| `target_ref` | niz | polna enoznačna oznaka veje, kot danes (npr. `protected:geo_indistinguishability:epsilon=1.0`) |
| `result_id` | niz | obstoječi enolični ključ rezultata (npr. `reidentification:protected:…:k5`) — vez na `metrics.csv` in `repetitions.csv` |

### Osi vrtenja (ključni parametri kot stolpci)

| stolpec | tip | pomen | družine |
|---|---|---|---|
| `epsilon` | število/prazno | ε veje: mehanizma (geo-ind) ali generatorja (`rn_ldp_synth`) | vse s parametrizirano vejo |
| `unit_m` | število/prazno | prostorska enota geo-ind (m) | geo-ind veje |
| `known_points` | celo/prazno | število točk, ki jih napadalec pozna (os »predznanje«) | reidentifikacija |
| `n_shadow` | celo/prazno | število senčnih modelov LiRA | sklepanje o članstvu |

Ti stolpci se ob implementaciji polnijo iz strukturiranih specifikacij (`AttackSpec`,
`MechanismSpec`), ne z razčlenjevanjem niza `target_ref` — nizov se ne razstavlja nazaj.

### Metrika

| stolpec | tip | pomen |
|---|---|---|
| `metric` | niz | ime metrike (`top1_acc`, `hausdorff_m`, `home_error_m`, `auc`, `tpr@fpr=0.01`, `cell_js_divergence`, …) |
| `value` | število/prazno | izmerjena vrednost; enote: deleži 0–1 (`*_acc`, `*_localised`, `auc`, `tpr@…`), metri (`*_m`), biti (`cell_js_divergence`) |
| `ci_low`, `ci_high` | število/prazno | bootstrap interval **znotraj zagona**; prazno pri metrikah na zveznih ocenah (`auc`, `tpr@…`) — tam interval čez semena daje `repetitions.csv` |
| `n_bootstrap` | celo/prazno | število bootstrap vzorcev; prazno, kjer bootstrapa ni |

### Statistika veje (ponovljena na vrsticah iste veje)

| stolpec | tip | pomen | vir danes |
|---|---|---|---|
| `n_pool` | celo | velikost napadljivega bazena: preživeli po ponovnem ujemanju (raw/protected) oz. število kandidatov (MIA) | `run.json` `arms` / novo pri MIA |
| `n_gallery_users` | celo/prazno | število uporabnikov v galeriji | `run.json` `arms` |
| `n_probes` | celo/prazno | število sond (reidentifikacija) | `run.json` `arms` |
| `n_rematch_dropped` | celo/prazno | poti, izgubljene pri ponovnem ujemanju izdane veje | `run.json` `arms` |
| `n_members`, `n_nonmembers` | celo/prazno | MIA: število članov in ne-članov — brez tega se `tpr@fpr` ne da brati (spodnja meja FPR je `1/n_nonmembers`) | novo (iz `_mia_pool`) |
| `spent_budget` | število/prazno | dejansko porabljeni ε mehanizma | `run.json` `arms` |

### Čas izvajanja

| stolpec | tip | pomen | vir danes |
|---|---|---|---|
| `attack_runtime_s` | število/prazno | čas enega zagona napada (prazno pri utility vrsticah) | `AttackResult.runtime_s` (se meri, a se še ne zapisuje ob vrstice) |
| `run_runtime_s` | število | čas celotnega zagona | `run.json` |

Pomnilniška špica (O6) v shemi še nima stolpca; ko jo val 2 začne meriti, se doda
`peak_memory_mb` in ta dokument dopolni.

## Zgleda vrstic (transponirano)

| stolpec | zgled 1: reidentifikacija | zgled 2: sklepanje o članstvu |
|---|---|---|
| `exp_id` | `geolife_geoind_reid` | `geolife_synth_mia` |
| `config_hash` | `a1b2c3d4e5f60718` | `9f8e7d6c5b4a3921` |
| `git_commit` | `9388cc8…` | `9388cc8…` |
| `seed` / `split_seed` | `3` / `42` | `3` / `42` |
| `max_users` | `50` | (prazno) |
| `family` | `reidentification` | `membership_inference` |
| `scope` / `arm_id` | `protected` / `geo_indistinguishability` | `synthetic` / `rn_ldp_synth` |
| `target_ref` | `protected:geo_indistinguishability:epsilon=1.0` | `synthetic:rn_ldp_synth:epsilon=2.0` |
| `result_id` | `reidentification:protected:…:k5` | `membership_inference:synthetic:…` |
| `epsilon` / `unit_m` | `1.0` / `100.0` | `2.0` / (prazno) |
| `known_points` / `n_shadow` | `5` / (prazno) | (prazno) / `16` |
| `metric` | `top1_acc` | `tpr@fpr=0.01` |
| `value` | `0.31` | `0.12` |
| `ci_low` / `ci_high` / `n_bootstrap` | `0.24` / `0.39` / `1000` | (prazno) / (prazno) / (prazno) |
| `n_pool` / `n_probes` | `1480` / `160` | `2100` / (prazno) |
| `n_members` / `n_nonmembers` | (prazno) | `1500` / `600` |
| `n_rematch_dropped` / `spent_budget` | `220` / `1.0` | (prazno) / (prazno) |
| `attack_runtime_s` / `run_runtime_s` | `84.2` / `1930.5` | `412.7` / `1930.5` |

## Kaj že obstaja in kaj mora val 2 dograditi

Že zapisano danes: vse poreklo zagona in statistika raw/protected vej (`run.json`), vse
vrstice metrik z intervali (`metrics.csv`), skupni čas zagona. Val 2 mora torej predvsem
**pripeti obstoječe podatke vrsticam** in dograditi troje: (1) strukturirane stolpce
`family`/`scope`/`arm_id`/osi iz specifikacij namesto nizov, (2) `attack_runtime_s` ob
vrstice (danes se izmeri in zavrže), (3) MIA števce `n_members`/`n_nonmembers` (danes se ne
zapisujeta). Zlepljenje v `reports/results_master.csv` sodi v `trajguard report`, ki že
obhodi vse zagone pod `results/`.
