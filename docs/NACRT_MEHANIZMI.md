# Načrt izvedbe: širina zaščitnih mehanizmov (ZM-1 do ZM-4)

Stanje ob zapisu: 2. september 2026, veja `main` na commitu 7f0d449, kampanja S4
zaključena (`docs/HANDOFF.md` §1). Ta dokument je predaja za štiri implementacijske
seje, po eno na mehanizem in po en PR na sejo. Vsaka seja prebere **samo** §1 (skupni
recept) in svoj razdelek ZM-x; prompt za vsako sejo je v §7.

**Kaj obstaja danes.** Mehanizma `none` in `geo_indistinguishability`
(`src/trajguard/privacy/`), generatorja `markov` in `rn_ldp_synth`
(`src/trajguard/synthesis/`), LDP gradnika GRR in OUE (`privacy/ldp.py`), ki ju
uporablja samo RN-LDP-Synth. Napadi: reidentifikacija, rekonstrukcija (vezana na
geo-ind), sklepanje o domu/delu, sklepanje o članstvu (LiRA) nad generatorji.

**Izbor (avtor, 2. september 2026).** Iz nabora v zasnovi §7 in `HANDOFF.md` §2.3 ter iz
zapiskov projekta »Izbirni predmeti« (blueprint članka, 45 analiziranih del) so izbrani:

