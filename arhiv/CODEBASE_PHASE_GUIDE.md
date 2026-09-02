# Trajguard Codebase Guide — Phase by Phase

> This document explains the entire trajguard codebase, built incrementally
> across eight development phases (P0–P7). It is written for someone with
> no prior knowledge of the project, privacy research, or location data.

## How to read this document

Trajguard is a research tool that answers one question: **how well do privacy
protections for location data actually work?** Location data here means GPS
trajectories — sequences of "I was at this latitude and longitude at this time"
points recorded by a phone or a navigation device (GPS stands for Global
Positioning System, the satellite network devices use to determine where they
are). Such traces are surprisingly revealing: even a handful of points can
identify a specific person, expose where they live and work, or betray that
their data was used to train a statistical model.

The tool works like a crash-test laboratory. It takes movement data, applies a
**protection mechanism** (something that distorts or hides the data, for example
adding random noise to every point), and then runs **attacks** against the
protected data — programs that play the role of an adversary trying to undo the
protection. By measuring how often each attack succeeds and how much the
protection damaged the usefulness of the data, the tool produces an evidence-based
trade-off: this much privacy costs this much data quality.

The code was built in phases, each one a working, tested slice:

- **Phase 0** laid down the skeleton: folder structure, tooling, data schemas,
  and the "contracts" every future component must follow.
- **Phases 1–4** built one complete path from raw GPS files to a first attack
  result with statistical error bars (the project calls this the *vertical
  slice*: get one thing working end to end before adding breadth).
- **Phases 5–6.5** added breadth: a real protection mechanism, data-quality
  measurements, a synthetic-data generator, and three more attack families.
- **Phase 7** added automated reporting that turns raw result files into a
  readable risk report.

Each phase section below follows the same pattern: the goal in plain language,
every file that was added or changed with an explanation of what it does and why
it exists, and a closing paragraph on how the pieces connect.

## Pre-phase: Initial setup

Before any code was written, two commits set the stage.

- `README.md` — the very first commit contained only a one-line README with the
  repository name. It existed purely so the repository was not empty.
- `CLAUDE.md` — the second commit uploaded the project "constitution": a short
  rulebook that the AI coding assistant reads at the start of every working
  session. It fixes the golden rules of the project — work in vertical slices,
  never write into the raw-data folder, make every random step reproducible via
  an explicit seed (a starting number that makes "random" results repeatable),
  and always prove that code works by showing a passing test.
- `docs/IMPLEMENTATION_PLAN.md` — the phased build plan, written in Slovenian.
  It defines phases P0 through P7, what each phase must produce, and a
  "definition of done" for each — the checklist that must pass before moving on.
  This document is the reason the commit history is so orderly.
- `docs/PROMPTS.md` — prepared instructions (one per phase, also in Slovenian
  with English prompt text) that the author pasted into the AI assistant to
  start each phase. It is documentation of *how* the code was built, not code
  itself.
- `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` — the full technical design
  document in Slovenian (~550 lines). It specifies the architecture: which
  modules exist, which data entities flow between them, which attacks and
  protections to implement, and how experiments are configured. Code comments
  throughout the project cite its section numbers (for example "design §6.1").

Together these files mean that every later commit can be checked against a
written plan. Nothing in the source tree yet — that starts with Phase 0.

## Phase 0 — Project skeleton and building blocks

*Commit: `180f0e1` "P0: bootstrap skeleton — tooling, datamodel, registry, seven ABCs"*

### Goal

Create the empty but well-organized shell of the project: the folder layout, the
development tools, the shared data structures every later component will pass
around, and — most importantly — the seven **interfaces** that all future
components must implement. An interface (in Python, an "abstract base class")
is like a wall socket specification: it says *what shape* a plug must have (which
methods a class must provide) without saying anything about what is behind it.
Phase 0 deliberately contains **no domain logic** — no maps, no data, no attacks
— only the sockets that later phases will plug things into.

### Files added

- `pyproject.toml` — the project's identity card. It names the package
  (`trajguard`), lists the external libraries it needs, and configures the
  development tools: `ruff` (a linter — a program that flags sloppy or
  inconsistent code), `mypy` (a type checker — a program that verifies the
  declared data types are used consistently), and `pytest` (the test runner).
  It also registers the `trajguard` command-line program that Phase 4 will fill
  in. Without this file, the project could not be installed or checked at all.

- `uv.lock` — a lock file produced by `uv`, the tool that manages the project's
  Python environment. It pins the exact version of every library the project
  uses, so that anyone (or any machine) recreating the environment gets
  byte-for-byte identical dependencies. This is one pillar of reproducibility:
  results cannot silently change because a library updated.

- `.github/workflows/ci.yml` — the continuous-integration recipe (continuous
  integration means a robot re-checks the whole project on every change pushed
  to GitHub). It runs the linter, the code formatter check, the type checker,
  and the test suite. If any of these fail, the change is flagged. This file is
  the project's automatic quality gate.

- `.gitignore` — tells the version-control system which files never to record:
  caches, virtual environments, downloaded data. It keeps the repository small
  and prevents accidentally committing gigabytes of GPS data.

- `README.md` (rewritten) — now describes what the project is and shows the four
  commands a developer runs: install the environment, lint, type-check, test.

- Folder placeholders (`data/raw/.gitkeep`, `data/interim/.gitkeep`,
  `data/processed/.gitkeep`, `data/protected/.gitkeep`, `data/synthetic/.gitkeep`,
  `maps/.gitkeep`, `config/defaults/.gitkeep`, `config/experiments/.gitkeep`,
  `tests/fixtures/.gitkeep`) — empty marker files that force the version-control
  system to keep otherwise-empty folders. They encode the project's data
  discipline in the folder names themselves: `data/raw/` holds original inputs
  and is treated as read-only forever; the other data folders hold regenerable
  intermediate products that can always be deleted and rebuilt.

- `src/trajguard/__init__.py` — the top-level package marker: a two-line file
  that makes `import trajguard` work and records the version number.

- `src/trajguard/datamodel/entities.py` — the **shared vocabulary of the whole
  system**. It defines nine small record types ("frozen dataclasses" — Python
  structures whose fields cannot be modified after creation, which prevents one
  component from accidentally corrupting data another component relies on):
  - `Map` — bookkeeping about one built road network: which region, which
    bounding box (the rectangle of latitude/longitude it covers), which
    coordinate reference system (the mathematical projection that turns
    latitude/longitude into flat x/y coordinates measured in meters), and where
    its files live on disk.
  - `RawTrajectory` — one trip exactly as parsed from the source files, before
    any cleaning: points, owner identifier, timestamps, source file.
  - `CleanTrajectory` — one trip after cleaning: filtered points plus computed
    statistics (length in meters, duration, average speed) and a record of what
    the cleaning did. It also carries a `split` label (see Phase 3).
  - `MatchedTrajectory` — one trip after being snapped onto roads: the sequence
    of road-segment numbers it traveled, the snapped coordinates, and a quality
    score for the match.
  - `ProtectedTrajectory` — the output of one privacy mechanism applied to one
    trip, with the mechanism's name, its parameters' fingerprint, and the
    formal guarantee it claims.
  - `SyntheticTrajectory` — one artificial trip sampled from a trained
    generator (Phase 6), with a record of which data it was trained on.
  - `AttackResult` — everything one attack run produced: predictions, scores,
    what it targeted, how long it took.
  - `MetricValue` — one named number computed from an attack result, with an
    optional confidence interval (a statistical range expressing how uncertain
    the number is).
  - `ExperimentConfig` — identifying metadata of one experiment run (its
    identifier, configuration fingerprint, seed, code version).
  It also defines `Split`, the fixed list of dataset roles: `train`, `test`,
  `shadow`, `attack`. Every other module imports these types; without this file
  each module would invent its own incompatible shapes for the same concepts,
  and data could not flow between phases.

