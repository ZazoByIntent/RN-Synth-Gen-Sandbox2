# Running trajguard — a practical guide

Every way to run this project, with the exact commands, what to expect, and what to
do when something goes wrong. All commands are run from the repository root. Every
command and error message in this guide was executed and captured on a clean clone
of `main` (July 2026); numbers marked "fixture" come from the committed test data.

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

**Expected outcome:** `177 passed` in roughly 20 seconds. The suite runs entirely on
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
A low score (below the 0.6 threshold used by experiments) with sparse blue dots far
from any road means the trajectory would be dropped in a real run.

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
filters, resampling) → map-matching (trajectories below match score 0.6 are
dropped) → one-time user split → reidentification attack, where the attacker knows
k ∈ {3, 5, 10} points of each target and searches for the nearest matching
trajectory.

**Expected outcome:**

- A console table: one row per (arm × known-points × metric) with the value and a
  95% bootstrap confidence interval. Metrics: `top1_acc` / `top5_acc` (how often the
  true person is the attacker's first / among the top-five guesses) and
  `linkage_rate`.
- `results/geolife_reid_baseline/` containing `metrics.csv` (long-form metrics),
  `matrix.csv` (the risk-matrix slice), and `run.json` (run metadata: how many
  trajectories survived each stage — your first stop when numbers look odd).
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
directory additionally gets `tradeoff.png` (attack accuracy versus utility damage),
and utility metrics (`cell_js_divergence`, `length_dist_error`) quantify how much
the noise distorted the data.

**Expected surprise that is not a bug:** at ε = 0.1 the noise is ~2 km per point, so
most or all protected trajectories fail re-matching and the arm reports zero or NaN
attack accuracy — "protection by destroying the release". Verified on fixture data:
the ε = 0.1 and ε = 1.0 arms dropped all 8 trajectories (`n_rematch_dropped = 8` in
`run.json`), ε = 10.0 kept 4. On real, denser Geolife data more will survive, but
the pattern (stronger noise → fewer survivors) is by design; the survivor counts per
arm are always recorded in `run.json`.

## 8. Aggregate risk report

```sh
uv run trajguard report
```

Aggregates everything under `results/` into `reports/`.

**Expected outcome:** the line `report: reports/report.md`, plus `metrics_long.csv`,
`metrics_long.parquet`, `risk_matrix.csv`, and one `tradeoff_<experiment>.png` per
experiment that produced trade-off data. Open `reports/report.md` for the summary.
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

## 10. How caching works (read before re-running with changed data)

The expensive pre-attack pipeline (clean + match + split) is cached under
`data/processed/<hash>/`. The hash covers the config values, the built map's
timestamp, and the dataset **path** — but **not the dataset's file contents**.

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