| Korak | Mehanizem | Vmesnik | Garancija | Javna koda | Obseg | Stanje |
| --- | --- | --- | --- | --- | --- | --- |
| ZM-1 | LDPTrace (Du et al., PVLDB 2023) | `SyntheticGenerator` | ε-LDP na pot | Python, Apache-2.0 | srednji | **zaključen** (2. september 2026, PR #32, združen v `main`) |
| ZM-2 | Točkovni LDP (GRR nad celicami) | `PrivacyMechanism` | ε-LDP na točko | lastna (gradnik `ldp.py`) | majhen | **zaključen** (4. september 2026, veja `claude/zm2-point-ldp`, PR na `main`) |
| ZM-3 | Naivna trojica: zaokroževanje, redčenje, Gaussov šum | `PrivacyMechanism` | brez | lastna | majhen | odprt |
| ZM-4 | PrivTrace (Wang et al., USENIX Sec 2023) | `SyntheticGenerator` | centralna DP na pot | Python, brez licence | velik | odprt |

Vrstni red je hkrati prioriteta: LDPTrace je edini celovit sintetizator pod lokalno DP in
edina primerjava, ki jo poglavje 7.3 poročila zares potrebuje; točkovni LDP je poceni
LDP protipol geo-ind; trojica da širino matrike tveganj; PrivTrace je centralno-DP
zgornja meja uporabnosti.

**Zadržek D5.** V projektu »Izbirni predmeti« je odločitev D5 (nabor baseline-ov za
članek) izrecno preložena do fiksacije arhitekture RN-LDP-Synth. Vse, kar je tu
implementirano, je zato **kandidat za baseline**, ne fiksen nabor; tako naj bo zapisano v
docstringih in v `HANDOFF.md`.

---

## 1. Skupni recept (velja za vsak korak)

### 1.1 Pravila iz `CLAUDE.md`, ki se tu najpogosteje kršijo

- Nova komponenta **podeduje ABC** (`PrivacyMechanism` ali `SyntheticGenerator`) in se
  registrira z `@register(kind, name)`; modul se uvozi v
  `src/trajguard/experiments/builtins.py`, sicer je orkestrator ne najde.
- **Vsa naključnost** iz `np.random.default_rng(seed)`; `seed` pride iz konfiguracije
  (mehanizmi: `seed=cfg.seed`; generatorji: vbrizg po podpisu konstruktorja, glej 1.3).
- **Poštena MIA:** `fit` sprejme samo pogled z `split == "train"` in glasno zavrne
  druge (vzorec v `markov.py` in `rn_ldp_synth.py`).
- Testi berejo samo `tests/fixtures/` in ne gredo na omrežje; celotna zbirka teče v
  sekundah. Fixture: `fixture_network` (session-scope `RoadNetwork` iz
  `tests/fixtures/maps/beijing_fixture`), `geolife_onroad` (8 poti po cestah).
- Definicija končanega: `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q`
  čisti, dokaz s prilepljenim izpisom. Kdor doda komponento, posodobi vrstico stanja v
  `CLAUDE.md` in `HANDOFF.md` §2.3 v istem PR.
- Ena seja = ena veja = en PR (`claude/zm1-ldptrace`, `claude/zm2-point-ldp`,
  `claude/zm3-naive-baselines`, `claude/zm4-privtrace`). Seja začne v plan mode.

### 1.2 Pogodba mehanizma (`PrivacyMechanism`), kot jo orkestrator zares uporablja

Preberi `src/trajguard/experiments/orchestrator.py`, funkciji `_protected_pool` in
`_arm_infos`, preden pišeš mehanizem. V praksi velja:

- Konstruktor dobi **samo parametre iz YAML plus `seed`** (`mech_cls(**params,
  seed=cfg.seed)`). Omrežja ali bbox danes ne dobi; ZM-2 to spremeni (glej 3.2).
- `apply(view)` mora vrniti `ProtectedTrajectory`, katerega `payload` je zaporedje
  trojic `(lat, lon, t)`. Orkestrator ga pretvori v `CleanTrajectory`
  (`_noisy_clean`, dolžina in bbox se preračunata), **ponovno ujame na cesto**
  (napadalčeva stran) in predpomni pod `data/protected/<hash>`. Število točk se sme
  spremeniti (redčenje). Če je `payload == view.as_gps()` za vse poti, orkestrator
  roko obravnava kot identiteto in ne ujema ponovno.
- Tabela rezultatov bere atributa `epsilon` in `unit_m`, če obstajata
  (`_arm_infos`). Roka brez `epsilon` se izriše v grafu `mechanisms`, graf
  `by_epsilon` jo preskoči (to je namerno).
- Napad `reconstruction` teče **samo** nad rokami `geo_indistinguishability`; druge
  roke preskoči. `poi_inference` teče nad izdanimi GPS točkami vsake roke; utility
  metriki (`cell_js_divergence`, `length_dist_error`) tečeta nad celotno izdajo, tudi
  nad potmi, ki ponovnega ujemanja ne preživijo.
- Seznam-vrednosti v `params` se **razširijo v mrežo rok** (`epsilon: [1, 2]` da dve
  roki). Zato parameter, ki je po naravi seznam (npr. bbox), ne sme iti skozi YAML.
- **Enota ε mora biti zapisana** v docstringu in v komentarju konfiguracije: geo-ind
  ima ε na 100 m na točko, točkovni LDP ε na točko nad celico, LDPTrace in RN-LDP-Synth
  ε na pot (na napravo), PrivTrace ε na pot pri zaupanja vrednem zbiralcu. Te vrednosti
  med seboj **niso primerljive**; poročilo to že pove (IZV §8, omejitve).

### 1.3 Pogodba generatorja (`SyntheticGenerator`), kot jo uporablja napad MIA

- `fit(train)` in `generate(n, seed)` sta abstraktni. Napad LiRA
  (`attacks/membership.py`, protokol `ShadowGenerator`) poleg tega zahteva
  `sequence_log_prob(edge_seq) -> float`, ki mora biti **končen za vsako zaporedje
  odsekov** (spodnja meja verjetnosti, vzorec `_PROB_FLOOR = 1e-12` v
  `rn_ldp_synth.py`). Kandidati so zaporedja celih števil v predstavitvi pogona, ki jih
  generator bere z `as_sequence()` (od PR B1 validacije LDPTrace, 3. september 2026):
  `edge_id` v načinu `segments`, indeksi celic v načinu `cells`
  (`dataset.representation`, `docs/NACRT_LDPTRACE_VALIDACIJA.md` §11). Generator, ki dela
  nad celicami mreže, zato v načinu `segments` potrebuje preslikavo odsek → celica
  (`ldptrace._build_edge_cells`), v načinu `cells` pa dobi verige celic neposredno.
- Orkestrator konstruktor kliče **po podpisu** (`_generator_ctor`): če ima parameter
  `network`, dobi `RoadNetwork`; če ima `seed`, dobi `cfg.seed + odmik` (0 tarča,
  1000 + k senčni model k). Isti razred z istimi parametri služi kot senčni model.
  V načinu `cells` (PR B2, 3. september 2026) `network` ni vbrizgan: podpis dobi `bbox`,
  `n_rows` in `n_cols` mreže iz `dataset.grid` (nasprotujoča vrednost v konfiguraciji je
  napaka), generator, ki `network` zahteva in `bbox` ne sprejme, je zavrnjen pred
  cevovodom (danes `rn_ldp_synth`). Nov generator naj po vzoru `ldptrace` sprejme
  `network=None, bbox=None` (natanko enega), če naj teče tudi nad Portom v načinu celic.
- Zaščite (`PrivacyMechanism`, koraka ZM-2 in ZM-3) tečejo samo na poti odsekov: način
  `cells` neprazen `privacy_mechanisms` zavrne pred cevovodom, ker se zaščitena izdaja
  ponovno ujema na zemljevid, ki ga tam ni.
- `spent_budget()` ni del ABC, a ga `rn_ldp_synth` ima (ε na napravo po `fit`);
  posnemaj zaradi enotnega poročanja.
- `payload` sintetične poti ni tipiziran (»odvisno od pogleda«); `markov` in
  `rn_ldp_synth` izdajata zaporedja `edge_id`. Napadi payloada ne berejo, utility nad
  sintezo v orkestratorju še ni priključena (`HANDOFF.md` §2.5); `rnldp_eval` jo meri
  na fixturih iz zaporedij odsekov.

### 1.4 Konfiguracije in stopnje

- **Konfiguracije S4 ostanejo zamrznjene** (`geolife_geoind_reid*.yaml`,
  `geolife_synth_mia*.yaml` so izmerjeni zapis stopenj). Nove roke gredo v nove
  sestrske datoteke: `config/experiments/geolife_mech_reid_u20.yaml` (perturbacije:
  sidri `none` in `geo_indistinguishability` ε = 1 plus nove roke) in
  `config/experiments/geolife_mech_mia_u20.yaml` (generatorji: sidri `markov` in
  `rn_ldp_synth` ε = 2 plus nove roke). Kopiji za u50 in 182 nastaneta šele, ko u20
  teče. Predpomnilnik surovega bazena se deli, ker so čiščenje, ujemanje in delitev
  enaki.
- **Najprej stopnja 20, potem 50, šele nato 182.** Vsaka perturbacijska roka pri 182
  pomeni ponovno ujemanje in tri klice reidentifikacije (k = 3/5/10, ~1–3,3 h na
  klic pri pragu 0,3); vsaka generatorska roka pomeni 17 prilagajanj (16 senčnih +
  tarča), pri RN-LDP-Synth ~100 s na seme pri u50.
- Za konfiguracije z realnim Geolife veljajo `docs/RUNNING.md` §6–§7.2; brez Geolife
  je dokaz test na fixturih plus dimni test iz `RUNNING.md` §5.

### 1.5 Dokumenti, ki se posodobijo v vsakem PR

`CLAUDE.md` (vrstica stanja), `docs/HANDOFF.md` §2.3 (korak zaprt, izmerjene številke
u20), `docs/RUNNING.md` (odstavek pri §7 ali §7.2), `docs/CODEBASE_STRUCTURE.md`
(seznam registriranih imen, vrstica ~156), po potrebi `docs/ARCHITECTURE.md` (tabela
napadov, meje MVP). `docs/REZULTATI_SHEMA.md` se **ne** spremeni: nove roke ne dodajajo
stolpcev (`arm_id` in `params` zadostujeta).

---

## 2. ZM-1 LDPTrace kot generator (`synthesis/ldptrace.py`, registrsko ime `ldptrace`) — ZAKLJUČEN

**Izvedeno 2. septembra 2026** (PR #32, združen v `main` 2. septembra 2026). Dejanske
odločitve, kjer je načrt spodaj puščal izbiro ali kjer se je izvedba od njega razlikovala:

- D-1.5: poročilo konca nosi **pravo zadnjo celico** (članek), tudi ko so poročila
  prehodov odrezana pri L_k; odstopanje od javne kode je zapisano v docstringu modula.
- L_k se računa nad **neodrezano** oceno OUE natanko po pravilu izvirne kode (negativne
  vrednosti ostanejo v vsoti in v tekoči vsoti; rezerva L_k = N²). Zato je
  `oue_estimate` v `privacy/ldp.py` dobil ključno besedo `clip` (`clip=False` vrne
  surovo nepristransko oceno; privzeto vedenje je nespremenjeno).
- Statistika za MIA je **brez člena dolžine** in brez uteži α/β (D-1.3).
- Nepristranska ocena OUE deli z **dejanskim številom seštetih poročil** na domeno (pri
  prehodih skupno število poročil prehodov, ne število poti). To **ni odstopanje**:
  preverjeno 2. septembra 2026 v izvirni kodi (`ldp.py`, `OUEServer.aggregate` poveča
  števec `n` ob vsakem poročilu), ki dela enako.
- Pri stopnji 20 je konfiguriran **samo** 12 × 12 (D-1.4) z ε ∈ {0,5, 2, 8}; roka
  6 × 6 ni dodana.
- Test uporabnosti pri »absurdno velikem ε« uporablja ε = 600, ne 80: ε se deli na
  L_k + 1 ≈ 12–20 poročil, zato pri ε = 80 na poročilo ostane le ≈ 5 in šum OUE nad
  100–800 položaji je še viden; nad ≈ 709 `exp` prekorači obseg.
- Izmerjene vrstice pri stopnji 20 (tri semena): `docs/HANDOFF.md` §2.3. Dekodiranje
  celic v odseke in roka `ldptrace` v `experiments/rnldp_eval.py` ostajata odprta
  (ločen PR, glej D-1.2). Validacija porta proti izvirni kodi (metrike članka, način
  surovih koordinat, Porto) ima lasten načrt: `docs/NACRT_LDPTRACE_VALIDACIJA.md`.
- **Validacija proti izvirni kodi je zaključena (4. september 2026, PR C = PR #36;
  PR #33–#36 so združeni v `main` 4. septembra 2026):** port in izvirnik (klon
  `2d30e41`, popravek samo za seme) sta bila pognana nad istimi 367.008 potmi Porta na
  mreži 6 × 6 pri ε ∈ {0,5, 1, 1,5} s petimi semeni; tabela devetih metrik in branje sta
  v `docs/HANDOFF.md` §2.3, dejanske odločitve v `docs/NACRT_LDPTRACE_VALIDACIJA.md`
  §12.5. LDPTrace ostaja kandidat za baseline (odločitev D5 je še odprta).

### 2.1 Kaj mehanizem počne (Du et al., PVLDB 2023; koda `zealscott/LDPTrace`)

Vsak uporabnik ima eno pot. Prostor je enakomerna mreža N × N celic. Uporabnik na
napravi pošlje tri vrste poročil, vsa z mehanizmom OUE (Optimized Unary Encoding, že v
`privacy/ldp.py`):

1. **Dolžina poti** v celicah: en OUE nad domeno N² (indeks = dolžina − 1, daljše se
   odrežejo na N²), proračun ε/10.
2. **Zgornja meja dolžine** L_k = 0,9-kvantil **zašumljene** ocene porazdelitve dolžin
   (iz koraka 1, ne iz surovih podatkov). To je drugi krog zbiranja.
3. **Prehodi**: pot se odreže na `length = min(len, L_k)`; uporabnik pošlje eno poročilo
   začetne celice (domena N²), `length − 1` poročil notranjih prehodov (domena 8·N²,
   indeks = celica · 8 + smer proti enemu od osmih sosedov) in eno poročilo končne
   celice (domena N²). Vsako poročilo dobi proračun (9ε/10)/(L_k + 1). Skupaj torej
   največ ε na pot (zaporedna kompozicija).

Strežnik nepristransko oceni frekvence (OUE estimator, `oue_estimate`), ocene prehodov
≤ 0 zavrže, negativne začetke/konce/dolžine odreže na 0, in vrstice normalizira (+1e-8)
nad osmimi sosedi v mreži plus »navideznim koncem«. **Sinteza** (Algoritem 1): začetna
celica iz ocene začetkov; dolžina L iz zašumljenega histograma; nato L − 1 korakov, kjer
je utež navideznega konca pomnožena z `min(1.0, 0.3 + 0.2·(l − 1))` (l = trenutno število
celic); hoja se ustavi ob navideznem koncu, ob doseženi L ali ob slepi ulici (vsota uteži
< 1e-5). Koda generira toliko poti, kot jih je v vhodu.

Privzete vrednosti kode: `epsilon 1.0`, `grid_num 6`, kvantil `0.9`, α = 0,3, β = 0,2,
seme 2022. Formula za N iz članka (§5.9, λ = 2,5) je v kodi napisana, a **nikoli
klicana**. Meje mreže koda vzame iz podatkov (ni zasebno); mi jih vzamemo iz javnega
zemljevida.

### 2.2 Preslikava v trajguard (odločitve; »priporočeno« pomeni predlog, ki ga seja potrdi ali spremeni)

- **D-1.1 Vhod in domena.** `fit` bere `view.as_segments()` (zaporedje `edge_id`), ne
  surovih GPS točk. Iz javnega omrežja se enkrat zgradi preslikava odsek → veriga celic:
  celici vozlišč u in v, vmes greedy 8-sosedska interpolacija kot v
  `GridMap.find_shortest_path` (vsak korak premakne vrstico in/ali stolpec proti cilju,
  diagonala ima prednost), zaporedni dvojniki se strnejo. Tako `fit` in
  `sequence_log_prob` gledata isto domeno in je primerjava z `rn_ldp_synth` (ki dela nad
  conami iz istih odsekov) poštena. Mreža je v projiciranih metrih nad bbox vozlišč
  omrežja (vzorec `_cell` v `rn_ldp_synth.py`). Alternativa (celice iz surovih GPS
  točk) je zvestejša izvirniku, a bi MIA ocenjevala drugo domeno kot `fit`;
  priporočeno: odseki.
- **D-1.2 Izhod.** `payload` = zaporedje indeksov celic (kot izvirnik), ne dekodirana
  zaporedja odsekov. Napadi payloada ne berejo; utility nad sintezo še ni priključena.
  Če bo poglavje 7.3 zahtevalo primerjavo utility na ravni odsekov, se dekodiranje doda
  kasneje s ponovno uporabo `_decode` iz `rn_ldp_synth.py` (ločen PR).
- **D-1.3 Statistika za MIA.** `sequence_log_prob(edge_seq)` = log P(začetek) +
  Σ log P(prehod) + log P(konec | zadnja celica) po agregiranem modelu **brez** α/β
  uteži (ki so pravilo generiranja, ne verjetnostni model). Prehodi z oceno 0 ali med
  nesosednjimi celicami dobijo spodnjo mejo 1e-12. Neznan `edge_id` sproži `ValueError`
  (kot pri `rn_ldp_synth`).
- **D-1.4 Mreža.** Privzeto `n_rows = n_cols = 12` zaradi primerljivosti z
  `rn_ldp_synth` (12 × 12 con); domena prehodov je potem 8 · 144 = 1152 bitov. Izvirnik
  ima 6 × 6 na svojih zbirkah; formula iz članka ostane neimplementirana (v izvirniku
  je mrtva koda). Odprto za avtorja: ali pri stopnji 182 preizkusiti tudi 6 × 6 ali 20 × 20.
- **D-1.5 Poročilo konca.** Članek poroča pravo zadnjo celico; javna koda pri odrezanih
  poteh poroča celico na mestu odreza. Priporočeno: **prava zadnja celica** (članek),
  proračun je enak; odstopanje od kode zapisano v docstringu.
- **D-1.6 Delitev proračuna.** Parameter `length_share = 0.1` (delež za dolžino),
  preostanek na `L_k + 1` poročil; α in β kot parametra `alpha = 0.3`, `beta = 0.2`;
  kvantil `quantile = 0.9`. `spent_budget()` vrne ε po `fit`, `None` pred njim.
- **D-1.7 Konstruktor.** `LDPTraceGenerator(network: RoadNetwork, epsilon: float = 1.0,
  n_rows: int = 12, n_cols: int = 12, quantile: float = 0.9, length_share: float = 0.1,
  alpha: float = 0.3, beta: float = 0.2, seed: int = 0)`; validacija: ε > 0,
  0 < quantile ≤ 1, 0 < length_share < 1, mreža ≥ 2 × 2. Podpis sam poskrbi za vbrizg
  `network` in `seed` (1.3).

### 2.3 Datoteke

Novo: `src/trajguard/synthesis/ldptrace.py`, `tests/test_ldptrace.py`,
`config/experiments/geolife_mech_mia_u20.yaml`. Spremenjeno:
`src/trajguard/experiments/builtins.py` (uvoz), dokumenti iz 1.5. Orkestrator se **ne**
spremeni.

### 2.4 Testi (`tests/test_ldptrace.py`, po vzorcu `tests/test_rn_ldp_synth.py`)

Verige celic so 8-povezane in brez zaporednih dvojnikov; `fit` je determinističen v
semenu konstruktorja, `generate` v svojem semenu; `fit` zavrne ne-train pogled in prazno
pot; `generate` pred `fit` sproži napako; `spent_budget` je `None` pred in ε po `fit`;
pri absurdno velikem ε (npr. 80) ocena začetkov in histogram dolžin sledita vhodu (kot
`test_high_epsilon_preserves_start_zones_and_lengths`); `sequence_log_prob` je končen
za poljubno zaporedje in koherentno pot oceni višje kot naključno; neznan odsek sproži
napako; ime v registru; generirane poti so 8-povezane in dolge ≤ N²; validacija
konstruktorja.

### 2.5 Dokaz

```sh
uv run ruff check . && uv run mypy src && uv run pytest -q
uv run trajguard repeat config/experiments/geolife_mech_mia_u20.yaml --seeds 1 2 3   # realni Geolife + maps/beijing
```

Pričakovano: vrstice `membership_inference:synthetic:ldptrace:epsilon=…` z `auc` in
`tpr@fpr=0.1` (0.001 in 0.01 pri u20 dajo NaN in opozorilo S4-2). Beri proti stropu
`markov` (AUC ~1,0 pri u20) in proti `rn_ldp_synth` pri istem ε. Neobvezno: dodaj roko
`ldptrace` v `experiments/rnldp_eval.py` (MIA je neposredno uporabna; za cell JSD
primerjaj verige celic realnih poti s payloadom).

### 2.6 Tveganja

Pri majhnem n (u20: ~30 train poti) so OUE ocene pri ε ≤ 1 skoraj enakomerne; to je
lastnost poštene LDP, ne napaka (enako opažanje v `RN_LDP_SYNTH_DESIGN.md` §8). Če vse
ocene prehodov iz neke celice padejo pod 0, hoja tam obstane (slepa ulica), zato test
pokriva kratke izhode. ε-mreža {0,5, 2, 8} je vzeta od `rn_ldp_synth` zaradi
primerljivosti; izvirnik uporablja {0,5, 1, 1,5}.

---

## 3. ZM-2 Točkovni LDP (`privacy/point_ldp.py`, registrsko ime `point_ldp`) — ZAKLJUČEN

**Izvedeno 4. septembra 2026** (veja `claude/zm2-point-ldp` iz `main` po združitvi PR
#33–#37; PR na `main`). Dejanske odločitve, kjer je načrt spodaj puščal izbiro ali kjer se
je izvedba od njega razlikovala:

- D-2.3: mreža **20 × 20** (k = 400) in ε ∈ {4, 6, 8}, kot priporočeno. Razlogi: ista
  mreža kot `utility_grid`, zato `cell_js_divergence` meri natanko škodo GRR nad isto
  mrežo; k = 400 drži ε v berljivem območju (p prave celice 0,12 / 0,50 / 0,88); finejša
  mreža reidentifikaciji ne pomaga, ker ponovno ujemanje pri celicah ~1,5 km odvrže vse
  poti (geo-ind pri ε = 1, premik 200 m, jih pri u20 že odvrže vse). Mreža ostaja
  parameter YAML (`n_rows`, `n_cols` kot skalarja), roka 50 × 50 je ena vrstica.
- Obratna preslikava indeks celice → meje celice je metoda `Grid.cell_bounds` v
  `representation/views.py` (ob `cell_of` in `chain`), ne zasebna funkcija mehanizma;
  ZM-3 (zaokroževanje na središče celice) jo lahko uporabi.
- `bbox` pod `params` mehanizma je napaka konfiguracije z jasnim sporočilom (orkestrator
  ga vbrizga iz `map.bbox`), po vzoru zavrnitve nasprotujočih vrednosti v `_generator_ctor`.
  Vbrizg je edina sprememba orkestratorja (zanka `mech_plans`, ~10 vrstic), ključ
  predpomnilnika `_protected_hash` že vsebuje bbox zemljevida prek `_version_hash`.
- Vrstni red naključnosti v `apply`: najprej vsi žrebi GRR (zanka z `grr_perturb`), nato
  tresenje (vektorizirano), zato `jitter=True` in `jitter=False` z istim semenom poročata
  iste celice; test »tresena točka leži v poročani celici« to uporabi.
- Izdane koordinate so pripete na bbox (zaščita pred prekoračitvijo zaradi zaokroževanja
  na zunanjem robu mreže); `params_hash` vključuje bbox; mreža 1 × 1 je zavrnjena (GRR
  potrebuje k ≥ 2).
- Izmerjene vrstice pri stopnji 20 (seme 42, pogon 864 s = 14,4 min, torej nad pragom
  10 min na seme in brez ponovitev `repeat`): `docs/HANDOFF.md` §2.3. Napoved iz D-2.3 se
  je potrdila: ponovno ujemanje odvrže vseh 238 sledi pri vseh treh ε (reidentifikacija
  0 nad praznim bazenom), medtem ko `cell_js_divergence` sledi deležu pravih celic (0,42 /
  0,18 / 0,03 pri ε = 4 / 6 / 8) in sklepanje o domu/delu ne umesti nikogar. Točkovni
  LDP ostaja kandidat za baseline (odločitev D5 je odprta).

### 3.1 Kaj mehanizem počne

Vsaka GPS točka se preslika v celico mreže nad bbox zemljevida (`Grid` iz
`representation/views.py`, isti razred kot utility mreža), celica se zamenja z
randomiziranim odgovorom GRR (`grr_perturb`, že v `ldp.py`): prava celica ostane z
verjetnostjo p = e^ε/(e^ε + k − 1), sicer enakomerno druga. Izdana točka je središče
poročane celice, čas ostane. Garancija: ε-LDP **na točko**; `spent_budget` = ε · število
točk (naivna zaporedna kompozicija, enako kot geo-ind). To je LDP protipol geo-ind
(metrična DP na točko) z enako naivno računico proračuna.

### 3.2 Odločitve

- **D-2.1 Od kod bbox.** Konstruktor mehanizma danes dobi samo parametre in `seed`;
  bbox kot seznam ne sme v YAML (razširil bi se v štiri roke, 1.2). Priporočeno: v
  zanki, ki instancira mehanizme (`orchestrator.py`, blok `mech_plans`), vbrizgaj
  `bbox=<bbox zemljevida iz RunConfig>` po podpisu konstruktorja, po vzorcu
  `_generator_ctor`. To je edina sprememba orkestratorja v celotnem načrtu; test
  `test_orchestrator.py` dobi primer, ki dokaže vbrizg. Alternativa (vbrizg `network`)
  je težja, ker zahteva projekcijo; ni potrebna.
- **D-2.2 Tresenje znotraj celice.** Priporočeno `jitter = True`: izdana točka je
  enakomerno naključna točka v poročani celici, ne središče. Razlog: zaporedne točke v
  isti celici bi sicer imele identične koordinate, kar ujemalniku da odseke ničelne
  dolžine. Ker je tresenje naknadna obdelava poročila z neodvisno naključnostjo,
  garancija ostane ε-LDP.
- **D-2.3 Mreža in ε.** Privzeto `n_rows = n_cols = 20` (kot `utility_grid`), kar je
  nad Pekingom celica ~1,5 km in k = 400. Verjetnost prave celice: ε = 4 → 0,12; ε = 6 →
  0,50; ε = 8 → 0,88; pri ε ≤ 2 je izdaja praktično enakomeren šum (»zaščita z uničenjem
  izdaje«, kot geo-ind pri ε = 0,1). Priporočena mreža za u20: `epsilon: [4.0, 6.0, 8.0]`.
  Odprto za avtorja: finejša mreža (npr. 50 × 50, k = 2500) zahteva še večji ε.
- **D-2.4 Konstruktor.** `PointLDP(epsilon: float, bbox: tuple[float, float, float,
  float], n_rows: int = 20, n_cols: int = 20, jitter: bool = True, seed: int = 0)`;
  `guarantee = "ldp"`, atribut `epsilon` (za tabelo rezultatov), brez `unit_m`.

### 3.3 Datoteke

Novo: `src/trajguard/privacy/point_ldp.py`, `tests/test_point_ldp.py`,
`config/experiments/geolife_mech_reid_u20.yaml`. Spremenjeno: `orchestrator.py`
(vbrizg bbox, ~5 vrstic), `tests/test_orchestrator.py` (en test),
`builtins.py`, dokumenti iz 1.5.

### 3.4 Testi

Determinizem v semenu; empirični delež točk, ki ostanejo v pravi celici, se pri ε = 6 in
n = 2000 točkah ujema s p = e^6/(e^6 + 399) ≈ 0,50 (toleranca ± 0,05); višji ε ohrani
več točk; časi in metapodatki ohranjeni, `guarantee == "ldp"`; `spent_budget` raste za
ε · n; vse izdane točke ležijo v bbox in (pri `jitter=True`) znotraj poročane celice;
neveljavni parametri (ε ≤ 0, mreža < 1, degeneriran bbox) so zavrnjeni; ime v registru;
orkestrator vbrizga bbox (end-to-end na fixturih z roko `point_ldp`).

### 3.5 Dokaz

```sh
uv run ruff check . && uv run mypy src && uv run pytest -q
uv run trajguard run config/experiments/geolife_mech_reid_u20.yaml     # realni Geolife
```

Pričakovano: reidentifikacija in `poi_inference` za roke `point_ldp:epsilon=…`; visok
`n_rematch_dropped` pri ε = 4 je pričakovan in ga zapiši v `run.json`/HANDOFF.
Rekonstrukcija roke preskoči (po zasnovi).

---

## 4. ZM-3 Naivna trojica (`privacy/naive.py`, imena `spatial_rounding`, `temporal_downsampling`, `gaussian_noise`)

### 4.1 Kaj mehanizmi počnejo

Trije mehanizmi **brez formalne garancije** (`guarantee = "none"`, `spent_budget()`
vrne `None`), ki predstavljajo, kar praksa najpogosteje počne:

- `SpatialRounding(cell_m)`: koordinate se zaokrožijo na središče kvadratne celice
  velikosti `cell_m` metrov na globalni mreži (širina na večkratnike `cell_m/111320°`,
  dolžina na večkratnike `cell_m/(111320·cos φ)°` pri zaokroženi širini). Determinističen,
  brez naključnosti. Mreža: `cell_m: [100, 500, 2000]`.
- `TemporalDownsampling(interval_s)`: obdrži prvo točko, nato vsako, ki je od zadnje
  obdržane oddaljena ≥ `interval_s`, in vedno zadnjo točko. Čiščenje že vzorči na 5 s.
  Mreža: `interval_s: [30, 120, 600]`.
- `GaussianNoise(sigma_m, seed)`: neodvisen Gaussov šum N(0, σ²) po obeh oseh v metrih
  (pretvorba v stopinje kot v `geoind.py`). Mreža: `sigma_m: [50, 200, 1000]`; 200 m je
  približno povprečni odmik geo-ind pri ε = 1.

### 4.2 Odločitve

- **D-3.1 En modul, trije razredi.** Recept v `CODEBASE_STRUCTURE.md` §9 govori o eni
  datoteki na komponento; tu si trije 40-vrstični razredi delijo pretvorbo metri ↔
  stopinje, zato en modul `privacy/naive.py` (pretvorbo lahko izlušči v `geometry.py`,
  če je tam še ni). Sprejemljivo je tudi tri datoteke; odloči seja.
- **D-3.2 Kratke izdaje.** Redčenje lahko pot skrajša pod `known_points` (3/5/10)
  reidentifikacijskega napadalca in pod `min_points` čiščenja. Preveri v
  `attacks/reidentification.py` (`_evenly_spaced`), kako se obnaša pri manj točkah, kot
  jih pozna napadalec, in dodaj test s kratko potjo. Ponovno ujemanje kratke poti bo
  pogosto padlo; to je izmerjen učinek, ne napaka.
- **D-3.3 Dvojniki.** Zaokroževanje da zaporedne identične točke; obdrži jih (zvesta
  izdaja) in s testom na fixturih dokaži, da `match_many` tega prenese. Če ujemalnik
  odpove, strni zaporedne dvojnike in to zapiši.
- **D-3.4 Brez atributa `epsilon`.** Roke se pojavijo v grafu `mechanisms` in v matriki
  tveganj, graf `by_epsilon` jih preskoči (1.2). Parametri v `params` se izpišejo kot
  `cell_m=500.0` itd.; `_parse_target_ref` v `report.py` to že prenese.

### 4.3 Datoteke

Novo: `src/trajguard/privacy/naive.py`, `tests/test_naive.py`. Spremenjeno:
`builtins.py`, `config/experiments/geolife_mech_reid_u20.yaml` (roke se dodajo k
ZM-2 konfiguraciji), dokumenti iz 1.5. Orkestrator se ne spremeni.

### 4.4 Testi

Zaokroževanje: izdane točke ležijo na mreži, idempotentno (dvakratna uporaba = enkratna),
največji premik ≤ `cell_m·√2/2`. Redčenje: prva in zadnja točka ohranjeni, razmiki ≥
`interval_s`, kratka pot (< 3 točke) ne pade. Gauss: determinizem v semenu, empirična
RMS razdalja ≈ σ·√2 pri n = 2000 (toleranca 10 %). Vsi: časi in metapodatki ohranjeni,
`guarantee == "none"`, `spent_budget() is None`, neveljavni parametri zavrnjeni, imena v
registru. En end-to-end test orkestratorja s `temporal_downsampling` (spremenjeno
število točk skozi ponovno ujemanje in predpomnilnik).

### 4.5 Dokaz

Kot ZM-2 (isti konfiguracijski file, razširjen). Pri 182 to pomeni **devet** novih
perturbacijskih rok; pred tem avtor odloči, katere vrednosti gredo naprej od u50.

---

## 5. ZM-4 PrivTrace kot generator (`synthesis/privtrace.py`, registrsko ime `privtrace`)

### 5.1 Kaj mehanizem počne (Wang et al., USENIX Security 2023; koda `DpTrace/PrivTrace`)

**Model zaupanja je drugačen:** zbiralec je zaupanja vreden in vidi vse poti; DP velja na
ravni ene poti (soseda zbirka se razlikuje za eno pot; uporabnik z m potmi ni pokrit).
Zato je PrivTrace v poročilu **zgornja meja uporabnosti**, ne enakovreden tekmec; poleg
nominalno enakega ε mora stati stavek o asimetriji zaupanja in prevod na raven
uporabnika (m·ε). Koraki:

1. **Dvoplastna mreža.** Prva plast K × K, K = √(|D|/c), c je konstanta na zbirko
   (Geolife: c = 500 → K = 6 pri 17 621 poteh). Za vsako celico se zbere dolžinsko
   normirano število obiskov (vsaka pot prispeva skupaj 1, občutljivost 1) z Laplaceovim
   šumom lestvice 1/ε₁. Celica z gostoto d_i se razdeli na κ_i × κ_i podcelic,
   κ_i = √(d_i · K · pop / 2·10⁷) (pop = prebivalstvo regije; dodatek E članka piše
   delitelj 20 000, članek ni konsistenten). Stanja Markovovega modela so nerazdeljene
   celice prve plasti plus vse podcelice, plus navidezni začetek in konec.
2. **Markovova modela.** Vsaka pot prispeva dolžinsko normirane števce vseh dvojic
   (prvi red) in trojic (drugi red) stanj; Laplace(1/ε₂) na vsak števec prvega reda,
   Laplace(1/ε₃) na vsak števec drugega reda. Negativne vrednosti popravi **NormCut**
   (Algoritem 2: negativne postavi na 0, njihovo maso odšteje najmanjšim pozitivnim,
   ponavlja do nenegativnosti).
3. **Adaptivna izbira reda** pri vsakem koraku iz zašumljenih števcev prvega reda
   trenutnega stanja: če je vsota izhodnih števcev < θ₁ = (√2/ε₂)·m (m = število
   stanj) **ali** razmerje največjega proti drugemu največjemu ≥ θ₂ = 5, uporabi prvi
   red, sicer drugi.
4. **Porazdelitev poti (začetek–konec)** iz vrstice navideznega začetka b_i in stolpca
   navideznega konca q_j z omejenimi najmanjšimi kvadrati nad t_ij (uteži 1/l_ij, l_ij
   najkrajša pot med celicama); porazdelitev dolžin se **ne** ocenjuje posebej.
5. **Sinteza** (Algoritem 1): vzorči (začetek, konec), **konec zavrže**, hodi po
   adaptivnem modelu do navideznega konca, brez omejitve dolžine; na koncu ena
   enakomerna točka na celico.

Proračun: ε₁ = 0,2ε, ε₂ = 0,4ε, ε₃ = 0,4ε; članek pregleduje ε od 0,2 do 2,0. Metrike:
JSD dolžin in premerov (50 razredov), gostota (500 naključnih krogov z naključnimi
polmeri, relativna napaka), vzorci prehodov nad 20 × 20 mrežo (dolžine 2–5, top 200).
Članek je v kodi AdaTrace našel korake brez DP (izbor porazdelitve dolžin in
mediana/povprečje iz surovih podatkov brez šuma) in jih popravil.

### 5.2 Odločitve

- **D-4.1 Mreža.** Formula za K in κ sloni na konstantah na zbirko in na prebivalstvu,
  kar pri našem bazenu (1 770 ujetih poti pri 182) da K ≈ 2. Priporočeno: parametra
  `first_level_k` (privzeto 6, kot članek za Geolife) in `population` (Peking ~21,5 M) z
  izvorno formulo κ (delitelj 2·10⁷), plus `max_sub_k` (varovalka). Odprto za avtorja:
  ali namesto formule uporabiti preprost `split_threshold`; oboje mora biti zapisano
  kot odstopanje od članka, če se izbere.
- **D-4.2 Brez reševalca najmanjših kvadratov.** Ker sinteza konec zavrže, porazdelitev
  parov vpliva samo na porazdelitev začetkov. Priporočeno: v v1 vzorčiti začetek
  neposredno iz zašumljene vrstice navideznega začetka (po NormCut) in korak 4
  izpustiti; to je zapisano odstopanje, ki prihrani novo odvisnost (`scipy` ni v
  `pyproject.toml`; dodajanje zahteva utemeljitev v PR).
- **D-4.3 Zgornja meja dolžine.** Članek je nima; dodaj `max_len` (privzeto N² stanj ali
  parameter), da hoja zagotovo konča; zapiši kot odstopanje.
- **D-4.4 Vhod in izhod.** Kot ZM-1: `fit` iz `as_segments()`, celice iz vozlišč
  odsekov, brez interpolacije (PrivTrace prehodov ne omejuje na sosede), zaporedni
  dvojniki strnjeni; `payload` = zaporedje id-jev listnih celic. `sequence_log_prob` po
  istem adaptivnem modelu s spodnjo mejo 1e-12.
- **D-4.5 Konstruktor.** `PrivTraceGenerator(network: RoadNetwork, epsilon: float =
  1.0, first_level_k: int = 6, population: float = 2.15e7, budget_split: tuple[float,
  float, float] = (0.2, 0.4, 0.4), theta2: float = 5.0, max_len: int = 200, seed: int =
  0)`; `spent_budget()` vrne ε (na pot, centralno) po `fit`. Docstring izrecno pove
  »trusted curator, trajectory-level DP; baseline candidate (D5 open)«.
- **Opomba po PR B2 (3. september 2026).** Orkestrator ima tudi način celic
  (`dataset.representation: cells`, `docs/NACRT_LDPTRACE_VALIDACIJA.md` §11), v katerem
  generator dobi mrežo (`bbox`, `n_rows`, `n_cols`) namesto omrežja in bere verige celic
  prek `as_sequence()` (§1.3). Konstruktor iz D-4.5 samo z `network` bi bil tam zavrnjen;
  če naj PrivTrace teče tudi nad Portom (primerjava z LDPTrace na isti mreži 6 × 6, isti
  vhod kot v `config/experiments/porto_cells_mia.yaml`), naj po vzoru `ldptrace` sprejme
  `network=None, bbox=None` (natanko enega) in v načinu `bbox` vzame verige kot vhod.
  Odločitev za sejo ZM-4; D-4.4 (celice iz vozlišč odsekov) velja za način `network`.

### 5.3 Datoteke

Novo: `src/trajguard/synthesis/privtrace.py` (verjetno 400+ vrstic; če preseže ~500,
razdeli mrežo v `synthesis/adaptive_grid.py`), `tests/test_privtrace.py`.
Spremenjeno: `builtins.py`, `config/experiments/geolife_mech_mia_u20.yaml` (roka
`privtrace`, ε {0,5, 2, 8} kot ostali generatorji; komentar o modelu zaupanja),
dokumenti iz 1.5.

### 5.4 Testi

NormCut: izhod nenegativen, vsota ohranjena, idempotenten na nenegativnem vhodu. Mreža:
celice z visoko gostoto se razdelijo, nizke ne; id-ji listov stabilni. Adaptivna izbira:
enotski test obeh vej pravila. Determinizem `fit`/`generate`; `fit` zavrne ne-train;
`spent_budget`; pri ε = 80 struktura prehodov sledi vhodu; `sequence_log_prob` končen in
koherentno > naključno; hoja konča ≤ `max_len`; validacija konstruktorja; ime v registru.

### 5.5 Dokaz

Kot ZM-1 z roko `privtrace`. Pričakovano: pri enakem nominalnem ε nižja MIA AUC in
boljša utility kot LDP roke (zaupanja vreden zbiralec); to je pričakovana asimetrija,
ne dokaz premoči, in se tako tudi zapiše.

---

## 6. Kar tokrat ni izbrano in zakaj

- **GEM / geo-graph-indistinguishability** (Takagi 2020, koda `tkgsn/GG-I`): principielna
  »segmentna perturbacija« nad cestnim grafom (eksponentni mehanizem nad vozlišči z
  razdaljo po grafu). Smiselna kasnejša ZM-5, ko bo vbrizg iz ZM-2 razširjen na
  `network`; pri 35 764 vozliščih zahteva predizračun razdalj. V zapiskih članka je le za
  citiranje in razmejitev.
- **NGRAM** (Cunningham 2021): potrebuje hierarhijo POI kategorij in ILP reševalec, javne
  kode ni, metrike niso primerljive s sintezo.
- **k-anonimnost (Never Walk Alone)**: deluje nad množico poti, zato bi potrebovala
  `fit` korak v `PrivacyMechanism` (sprememba ABC); javne kode ni; zasnova §10 jo
  izrecno odlaga.
- **SquareWave**: mehanizem za numerične porazdelitve, brez naravnega mesta v tem
  benchmarku; javne kode nisem našel.
- **MTNet, STEGA, ControlTraj, Diff-RNTraj**: globoki generatorji (PyTorch, GPU), po
  `ARCHITECTURE.md` horizont B.

---

## 7. Prompti za seje (kopiraj v celoti v novo sejo)

### 7.1 ZM-1 LDPTrace

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_MEHANIZMI.md SAMO §1 (skupni recept) in §2 (ZM-1 LDPTrace); arhiva arhiv/ ne
odpiraj. Kot vzorec preberi src/trajguard/synthesis/rn_ldp_synth.py (grid, zone_sequence,
fit, sequence_log_prob), src/trajguard/privacy/ldp.py (oue_perturb, oue_estimate),
protokol ShadowGenerator v src/trajguard/attacks/membership.py, funkcijo _generator_ctor v
src/trajguard/experiments/orchestrator.py in tests/test_rn_ldp_synth.py. Po potrebi za
podrobnost izvirnika uporabi podagenta, ki prebere javno kodo
https://github.com/zealscott/LDPTrace (LDPTrace/code/main.py, grid.py, trajectory.py,
ldp.py); glavni kontekst naj ostane čist.

Naloga: implementiraj LDPTrace kot SyntheticGenerator z registrskim imenom "ldptrace" v
src/trajguard/synthesis/ldptrace.py po odločitvah D-1.1 do D-1.7 iz načrta (vhod iz
as_segments z 8-sosedsko interpolacijo, OUE poročila dolžina/začetek/prehodi/konec z
delitvijo ε/10 in 9ε/10 nad L_k+1 poročil, L_k iz zašumljene ocene, sinteza po Algoritmu
1 z utežjo konca min(1, 0.3 + 0.2·(l−1)), payload = celice, sequence_log_prob brez α/β,
spodnja meja 1e-12). Kjer bi od načrta odstopil, to najprej predlagaj.

Postopek: začni v plan mode in počakaj na mojo potrditev. Nato ustvari vejo
claude/zm1-ldptrace, napiši modul, uvoz v experiments/builtins.py, tests/test_ldptrace.py
(seznam testov je v načrtu §2.4) in novo konfiguracijo
config/experiments/geolife_mech_mia_u20.yaml (kopija geolife_synth_mia_u20.yaml s
sidrnima rokama markov in rn_ldp_synth ε=2 ter roko ldptrace ε ∈ {0.5, 2.0, 8.0};
konfiguracije S4 ostanejo nespremenjene). Definicija končanega: uv run ruff check ., uv run
mypy src, uv run pytest -q čisti, izpis prilepljen. Če imam lokalno Geolife in
maps/beijing, poženi še uv run trajguard run config/experiments/geolife_mech_mia_u20.yaml
in izmerjene vrstice zapiši v docs/HANDOFF.md §2.3. V istem PR posodobi vrstico stanja v
CLAUDE.md, docs/RUNNING.md §7.2, docs/CODEBASE_STRUCTURE.md (seznam registriranih imen) in
označi ZM-1 kot zaključen v docs/NACRT_MEHANIZMI.md. Docstring naj pove, da je LDPTrace
kandidat za baseline (odločitev D5 v projektu Izbirni predmeti je odprta). Koda,
identifikatorji, docstringi in testi v angleščini; pogovor z mano v slovenščini, brez
nepojasnjenih kratic.
```

### 7.2 ZM-2 Točkovni LDP

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_MEHANIZMI.md SAMO §1 in §3 (ZM-2 točkovni LDP); arhiva arhiv/ ne odpiraj. Kot
vzorec preberi src/trajguard/privacy/geoind.py, src/trajguard/privacy/ldp.py
(grr_perturb), razred Grid v src/trajguard/representation/views.py, v
src/trajguard/experiments/orchestrator.py funkcije _protected_pool, _arm_infos in blok,
ki instancira mehanizme (mech_plans), ter tests/test_geoind.py in
tests/test_orchestrator.py.

Naloga: implementiraj PrivacyMechanism "point_ldp" v src/trajguard/privacy/point_ldp.py po
odločitvah D-2.1 do D-2.4 (GRR nad celicami Grid nad bbox zemljevida, izdana točka
enakomerno v poročani celici, ε na točko, spent_budget = ε·n točk, guarantee "ldp") in
edino spremembo orkestratorja: vbrizg bbox zemljevida v konstruktor mehanizma po podpisu,
po vzorcu _generator_ctor, s testom. Nato nova konfiguracija
config/experiments/geolife_mech_reid_u20.yaml (kopija geolife_geoind_reid_u20.yaml s
sidrnima rokama none in geo_indistinguishability ε=1 ter roko point_ldp ε ∈ {4.0, 6.0,
8.0}; enota ε zapisana v komentarju; konfiguracije S4 ostanejo nespremenjene).

Postopek: plan mode in moja potrditev, veja claude/zm2-point-ldp, modul, uvoz v
builtins.py, tests/test_point_ldp.py po §3.4, ruff/mypy/pytest z izpisom; po možnosti
uv run trajguard run config/experiments/geolife_mech_reid_u20.yaml in vrstice (vključno
n_rematch_dropped) v docs/HANDOFF.md §2.3. Posodobi CLAUDE.md (stanje), docs/RUNNING.md
§7, docs/CODEBASE_STRUCTURE.md in označi ZM-2 v docs/NACRT_MEHANIZMI.md. Koda in testi v
angleščini, pogovor v slovenščini brez nepojasnjenih kratic.
```

### 7.3 ZM-3 Naivna trojica

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_MEHANIZMI.md SAMO §1 in §4 (ZM-3 naivna trojica); arhiva arhiv/ ne odpiraj. Kot
vzorec preberi src/trajguard/privacy/geoind.py, src/trajguard/privacy/none.py, funkciji
_protected_pool in _noisy_clean v src/trajguard/experiments/orchestrator.py,
_evenly_spaced v src/trajguard/attacks/reidentification.py in tests/test_geoind.py.

Naloga: implementiraj tri mehanizme brez formalne garancije v
src/trajguard/privacy/naive.py: "spatial_rounding" (cell_m), "temporal_downsampling"
(interval_s, prva in zadnja točka ohranjeni) in "gaussian_noise" (sigma_m, seed), vsi z
guarantee "none" in spent_budget None, po odločitvah D-3.1 do D-3.4. Preveri obnašanje
reidentifikacije in ponovnega ujemanja pri kratkih in podvojenih izdajah ter to pokrij s
testi. Roke dodaj v config/experiments/geolife_mech_reid_u20.yaml (iz ZM-2) z mrežami
cell_m [100, 500, 2000], interval_s [30, 120, 600], sigma_m [50, 200, 1000].

Postopek: plan mode in moja potrditev, veja claude/zm3-naive-baselines, modul, uvoz v
builtins.py, tests/test_naive.py po §4.4 vključno z end-to-end testom orkestratorja s
temporal_downsampling, ruff/mypy/pytest z izpisom; po možnosti zagon
geolife_mech_reid_u20.yaml in vrstice v docs/HANDOFF.md §2.3. Posodobi CLAUDE.md,
docs/RUNNING.md, docs/CODEBASE_STRUCTURE.md in označi ZM-3 v docs/NACRT_MEHANIZMI.md. Koda
in testi v angleščini, pogovor v slovenščini brez nepojasnjenih kratic.
```

### 7.4 ZM-4 PrivTrace

```
Nadaljujeva delo v repozitoriju trajguard. Preberi CLAUDE.md, docs/ARCHITECTURE.md ter iz
docs/NACRT_MEHANIZMI.md SAMO §1 in §5 (ZM-4 PrivTrace); arhiva arhiv/ ne odpiraj. Kot
vzorec preberi src/trajguard/synthesis/ldptrace.py (iz ZM-1) in
src/trajguard/synthesis/markov.py, protokol ShadowGenerator v
src/trajguard/attacks/membership.py ter tests/test_ldptrace.py. Za podrobnosti izvirnika
uporabi podagenta, ki prebere https://github.com/DpTrace/PrivTrace (discretization/,
primarkov/, generator/) in članek https://arxiv.org/abs/2210.00581 (§4, Algoritma 1 in 2,
dodatek B); glavni kontekst naj ostane čist.