- `src/trajguard/datamodel/__init__.py` — re-exports all the entity types so the
  rest of the code can write `from trajguard.datamodel import CleanTrajectory`
  without knowing the internal file layout.

- `src/trajguard/experiments/registry.py` — the **phone book** of the system. It
  provides a `@register(kind, name)` decorator (a Python annotation placed above
  a class) and a `get(kind, name)` lookup. A class decorated with
  `@register("attack", "reidentification")` becomes findable by that name at run
  time. This is what lets an experiment configuration file say `matcher: leuven`
  as plain text and have the right class picked up automatically. The registry
  also validates registrations: it refuses unknown kinds, refuses a class that
  does not implement the matching interface, and refuses duplicate names. The
  seven kinds are `map_source`, `dataset`, `matcher`, `mechanism`, `generator`,
  `attack`, and `metric`.

- The seven interface files (one per subsystem). Each declares one abstract base
  class — a contract with the methods every implementation must provide:
  - `src/trajguard/maps/base.py` — `MapSource`: anything that can `load()` a
    road network for one geographic region and report its target coordinate
    system.
  - `src/trajguard/datasets/base.py` — `DatasetLoader`: anything that can read
    one GPS collection and yield `RawTrajectory` records. It must also declare
    its `native_region` (for example "beijing"), which a later safety check
    uses to prevent pairing data with the wrong map.
  - `src/trajguard/matching/base.py` — `MapMatcher`: anything that can snap a
    cleaned trajectory onto road segments.
  - `src/trajguard/privacy/base.py` — `PrivacyMechanism`: anything that can
    `apply()` a protective transformation to one trajectory and account for its
    "privacy budget" (a running total of how much formal privacy guarantee has
    been consumed).
  - `src/trajguard/synthesis/base.py` — `SyntheticGenerator`: anything that can
    `fit()` on training trajectories and `generate()` artificial ones.
  - `src/trajguard/attacks/base.py` — `Attack`: anything that can be
    `configure()`d with attacker knowledge and `run()` against target data,
    returning an `AttackResult`. Each attack also declares its `target_scope` —
    whether it makes sense against raw, protected, or synthetic data.
  - `src/trajguard/evaluation/base.py` — `Metric`: anything that can turn an
    attack result into named numbers.
  If one of these files were missing, that whole subsystem would have no
  contract, and the registry could not verify that a plugged-in class actually
  fits the socket.

- `src/trajguard/representation/__init__.py` — at this stage only a placeholder
  saying "a `TrajectoryView` type will exist here" (the real class lands in
  Phase 3). It reserves the concept of *views* — the idea that one trajectory
  can be looked at as GPS points, as road segments, or as grid cells.

- `src/trajguard/reporting/__init__.py`, plus empty `__init__.py` markers for
  `attacks/`, `datasets/`, `evaluation/`, `experiments/`, `maps/`, `matching/`,
  `privacy/`, `synthesis/` — package markers so each subsystem folder is
  importable. Deliberately empty: the plan forbids speculative scaffolding.

- `tests/test_registry.py` — the first test file. It verifies the phone book:
  registering a class and getting it back works; registering the same name twice
  fails loudly; registering under an unknown kind fails; registering a class
  under the wrong kind (an attack pretending to be a metric) fails; and every
  one of the seven abstract classes refuses to be instantiated directly. It also
  snapshots and restores the registry around each test so tests cannot pollute
  one another.

- `tests/conftest.py` — at this point a single-line placeholder where shared
  test fixtures (reusable test ingredients) will accumulate.

### How it fits together

Phase 0 is pure architecture. The datamodel defines *what* flows through the
system, the seven abstract classes define *who* is allowed to process it, and
the registry defines *how* components are found by name at run time. The
tooling (`pyproject.toml`, the lock file, the continuous-integration workflow)
guarantees that every later phase is automatically linted, type-checked, and
tested. Nothing runs yet, but every later phase plugs into exactly these
sockets — which is why the codebase stays orderly as it grows.

## Phase 1 — Loading real-world data and maps

*Commit: `59417e0` "P1: OSM map source, Geolife loader, trajectory cleaning"*

### Goal

Give the system its two raw ingredients: a **road network** and **GPS
trajectories**. The road network comes from OpenStreetMap (a free, crowd-sourced
world map, abbreviated OSM). The trajectories come from Geolife, a well-known
research dataset of GPS traces recorded by volunteers in Beijing, published by
Microsoft Research. Phase 1 also adds **cleaning**: real GPS data contains
glitches (impossible jumps, duplicated timestamps, uselessly short recordings),
and attacks must not be run on garbage.

### Files added

- `src/trajguard/maps/base.py` (extended) — gains the `RoadNetwork` container:
  one built road network held in memory as a graph (a mathematical structure of
  nodes = intersections and edges = road segments connecting them) plus two
  tables listing every node and every edge with their coordinates and lengths.
  Everything downstream — map matching, attacks — works against this one
  container, so no other module ever needs to know how maps are stored on disk.

- `src/trajguard/maps/osm.py` — `OSMMapSource`, the first real plug for the
  `MapSource` socket. Its `build()` method downloads the road network inside a
  configured bounding box from OpenStreetMap (using the OSMnx library), converts
  the coordinates from latitude/longitude degrees into a flat, meter-based
  projection (so that distances can be computed with ordinary geometry), and
  saves three artifacts per region: the graph itself, node/edge tables in
  Parquet format (a compact, typed, columnar file format widely used in data
  work), and a small `meta.json` with provenance (region, bounding box,
  projection, download timestamp). Its `load()` method reads those artifacts
  back **without touching the internet** — important because tests and
  experiment runs must be reproducible offline. If no built map exists, `load()`
  fails with a message telling the user exactly which command to run.

- `src/trajguard/maps/build.py` — a small command-line helper
  (`python -m trajguard.maps.build config/maps.yaml`) that reads the region
  definitions from a configuration file and builds each requested network. It
  exists so that the expensive, internet-touching download step is an explicit,
  one-time, human-invoked action — never something a test or an experiment does
  implicitly.

- `config/maps.yaml` — the region catalogue. Three entries: `beijing` (the map
  Geolife data belongs to), `ljubljana` (reserved for future synthetic-data
  work, deliberately never used with Geolife), and `beijing_fixture` (a tiny
  Beijing fragment used to generate the committed test map; flagged so default
  builds skip it). Each entry has a `bbox` (the min/max longitude and latitude
  rectangle to download) and a `crs` (the target coordinate reference system,
  for example `EPSG:32650`, the standard meter-based projection for Beijing).

