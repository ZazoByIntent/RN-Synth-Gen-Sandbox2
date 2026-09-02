# Arhiv dokumentacije

Dokumenti, ki so svojo nalogo opravili. Ostajajo zaradi sledljivosti (zgodovina
odločitev, izmerjene vrednosti, način dela), niso pa navodila za delo in **nobena seja
jih ne bere, razen če uporabnik izrecno vpraša po zgodovini**. Živa dokumentacija je v
`docs/`, njen zemljevid s pravili »kdaj brati« je v `CLAUDE.md`.

| Datoteka | Kaj je | Zakaj v arhivu (2. september 2026) |
|---|---|---|
| `IMPLEMENTATION_PLAN.md` | Fazni načrt P0–P7 z definicijo dokončanosti na fazo (julij 2026). | Vse faze so izvedene in združene. Razdelek »horizont B« je povzet v `docs/ARCHITECTURE.md` (MVP boundaries). |
| `PROMPTS.md` | Prompti za Claude Code, en na fazo P0–P7, ter ponovljivi recenzijski prompt. | Vsi prilepljeni in izvedeni. |
| `CODEBASE_DOCUMENTATION_PROMPT.md` | Enkratni prompt, s katerim je nastal `CODEBASE_PHASE_GUIDE.md`. | Naloga opravljena; drevo datotek v njem je zastarelo. |
| `CODEBASE_PHASE_GUIDE.md` | Zgodovinski sprehod po kodi po fazah (stanje 6. julija 2026, 1100 vrstic). | Opisuje kodo pred valovi 0–2 in popravki S4: trdi, da je v orkestrator ožičena samo reidentifikacija, in ne pozna modulov `repeat.py`, `plots.py`, `results_io.py`, `results_schema.py`, `ldp.py`, `rn_ldp_synth.py`, `rnldp_eval.py`. Razlaga zasnove (»zakaj«) je v `docs/CODEBASE_STRUCTURE.md`. |
| `HANDOFF_2026-08-21.md` | Celotna predaja dela: analiza vrzeli (4. avgust 2026), recenzija, dnevnik izvedbe valov 0–2, prvi pogon S4 (§1.10), stopnji 50 in 182 (§1.11–1.12), zgodovinski prompti. | Zaprte postavke in dnevnik so zgodovina; živi deli (zapis kampanje in odprte postavke) so preneseni v skrajšani `docs/HANDOFF.md`. |
| `HANDOFF_S4_POPRAVKI.md` | Odločitve S4-1 do S4-5, razrez na PR 1–3, izid validacijskega pogona pri 20 uporabnikih (§4). | Vsi trije PR-ji izvedeni 16. avgusta 2026, validacija 17. avgusta; §4 je prenesen v `docs/HANDOFF.md` 1.2. |

Oznake S4-1 … S4-5, O1–O6, A1–A4, M1–M5 in D1–D5, ki jih koda in dokumentacija še
uporabljata, so razložene v `HANDOFF_2026-08-21.md` (razdelek 1) in na kratko v
`docs/HANDOFF.md` 1.1.