Naloga: implementiraj PrivTrace kot SyntheticGenerator "privtrace" v
src/trajguard/synthesis/privtrace.py po odločitvah D-4.1 do D-4.5 (dvoplastna mreža z
Laplace(1/ε₁) na normirane gostote, Markov 1. in 2. reda z Laplace(1/ε₂), Laplace(1/ε₃)
in NormCut, adaptivna izbira reda s θ₁ = (√2/ε₂)·m in θ₂ = 5, začetek iz vrstice
navideznega začetka brez reševalca najmanjših kvadratov, max_len varovalka, payload =
listne celice, sequence_log_prob s spodnjo mejo 1e-12). Vsako odstopanje od članka
(D-4.2, D-4.3, izbrana varianta D-4.1) zapiši v docstring. Docstring izrecno pove, da gre
za zaupanja vrednega zbiralca in DP na ravni ene poti, torej zgornjo mejo uporabnosti in
kandidat za baseline (D5 odprta). Nove odvisnosti ne dodajaj brez utemeljitve.

Postopek: plan mode in moja potrditev (predlagaj razrez, če bi modul presegel ~500
vrstic), veja claude/zm4-privtrace, modul, uvoz v builtins.py, tests/test_privtrace.py po
§5.4, roka privtrace ε ∈ {0.5, 2.0, 8.0} v config/experiments/geolife_mech_mia_u20.yaml s
komentarjem o modelu zaupanja, ruff/mypy/pytest z izpisom; po možnosti zagon in vrstice v
docs/HANDOFF.md §2.3. Posodobi CLAUDE.md, docs/RUNNING.md §7.2, docs/CODEBASE_STRUCTURE.md
in označi ZM-4 v docs/NACRT_MEHANIZMI.md. Koda in testi v angleščini, pogovor v
slovenščini brez nepojasnjenih kratic.
```

---

## 8. Viri

- Du, Hu, Zhang, Fang, Chen, Zheng, Gao: *LDPTrace: Locally Differentially Private
  Trajectory Synthesis*, PVLDB 16(8), 2023. arXiv 2302.06180. Koda:
  https://github.com/zealscott/LDPTrace (Apache-2.0).
- Wang, Zhang, Wang, He, Backes, Chen, Zhang: *PrivTrace: Differentially Private
  Trajectory Synthesis by Adaptive Markov Models*, USENIX Security 2023. arXiv 2210.00581.
  Koda: https://github.com/DpTrace/PrivTrace (brez datoteke LICENSE).
- Wang, Blocki, Li, Jha: *Locally Differentially Private Protocols for Frequency
  Estimation*, USENIX Security 2017 (OUE; že v `privacy/ldp.py`).
- Andrés, Bordenabe, Chatzikokolakis, Palamidessi: *Geo-indistinguishability*, CCS 2013
  (obstoječi `geoind.py`).
- Takagi, Cao, Asano, Yoshikawa: *Geo-Graph-Indistinguishability*, 2020. Koda:
  https://github.com/tkgsn/GG-I (za morebitno ZM-5).
- Gursoy et al.: *AdaTrace*, CCS 2018, koda https://github.com/git-disl/AdaTrace (Java);
  Cunningham et al.: NGRAM, PVLDB 2021 (brez javne kode). Oba samo za citiranje.
- Zapiski projekta »Izbirni predmeti« (blueprint članka, odločitev D5, analize 45 del):
  `C:\Users\Adm\Documents\Dr studij\Dr\Projekti\Izbirni predmeti\memory\`.
