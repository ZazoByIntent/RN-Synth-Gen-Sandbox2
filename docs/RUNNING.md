# Running trajguard — a practical guide

Every way to run this project, with the exact commands, what to expect, and what to
do when something goes wrong. All commands are run from the repository root. Every
command and error message in this guide was executed and captured on a clean clone
of `main` (July 2026); numbers marked "fixture" come from the committed test data.

**Sections — jump to the one you need, do not read the whole file:** §0 setup ·
§1 tests and lint · §2 one-time inputs (map build, Geolife) · §3 notebooks 01 / 02 /
03 · §4 visual recipes (map, one trajectory before/after) · §5 fixture smoke test ·
§6 baseline reidentification and the population threshold · §7 geo-ind grid,
reconstruction, POI inference · §7.1 repetitions across seeds · §7.2 membership
inference · §7.3 runtime budget and scope reduction · §7.4 validation run and the
threshold history · §7.5 mechanism-breadth perturbation config (point LDP and the naive
baselines) · §8
`trajguard report` · §9 RN-LDP-Synth evidence sweep ·
§9.1 LDPTrace validation inputs (Porto conversion) · §9.2 membership inference in the
cells representation (Porto) · §9.3 LDPTrace validation run (reference vs port) · §10
caching · §11 troubleshooting.

## 0. One-time setup

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/), the Python package
manager this project uses. Then:

```sh
uv sync
```

This creates a local virtual environment (`.venv/`) and installs the exact locked
versions of every dependency from `uv.lock`. Every command below is prefixed with
`uv run`, which means "run inside that environment" — you never need to activate
anything manually.

## 1. Health check: the test suite (no downloads needed)

```sh
uv run pytest
```

**Expected outcome:** `353 passed` in about a minute (September 2026). The suite runs entirely on
small fixture files committed under `tests/fixtures/` — no internet, no dataset, no
built map required. If this is green, your environment is set up correctly.

The same checks CI runs, if you want them locally:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

**Expected outcome:** all three exit silently (or print "All checks passed!").

## 2. One-time inputs for real experiments

Experiments need two inputs that are deliberately not in git.

### 2.1 Build the road networks

```sh
uv run python -m trajguard.maps.build config/maps.yaml --region beijing
```

**Expected outcome:** a line like `beijing: <N> nodes, <M> edges -> maps/beijing`,
and a `maps/beijing/` directory containing `graph.graphml`, `edges.parquet`,
`nodes.parquet` and `meta.json`. This downloads street data from OpenStreetMap, so
it needs internet and can take a few minutes; a `cache/` directory appears in the
repo root (the download cache — harmless, git-ignored). You only do this once.

Running the command without `--region` also builds Ljubljana, which is reserved for
synthetic-trajectory work — you do not need it for Geolife experiments.

### 2.2 The Geolife dataset

