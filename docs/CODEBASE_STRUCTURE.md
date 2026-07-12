# How the trajguard codebase is laid out — and why

> A tour for a developer joining the project. It explains the folder structure,
> the three architectural ideas everything hangs on, and the design decisions
> behind them — the "why", not just the "what". It describes the codebase as it
> is **today**; for the commit-by-commit history read
> `docs/CODEBASE_PHASE_GUIDE.md`, for a terse API reference read
> `docs/ARCHITECTURE.md`, and for runnable commands read `docs/RUNNING.md`.

## 1. What this project is, in one paragraph

Trajguard is a benchmark — a crash-test laboratory — for privacy protections on
GPS movement data. It takes real trajectories (sequences of "this latitude and
longitude at this time"), applies a protection mechanism (for example, adding
random noise to every point, or replacing the data with synthetic trajectories),
and then runs attacks against the protected output: programs playing an
adversary who tries to re-identify people, recover the original path, or detect
whose data trained a generator. The output is always a trade-off with error
bars: this much privacy costs this much data quality.

## 2. The mental model: an assembly line with replaceable stations

Everything in `src/trajguard/` is one station on a single assembly line. Data
enters as raw GPS files and moves left to right; each station consumes one
well-defined record type and produces the next:

```
raw GPS files ─► load ─► clean ─► split ─► map-match ─┬─► protect (add noise) ──┐
                                                      ├─► synthesize (generate) ┤
                                                      └─► leave unprotected ────┤
                                                                                ▼
                                                            attack ─► score ─► report
```

Two things make this more than a script:

1. **Every station is a replaceable part.** A station is defined by an
   interface (an abstract base class, "ABC" — a Python class that declares
   which methods an implementation must provide, without providing them
   itself). Any class that implements the interface can be plugged in without
   touching the rest of the line.
2. **The records that move between stations are frozen.** Each intermediate
   product (`RawTrajectory`, `CleanTrajectory`, `MatchedTrajectory`, …) is an
   immutable dataclass, so no station can accidentally corrupt what another
   station produced.

If you keep this picture in mind, every folder in the repository has an obvious
place: it is either a station, the conveyor belt (orchestration), the records
on the belt (datamodel), or the warehouse (data folders and caches).

## 3. Top-level layout

```
trajguard/
├── src/trajguard/     # all the code (one package per pipeline station — §5)
├── tests/             # pytest suite + committed fixtures; offline, runs in ~20 s
├── config/            # experiment definitions (YAML) + the map-region catalogue
├── docs/              # design docs and guides (this file among them)
├── data/
│   ├── raw/           # original datasets — IMMUTABLE, the pipeline never writes here
│   ├── interim/       # cleaned trajectories        ┐
│   ├── processed/     # map-matched trajectories    │  regenerable caches, keyed by
│   ├── protected/     # mechanism outputs           │  a content hash — safe to delete
│   └── synthetic/     # generator outputs           ┘
├── maps/              # built road networks (expensive one-time OpenStreetMap builds)
├── notebooks/         # visual sanity checks (e.g. "does map-matching look right?")
├── results/           # one folder per experiment run (metrics.csv, run.json, plots)
└── reports/           # aggregated human-readable report (trajguard report)
```

Why the data folders are split this way: `data/raw/` holds inputs we cannot
regenerate (downloaded datasets), so the code treats it as read-only and the
orchestrator actively refuses any configuration that would write into it.
Everything else under `data/` is a cache: each artifact lives in a
subdirectory named by a hash of every setting that produced it, so a re-run
with identical settings is instant, and any settings change automatically
lands in a fresh directory instead of silently overwriting the old one. You
can delete `interim/ processed/ protected/ synthetic/ results/ reports/` at
any time and lose nothing but compute time.

## 4. The three ideas the architecture stands on

### 4.1 A shared vocabulary of frozen records (`datamodel/`)

`src/trajguard/datamodel/entities.py` defines the record types that flow down
the assembly line — `RawTrajectory`, `CleanTrajectory`, `MatchedTrajectory`,
`ProtectedTrajectory`, `SyntheticTrajectory`, `AttackResult`, `MetricValue`,
plus bookkeeping types (`Map`, `ExperimentConfig`). They are frozen
dataclasses: once created, a record cannot be modified.

**Why:** in a pipeline where six subsystems hand data to each other, the
cheapest way to prevent a whole class of bugs is to make the handed-over data
untouchable. A station that wants to change something must create a new record
— which is exactly the assembly-line semantics we want, and it keeps every
cached artifact trustworthy. It also gives the whole team (and every document)
one set of names for the things in flight.

### 4.2 Seven interfaces, one per station kind (the ABCs)

Each subsystem package contains a `base.py` with exactly one abstract base
class:

| Interface | Package | Contract in one sentence |
| --- | --- | --- |
| `MapSource` | `maps/` | can load a road network for one region |
| `DatasetLoader` | `datasets/` | can yield `RawTrajectory` records and names its home region |
| `MapMatcher` | `matching/` | can snap a cleaned trajectory onto road segments |
| `PrivacyMechanism` | `privacy/` | can transform one trajectory and account for its privacy budget |
| `SyntheticGenerator` | `synthesis/` | can fit on training trajectories and generate artificial ones |
| `Attack` | `attacks/` | can be configured with attacker knowledge and run against target data |
| `Metric` | `evaluation/` | can turn an attack result into named numbers |

**Why interfaces at all:** this is a research codebase whose whole purpose is
to grow — new attacks, new mechanisms, new datasets will keep arriving for
years. The interfaces mean that growth happens by *adding* a file that
implements a known contract, never by *editing* the pipeline. The golden rule
in `CLAUDE.md` ("every new component subclasses the relevant ABC") is what
keeps the 40-odd source files from tangling into each other.

**Why exactly these seven:** they are the seven points where the design
document (design §2.3) expects variation. Everything else — cleaning rules,
splitting, caching, plotting — is benchmark infrastructure that should behave
identically no matter which components are plugged in, so it is deliberately
*not* behind an interface.

### 4.3 The registry: from a name in YAML to a class in Python

`experiments/registry.py` is a phone book. A component registers itself with a
decorator:

```python
@register("attack", "reidentification")
class ReidentificationAttack(Attack): ...
```

and the orchestrator later looks it up with `get("attack", "reidentification")`.
The registry validates on registration: unknown kinds, duplicate names, and
classes that do not actually subclass the matching interface are all rejected.

**Why:** experiments are described in YAML files (`config/experiments/*.yaml`)
where a line like `matcher: leuven` is just text. Something has to turn that
text into the right class, and a registry does it without the orchestrator
ever importing concrete implementations by name — which is what keeps the
orchestrator generic.

One subtlety a newcomer always hits: a `@register` decorator only runs when
its file is imported. `experiments/builtins.py` exists solely to import every
first-party implementation in one place; the orchestrator imports that single
module and thereby "knows" every component. If you add a component and the
orchestrator cannot find it, the missing import in `builtins.py` is the reason.

Currently registered names (grep for `@register` to refresh this list):
`osm` (map source); `geolife` (dataset); `leuven` (matcher); `none`,
`geo_indistinguishability` (mechanisms); `markov`, `rn_ldp_synth`
(generators); `reidentification`, `membership_inference`, `reconstruction`,
`poi_inference` (attacks); `top_k_accuracy`, `linkage_rate` (metrics).

## 5. Package-by-package tour of `src/trajguard/`

In pipeline order, with the reason each package exists:

- **`datamodel/`** — the frozen record types (§4.1). No logic, only shapes.
- **`maps/`** — `osm.py` downloads a road network from OpenStreetMap once
  (`build.py` is the explicit command-line step for that) and afterwards loads
  it from disk without network access. The split into an expensive, explicit,
  human-invoked *build* and a cheap, offline *load* exists so that no test or
  experiment ever touches the internet implicitly — a precondition for
  reproducible results.
- **`datasets/`** — `geolife.py` parses the Geolife GPS files into
  `RawTrajectory` records; `cleaning.py` removes GPS glitches (impossible
  speeds, too-short recordings) because attacks on garbage data produce
  garbage conclusions; `split.py` assigns every **user** to exactly one of
  four roles (`train`/`test`/`shadow`/`attack`). Splitting by user rather than
  by trajectory is essential: if one person's trips appeared in both the
  training data and the attack targets, a membership-inference experiment
  would be measuring leakage that the experimental setup itself created.
- **`matching/`** — `leuven.py` snaps noisy GPS points onto the roads actually
  traveled (map matching: GPS navigation in reverse). Attacks that compare
  routes need road-segment sequences, not jittery dots, and the match-quality
  score gives the pipeline a principled way to discard trajectories it cannot
  trust.
- **`representation/`** — `views.py` provides `TrajectoryView`, a uniform way
  to look at one trajectory as GPS points (`as_gps()`), road segments
  (`as_segments()`), or grid cells (`as_cells()`). Mechanisms and generators
  ask for the view they need instead of caring how trajectories are stored —
  one adapter instead of N×M conversion paths.
- **`privacy/`** — the protection mechanisms. `none.py` is the scientifically
  indispensable control group ("what if we did nothing"); `geoind.py` is
  planar-Laplace location noise with the geo-indistinguishability guarantee
  (a location-flavored variant of differential privacy — smaller epsilon means
  more noise and more privacy); `ldp.py` holds the local-differential-privacy
  randomizers (GRR and OUE — coin-flipping schemes that let a server learn
  population statistics without trusting any individual report) used by the
  RN-LDP-Synth generator.