- `src/trajguard/datasets/geolife.py` — `GeolifeLoader`, the first plug for the
  `DatasetLoader` socket. Geolife ships as thousands of small `.plt` text files
  organized as `Data/<user>/Trajectory/<timestamp>.plt`, each with six header
  lines followed by one line per GPS point. The loader walks that tree, parses
  each file into a `RawTrajectory` (silently skipping malformed lines), converts
  the date and time text into Unix timestamps (seconds since 1970, the standard
  machine representation of time), and drops the altitude column because no
  planned attack uses it. It declares `native_region = "beijing"`, which the
  Phase 4 safety check will compare against the configured map.

- `src/trajguard/datasets/cleaning.py` — the data scrubber. `CleaningConfig`
  holds four thresholds, and `clean()` applies them to one raw trajectory:
  (1) drop any point that would imply a speed above `max_speed_kmh` (default
  200 km/h) since a car does not teleport — this also removes points whose
  timestamps go backwards; (2) thin the points so consecutive ones are at least
  `resample_s` seconds apart (default 5), without inventing any new positions;
  (3) reject the whole trajectory if fewer than `min_points` (20) remain or if
  it is shorter than `min_length_m` (500 meters). It records what it did in
  `cleaning_flags`, and computes the summary statistics (bounding box, length,
  duration, mean speed) stored on the resulting `CleanTrajectory`. It also
  defines `haversine_m()`, the standard formula for the distance in meters
  between two latitude/longitude points on the Earth's surface, which several
  later modules reuse.

- `tests/fixtures/geolife/…` (20 `.plt` files) and
  `tests/fixtures/geolife/README.md` — a **synthetic stand-in for Geolife**.
  The real dataset's license does not clearly allow redistribution, so the
  project generated 20 fake trajectories (5 users × 4 trips) in the exact
  Geolife file format, placed inside the tiny test-map area. Crucially, the
  fixtures contain *planted defects* that the cleaning tests assert on: one file
  with three impossible speed spikes, one with only 5 points, one only ~70
  meters long, and one fully deterministic L-shaped trip whose every statistic
  is known in advance. The README documents each planted defect in a table.

- `tests/fixtures/maps/beijing_fixture/…` (`graph.graphml`, `nodes.parquet`,
  `edges.parquet`, `meta.json`) — a small committed road network (183 nodes,
  388 edges) covering the same tiny area as the fixtures. It was built once
  with the real `build()` code and committed, so every test can load a genuine
  road network **without any internet access**.

- `tests/conftest.py` (extended) — shared fixtures pointing tests at the
  committed data: `geolife_root` (the fake Geolife tree) and `fixture_maps_dir`
  (the committed map).

- `tests/test_geolife.py` — verifies the loader: it is registered under the
  name `geolife`, yields exactly 20 trajectories for 5 users, parses the known
  deterministic file to the exact expected coordinates and timestamps, skips
  header lines, and produces strictly increasing timestamps.

- `tests/test_cleaning.py` — verifies the scrubber against the planted defects:
  the three speed spikes are removed (and counted in the flags), the too-short
  and too-few-points files are rejected, *only* the planted defects are
  rejected, thinning respects the minimum spacing, the known L-shaped trip
  yields the expected length/duration/speed, and cleaning is deterministic.

- `tests/test_maps.py` — verifies `OSMMapSource.load()` round-trips the
  committed fixture network: tables match the graph, the expected columns
  exist, projected coordinates are in meters while the preserved
  latitude/longitude copies stay in degrees, and a missing map produces the
  helpful error message.

- `pyproject.toml` / `uv.lock` (updated) — the new dependencies arrive here
  (OSMnx, GeoPandas, NetworkX, PyArrow, pyproj, PyYAML), each needed by the
  map or dataset code above.

### How it fits together

Phase 1 fills the first two sockets defined in Phase 0: `OSMMapSource` plugs
into `MapSource`, and `GeolifeLoader` plugs into `DatasetLoader`; both register
themselves in the phone book. The cleaning module sits between the loader and
everything else, turning `RawTrajectory` records into trustworthy
`CleanTrajectory` records. The committed test fixtures are the quiet hero of
this phase: because a small real map and format-faithful fake trajectories live
inside the repository, every subsequent phase can be tested quickly and offline.

## Phase 2 — Matching GPS points to roads

*Commit: `e70a410` "P2: Leuven map matcher, quality filter, sanity notebook"*

### Goal

Snap noisy GPS dots onto the roads people actually traveled. A map matcher is
like GPS navigation in reverse — instead of telling you where to go, it figures
out which roads you actually drove on based on your recorded GPS dots. This
matters because several attacks compare *routes*, not raw dots, and because a
sequence of road-segment numbers is a much cleaner representation than jittery
coordinates. Phase 2 also introduces a quality score, so trajectories that
cannot be matched convincingly are discarded rather than polluting experiments.

### Files added