Real Geolife is distributed by Microsoft Research under a licence that does not
permit redistribution, so you must download it yourself ("Geolife GPS Trajectories
1.3"). Unpack it so that this layout exists:

```
data/raw/geolife/Data/<user id>/Trajectory/<timestamp>.plt
```

This is the same layout as the miniature example in `tests/fixtures/geolife/`.

**Tip:** the full dataset has 182 users and the reidentification attack compares
trajectories pairwise, so a first full run is slow. To see everything work end to
end, start with a subset — copy a handful of user folders (say `Data/000` through
`Data/020`) instead of all of them.

## 3. Map-matching sanity notebook (works offline)

`notebooks/01_matching_sanity.ipynb` is the visual check that trajectory import and
map-matching work: it loads road-following test trajectories, snaps them onto a
committed slice of Beijing's real OpenStreetMap network, prints a match-quality
table, and draws the raw GPS points against the snapped paths. It runs entirely
from `tests/fixtures/` — you do not need the built map or the Geolife download.
(For the same before/after picture of one single trajectory of your choice, see
§4.2 instead.)

Run it headlessly (executes the notebook and saves the outputs into the file, which
you then open in VS Code or any notebook viewer):

```sh
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/01_matching_sanity.ipynb
```

Or interactively (the project does not ship Jupyter's browser interface, so uv adds
it just for this launch):

```sh
uv run --with jupyterlab jupyter lab notebooks/01_matching_sanity.ipynb
```

**Expected outcome:** a table reporting **kept 8 / dropped 1 at min_match_score=0.6**
— eight road-following traces match with scores around 0.88–0.94, and one deliberate
off-road random walk collapses to ≈0.02 and is correctly rejected. Three figures: all
matched paths on the network, per-trajectory panels (blue GPS dots hugging the red
snapped path), and the rejected off-road walk.

To run the same check against your full `maps/beijing` build instead of the fixture
slice, change the first code cell to:

```python
net = OSMMapSource(
    region="beijing",
    bbox=(116.20, 39.75, 116.55, 40.05),
    crs="EPSG:32650",
    out_dir=Path("..") / "maps",
).load()
```

Expect the same matches but a noticeably slower run, and skip the overview plot cell
(it would draw every street in Beijing). The per-trajectory panels stay fast because
they crop to each path's surroundings.

## 3.1 End-to-end pipeline walkthrough notebook (works offline)

`notebooks/02_pipeline_walkthrough.ipynb` is a presentation-ready tour of every
stage and every runnable combination in the benchmark: bare maps → raw trajectories
→ cleaning → map matching → representation views → splits → anonymization (with and
without re-matching) → synthetic generation → all four attack families → utility
metrics → a full orchestrated experiment → the risk report → the RN-LDP-Synth
evidence sweep. Like the sanity notebook it runs entirely from `tests/fixtures/`
by default (set `USE_REAL_DATA = True` in the setup cell to point it at your full
`maps/beijing` build and Geolife download instead).

Run it headlessly, or interactively, exactly like the sanity notebook:

```sh
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/02_pipeline_walkthrough.ipynb
```

**Expected outcome:** every cell executes without errors; along the way you get the
registry tables (implemented vs planned components), per-stage data-frame previews,
match-quality numbers on the fixture slice, attack results for all four families,
and at the end a small orchestrated run whose `tradeoff.png` is displayed inline.
Note that no automation executes the notebooks (CI runs only `ruff`, `mypy`,
`pytest`), so re-run them manually after changes that alter their outputs.

## 3.2 S4 sweep-analysis notebook (reads results, runs nothing)

`notebooks/03_s4_sweep.ipynb` is the analysis layer for the S4 campaign of
systematic runs: it reads `reports/results_master.csv` (or concatenates the
per-run `results.csv` tables itself when the master does not exist yet),
aggregates repetitions of the same experiment across seeds via
`trajguard.reporting.results_io` (mean + Student-t 95% CI, the §7.1 across-seed
kind — never mixed with within-run bootstrap intervals), draws the four planned
report figures into `reports/s4_figures/` and inline, and lists every attack
invocation that exceeded the attack time budget (300 s at the 20/50 rungs,
1200 s at 182; §7.3) together with the §7.3 reduction ladder. It is strictly a
reader: it never launches experiments and never writes
under `results/`.

Run experiments first (§6–§7.2), then execute the notebook headlessly, or open
it interactively like the other notebooks (§3):

```sh
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/03_s4_sweep.ipynb
```

**Expected outcome:** every cell executes; with only fixture-scale runs under
`results/` you get the same statistically meaningless numbers as §5 — the point
is the plumbing. With no runs at all, the first cell stops with a clear
"run an experiment first" error.

**Stability warning:** the notebook and `src/trajguard/reporting/results_io.py`
are pinned to the results-table header (`RESULTS_COLUMNS`,
`docs/REZULTATI_SHEMA.md`). A table with a foreign header fails loudly instead
of misaligning columns — so any schema change must update the schema module,
the doc, `results_io.py`, and this notebook in the same PR. CI does not execute
notebooks, so refresh this one manually after new runs.

## 4. Quick visual recipes

Two small standalone scripts for common "let me just look at it" needs. Both write a
PNG into the repo root; both were run and verified. You can paste each block
directly into a terminal as shown (it feeds the script to Python via stdin), or save
the Python part to a file and run `uv run python <file>`.

### 4.1 Show the bare road network (no trajectories)

Draws your built Beijing map and nothing else. Requires `maps/beijing` (§2.1); no
dataset needed.

```sh
uv run python - <<'EOF'
from pathlib import Path
import matplotlib.pyplot as plt
from trajguard.maps.osm import OSMMapSource

net = OSMMapSource("beijing", (116.20, 39.75, 116.55, 40.05), "EPSG:32650", Path("maps")).load()
ax = net.edges.plot(color="dimgray", linewidth=0.4, figsize=(12, 12))
ax.set_aspect("equal")
ax.set_axis_off()
plt.savefig("beijing_map.png", dpi=200, bbox_inches="tight")
print(f"wrote beijing_map.png ({len(net.nodes)} nodes, {len(net.edges)} edges)")
EOF
```

**Expected outcome:** `wrote beijing_map.png (<N> nodes, <M> edges)` and the image in
the repo root. For the full Beijing network this draws tens of thousands of street
segments, so give it a moment. To view the offline fixture slice instead, use
`OSMMapSource("beijing_fixture", (116.30, 39.98, 116.32, 39.995), "EPSG:32650", Path("tests/fixtures/maps"))`.
For Ljubljana (if built): `OSMMapSource("ljubljana", (14.42, 46.00, 14.57, 46.10), "EPSG:3794", Path("maps"))`.

### 4.2 One chosen trajectory: before vs after map matching

Picks a single trajectory by its identifier, cleans it, matches it onto the network,
and draws the raw GPS points (blue dots, "before") over the snapped road path (red
line, "after"). As written it runs fully offline on the committed fixtures:

```sh
uv run python - <<'EOF'
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from pyproj import Transformer

from trajguard.datasets.cleaning import CleaningConfig, clean
from trajguard.datasets.geolife import GeolifeLoader
from trajguard.maps.osm import OSMMapSource
from trajguard.matching.leuven import LeuvenMapMatcher

logging.disable(logging.WARNING)  # silence the matcher's linear-search notices

TRAJ_ID = "geolife/005/20081202080000"   # <-- pick any trajectory id
net = OSMMapSource("beijing_fixture", (116.30, 39.98, 116.32, 39.995),
                   "EPSG:32650", Path("tests/fixtures/maps")).load()
loader = GeolifeLoader(Path("tests/fixtures/geolife_onroad"))

print("available ids:", [r.traj_id for r in loader.iter_trajectories()][:5], "...")
raw = next(r for r in loader.iter_trajectories() if r.traj_id == TRAJ_ID)
traj = clean(raw, CleaningConfig())
m = LeuvenMapMatcher().match(traj, net)
print(f"{TRAJ_ID}: match_score={m.match_score:.3f}, frac_matched={m.frac_matched:.2f}")

to_xy = Transformer.from_crs("EPSG:4326", net.crs, always_xy=True)
gx, gy = zip(*[to_xy.transform(lon, lat) for lat, lon, _ in traj.points])
xs = [p[0] for p in m.matched_points]
ys = [p[1] for p in m.matched_points]
pad = 80
ax = net.edges.cx[min(xs) - pad : max(xs) + pad, min(ys) - pad : max(ys) + pad].plot(
    color="lightgray", linewidth=1, figsize=(9, 9))
ax.scatter(gx, gy, s=12, color="tab:blue", zorder=3, label="raw GPS (before)")
ax.plot(xs, ys, "-", color="tab:red", linewidth=2, zorder=2, label="matched (after)")
ax.set_aspect("equal")
ax.legend()
plt.savefig("trajectory_before_after.png", dpi=200, bbox_inches="tight")
print("wrote trajectory_before_after.png")
EOF
```

**Expected outcome (fixture):** the available-ids line, then
`geolife/005/20081202080000: match_score=0.877, frac_matched=1.00`, and
`trajectory_before_after.png` showing blue GPS dots hugging the red snapped path.
The blue-to-red offsets are the ~3 m synthetic GPS noise being corrected.

To use it on **your real data** instead, change three lines: point the loader at
`GeolifeLoader(Path("data/raw/geolife"))`, load the full map with
`OSMMapSource("beijing", (116.20, 39.75, 116.55, 40.05), "EPSG:32650", Path("maps"))`,
and set `TRAJ_ID` to one of your own — trajectory ids have the form
`geolife/<user folder>/<plt filename without extension>`, and the printed
"available ids" line shows the first few so you can copy one. Matching a long
trajectory against the full network takes noticeably longer than the fixture run.
A low score (below the experiment's `min_match_score` — 0.05 at the measurement
rungs, 0.3 for the reporting run, see §6) with sparse blue dots far from any road
means the trajectory would be dropped in a real run.

## 5. Smoke test: the full experiment pipeline on fixture data

You can push the committed fixture trajectories through the *entire* pipeline —
load, clean, match, split, attack, metrics — without downloading Geolife:

```sh
cp -r tests/fixtures/geolife_onroad/Data data/raw/geolife/
find data/processed -mindepth 1 ! -name '.gitkeep' -delete   # clear stale caches (see §10)
uv run trajguard run config/experiments/geolife_reid_baseline.yaml
```

This needs a map at `maps/beijing` (§2.1). If you have not built the real one and
just want the plumbing test fully offline, you can temporarily stand in the
committed fixture slice: `cp -r tests/fixtures/maps/beijing_fixture maps/beijing`
(delete or rebuild it before doing real runs).

**Expected outcome:** a metrics table on the console and files under
`results/geolife_reid_baseline/`. Verified against the fixture map: `run.json`
records `n_matched = 8` trajectories from 2 users, and the attack reports top-1
accuracy 0.25 with top-5 accuracy 1.0. **These numbers are statistically
meaningless** — with two users the attacker's top-5 list always contains the right
answer. The point of this run is only to prove every pipeline stage executes.

## 6. Experiment: baseline reidentification (real Geolife)

```sh
uv run trajguard run config/experiments/geolife_reid_baseline.yaml
```

Runs the whole pipeline on unprotected data: import → cleaning (speed/length
filters, resampling) → map-matching → one-time user split → reidentification
attack, where the attacker knows k ∈ {3, 5, 10} points of each target and
searches for the nearest matching trajectory.

**What population these numbers describe.** The report measures *driving traces*,
defined operationally: the population is the set of cleaned trajectories that match
the drive road network with `match_score ≥ min_match_score`
(`map_matching.min_match_score`); everything below is dropped before the split.
The threshold has two values, both measured, not asserted:

- **0.3 — the reporting population** (author decision, 17 Aug 2026, from the
  50-rung measurement, `docs/HANDOFF.md` 1.3): the strictest-with-margin threshold whose
  projected non-member count at 182 users (118) clears the 100 needed to revive
  the `tpr@fpr = 0.01` operating point. The full-scale configs
  (`geolife_geoind_reid`, `geolife_synth_mia`) use it.
- **0.05 — the measurement-rung population** (u20/u50 configs, unchanged): the one
  natural break of the score distribution — 85 % of cleaned Geolife trajectories
  at the 20-user rung score below it (walking, cycling, subway, or outside the
  bbox) and essentially do not match the drive network at all.

The diagnostic cell in `notebooks/03_s4_sweep.ipynb` §9 shows the score
distribution and the threshold table per rung. See §7.4 for the history of how
these thresholds were chosen.

**Expected outcome:**

- A console table: one row per (arm × known-points × metric) with the value and a
  95% bootstrap confidence interval. Metrics: `top1_acc` / `top5_acc` (how often the
  true person is the attacker's first / among the top-five guesses) and
  `linkage_rate`.
- `results/geolife_reid_baseline/` containing `metrics.csv` (long-form metrics),
  `results.csv` (the same rows in the unified results-table schema from
  `docs/REZULTATI_SHEMA.md`: run provenance, pivot-axis columns like ε and
  known_points, arm statistics, runtimes, and each attack's peak memory in MB —
  the file you pivot in Excel; `peak_memory_mb` is traced with `tracemalloc`,
  which slows the attacks and thereby inflates `attack_runtime_s` a little, so
  set `metrics: {memory: false}` for timing-critical sweeps),
  `matrix.csv` (the per-run risk-matrix slice: one row per target arm, one column
  per attack family's headline metric — reidentification at its largest
  known-points level; the per-k view stays in `results.csv`), and `run.json`
  (run metadata: how many trajectories survived each stage — your first stop
  when numbers look odd).
- Console lines `Searching closeby nodes with linear search...` during matching are
  harmless progress noise from the matching library.

Intermediate artifacts are cached under `data/processed/` (§10), so re-running the
same config is much faster than the first run.

## 7. Experiment: geo-indistinguishability grid (real Geolife)

```sh
uv run trajguard run config/experiments/geolife_geoind_reid.yaml
```

The same attack, but additionally on data protected with planar Laplace noise
("geo-indistinguishability") at ε ∈ {0.1, 1.0, 10.0} — smaller ε means stronger
noise. The grid expands automatically: each ε becomes its own arm next to the
unprotected baseline.

**Expected outcome:** the console table now includes
`reidentification:protected:geo_indistinguishability:epsilon=…` rows, the results
directory additionally gets `tradeoff.png` (reidentification accuracy versus
utility damage) plus one `tradeoff_<family>.png` per further attack family whose
arms carry utility values (e.g. `tradeoff_reconstruction.png`; membership
inference gets none — utility is only measured over protected releases, and its
arms are synthetic), and utility metrics (`cell_js_divergence`,
`length_dist_error`) quantify how much the noise distorted the data.

Beyond `tradeoff`, `reporting.plots` accepts the four planned report figures
(report §6.8, §7.2–7.6), all drawn from the same rows that go into `results.csv`:

- `by_epsilon` — one `by_epsilon_<family>.png` per attack family: the family's
  headline metric versus the arm's ε (log axis), a line per arm and — for
  reidentification — per known-points level. Arms without an ε (raw, identity,
  non-private generators) do not appear.
- `by_knowledge` — `by_knowledge_<family>.png` for families with the
  known-points knob (today reidentification): headline metric versus the number
  of points the attacker knows, a line per target arm.
- `mechanisms` — `mechanisms_<family>.png`: horizontal bars comparing all arms
  on the family's headline metric (reidentification at its largest
  known-points), with the within-run bootstrap interval as whiskers.
- `runtime` — a single `runtime.png`: one bar per attack invocation with its
  runtime in seconds (log axis), coloured by family.

A requested plot for which the run produced no matching rows is simply not
written (no empty file); a plot whose axis cannot exist for the config at all
(e.g. `by_knowledge` without a known-points attack) is rejected up front. The config also runs the reconstruction attack: one
`reconstruction:protected:geo_indistinguishability:epsilon=…` row per ε arm with
`hausdorff_m`, `dtw_m`, and `mean_spatial_error_m` in metres — the attacker's MAP
inversion of the noise (it knows ε and unit_m, design §6.3). Expect the mean
spatial error to sit *below* the mechanism's mean displacement `2·unit_m/ε` on
smooth paths: that gap is exactly the privacy the inversion claws back. The
identity arm gets no reconstruction row (there is no noise to invert).

The config also runs the POI inference attack (POI — point of interest: here the
inferred home and work location of each user, design §6.4). It produces one
`poi_inference:protected:…` row set per arm — including the identity arm `none` —
with four metrics: `home_error_m` / `work_error_m` (metres between the inferred
and the true home/work location, averaged over the users the attack managed to
place) and `home_localised` / `work_localised` (the fraction of all users whose
location the attacker pins within `threshold_m`, default 200 m). Unlike
reidentification, this attack reads the released GPS points directly, so its rows
survive even for arms whose noise made every trajectory fail re-matching (the
ε = 0.1 arm still gets a row — expect NaN/blank errors there, because the noise
dissolves every stay-point). Read the `protected:none` row as a sanity value: the
identity mechanism releases the raw points, so near-zero error and localised = 1.0
there mean the harness is honest, not that the data is safe.

**Expected surprise that is not a bug:** at ε = 0.1 the noise is ~2 km per point, so
most or all protected trajectories fail re-matching and the arm reports zero or NaN
attack accuracy — "protection by destroying the release". Verified on fixture data:
the ε = 0.1 and ε = 1.0 arms dropped all 8 trajectories (`n_rematch_dropped = 8` in
`run.json`), ε = 10.0 kept 4. On real, denser Geolife data more will survive, but
the pattern (stronger noise → fewer survivors) is by design; the survivor counts per
arm are always recorded in `run.json`.

## 7.1 Repetitions: mean and 95% CI across seeds

```sh
uv run trajguard repeat config/experiments/geolife_geoind_reid.yaml --seeds 1 2 3 4 5
```

Runs the same experiment once per seed and aggregates every metric across the
repetitions. The population and the train/test/shadow/attack split stay pinned by
`experiment.split_seed` in the YAML, so the expensive cleaning/matching pool is
computed once and shared; each seed only redraws the mechanism noise and the
attacker's knowledge. (A single extra repetition without aggregation:
`trajguard run <config> --seed N`.)