- **`synthesis/`** — the generators. `markov.py` learns "after road segment A
  comes segment B x% of the time" and generates new trajectories; it is the
  non-private ceiling the private generator is compared against. 
  `rn_ldp_synth.py` is the project's own contribution: it collects only
  privacy-randomized reports from (simulated) devices and synthesizes a
  population of road-network-valid trajectories from the aggregates — see
  `docs/RN_LDP_SYNTH_DESIGN.md` for the full design and privacy proof.
- **`attacks/`** — the four adversary families, one file each:
  `reidentification.py` ("whose trajectory is this?"), `membership.py` ("was
  this person's data used for training?"), `reconstruction.py` ("can the
  original path be recovered from the noisy one?"), and `attribute.py`
  ("where does this person live and work?"). Each answers a distinct
  real-world privacy question, which is why they are separate classes rather
  than options on one attack.
- **`evaluation/`** — turns attack output into honest numbers: `metrics.py`
  (accuracy-style metrics with bootstrap confidence intervals — a resampling
  technique that puts error bars on results from small samples), `roc.py`
  (tie-safe curves for membership attacks), and `utility.py` (how much a
  protection damaged the data: spatial-distribution divergence and trip-length
  distortion). Privacy results without utility results would be meaningless —
  deleting all data is perfectly private — so both sides live in this package.
- **`geometry.py`** — shared trajectory distances (Dynamic Time Warping,
  Hausdorff, mean spatial error). It exists because both the linkage attack
  and the reconstruction attack need the same mathematics; a copy in each
  would inevitably drift apart.
- **`experiments/`** — the conveyor belt: `registry.py` (§4.3),
  `builtins.py` (the import hub), `orchestrator.py` (reads a YAML config,
  validates it loudly, enforces the safety rules, runs the pipeline, caches,
  and writes results with full provenance), `cli.py` (the `trajguard run` /
  `trajguard report` commands), and `rnldp_eval.py` (the standalone
  RN-LDP-Synth evidence sweep, runnable offline on the committed fixtures).
- **`reporting/`** — `tradeoff.py` draws the privacy-versus-utility plot;
  `report.py` aggregates every `results/*/run.json` into tidy tables, a risk
  matrix (mechanisms × attack families), and a rendered Markdown report. Kept
  separate from `evaluation/` because it consumes finished result files, never
  live pipeline objects — you can regenerate every report without rerunning a
  single experiment.

## 6. The design decisions, and what each one buys

These are the deliberate choices behind the layout above. They are written
down as golden rules in `CLAUDE.md`; here is the reasoning.

**Vertical slices before breadth.** The project was built as one complete
path (raw files → first attack number) before any second implementation of
anything was added. That is why every package contains exactly the
implementations that are actually used — there is no speculative scaffolding
to mislead you. When you add something, follow the same rule: make it run end
to end before generalizing it.

**Determinism everywhere.** Every stochastic step takes an explicit seed from
the configuration, and bare `random` / `np.random` calls are banned in favor
of seeded `np.random.Generator` objects. The payoff: any result — including a
suspicious one — can be reproduced bit-for-bit, and caching is sound because
identical settings genuinely produce identical outputs. (For the LDP
mechanism there is one important nuance: the seed exists for experiment
reproducibility and provides no privacy; a real deployment needs randomness
the server cannot know.)

**Immutable raw data, hash-keyed caches.** `data/raw/` is never written to —
the orchestrator refuses configurations that try. Every derived artifact is
cached under a fingerprint of the settings that produced it. This makes every
run answerable to the question "exactly which inputs and settings produced
this number?", which is the difference between research output and anecdote.
One practical trap, documented in `RUNNING.md` §10: the cache key covers the
dataset *path*, not the file *contents*, so after changing raw data you must
clear `data/processed/` yourself.

**One split, at the `CleanTrajectory` level, by user, with a fixed seed.** The
train/test/shadow/attack assignment happens once and the label rides along on
every downstream artifact. Shadow models (the attacker's practice replicas in
membership inference) train strictly on their own split. Any laxness here
would quietly bias the benchmark's headline results, which is why it is a
structural rule and not a convention.

**The map/dataset region guard.** The orchestrator rejects any run where the
map's region differs from the dataset's native region (Geolife → Beijing;
Ljubljana is reserved for synthetic work). Without the guard, a mismatched
pairing would not crash — map matching would just silently produce garbage,
and the garbage would flow into published numbers. Loud refusal beats silent
nonsense; you will find the same philosophy in the orchestrator's key-by-key
config validation and in its up-front rejection of attacks it cannot drive.

**Tests run offline against committed fixtures.** `tests/fixtures/` contains
a small real road network (committed once, built with the real code) and
format-faithful fake Geolife files with *planted defects* that the cleaning
tests assert on. Tests never touch the network and never read `data/`. This
is what makes the ~180-test suite finish in about 20 seconds, which in turn
is what makes "every change ships with a passing test" a rule people actually
follow.

**Lean dependencies.** Plain PyYAML instead of a configuration framework,
frozen dataclasses instead of pydantic, argparse instead of a CLI framework,
Parquet + DuckDB instead of a spatial database. Each choice trades features
we do not need for fewer moving parts a future reader has to learn. Adding a
dependency requires a one-line justification in the pull request.

## 7. What happens when you run an experiment

`uv run trajguard run config/experiments/geolife_geoind_reid.yaml` does, in
order (all inside `experiments/orchestrator.py` unless noted):

1. **Validate loudly.** The YAML is parsed into a typed configuration; any
   unknown key, metric, or parameter fails immediately with its name. The
   region guard and the `data/raw/` write guard run before any real work, and
   every configured mechanism and attack is instantiated up front so a bad
   name dies in seconds, not after an hour of matching.
2. **Prepare the pool.** Load the road network from `maps/`, load and clean
   the trajectories, split users, map-match everything, drop low-quality
   matches — then cache the whole pool under `data/processed/<hash>/`.
3. **Expand the arms.** A parameter list like `epsilon: [0.1, 1.0, 10.0]`
   becomes one experimental arm per value, next to the unprotected baseline.
   Each protected release is re-matched onto the roads (the attacker sees
   noisy data processed the way a real adversary would process it) and cached
   under `data/protected/<hash>/`.
4. **Attack and score.** The re-identification attack runs per arm and per
   attacker-knowledge level, with the probe population held fixed on the raw
   pool so all arms share the same denominator; metrics get bootstrap
   confidence intervals; utility metrics compare each noisy release with the
   raw one.
5. **Write with provenance.** The run directory under `results/` receives
   `metrics.csv`, `matrix.csv`, `tradeoff.png`, and `run.json` — the last one
   recording the configuration fingerprint, code version, seed, and how many
   trajectories survived each stage (your first stop when numbers look odd).

`uv run trajguard report` then aggregates every accumulated `run.json` into
`reports/report.md` with the risk matrix and per-attack tables.

## 8. Honest seams: what is deliberately not wired up

Two seams exist on purpose, and the code announces them instead of hiding them:

- **The orchestrator's run loop drives only re-identification** (see
  `_ORCHESTRATOR_ATTACKS` in `orchestrator.py`). The membership,
  reconstruction, and attribute attacks are fully implemented and tested, but
  they need inputs the loop does not yet supply (a fitted generator, the noise
  parameters, clean GPS points), so a config naming them is rejected up front
  rather than crashing mid-pipeline. They join the set as they are wired in.