- `src/trajguard/matching/leuven.py` — `LeuvenMapMatcher`, the first plug for
  the `MapMatcher` socket, built on the `leuvenmapmatching` library. Internally
  it uses a hidden Markov model (a statistical technique that finds the most
  plausible sequence of hidden states — here, road segments — behind a sequence
  of noisy observations — here, GPS points). For each trajectory it returns a
  `MatchedTrajectory` with the road-segment sequence, the snapped coordinates,
  and two quality numbers: `frac_matched` (what fraction of the input points
  found a road) and `match_score`, a deliberately matcher-independent formula —
  the fraction matched, discounted by how far the GPS points sat from the
  matched road — so a different matcher library could be swapped in later and
  produce comparable scores. The file also handles several subtle realities:
  it caches the converted network per `RoadNetwork` object (building the
  matcher's internal map is expensive), it collapses parallel roads between the
  same two intersections onto the shortest one (the library cannot represent
  parallel edges), and it trims artificial edges the algorithm sometimes adds
  before the first or after the last real observation.

- `src/trajguard/matching/base.py` (extended) — gains `match_many()`, a small
  matcher-agnostic helper that matches a whole list of trajectories and drops
  every one whose `match_score` falls below a configured threshold, returning
  both the survivors and the count of dropped ones. It lives in the base module
  (not in the Leuven file) because the filtering rule belongs to the benchmark,
  not to any particular matching library.

- `notebooks/01_matching_sanity.ipynb` — a Jupyter notebook (an interactive
  document mixing code and plots) that draws 8–9 matched trajectories over the
  fixture road network for visual inspection. The design document insists on
  eyeballing matcher output before trusting it at scale; this notebook is that
  ritual, kept runnable entirely offline from the committed fixtures. One
  off-road "random walk" trajectory is included as a negative control — it
  should visibly fail.

- `tests/fixtures/geolife_onroad/…` (8 `.plt` files) and
  `tests/fixtures/geolife_onroad/README.md` — a second synthetic fixture set,
  this time **following actual streets**: each trajectory is a shortest path
  through the committed fixture graph, sampled every ~25 meters with mild
  artificial GPS noise. The README pins down each route (start node, end node,
  edge count, length). These exist because the Phase 1 random-walk fixtures do
  not follow roads and therefore cannot be map-matched; the matching tests need
  trajectories whose *correct answer is known*.

- `tests/test_matching.py` — the matcher's proof. It verifies that one
  documented route produces exactly the expected sequence of edge numbers, that
  the sequence is contiguous in the graph (each edge ends where the next
  begins), that all on-road fixtures match fully with small offsets and high
  scores, that timestamps survive matching unchanged, and — the negative
  control — that the off-road walk scores below the 0.6 threshold and is
  dropped by `match_many()`.

- `tests/conftest.py` (extended) — adds `onroad_root` and a session-wide
  `fixture_network` fixture that loads the committed road network once for the
  whole test run (loading it per test would be wastefully slow).

- `pyproject.toml` / `uv.lock` (updated) — adds `leuvenmapmatching` and the
  notebook tooling.

### How it fits together

Phase 2 completes the data-preparation chain: raw files (Phase 1 loader) →
cleaned points (Phase 1 cleaner) → road-segment sequences (this phase). The
`MatchedTrajectory` records produced here are exactly what the Phase 4
re-identification attack will compare, and the `match_score` threshold gives the
pipeline a principled way to refuse unreliable inputs. The on-road fixtures and
the sanity notebook establish trust: the matcher is not a black box, because a
route with a known answer is pinned in a test and humans can look at pictures.

## Phase 3 — Splitting data and preparing for experiments

*Commit: `e201403` "P3: by-user split, trajectory views, NoProtection baseline"*

### Goal

Prepare the experimental furniture that fair privacy testing requires. Three
things: (1) divide the users into non-overlapping groups so that, for example,
data used to *train* a generator is never also used to *attack* it (that would
be cheating in the attacker's favor or against it); (2) create a uniform way to
look at one trajectory in different representations (GPS points, road segments,
grid cells); and (3) implement the simplest possible "protection" — none at all
— which serves as the upper bound of risk that every real protection is
compared against.

### Files added

- `src/trajguard/datasets/split.py` — `split_by_user()` assigns every **user**
  (and therefore all of that user's trajectories) to exactly one of the four
  roles: `train` (for fitting generators), `test` (for held-out evaluation),
  `shadow` (for the attacker's own practice models, used by the Phase 6
  membership attack), and `attack` (the targets). Splitting by user rather than
  by trajectory is the whole point: if one person's trips landed in both
  `train` and `attack`, a membership-inference experiment would be meaningless.
  The assignment is deterministic in the seed, independent of the input order,
  never mutates its inputs (it returns fresh copies with the `split` field
  filled in), and uses the "largest remainder" method so the group sizes add up
  exactly even when fractions of users do not divide evenly.

- `src/trajguard/representation/views.py` — two classes. `Grid` divides a
  bounding box into `n_rows × n_cols` rectangular cells and can say which cell
  any point falls into (points outside the box clamp to the border cells rather
  than crashing). `TrajectoryView` wraps a clean and/or matched form of one
  trajectory and offers uniform accessors: `as_gps()` (latitude/longitude/time
  triples), `as_segments()` (the matched edge-number sequence), and
  `as_cells(grid)` (one grid-cell index per point). Two more views —
  `as_graph_path()` and `as_poi_visits()` — deliberately raise
  `NotImplementedError`: they are documented hooks for future work, not
  scaffolding. Each accessor fails with a clear message when the underlying
  form was not provided. This class exists so that protections and generators
  can say "give me the GPS view" or "give me the segment view" without caring
  how the trajectory is stored.

- `src/trajguard/representation/__init__.py` (rewritten) — the Phase 0
  placeholder is replaced by real exports of `Grid` and `TrajectoryView`.

- `src/trajguard/privacy/base.py` (extended) — gains `params_hash()`, a helper
  that turns a mechanism's parameter dictionary into a short, stable
  fingerprint. Fingerprints like this are how the project versions everything:
  two runs with identical parameters produce identical hashes and can share
  cached results; any parameter change produces a new hash.

- `src/trajguard/privacy/none.py` — `NoProtection`, the first plug for the
  `PrivacyMechanism` socket. It returns the GPS view completely unchanged,
  declares `guarantee = "none"`, and spends no privacy budget. It looks
  trivial, but it is scientifically essential: it is the control group. Every
  attack's success rate on unprotected data is the baseline against which every
  real mechanism is judged.

- `tests/test_split.py` — verifies the splitter on the 26 fixture trajectories
  (7 users): same seed gives the same split, different seeds differ, input
  order does not matter, no user appears in both `train` and `attack`, group
  sizes follow the largest-remainder arithmetic exactly, inputs are not
  mutated, and malformed fraction dictionaries are rejected loudly.

- `tests/test_views.py` — verifies the views and the baseline mechanism: each
  accessor returns the expected shape, grid cell arithmetic is exact at
  corners and boundaries (including the clamping), missing forms raise clear
  errors, the future hooks raise `NotImplementedError`, and `NoProtection`
  passes data through unchanged with a deterministic, parameter-sensitive
  fingerprint.

### How it fits together

Phase 3 is the connective tissue between data preparation (Phases 1–2) and
experimentation (Phase 4 onward). The split gives every trajectory a role;
the views give every downstream component a single, uniform way to consume a
trajectory; and `NoProtection` gives experiments their indispensable "what if
we did nothing" arm. Note the discipline: the `split` field was already
declared on `CleanTrajectory` in Phase 0, and `params_hash` lands exactly when
the first mechanism needs it — nothing was built before its time.

## Phase 4 — The first privacy attack and experiment runner

*Commits: `7ffc735` "P4: reidentification attack, metrics+CI, orchestrator, CLI",
`e91c973` "P4 review fixes", `5da6f83` "Apply ruff format"*

### Goal

Close the vertical slice: with one command, go from raw GPS files all the way
to an attack-success number with statistical error bars. This phase delivers
the first attack (re-identification — linking an "anonymous" trajectory back to
the person it belongs to), the first metrics, the **orchestrator** (the
conductor that reads an experiment description file and runs every pipeline
step in order), and the `trajguard` command-line program.

### Files added or changed

- `src/trajguard/attacks/base.py` (extended) — gains `BackgroundKnowledge`, a
  small record describing what the attacker is assumed to know: how many points
  of the target trip they observed (`known_points`), which distance measure
  they use to compare trips, and a seed for any randomness. Modeling attacker
  knowledge explicitly is standard practice in privacy research — an attack
  result is meaningless without stating what the attacker knew.

- `src/trajguard/attacks/reidentification.py` — `ReidentificationAttack`, the
  first plug for the `Attack` socket, modeled on the famous 2013 result by
  de Montjoye and colleagues that four spatio-temporal points suffice to
  identify most people. The scenario: the attacker has seen a few points of
  someone's trip (the *probe*) and searches a database of trajectories with
  known owners (the *gallery*) for the closest match. Concretely, for every
  probe the attack takes `known_points` evenly spaced points, computes the
  Dynamic Time Warping distance (a measure of how similar two point sequences
  are even when they move at different speeds, abbreviated DTW) to every
  gallery trajectory except the probe itself, keeps each gallery user's best
  distance, and returns a `Ranking` of users from nearest to farthest. A probe
  is only attempted for users with at least two trajectories (otherwise there
  is nothing in the gallery to link to). The metric layer then reads off
  whether the true owner ranked first.

- `src/trajguard/evaluation/metrics.py` — the first plugs for the `Metric`
  socket, plus the statistics machinery. `TopKAccuracy` asks "was the true
  owner among the attacker's top k guesses?"; `LinkageRate` asks "was the very
  first guess correct?". Both inherit from `SampledMetric`, which frames a
  metric as the average of per-probe 0-or-1 outcomes — the shape needed for
  `bootstrap_ci()`, which computes a bootstrap confidence interval (a
  statistical technique that resamples the outcomes many times, with
  replacement, to estimate a range the true value plausibly lies in). The
  `evaluate()` helper packages each metric's point value and interval into
  `MetricValue` records. Without this file, attack output would be a bare
  number with no honesty about its uncertainty on a small sample.

- `src/trajguard/experiments/orchestrator.py` — the largest and most important
  file in the project: the conductor. It does four jobs. **First**, it parses
  and validates the experiment configuration file (written in YAML, a
  human-friendly text format for structured settings) into a fully-typed
  `RunConfig`, rejecting anything it does not understand — a misspelled metric,
  an unsupported split scheme, an unknown export format — with a message naming
  the exact offending key. This "loud validation" was hardened in the review
  commit: silence is how wrong results get published. **Second**, it enforces
  safety rules before any expensive work: the configured map region must equal
  the dataset's native region (a `ConsistencyError` stops Geolife from being
  attacked on a Ljubljana map), and no output or cache directory may point
  inside the immutable `data/raw/`. **Third**, it runs the pipeline: load the
  road network, load and clean the trajectories, split them by user, map-match
  them, apply each configured mechanism, run each configured attack at each
  knowledge level, and evaluate the metrics. **Fourth**, it caches and records:
  the matched pool is written to `data/processed/<hash>/` as Parquet plus a
  `meta.json` sidecar, keyed by a fingerprint of every setting that influenced
  it, so re-running an experiment skips straight to the attack; and every run
  writes `metrics.csv` and a `run.json` with full provenance (configuration
  fingerprint, code version, seed, split sizes, runtime).

- `src/trajguard/experiments/builtins.py` — a deceptively small but essential
  file. The registry only knows about a class once the file defining it has
  been imported, so this module simply imports every first-party
  implementation, triggering all the `@register` decorators. The orchestrator
  imports this one module and thereby gains access to every loader, matcher,
  mechanism, attack, and metric by name. Without it, `registry.get()` would
  find nothing.

- `src/trajguard/experiments/cli.py` — the command-line entry point behind the
  `trajguard` command declared in `pyproject.toml`. `trajguard run <config>`
  loads the configuration, runs the experiment, and prints a neatly aligned
  table of every metric with its confidence interval. It exists so the entire
  pipeline is reachable with one typed command — the Phase 4 definition of
  done.

- `config/experiments/geolife_reid_baseline.yaml` — the first real experiment
  description. Reading it top to bottom: `experiment` names the run and fixes
  the master `seed`; `map` says which road network to use (source `osm`,
  region `beijing`, the bounding box and projection); `dataset` points at the
  Geolife folder; `cleaning` sets the four scrubbing thresholds; `map_matching`
  chooses the `leuven` matcher, its tuning knobs, and the 0.6 minimum match
  score; `split` gives the four user-group fractions (50/20/20/10); the
  `privacy_mechanisms` list contains only `none` (this is the unprotected
  baseline); `attacks` requests re-identification with the attacker knowing 3,
  5, or 10 points, against both the raw and the protected data; `metrics`
  requests top-1 accuracy, top-5 accuracy, and linkage rate with a
  1000-resample bootstrap at 95% confidence; and `reporting` asks for a CSV
  export (comma-separated values, a spreadsheet-readable table format).

- `tests/test_reidentification.py` — builds a tiny hand-crafted world (two
  users with two near-parallel trajectories each, plus a single-trajectory
  distractor user) where the correct answers are obvious, and verifies: probes
  link to the right user, rankings are sorted and deduplicated, single-
  trajectory users are never probed, the metrics compute the exact expected
  fractions, the bootstrap is deterministic and brackets the point estimate,
  and an unsupported distance measure is rejected.

- `tests/test_orchestrator.py` — the end-to-end proof. Using the committed
  fixtures (copied so the folder name matches the `beijing` region), it runs
  the whole pipeline through the public `run()` function and checks that
  metrics land in `metrics.csv` with sane values, that the raw and
  protected-by-`none` arms coincide, that runs are deterministic, that the
  matched pool is cached as Parquet and reused, and — a long list of "loud
  failure" tests — that a Ljubljana/Geolife pairing, an unknown attack, an
  unknown map source, an unsupported split scheme, an unknown export format,
  and any output directory under `data/raw/` are all rejected before damage
  is done.

- `src/trajguard/attacks/reidentification.py` and `cli.py` were touched again
  by the review-fix commit `e91c973`, and the formatting commit `5da6f83` is a
  one-line cosmetic cleanup. The substance of `e91c973` is in the
  orchestrator: implementations are now looked up strictly through the
  registry (no hard-wired class names), mechanisms are actually applied via
  their `apply()` method, the pool cache became typed Parquet tables instead
  of ad-hoc files, and configuration validation became the loud, key-by-key
  affair described above.

### How it fits together

Phase 4 is the moment the project becomes an instrument instead of a parts
box. The YAML file names components; the registry resolves those names to the
classes built in Phases 1–3; the orchestrator wires them into a pipeline (load
→ clean → split → match → protect → attack → evaluate) and writes results with
full provenance. One command — `trajguard run
config/experiments/geolife_reid_baseline.yaml` — now produces the first
scientific number: how often an attacker with k known points re-identifies an
unprotected trajectory, with a confidence interval. Everything after this
phase is breadth, not new plumbing.

## Phase 5 — Adding a real privacy protection and measuring quality

*Commits: `6b13df8` (mechanism), `620c170` (utility metrics), `ec96523` (fixed
probe population), `1eaaf19` (tradeoff plot), `67b4448` (parameter grid,
re-matching, caching), `4a29921` (experiment config), `452fff3` (plot labels)*

### Goal

Introduce the first genuine protection — location noise with a formal
mathematical guarantee — and answer the two questions that define the whole
project: **how much does the noise lower the attack's success**, and **how much
does it damage the data's usefulness**? The phase ends with a
privacy-versus-utility trade-off curve, the project's signature output.

### Files added or changed

- `src/trajguard/privacy/geoind.py` — `GeoIndistinguishability`, the planar
  Laplace mechanism from Andrés et al. (2013). Geo-indistinguishability is a
  location-flavored variant of differential privacy (a mathematical framework
  that limits how much any individual's data can influence what an observer
  sees). The mechanism displaces every GPS point independently by a random
  offset: a random direction, and a random distance drawn so that nearby true
  locations remain statistically hard to tell apart. The strength knob is
  `epsilon` — **smaller epsilon means more noise and more privacy**. With the
  scale parameter `unit_m` (default 100 meters), the average displacement is
  `2 × unit_m / epsilon`: at epsilon 0.1 points jump ~2 kilometers, at 10 only
  ~20 meters. The mechanism draws all randomness from one seeded generator (so
  runs are reproducible), leaves timestamps untouched, and tracks its privacy
  budget as epsilon-per-point, a deliberately naive but honest accounting.

- `src/trajguard/privacy/base.py` (extended) — the `PrivacyMechanism` base
  gains a constructor that stores the configuration seed, formalizing the rule
  that stochastic mechanisms derive all randomness from it.

- `src/trajguard/evaluation/utility.py` — the "how much did we break the data"
  side of the scale. Two utility metrics compare the raw release with the
  noisy release of the same trajectories: `cell_js_divergence` overlays the
  map with a grid and computes the Jensen–Shannon divergence (a symmetric,
  0-to-1 measure of how different two probability distributions are) between
  the two releases' cell-visit patterns — "do people still appear to be in the
  same places?"; `length_dist_error` computes the Wasserstein-1 distance (the
  average amount by which one distribution of numbers must shift to become the
  other, here in meters) between the two releases' trip-length distributions —
  "are trips still the same length?". Both get confidence intervals from a
  *paired* bootstrap: a trajectory and its noisy twin are always resampled
  together, preserving their coupling. These functions are plain functions
  rather than `Metric` plugs because they compare two populations rather than
  score one attack; the orchestrator dispatches them by name via the
  `UTILITY_METRICS` table.

- `src/trajguard/attacks/reidentification.py` (changed, `ec96523`) — a
  methodological fix worth understanding. Heavy noise can destroy so many
  trajectories that the protected gallery shrinks; if probes were drawn from
  the shrunken pool, arms with different noise levels would be scored over
  different populations and their numbers would not be comparable. The attack
  now accepts the probe set separately (always the raw pool): a probe whose
  trajectory did not survive protection simply fails to link (scoring 0)
  instead of silently vanishing from the denominator.

- `src/trajguard/reporting/tradeoff.py` — the first inhabitant of the
  reporting layer: `plot_tradeoff()` draws attack success (vertical axis)
  against utility loss (horizontal axis), one labeled point per experimental
  arm, using the matplotlib plotting library (imported lazily so merely
  importing trajguard stays fast). Points that could not be computed (for
  example an arm whose release was entirely destroyed by noise) are skipped
  but listed in a footnote, so a missing point reads as a finding rather than
  a bug. A follow-up commit (`452fff3`) shortened the labels and alternated
  their placement so neighboring points stay readable.

- `src/trajguard/experiments/orchestrator.py` (substantially extended,
  `67b4448`) — three new powers. **Parameter grids**: a mechanism entry may
  give a list of values (`epsilon: [0.1, 1.0, 10.0]`), and the orchestrator
  expands it into one experimental arm per combination, canonicalizing numbers
  so YAML `1` and `1.0` mean the same arm. **Protected re-matching and
  caching**: after a mechanism perturbs the GPS points, the noisy release is
  map-matched again — the attacker sees noisy data snapped back onto roads,
  exactly as a realistic adversary would process it — and the result is cached
  under `data/protected/<hash>/`, keyed by pipeline fingerprint × mechanism
  parameters × seed. A mechanism whose output is identical to its input (the
  `none` baseline) is detected and reuses the raw pool for free. **Utility
  wiring**: for every protected arm the configured utility metrics run over
  the full release (including trajectories that later failed re-matching,
  because utility measures the mechanism, not the attacker's view), and two
  new artifacts appear per run: `matrix.csv` (the headline accuracy pivoted by
  arm × known points) and `tradeoff.png`.

- `config/experiments/geolife_geoind_reid.yaml` — the Phase 5 experiment. It
  differs from the baseline configuration in three places: the mechanism list
  now contains both `none` and `geo_indistinguishability` with the epsilon
  grid `[0.1, 1.0, 10.0]`; the `metrics` section adds
  `utility: [cell_js_divergence, length_dist_error]` and a 20×20
  `utility_grid`; and `reporting` adds `plots: [tradeoff]`. Its header comment
  is candid about what to expect: at epsilon 0.1 the noise averages ~2
  kilometers, so most trajectories will not survive re-matching — "protection
  by destroying the release", which the survivor counts in `run.json` make
  visible.

- `tests/test_geoind.py` — verifies the mechanism: same seed gives identical
  noise, different seeds differ, the measured average displacement over 2000
  points matches the theoretical `2 × unit_m / epsilon` (a genuine statistical
  check of the noise law), higher epsilon means less noise, timestamps and
  metadata survive, the budget accumulates per point, and invalid parameters
  are rejected.

- `tests/test_utility.py` — verifies the utility metrics: identical releases
  score exactly zero, a shifted release scores positive divergence, inflating
  every trip by exactly 500 meters yields exactly 500 as the length error, and
  the paired bootstrap is deterministic and brackets the point estimate.

- `tests/test_reidentification.py` / `tests/test_orchestrator.py` (extended) —
  new tests pin the fixed-probe behavior (a shrunken or even empty gallery
  yields failed links, never missing probes), the grid expansion (int/float
  canonicalization included), the end-to-end geo-ind run (the noisy arm is
  attacked, survivor counts add up, identity arms need no cache entry, the
  utility numbers are zero for `none` and positive for real noise), cache
  reuse, and the new loud rejections (a tradeoff plot without the metrics it
  needs, unknown utility names, misspelled mechanism parameters).

### How it fits together

Phase 5 turns the instrument built in Phase 4 into a real experiment. The
orchestrator now runs a whole family of arms per experiment — unprotected,
identity-protected, and one arm per epsilon — over the *same* cleaned,
split, matched population, with probes held fixed so the numbers are
comparable. For each arm it produces attack success (privacy side) and
distribution distortion (utility side), and the tradeoff plot puts both on one
picture. This is the project's central deliverable in miniature: a defensible
answer to "how much privacy does this much noise buy, and at what cost?".

## Phase 6 — More attacks and synthetic data generation

*Commits: `24ff6ad` "P6a: MarkovGenerator + shared geometry distances",
`330ae2b` "P6b: LiRA-lite membership-inference attack", `5a07883` "P6c: MAP
reconstruction attack", `ff73d61` "P6 review fixes", `e2622ef` "P6.5:
PoiInferenceAttack"*

### Goal

Cover the remaining three attack families from the research plan, plus the
first synthetic-data generator they need. After this phase the benchmark can
ask four distinct privacy questions: *Who does this trajectory belong to?*
(Phase 4), *Was this person's data used to train the generator?* (membership
inference), *Can the original path be recovered from the noisy one?*
(reconstruction), and *Where does this person live and work?* (attribute
inference).

### Files added or changed

- `src/trajguard/geometry.py` — a new shared home for trajectory distance
  mathematics: `dtw()` (Dynamic Time Warping, moved out of the
  re-identification attack where it had lived since Phase 4), `hausdorff()`
  (the worst-case distance between two point sets — "how far is the most
  stranded point of one path from the other path?"), and
  `mean_spatial_error()` (the average point-by-point distance between two
  aligned paths). It exists because the new reconstruction attack needs the
  same distances the linkage attack uses; copying the code would invite the
  two to drift apart.

- `src/trajguard/synthesis/markov.py` — `MarkovGenerator`, the first plug for
  the `SyntheticGenerator` socket. A Markov model is a statistical model that
  learns "after segment A, segment B follows x% of the time" from training
  data, and can then generate new sequences by repeatedly rolling those
  weighted dice. This one works over road-segment sequences, brackets each
  training sequence with artificial START and END symbols so it also learns
  where trips begin and end, and applies additive smoothing (every possible
  next step keeps a small nonzero probability) so it can score *any* sequence
  without collapsing to "impossible". That scoring method,
  `sequence_log_prob()`, is exactly the statistic the membership attack
  queries. The generator refuses to fit on anything but the `train` split — a
  hard guard for experimental hygiene — and generates deterministically from a
  seed.

- `src/trajguard/attacks/membership.py` — `MembershipInferenceAttack`, a
  simplified version ("LiRA-lite") of the state-of-the-art likelihood-ratio
  attack of Carlini et al. (2022). Membership inference asks: given a
  released generator, can an attacker tell whether one specific trajectory was
  in its training data? The attack trains many *shadow generators* — replicas
  the attacker builds on random subsets of similar data — some of which
  happened to include the candidate trajectory (the IN group) and some not
  (the OUT group). It then fits a bell curve to the candidate's likelihood
  under each group and scores the candidate by which curve better explains the
  real generator's likelihood: a log-likelihood ratio. High score means
  "probably a training member". The helper `membership_report()` condenses the
  scores into the honest headline numbers of this literature: the area under
  the ROC curve, and the true-positive rate at very low false-positive rates
  (see the next file).

- `src/trajguard/evaluation/roc.py` — the scoring curves for membership-style
  attacks, written with care around ties. `roc_auc()` computes the area under
  the receiver-operating-characteristic curve (AUC — the probability that a
  randomly chosen member outranks a randomly chosen non-member; 0.5 is
  guessing, 1.0 is perfect). `tpr_at_fpr()` computes the best true-positive
  rate achievable while keeping the false-positive rate under a target such as
  0.1% — Carlini's argument being that an attack matters only if it is right
  when it is confident. Both functions handle tied scores exactly (a real
  classifier must accept a whole tie group or none of it), a correctness point
  pinned down in the final review commit.

- `src/trajguard/attacks/reconstruction.py` — `ReconstructionAttack`, an
  attacker who knows exactly which noise mechanism was used and with which
  parameters (a standard worst-case assumption), and tries to undo it. The
  mathematics: knowing the planar-Laplace noise statistics gives the expected
  size of the random displacement; assuming that real movement is smooth (a
  vehicle does not zigzag wildly between seconds) gives a prior. Combining the
  two yields a maximum-a-posteriori estimate (MAP — the single most probable
  true path given the noisy observations and the smoothness assumption), which
  here takes the form of a Whittaker smoother: a curve-fitting step that
  penalizes curvature in proportion to how noisy the data is known to be. If
  the true path is smoother than the noise, the estimate lands closer to the
  truth than the released points — quantifying how much of the promised
  protection survives a knowledgeable adversary. `reconstruction_report()`
  reports Hausdorff, DTW, and mean spatial error in meters, with bootstrap
  confidence intervals.

- `src/trajguard/attacks/attribute.py` (P6.5) — `PoiInferenceAttack`, the
  fourth and final attack family (POI stands for point of interest — a
  meaningful place such as a home or workplace). It is deliberately simple:
  cluster each user's points into *stay-points* (maximal stretches where the
  person lingered within a 200-meter radius for at least five minutes), then
  estimate **home** as the weighted center of night-time stays (10 pm–7 am
  local time) and **work** as the center of daytime stays (9 am–6 pm),
  converting timestamps to Beijing local time. Ground truth is obtained by
  running the same procedure on the unprotected data. `attribute_report()`
  reports the average home/work estimation error in meters and the fraction of
  users pinned within 200 meters — arguably the most intuitively alarming
  privacy number the benchmark produces.

- `src/trajguard/experiments/builtins.py` (extended per commit) — each new
  attack and the generator are added to the registration imports as they land.

- `src/trajguard/experiments/orchestrator.py` (changed, `ff73d61`) — a
  fail-fast guard: the orchestrator's run loop was built for the
  re-identification contract, and the new attacks need inputs it does not yet
  supply (a fitted generator, the noise parameters, clean GPS points). Rather
  than crash mid-pipeline, the orchestrator now probes each configured
  attack's constructor *before* doing any expensive work and rejects a
  configuration naming an attack it cannot actually drive.

- `tests/test_geometry.py` — verifies the distances: identity gives zero,
  symmetry holds, empty inputs behave, and a hand-computable Hausdorff case
  gives the exact expected value.

- `tests/test_markov.py` — verifies the generator on a tiny corpus: generation
  is deterministic in the seed, generated segments never leave the training
  vocabulary, sequences the model saw score higher than never-seen ones, the
  train-split-only guard fires, and generating before fitting fails.

- `tests/test_membership.py` — builds a universe where members are trivially
  memorized (each trajectory uses its own private segment numbers) and checks
  that the attack separates members from non-members (AUC well above chance),
  carries ground truth in its predictions, and is deterministic; it also tests
  the ROC functions directly, including the tie-safety cases.

- `tests/test_reconstruction.py` — generates truth + genuine planar-Laplace
  noise and verifies the mathematical promise: the reconstruction lands closer
  to the truth than the raw noisy release, all three reported metrics are
  finite with ordered confidence intervals, the estimate is deterministic, and
  a stronger smoothness prior smooths more.

- `tests/test_attribute.py` — builds three users with known home/work dwell
  spots and verifies: stay-point detection finds the dwell, on raw data the
  inference is exact (zero error, everyone localized), and across a real
  geo-indistinguishability sweep the attack degrades as designed — at epsilon
  10 homes are pinned within meters, at epsilon 1 within the threshold, and at
  epsilon 0.1 no one is localized at all.

### How it fits together

Phase 6 fills the last two sockets (`SyntheticGenerator` and the remaining
`Attack` families) and makes the attack suite complete. The membership attack
consumes what the generator produces, closing the synthesis→attack loop; the
reconstruction attack consumes what the Phase 5 mechanism produces, closing the
protection→attack loop; the attribute attack consumes protected GPS points and
answers the most human question of all. Note the honest seam: these three
attacks have full standalone harnesses and tests, but only re-identification is
wired into the orchestrator's run loop — and the orchestrator says so loudly
instead of pretending otherwise.

## Phase 7 — Automated reporting

*Commits: `3c41e01` "P7: reporting layer — risk matrix, tidy tables, tradeoff
plots, Markdown report", `6033d06` "Review fixes: MIA tie-safe TPR,
orchestrator fail-fast for unwired attacks, cache/guard robustness"*

### Goal

Turn a folder of machine-oriented result files into a single, human-readable
risk report. After many experiment runs, `results/` contains one `run.json`
per experiment; someone writing a research report needs those aggregated into
tables, a risk matrix (attack families as columns, protection variants as
rows), trade-off plots, and prose-ready Markdown — with one command.

### Files added or changed

- `src/trajguard/reporting/report.py` — the aggregation engine, in five
  stages. **Loading**: `load_results()` reads every `results/*/run.json` and
  parses each metric's machine identifier (for example
  `reidentification:protected:geo_indistinguishability:epsilon=2.0:k10`) into
  tidy columns — attack family, target arm, mechanism, parameters, attacker
  knowledge — refusing loudly on anything unrecognized, since a silently
  misparsed row would corrupt every table downstream. **Tables**:
  `export_tables()` writes the full tidy table as `metrics_long.csv` and
  `.parquet`, the formats a statistician or a plotting script would want.
  **Risk matrix**: `risk_matrix()` pivots results into the report's
  centerpiece — one row per released arm, one column per attack family, each
  cell showing that family's headline metric (top-1 accuracy for
  re-identification, AUC for membership, error-in-meters for reconstruction
  and attribute inference) at the attacker's most generous knowledge level.
  Runs are grouped by their pipeline fingerprint so only genuinely comparable
  experiments merge into one matrix, and two runs disagreeing on the same cell
  raise an error instead of one silently winning. **Summaries**:
  `summarize_by_attack()` produces the detailed per-attack tables with every
  metric and confidence interval. **Rendering**: `generate_report()` runs all
  of the above, regenerates the trade-off plot for every run that has both
  sides of the trade-off, and renders everything through a template into
  `reports/report.md`.