**Expected outcome:** one `results/<exp_id>/seed<N>/` directory per seed with the
usual artifacts, plus `results/<exp_id>/repetitions.csv` and a console table with
the across-seed mean and a Student-t 95% confidence interval per metric. This
interval reflects variance *between* repetitions; the bootstrap interval inside
each seed's `metrics.csv` reflects resampling uncertainty *within* one run — do
not mix the two in report tables.

**Expected zero-width intervals that are not a bug:** the `raw` arm and the
identity arm `protected:none` produce *identical* values in every seed, so their
across-seed interval has width zero (e.g. `top1_acc = 0.500 [0.500, 0.500]`).
The run seed only redraws the mechanism noise and the shadow subsets; the
attacker's known points are evenly spaced (`_evenly_spaced` in
`attacks/reidentification.py`), not sampled. An arm without noise therefore has
no source of randomness left, and a degenerate interval is the correct answer,
not a missing one (first S4 campaign, S4-5 in `docs/HANDOFF.md` 1.1).

## 7.2 Experiment: membership inference against synthetic generators

```sh
uv run trajguard run config/experiments/geolife_synth_mia.yaml
```

Answers a different question than sections 6–7: not "can the attacker link or
undo a noisy release" but "did the generator memorize its training data". The
attack (LiRA — likelihood-ratio membership inference) asks, per trajectory:
was this exact path in the generator's training set? The target generator is
fitted on the train split; members are train paths, non-members test paths, and
the attacker's shadow generators — same-class models used to calibrate the
score — train on the shadow split plus the queried candidate paths, never on
the rest of the training data (fair-MIA rule from `CLAUDE.md`).