- **RN-LDP-Synth is evaluated through its own harness**
  (`python -m trajguard.experiments.rnldp_eval`), not through `trajguard run`,
  because the run loop does not yet instantiate generators or attack synthetic
  pools. Its measured evidence so far is fixture-scale only — see
  `docs/RN_LDP_SYNTH_DESIGN.md` §10–§12 for the numbers and their caveats.

## 9. Recipe: adding a new component

Say you want to add a new privacy mechanism. The same five steps apply to any
of the seven component kinds:

1. Create one file in the matching package (e.g. `privacy/my_mechanism.py`)
   with a class that subclasses the ABC from that package's `base.py` and
   implements its abstract methods. Take every random decision from a seeded
   `np.random.Generator` derived from the constructor's `seed`.
2. Decorate it with `@register("mechanism", "my_mechanism")`.
3. Import the module in `experiments/builtins.py` so the registration runs.
4. Write a test in `tests/` that proves its behavior against the committed
   fixtures — deterministic under a fixed seed, correct on a case whose answer
   you know in advance, loud on invalid parameters. No network, no `data/`.
5. Run the checks and include their output in the pull request:
   `uv run ruff check .`, `uv run mypy src`, `uv run pytest`.

If it is a mechanism or attack, you can now name it in an experiment YAML and
the orchestrator will find it — no orchestrator changes needed (unless the
component needs inputs the run loop does not supply yet; then you have found
one of the seams in §8, and that wiring is its own, separate task).

## 10. Where to read next

- `CLAUDE.md` — the golden rules, in force for every change.
- `docs/ARCHITECTURE.md` — compact reference: ABC signatures, entity fields,
  config keys, region table.
- `docs/CODEBASE_PHASE_GUIDE.md` — the same codebase explained historically,
  phase by phase, file by file.
- `docs/RUNNING.md` — every runnable command with expected output and
  troubleshooting.
- `docs/RN_LDP_SYNTH_DESIGN.md` — design, privacy proof, and first measured
  results of the RN-LDP-Synth generator.
- `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` — the original design
  document (Slovenian); it wins over `ARCHITECTURE.md` on conflicts.