- `src/trajguard/reporting/templates/report.md.j2` — the report's skeleton,
  written for the Jinja2 template engine (a tool that fills placeholders in a
  text file with computed values). It defines the report sections in order: a
  provenance table of runs (seed, code version, split sizes, runtime), the
  risk matrix with a plain-language reading guide ("higher means more risk,
  except error-in-meters metrics, where lower error means a stronger attack"),
  per-attack detail tables, the utility comparison, an "arm health" table
  (pool sizes, probe counts, how many trajectories each mechanism destroyed,
  spent privacy budget), the embedded trade-off plots, and the list of
  exported files. Keeping the layout in a template means the wording and
  structure of the report can evolve without touching Python code.

- `src/trajguard/experiments/cli.py` (extended) — the command-line program
  gains its second subcommand: `trajguard report --results results --out
  reports`. Running experiments and reporting on them are now the tool's two
  verbs.

- `src/trajguard/reporting/__init__.py` (updated) and `pyproject.toml` /
  `uv.lock` (updated) — the package now ships the template as package data,
  and Jinja2 joins the dependency list.

- `tests/test_reporting.py` — verifies the layer twice over. Against
  hand-written `run.json` payloads it checks the identifier parsing, the loud
  rejection of junk, the risk-matrix pivot (headline at the largest knowledge
  level, raw-then-identity-then-numeric arm ordering, grouping by pipeline
  fingerprint, loud conflicts), the table round-trip through CSV and Parquet,
  and the complete rendered report text. Then, as an integration test, it runs
  a real orchestrator experiment on the fixtures and generates a report from
  its genuine output — proving the two layers actually speak the same format.

- The final review commit (`6033d06`) hardened several edges across the
  codebase: `evaluation/roc.py` got the exact tie-handling described in Phase
  6 (tied scores can no longer inflate the low-false-positive-rate numbers);
  the orchestrator got the explicit list of attacks its run loop can actually
  drive, rejecting the others up front; the pool cache's completion marker is
  now written atomically (a crash mid-write can no longer leave a corrupted
  cache that poisons every later run) and the cache key tracks the map's
  download timestamp (rebuilding a map invalidates stale pools); the
  `data/raw/` write guard became path-component-based so it catches absolute
  paths from any working directory; and `maps/osm.py` now reloads its custom
  longitude/latitude attributes as numbers rather than text. Small commits
  like this one are where "it works" becomes "it cannot silently lie".

### How it fits together

Phase 7 closes the loop begun in Phase 4: the orchestrator writes `run.json`
files with full provenance, and the reporting layer is their mirror image —
it parses exactly what the orchestrator emits (the integration test enforces
this) and refuses anything else. With it, the full workflow is two commands:
`trajguard run <config>` for each experiment, then `trajguard report` to turn
the accumulated results into the risk matrix, tables, and plots that feed the
written research report.

## Summary: the full picture

When you type `trajguard run config/experiments/geolife_geoind_reid.yaml`,
this is what happens, in order, naming the module responsible for each step:

1. **Read and validate the configuration** (`experiments/orchestrator.py`).
   The YAML file is parsed into a typed configuration; every unknown or
   unsupported value fails immediately with a named key. The map region is
   checked against the dataset's home region, output paths are checked against
   the immutable `data/raw/`, and every configured mechanism and attack is
   instantiated up front so a bad name or parameter dies before any real work.

2. **Load the road network** (`maps/osm.py`), built once beforehand by
   `python -m trajguard.maps.build` and read from disk without touching the
   internet.

3. **Load, clean, split, and match the trajectories** (`datasets/geolife.py`,
   `datasets/cleaning.py`, `datasets/split.py`, `matching/leuven.py`). Raw
   `.plt` files become cleaned trajectories; every user is assigned to
   train/test/shadow/attack; every trajectory is snapped onto roads and scored,
   with low-quality matches dropped. The entire result is cached in
   `data/processed/` under a fingerprint of every setting involved, so the
   next run skips straight ahead.

4. **Produce one arm per protection variant** (`privacy/none.py`,
   `privacy/geoind.py`, orchestrator). The mechanism grid expands into arms —
   here: no protection, plus planar-Laplace noise at epsilon 0.1, 1.0, and
   10.0. Each perturbed release is re-matched onto the roads (the attacker's
   realistic view) and cached in `data/protected/`.

5. **Attack every arm** (`attacks/reidentification.py`). For each arm and each
   attacker knowledge level (3, 5, 10 known points), the linkage attack ranks
   gallery users by trajectory similarity, with the probe population held
   fixed on the raw pool so all arms are scored over the same denominator.

6. **Score the attacks and the damage** (`evaluation/metrics.py`,
   `evaluation/utility.py`). Attack success becomes top-1/top-5 accuracy and
   linkage rate with bootstrap confidence intervals; data damage becomes the
   cell-visit divergence and trip-length error of each noisy release against
   the raw one.

7. **Write the results** (orchestrator, `reporting/tradeoff.py`). The run
   directory receives `metrics.csv`, `matrix.csv` (accuracy by arm × attacker
   knowledge), `tradeoff.png` (privacy versus utility on one picture), and
   `run.json` (every number plus full provenance: configuration fingerprint,
   code version, seed, pool and probe sizes, destroyed-trajectory counts,
   spent privacy budget).

8. **Aggregate everything into a report** (`reporting/report.py`,
   `trajguard report`). All accumulated runs are merged into tidy tables, the
   attack × mechanism risk matrix, per-attack detail tables, arm-health
   statistics, and regenerated trade-off plots, rendered through the Jinja2
   template into `reports/report.md`.

Standing slightly apart from this pipeline are the Phase 6 components: the
Markov generator (`synthesis/markov.py`) and the membership, reconstruction,
and attribute attacks, each fully implemented and tested through standalone
harnesses but not yet wired into the orchestrator's run loop — a seam the
orchestrator itself announces rather than hides.

The architecture that makes all of this legible is unchanged since Phase 0:
frozen data records flow between seven interfaces, implementations plug in
through a name registry, every stochastic step draws from an explicit seed,
every expensive product is cached under a content fingerprint, the raw data
folder is never written to, and every claim in the codebase is backed by a
test that runs offline against a small committed fixture world. If you
remember one thing about trajguard, make it this: it is a pipeline of
replaceable parts for measuring, with honest error bars, how much privacy a
location-data protection really buys — and what it costs.