**Expected outcome:** one `membership_inference:synthetic:<generator>` row set
per generator arm in `metrics.csv` with `auc` (how well the attacker separates
members from non-members; 0.5 is chance, 1.0 is certain) and one `tpr@fpr=…`
row per configured operating point (the fraction of true members caught while
keeping false accusations below that rate — the honest headline number per
Carlini 2022). These are score-based metrics, so the `ci_low`/`ci_high` columns
stay empty by design: the confidence interval comes from repetitions
(`trajguard repeat`, §7.1), not from within-run bootstrap. The shipped config
runs the non-private `markov` baseline, where the attack *should* score high —
that arm is the memorization ceiling to compare private generators against —
plus the `rn_ldp_synth` prototype at ε ∈ {0.5, 2.0, 8.0}, one arm per ε with
same-class shadows sharing that ε. Read those rows against the markov ceiling:
a working privacy mechanism pulls `auc` toward 0.5 and the low-FPR TPR toward
zero as ε shrinks.

**Mechanism-breadth sibling config (`docs/NACRT_MEHANIZMI.md` §1.4, §2):**

```sh
uv run trajguard repeat config/experiments/geolife_mech_mia_u20.yaml --seeds 1 2 3
```

The S4 configs above are frozen, so new generator arms live in
`geolife_mech_mia_u20.yaml`: the same 20-user population, split, attack and
300 s budget, with the arms `markov`, `rn_ldp_synth` at ε = 2 (anchors) and the
LDPTrace baseline candidate `ldptrace` at ε ∈ {0.5, 2.0, 8.0}. Expected outcome:
`results/geolife_mech_mia_u20/seed{1,2,3}/` plus `repetitions.csv` with one
`membership_inference:synthetic:ldptrace:epsilon=…` row set per ε (`auc`,
`tpr@fpr=0.1`; the 0.001 and 0.01 points are NaN at this rung, S4-2). The
`ldptrace` arms are cheap (a few seconds per seed): the generator only sums
Optimized-Unary-Encoding bit vectors over a 12×12 grid, no Dijkstra calibration.
For both `rn_ldp_synth` and `ldptrace` ε is spent per trajectory (per device),
not per point, so these rows are not comparable with the geo-indistinguishability
ε of §7. Measured rows: `docs/HANDOFF.md` §2.3.

## 7.3 Computational budget and scope reduction (report §6.6)

Every attack invocation has a runtime budget, configurable as
`metrics.attack_time_budget_s`: **X = 300 seconds** at the 20/50 measurement
rungs (the author's decision, 5 Aug 2026) and **X = 1200 seconds** for the
182-user reporting run (the author's decision, 17 Aug 2026, from the 50-rung
measurement, `docs/HANDOFF.md` 1.3: at threshold 0.3 the projected gallery is ~590
traces and the dearest call — reidentification k10, DTW roughly quadratic in
gallery size — lands at ~750 s, over the old budget and under the new one). The
orchestrator compares each invocation's `attack_runtime_s` against it and, when
exceeded, prints a console warning and records the offenders in `run.json` under
`over_budget` (`budget_s`, `memory_traced`, and the worst-first `attacks` list).
Exceeding the budget **never fails or trims a run** — results stay complete, and
automatic scope reduction is deliberately absent because it would silently change
the experiment. The flag exists so you apply the rules below when planning the
*next* runs of a sweep.

The rules, applied one step at a time (re-measure after each step):

- **R0 — how to measure.** The budget applies to one attack invocation
  (`attack_runtime_s` in `results.csv`). Decide on times measured with
  `metrics: {memory: false}`: peak-memory tracing roughly doubles attack time,
  and `run.json` marks such runs with `memory_traced: true`.
- **R1 — the run stands.** An over-budget run stays in `results/` and in the
  master table; reduction applies to future runs only.
- **R2 — the reduction ladder.**
  0. **Diagnose before reducing:** check that the over-budget cost depends on
     the data at all — compare `attack_runtime_s` across runs with different
     `dataset.max_users` (or one cheap re-run at a lower step). If `max_users`
     does not move the cost, the cause sits in how the mechanism or attack is
     built, the fix belongs there, and the ladder below does not apply to it.
     First known counterexample: S4-3 (`docs/HANDOFF.md` 1.1) — the `rn_ldp_synth` constructor
     calibrated its decode-inflation factor from the map and config alone
     (~65 s per generator, 17 generators per MIA arm), so no `max_users` step
     could touch the cost; the fix was caching the calibration result across
     generators, not reducing scope.
  1. Reduce `dataset.max_users` one step down the design §6.4 sample ladder:
     182 → 100 → 50 → 20.
  2. If still over budget at 20 users, turn the family's own knob:
     membership inference — halve `n_shadow` (not below 8); reidentification —
     drop the largest `known_points` level. Reconstruction and POI inference
     have no knob of their own (their cost scales with the pool), so go to 3.
  3. Whatever remains over budget is **excluded from the sweep** (the arm or
     the attack), and the exclusion — with its measured runtime — is recorded
     in the report and in `docs/HANDOFF.md`.
- **R3 — traceability.** Record every reduction as a comment in the experiment
  YAML (which ladder step, why); the `max_users` and `config_hash` columns in
  `results.csv` keep reduced runs distinguishable on their own.

## 7.4 Validation run and the population threshold (S4-1)

**Population definition.** All Geolife experiments measure driving traces, defined
operationally as cleaned trajectories with `match_score ≥ min_match_score` against
the drive network (see §6). The measurement-rung threshold **0.05** was chosen from
the measured score distribution (diagnostic cell, `notebooks/03_s4_sweep.ipynb` §9,
executed 16 Aug 2026 at `max_users: 20`): the distribution has exactly one natural
break, at ≈ 0.05 — 85 % of cleaned trajectories (1371/1607) score below it and do
not match the drive network at all, while above it a thin, roughly flat tail runs
to ~0.85 with no second break. The reporting threshold **0.3** was then chosen
from the 50-rung measurement (see the last paragraph of this section). The report
presents the distribution alongside the results, so the population boundary is a
measured quantity, not a claim.

**Validation-run success criterion** (`arhiv/HANDOFF_S4_POPRAVKI.md` §2; measured
outcome in `docs/HANDOFF.md` 1.2). After the
S4 fix PRs, the campaign is repeated at `max_users: 20` with the same configs and
seeds as the first run. The run passes when both hold:

1. at least **11 non-members** survive into the membership-inference pool
   (projected to ≥ 100 at 182 users, which revives the `fpr = 0.01` operating
   point), and
2. the reidentification gallery covers at least **15 of 20 users**.

In addition, the `rn_ldp_synth` arm must come in under the 300 s budget (proof of
the S4-3 fix) and `trajguard report` must produce `report.md` and
`risk_matrix.csv` (proof of S4-4). At threshold 0.05 the diagnostic cell measures
236 surviving traces, 16/20 users, 15 non-members — the only threshold in the
candidate set that meets both criteria at this rung.

**If the criterion fails,** the agreed lever sequence is: first retry at
`max_users: 50` (the 20-user rung may simply be too small for MIA); only if it
fails there too, change the MIA split fractions (e.g. a larger `test`), recording
explicitly in the report that a smaller `train` means a weaker target generator
and therefore less memorization for the attack to measure. If no reasonable
threshold keeps enough data, the reserve option from S4-1 opens (filtering by
Geolife transport-mode labels) — that is a new author decision, not an
implementation one.

**The reporting threshold, measured at the 50 rung.** The author's note of
16 Aug 2026 projected that a stricter threshold of **0.5** would suffice from
`max_users: 50` up (≈ 116 non-members at 182 users). The 50-rung measurement
(17 Aug 2026, diagnostic cell §9 over the rung's 3243 cleaned traces;
`docs/HANDOFF.md` 1.3) did **not** confirm it: at 0.5 only 111 traces and 8 non-members survive,
projecting **81** non-members at 182 — below the 100 needed for `fpr = 0.01`.
By the measured table, 0.4 is the strictest threshold that reaches 100 exactly;
**0.3** reaches it with margin (162 traces, 33/50 users, 12 non-members,
projection 118). The author's decision (17 Aug 2026): the 182-user reporting
configs use **0.3**; the u20/u50 configs stay at 0.05 as the measured record of
those rungs.

## 7.5 Mechanism-breadth sibling config: point LDP and the naive baselines (real Geolife)

```sh
uv run trajguard run config/experiments/geolife_mech_reid_u20.yaml
```

The S4 configs of §7 are frozen, so new perturbation arms live in
`geolife_mech_reid_u20.yaml` (`docs/NACRT_MEHANIZMI.md` §1.4, §3, §4): the same 20-user
population, cleaning, matching threshold 0.05, split, attacks and 300 s budget, with
the arms `none` and `geo_indistinguishability` at ε = 1 (anchors from S4), the
point-LDP mechanism `point_ldp` at ε ∈ {4, 6, 8} (ZM-2) and the three naive baselines
of ZM-3 (`privacy/naive.py`, nine arms, see the end of this section). The point-LDP
part first. Point LDP (`privacy/point_ldp.py`)
maps every GPS point to a cell of a 20 × 20 grid over the map bbox (k = 400 cells,
~1.5 × 1.7 km over Beijing, the same grid as `metrics.utility_grid`), replaces the
cell by k-ary randomized response — the true cell survives with probability
e^ε/(e^ε + 399): 0.12 / 0.50 / 0.88 at ε = 4 / 6 / 8 — and releases a uniformly
random point inside the reported cell; timestamps stay. ε is spent per point
(`spent_budget` = ε × released points), like geo-ind but unlike the per-trajectory ε
of §7.2. The map bbox is injected by the orchestrator (a mechanism whose constructor
takes `bbox` receives `map.bbox`); setting `bbox` under `params` is a config error.

**Expected outcome:** `reidentification:protected:point_ldp:epsilon=…` rows at
k = 3/5/10, `poi_inference` and utility rows per arm; reconstruction rows only for
the geo-ind arm (the attack skips other mechanisms). **Expected surprise that is not
a bug:** on this coarse grid every released point is displaced by hundreds of metres
even when the true cell is reported, so re-matching drops most or all trajectories at
every ε (`n_rematch_dropped` in `run.json` — the same "protection by destroying the
release" as geo-ind at ε ≤ 1 in §7); the informative rows are `poi_inference` (it
reads the released points directly) and `cell_js_divergence` (the perturbed cell
histogram on the same grid). Measured on 4 Sep 2026 (seed 42, warm raw-pool cache,
`PYTHONHASHSEED=0`): 864 s in total, of which ~500 s is reidentification on the two
238-trace pools (`raw`, `none`); every `point_ldp` arm dropped all 238 trajectories at
re-matching (`n_pool = 0`, reidentification 0.000 in ~0.01 s), `cell_js_divergence`
0.42 / 0.18 / 0.03 at ε = 4 / 6 / 8, no attack over budget. Rows and the reading:
`docs/HANDOFF.md` §2.3. A finer grid is one YAML line
(`params: {epsilon: [8.0], n_rows: 50, n_cols: 50}`), but needs a larger ε for the same
survival probability (k = 2500: 0.54 at ε = 8).

**The naive baselines (ZM-3, same config, same command).** Three mechanisms without a
formal guarantee (`privacy/naive.py`; `guarantee = "none"`, `spent_budget` None, no ε,
so the `by_epsilon` plot skips them and the `mechanisms` plot lists them by parameter):
`spatial_rounding` at `cell_m` ∈ {100, 500, 2000} snaps every point to the centre of a
`cell_m` × `cell_m` metre cell of a global grid (maximum displacement `cell_m`·√2/2 =
71 / 354 / 1414 m, mean ≈ 0.38·`cell_m`; consecutive points in one cell become identical
released points, which the matcher tolerates); `temporal_downsampling` at `interval_s`
∈ {30, 120, 600} keeps the first point, then one point per interval and the last point
(cleaning resamples at 5 s, so 30 s keeps ~1/6 of the points and 600 s a handful per
trajectory); `gaussian_noise` at `sigma_m` ∈ {50, 200, 1000} adds independent N(0, σ²)
metres per axis (radial RMS σ·√2; σ = 200 m sits in the range of geo-ind at ε = 1).
Every perturbing arm is re-matched once (~1–2 min at u20, cached under
`data/protected/`) and then attacked; the raw-pool cache and the ZM-2 protected caches
are reused, so adding arms costs only their own re-matching and attacks. **Expected
outcome:** arms with a small displacement (rounding 100 m, downsampling 30 s, Gaussian
50 m) keep most of the 238 trajectories and reidentify close to the raw pool; arms
whose displacement exceeds the 50 m matching radius (rounding 500 / 2000 m, Gaussian
1000 m) drop most or all trajectories at re-matching, exactly like `point_ldp` above;
downsampling at 600 s leaves too few points for many releases to re-match. As above,
`n_rematch_dropped` in `run.json` says which happened, and the rows that stay
informative when the pool empties are `poi_inference` and the utility metrics.
**Measured on 4 Sep 2026** (seed 42, warm caches for the raw pool and the ZM-2 arms,
`PYTHONHASHSEED=0`): 1054 s in total (~495 s of it reidentification on `raw` and
`none`; re-matching all nine new arms took ~75 s together), no attack over budget, and
the ZM-2 rows reproduced to the digit. Re-matching kept 104 / 32 / 10 of 238
trajectories for rounding 100 / 500 / 2000 m, 222 / 207 / 212 for downsampling 30 /
120 / 600 s and 11 / 1 / 0 for Gaussian 50 / 200 / 1000 m — so Gaussian 50 m already
behaves like geo-ind at ε = 1, not like a "small" perturbation. The surprise that is
not a bug: **downsampling raises `top1_acc` above the raw pool** (0.49–0.54 at k = 3
versus 0.28) while keeping almost the whole pool, because the attack's unnormalised
DTW favours short gallery sequences (a hypothesis recorded, not verified, in
`docs/HANDOFF.md` §2.3 and §2.5). Rows and the reading: `docs/HANDOFF.md` §2.3.

## 8. Aggregate risk report

```sh
uv run trajguard report
```

Aggregates everything under `results/` into `reports/`. Both layouts are
discovered: a single run at `results/<exp_id>/run.json` and a repetition
experiment at `results/<exp_id>/seed<N>/run.json` (mixing the two inside one
experiment directory is a loud error). A repetition experiment is folded into
**one row per experiment arm**: the value is the across-seed mean and the CI the
Student-t 95% interval — the same statistics as `repetitions.csv` and the
`03_s4_sweep.ipynb` notebook, computed from the per-seed `results.csv` files.
Consequently the CIs in `metrics_long.*` mean different things by layout: the
within-run bootstrap interval for a single run, the across-seed interval for a
repetition experiment. The raw per-seed rows always remain available in
`results_master.csv`.

The report also enforces the `tpr@fpr` validity rule (S4-2, `docs/HANDOFF.md` 1.1): the
operating point needs at least `1/fpr` non-members (the boundary counts as
valid). New runs already record NaN plus a `run.json` warning for unresolvable
points; stored values from older runs are suppressed at report time. Suppressed
cells render as "–"/blank, and every suppression is listed in the report's
**Warnings** section together with warnings carried in `run.json`.

**Expected outcome:** the line `report: reports/report.md`, plus `metrics_long.csv`,
`metrics_long.parquet`, `risk_matrix.csv`, `results_master.csv` (every run's
`results.csv` concatenated into one table following `docs/REZULTATI_SHEMA.md` —
repetition runs under `seed<N>/` included; the single file to hand to Excel or
pandas), and one `tradeoff_<experiment>.png` per experiment that produced
trade-off data. Open `reports/report.md` for the summary.
Options: `--results <dir>` and `--out <dir>` if you keep results elsewhere.

## 9. RN-LDP-Synth evidence sweep (offline, fixture scale)

```sh
uv run python -m trajguard.experiments.rnldp_eval
```

Runs the membership-inference and utility evaluation of the RN-LDP-Synth generator
against the committed fixture network — no downloads needed.

**Expected outcome:** finishes in well under a minute (about 7 seconds with the
defaults: ε ∈ {0.5, 2, 8, 80}, 16 shadow models, population 20) and prints a
Markdown table with one row per arm plus a non-private Markov baseline. How to read
the columns:

- **MIA AUC** — how well a membership-inference attacker separates training members
  from non-members: 0.5 is coin-flipping (good for privacy), 1.0 is always right
  (no privacy). Expect values near 0.5 for moderate ε and ≈1.0 at ε = 80, which
  deliberately demonstrates privacy collapse at an absurdly weak setting.
- **TPR@FPR=0.01 / 0.1** — the attacker's hit rate when allowed only 1% / 10% false
  alarms (the stricter, more honest view of the same attack).
- **Cell JSD (bits)** — utility: how much the synthetic data's spatial distribution
  deviates from the real one (0 = identical).
- **Length W1 (m)** — utility: distortion of the trip-length distribution in metres.

Useful flags: `--epsilons 0.5 2` and `--n-shadow 4 --n-pop 8` for a faster run,
`--out sweep.json` to also save the results as JSON. At this fixture scale the
numbers are noisy evidence, not publishable results.

## 9.1 LDPTrace validation inputs: Porto → reference `.dat` (offline, ~6 minutes)

The `ldptrace` generator is validated against the authors' code on the public Porto
taxi data (plan and progress: `docs/NACRT_LDPTRACE_VALIDACIJA.md`). One-time input:
`train.csv` of the Kaggle "Taxi Trajectory Prediction" competition (ECML/PKDD 2015,
1.94 GB), placed at `data/raw/porto/train.csv` and never modified. Then:

```sh
uv run python scripts/porto_to_ldptrace_dat.py data/raw/porto/train.csv data/interim/porto
```

Keeps every trip without `MISSING_DATA`, with at least two points and lying entirely
inside the central-Porto bbox lon −8.64…−8.60, lat 41.14…41.17 (the default;
`--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT` overrides it, `--max-trajectories N` stops
early for a smoke run — 50 000 trips take ~40 s). The bbox was chosen so that the
count lands near the paper's 361 591 "central areas" trajectories; the plan's first
proposal (−8.69…−8.55 × 41.13…41.19) kept 81 % of the file.

**Expected outcome** (measured 3 September 2026: 371 s, well under 1 GB of memory):
the stats are printed as JSON and written to `data/interim/porto/porto_stats.json`:

```
"n_read": 1710670, "n_kept": 367008,
"n_dropped": {"missing_data": 10, "too_short": 36508, "outside_bbox": 1307144},
"n_points": 12136174,
"bbox": [-8.64, 41.140008, -8.600004, 41.169996],
"grid_bbox": [-8.640001, 41.140007, -8.600003, 41.169997]
```

plus `porto.dat` (245 MB — the text format the `ldptrace_dat` dataset loader reads,
one user per trajectory, timestamps 0, 15, 30, … s) and `porto.xz` (48 MB, `lzma` +
`pickle`, what the reference code loads). `grid_bbox` is the point bbox widened by
1e-6 on each side (the reference's own rule); it is the bbox to put into the
cells-mode configuration (PR B2) and into the reference run (PR C) so both sides share
one grid. All three outputs are regenerable caches and stay out of git. The loader has
no map (`native_region = "none"`), so `trajguard run` takes it only in the cells
representation — §9.2.

## 9.2 Membership inference in the cells representation (Porto, ~1 minute)

```sh
uv run trajguard run config/experiments/porto_cells_mia.yaml
uv run trajguard repeat config/experiments/porto_cells_mia.yaml --seeds 1 2 3
```

`dataset.representation: cells` (PR B2 of `docs/NACRT_LDPTRACE_VALIDACIJA.md`) runs the
pipeline without a road network: no `map` and no `map_matching` block, every clean
trajectory becomes its chain of cells on `dataset.grid` (here the paper's 6×6 grid over
`grid_bbox` from §9.1), and the membership attack scores those chains. It is a vertical
slice for the LDPTrace validation: only `membership_inference` is accepted,
`privacy_mechanisms` must be empty, and a generator that needs the network
(`rn_ldp_synth`) is refused before the pipeline; `markov` and `ldptrace` run, the latter
with the grid injected (`bbox`, `n_rows`, `n_cols` — naming them in the arm's params
with other values is a config error). `max_users: 2000` keeps 2 000 trips (every trip is
its own user in the `.dat` loader); delete the key for the whole population.

**Expected outcome** (measured 3 September 2026): the first run takes ~58 s, almost all
of it reading and cleaning the 367 008 trips before the 2 000 are drawn; the pool cache
`data/processed/<hash>/` then holds `clean.parquet`, `chains.parquet` and `meta.json` for
those 2 000 only. Nothing is re-matched here, so `n_rematch_dropped` stays empty in
`results.csv`. Every later run reads the cache in ~3 s per seed; the attack itself takes
0.3 s (`markov`) or 0.7 s (`ldptrace`) per arm. The printed table has one
`membership_inference:synthetic:<arm>` row set per arm with `auc`, `tpr@fpr=0.01` and
`tpr@fpr=0.1`; `tpr@fpr=0.001` is NaN with a warning (it needs 1 000 non-members, the
0.2 test split has 400). Aggregate across seeds 1–3 (`repetitions.csv`):

```
result                                              metric         n      mean  95% CI (repetitions)
membership_inference:synthetic:markov:order=1       auc            3     0.582  [0.558, 0.607]
membership_inference:synthetic:markov:order=1       tpr@fpr=0.1    3     0.166  [0.116, 0.216]
membership_inference:synthetic:ldptrace:epsilon=0.5 auc            3     0.511  [0.471, 0.551]
membership_inference:synthetic:ldptrace:epsilon=0.5 tpr@fpr=0.1    3     0.096  [0.042, 0.149]
membership_inference:synthetic:ldptrace:epsilon=1.0 auc            3     0.498  [0.450, 0.547]
membership_inference:synthetic:ldptrace:epsilon=1.0 tpr@fpr=0.1    3     0.100  [0.081, 0.119]
membership_inference:synthetic:ldptrace:epsilon=1.5 auc            3     0.496  [0.458, 0.535]
membership_inference:synthetic:ldptrace:epsilon=1.5 tpr@fpr=0.1    3     0.110  [0.085, 0.136]
```

Read it against the `markov` ceiling: on a 6×6 grid the chains are short (train chains
1–25 cells, median 5) and widely shared, so even the memorizing baseline scores only
0.58, and the `ldptrace` arms sit at chance for every ε. The public length cap L_k of
`ldptrace` is unstable at this sample size (1 to 7 across seeds and ε; the true maximum
is 25) — the paper works with the whole population. Measured rows and reading:
`docs/HANDOFF.md` §2.3.

## 9.3 LDPTrace validation run: the authors' code vs the `ldptrace` port (Porto, hours)

PR C of `docs/NACRT_LDPTRACE_VALIDACIJA.md`: both implementations synthesize the same
367 008 Porto trips (§9.1) on the same 6×6 grid and are scored with the paper's nine
utility metrics (`evaluation/ldptrace_metrics.py`). Three columns come out — the reference
with its own printed metrics, the reference's synthesis with our metrics, and the port with
our metrics — each as mean and range over seeds 1–5 at ε ∈ {0.5, 1.0, 1.5}. Measured
table and reading: `docs/HANDOFF.md` §2.3.

**One-time setup of the reference code** (kept out of git; `external/` is ignored):

```sh
git clone https://github.com/zealscott/LDPTrace external/LDPTrace     # commit 2d30e41 was used
cd external/LDPTrace && git apply ../../scripts/ldptrace_reference.patch && cd ../..
cp data/interim/porto/porto.xz external/LDPTrace/LDPTrace/data/porto.xz
```

The patch is the only artefact of the reference in this repository: it adds `--seed`
(the code hard-codes 2022 twice) and puts the seed into the synthesis file name so five
seeds do not overwrite each other. Nothing else changes; the reference imports only numpy
and runs in this project's `uv` environment (no numpy 2 fixes were necessary).

**Reference side** — 15 runs, each from `external/LDPTrace/LDPTrace/code/` (the code uses
relative paths), stdout to a log per run; `--multiprocessing` must stay off on Windows
(the script has no `__main__` guard):

```powershell
# from the repository root, PowerShell; one run ≈ 10–23 min, so run this detached
$log = "$PWD\results\ldptrace_validation\reference"; New-Item -ItemType Directory -Force $log | Out-Null
Set-Location external\LDPTrace\LDPTrace\code
foreach ($eps in "0.5", "1.0", "1.5") { foreach ($seed in 1..5) {
  cmd /c "uv run python main.py --dataset porto --grid_num 6 --max_len 0.9 --epsilon $eps --re_syn --seed $seed > `"$log\eps${eps}_seed${seed}.log`" 2>&1"
} }
```

Each run writes `LDPTrace/data/porto/syn_porto_eps_<ε>_max_0.9_grid_6_seed_<s>.pkl`
(a plain pickle of the synthetic trajectories as `(x, y)` points, one point per cell) and
prints `Quantile: <L_k>` plus the nine metrics into the log. Two runs must not start in the
same second (the code creates `log/LDPTrace/<MMDD_HHMMSS>/` without `exist_ok`); the
4 September 2026 run used two detached workers with staggered starts.

**Port side and scoring** — the harness reads the `.dat` directly (no orchestrator cache,
no split), maps points to cells with the reference's closed-interval rule and runs the port
for every (ε, seed); then it scores the reference's saved syntheses with the same metrics
and parses the reference logs:

```sh
uv run python -m trajguard.experiments.ldptrace_eval --dat data/interim/porto/porto.dat \
    --stats data/interim/porto/porto_stats.json --grid 6 --epsilons 0.5 1.0 1.5 \
    --seeds 1 2 3 4 5 --label port --out results/ldptrace_validation/port.json
uv run python -m trajguard.experiments.ldptrace_eval --dat data/interim/porto/porto.dat \
    --stats data/interim/porto/porto_stats.json --grid 6 --epsilons 0.5 1.0 1.5 \
    --seeds 1 2 3 4 5 --label "reference (our metrics)" \
    --score-synthesis "external/LDPTrace/LDPTrace/data/porto/syn_porto_eps_{eps}_max_0.9_grid_6_seed_{seed}.pkl" \
    --out results/ldptrace_validation/reference_ours.json
uv run python -m trajguard.experiments.ldptrace_eval --epsilons 0.5 1.0 1.5 --seeds 1 2 3 4 5 \
    --label "reference (own metrics)" \
    --reference-log "results/ldptrace_validation/reference/eps{eps}_seed{seed}.log" \
    --out results/ldptrace_validation/reference_own.json
uv run python -m trajguard.experiments.ldptrace_eval --compare \
    results/ldptrace_validation/reference_own.json results/ldptrace_validation/reference_ours.json \
    results/ldptrace_validation/port.json
```

`{eps}` and `{seed}` are placeholders the harness fills from `--epsilons` / `--seeds`
(`{eps}` as Python's float repr: `1.0`, exactly as the reference names its files).
`--max-trajectories N` keeps the first N trips of the file for a timing run;
`--save-synthesis DIR` stores the port's synthetic points in the reference's format (the
test suite scores such a file and gets the run's values back to the digit).

**Expected outcome** (measured 4 September 2026): reading the `.dat` takes 80 s
once; the port needs about 4 min per (ε, seed) (fit 24–37 s, synthesis of 367 008 chains
78–134 s, the nine metrics 107–137 s; 15 runs in 60 min), the reference 10–23 min per run
(point → cell conversion 1.5 min, OUE reports 2 min, synthesis 3 min, its own metrics
about 10 min, of which the diameter 6 min; 15 runs in 2 h 16 min on two workers), and
scoring its 15 syntheses with our metrics about 27 min. Each command
prints a table with one row per (ε, metric) and `mean [min; max]` over the seeds; the
`--compare` table is the one recorded in `docs/HANDOFF.md` §2.3. Output stays out of git
(`results/`). The grid check that precedes any measurement — the reference's
`trajectory_point2grid` and the harness give the same chain for the first 20 000 trips
once the closed-interval cell rule is used — is recorded in
`docs/NACRT_LDPTRACE_VALIDACIJA.md` §12.5.

## 10. How caching works (read before re-running with changed data)

The expensive pre-attack pipeline (clean + match + split) is cached under
`data/processed/<hash>/`. The hash covers the config values, the built map's
timestamp, and the dataset **path** — but **not the dataset's file contents**.
In the cells representation (§9.2) an entry holds `clean.parquet`, `chains.parquet` and
`meta.json` instead of the matched table, and the hash additionally covers
`dataset.representation` and `dataset.grid` (rows, columns, bbox) — only there, so the
keys of existing segments caches do not change.

**In practice:** if you add, remove, or change files under `data/raw/geolife` and
re-run, the orchestrator will silently reuse the old cached pool and your results
will not change. After any change to the raw data, clear the cache:

```sh
find data/processed -mindepth 1 ! -name '.gitkeep' -delete
```

Everything under `data/interim`, `data/processed`, `data/protected`,
`data/synthetic`, `results/` and `reports/` is regenerable and safe to delete.
`data/raw/` is your immutable input — the pipeline never writes there, and neither
should you (except to drop in downloaded datasets).

## 11. Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `FileNotFoundError: no built map at maps/beijing; run: python -m trajguard.maps.build config/maps.yaml --region beijing` | The road network has not been built. Run exactly that command (§2.1). |
| Map build fails with a network/HTTP error or hangs | The build downloads from OpenStreetMap servers and needs internet. Retry later; if a retry keeps failing immediately, delete the `cache/` directory (a corrupted download cache) and try again. |
| `ConsistencyError: map.region 'ljubljana' != dataset 'geolife' native_region 'beijing'; refusing to run (design T1)` | Deliberate safety guard: the map and dataset must cover the same city, otherwise matching would silently produce garbage. Fix the `map.region` in your config; Geolife requires `beijing`. |
| Every metric in the table is `nan` | No trajectories reached the attack. Open `results/<experiment>/run.json` and check `n_matched`. If it is 0, either the dataset layout is wrong (must be `data/raw/geolife/Data/<user>/Trajectory/*.plt`, §2.2) or you are hitting a stale cache from a run before the data existed — clear it (§10) and re-run. |
| You changed the raw data but the results are identical | Stale cache — the cache key does not include file contents (§10). Clear `data/processed` and re-run. |
| A protected arm (small ε) reports 0/NaN accuracy while other arms look fine | Not a bug: strong noise destroyed the trajectories during re-matching. Check `n_rematch_dropped` in `run.json` (§7). |
| `FileNotFoundError: no run.json found under results/*/ — run an experiment first (trajguard run <config>)` | `trajguard report` found no results to aggregate. Run at least one experiment first, or point it at the right directory with `--results`. |
| Console spam: `Searching closeby nodes with linear search, use an index and set max_dist` | Harmless log notice from the matching library; it does not affect results. The notebook and the §4.2 script silence it with `logging.disable(logging.WARNING)`. |
| `jupyter: command not found`, or Jupyter Lab missing | Always prefix with `uv run`; for the browser interface use `uv run --with jupyterlab jupyter lab …` (§3). |
| A real-Geolife run takes very long | Expected on the first pass over all 182 users (pairwise trajectory comparison). Use a user subset (§2.2); repeat runs are much faster thanks to the cache. |
| `StopIteration` from the §4.2 script | The `TRAJ_ID` does not exist under the loader's root. Ids have the form `geolife/<user folder>/<plt filename without extension>`; copy one from the printed "available ids" line. |
