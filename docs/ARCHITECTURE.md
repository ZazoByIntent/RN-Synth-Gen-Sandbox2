# trajguard architecture — quick reference

English distillation of `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` ("the
design doc", §0–§10) for day-to-day coding, so you rarely need to open the ~550-line
Slovenian original. If this file and the design doc disagree, the design doc wins —
fix this file in the same PR. The golden rules in `CLAUDE.md` outrank both.

## Data flow and storage (design §3, §9)

```
data/raw/  (immutable source files: Geolife .plt, …)
    │  DatasetLoader.iter_trajectories()
    ▼
RawTrajectory ── cleaning (speed filter, min length/points, resample) ──►
    CleanTrajectory  (data/interim/)   ◄── train/test/shadow/attack split
    │                                      assigned HERE, once, seeded
    ├── dataset.representation: cells ── Grid.chain(as_cells(grid)) ──► CellChain
    │      (no map, no matching; membership_inference only)         (data/processed/)
OSM ─► MapSource ─► RoadNetwork (maps/)
    │                   │
    └───── MapMatcher.match() ──► MatchedTrajectory  (data/processed/)
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
          PrivacyMechanism   SyntheticGenerator   (unprotected baseline)
                    │               │                │
       ProtectedTrajectory   SyntheticTrajectory     │
        (data/protected/)     (data/synthetic/)      │
                    └───────────────┼────────────────┘
                                    ▼
              TrajectoryView (as_gps / as_segments / as_sequence / as_cells / …)
                                    ▼
                     Attack.run() ──► AttackResult
                                    ▼
              Metric.compute() ──► MetricValue (+ bootstrap CI)
                                    ▼
                            results/ , reports/
```

- Every step is idempotent and cached, keyed by `hash(config + input_hash + seed)`;
  reruns skip already-computed artifacts.
- The `split` label propagates through all downstream artifacts; shadow models train
  strictly on their own split (fair MIA — design risk T3).
- Design §3 draws the `RawTrajectory` Parquet inside `data/raw/`; that conflicts with
  the raw-immutability golden rule. Treat `data/raw/` as source-files-only and cache
  parsed output under `data/interim/`.
- `TrajectoryView` wraps the clean and/or matched form, or — for the cells
  representation and the membership attack's shadow models — a bare integer
  `sequence` (edge ids in the segments representation, grid-cell indices in the cells
  representation). Generators and the membership attack read `as_sequence()`, which
  returns that sequence or falls back to the matched edge sequence, so the segments
  path is unchanged; `as_segments()` never falls back to a bare sequence. `Grid.chain()`
  in `representation/views.py` is the single implementation of the LDPTrace cell
  chain (consecutive duplicates collapsed, king's walk between non-adjacent cells),
  used by `LDPTraceGenerator` in both of its input modes (`network=` for the segments
  representation, `bbox=` for the cells representation; see the module docstring).
- The orchestrator runs one of two representations per config
  (`dataset.representation`, default `segments`). In `cells` the pool is a list of
  `CellChain(traj_id, user_id, chain)` records cut by `_cell_pool` in
  `experiments/orchestrator.py` (load → clean → user subsample → split → `Grid.chain`
  over the per-point cells of `dataset.grid`), cached as `clean.parquet` +
  `chains.parquet`; no road network is loaded, only `membership_inference` runs, and
  generators receive the grid (`bbox`, `n_rows`, `n_cols`) instead of `network`.

## The seven ABCs (design §2.3)

§2.3's prose says "five extension points" but lists seven — **seven is correct**.
Each ABC lives in its own module under the matching package (see layout below).

```python
class MapSource(ABC):
    @abstractmethod
    def load(self) -> "RoadNetwork": ...
    @property
    @abstractmethod
    def crs(self) -> str: ...

class DatasetLoader(ABC):
    dataset_id: str
    native_region: str          # e.g. "beijing" — checked against map.region
    @abstractmethod
    def iter_trajectories(self) -> Iterator["RawTrajectory"]: ...

class MapMatcher(ABC):
    @abstractmethod
    def match(self, traj: "CleanTrajectory", net: "RoadNetwork") -> "MatchedTrajectory": ...

class PrivacyMechanism(ABC):
    guarantee: str              # "none" | "geo-ind" | "ldp" | "central-dp" | "k-anon"
    @abstractmethod
    def apply(self, traj: "TrajectoryView", **params) -> "ProtectedTrajectory": ...
    @abstractmethod
    def spent_budget(self) -> float | None: ...

class SyntheticGenerator(ABC):
    @abstractmethod
    def fit(self, train: Sequence["TrajectoryView"]) -> None: ...
    @abstractmethod
    def generate(self, n: int, seed: int) -> Sequence["SyntheticTrajectory"]: ...

class Attack(ABC):
    target_scope: set[str]      # subset of {"raw", "protected", "synthetic"}
    @abstractmethod
    def configure(self, knowledge: "BackgroundKnowledge") -> None: ...
    @abstractmethod
    def run(self, target, aux) -> "AttackResult": ...

class Metric(ABC):
    @abstractmethod
    def compute(self, result: "AttackResult", ground_truth) -> dict: ...
```

Concrete implementations register by name so the orchestrator can address them from
YAML. The registry lives in `src/trajguard/experiments/registry.py` — a
`register(kind, name)` decorator plus a `get(kind, name)` lookup (the design doc's
`ptregistry` refers to this):

```python
@register("attack", "reidentification")
class ReidentificationAttack(Attack): ...
```

## Datamodel entities (design §4)

Frozen dataclasses in `src/trajguard/datamodel/`. On disk: one Parquet table per
entity, DuckDB as the query layer; IDs stay stable across pipeline steps.

| Entity | Key fields |
| --- | --- |
| `Map` | `map_id`, `source` (osm/synthetic), `region`, `bbox`, `crs`, `osm_timestamp`, paths to graph/edges/nodes |
| `RawTrajectory` | `traj_id`, `user_id`, `dataset_id`, `points` [(lat, lon, t, alt?)], `start_t`, `end_t`, `n_points`, `source_file` |
| `CleanTrajectory` | `traj_id`, `user_id`, `points` [(lat, lon, t)], `bbox`, `duration_s`, `length_m`, `mean_speed`, `cleaning_flags`, `split` ∈ {train, test, shadow, attack} |
| `MatchedTrajectory` | `traj_id`, `user_id`, `map_id`, `edge_seq` [edge_id], `matched_points` [(x, y, t, offset_m)], `match_score`, `frac_matched` |
| `ProtectedTrajectory` | `traj_id`, `source_traj_id` (→ `MatchedTrajectory.traj_id`), `mechanism_id`, `params_hash`, `guarantee`, `epsilon`, `payload`, `map_id` |
| `SyntheticTrajectory` | `syn_id`, `generator_id`, `params_hash`, `payload`, `trained_on_split`, `map_id` |
| `AttackResult` | `result_id`, `attack_id`, `exp_id`, `target_data_ref`, `predictions`, `scores`, `ground_truth_ref`, `runtime_s` |
| `MetricValue` | `metric_id`, `result_id`, `name`, `value`, `ci_low`, `ci_high`, `n_bootstrap` |
| `ExperimentConfig` | `config_hash`, `raw_yaml`, `resolved_yaml`, `schema_version`; run record adds `exp_id`, `map_id`, `dataset_id`, `git_commit`, `seed`, `created_at` |

Naming notes: `MetricValue` is the design's "Metric" table, renamed to avoid clashing
with the `Metric` ABC. The plan's P0 list omits `RawTrajectory`, but
`DatasetLoader.iter_trajectories` forward-references it — creating it in P0 with the
others is fine. Relations: `Experiment 1─* Attack 1─* AttackResult 1─* MetricValue`.

## Map/dataset consistency (design §0)

| Dataset | `native_region` | Map CRS |
| --- | --- | --- |
| Geolife, T-Drive | `beijing` | EPSG:32650 (UTM 50N) |
| Porto Taxi | `porto` | EPSG:32629 (UTM 29N) |
| synthetic paths / RN-LDP-Synth only | `ljubljana` | EPSG:3794 (D96/TM) |
| LDPTrace `.dat` files (`ldptrace_dat`; Porto for the validation run) | `none` | no map — cells representation only |

The orchestrator rejects any config where `map.region != dataset.native_region`
whenever a `map` block is given. Ljubljana is never a target for Geolife attacks
(design risk T1). `ldptrace_dat` has no map at all (`native_region = "none"`), so the
same check rejects it with any `map` block; it runs in the cells representation
(`dataset.representation: cells`, no `map` block), the input of the LDPTrace
validation (`docs/NACRT_LDPTRACE_VALIDACIJA.md`).

## Attack families (design §6)

| Attack | `target_scope` | Approach | Primary metrics | Phase |
| --- | --- | --- | --- | --- |
| Reidentification / linkage (de Montjoye 2013) | raw, protected | attacker knows k target points; NN over matched trajectories (DTW/Hausdorff) | top-1/top-k accuracy, linkage rate | P4 |
| Membership inference, LiRA-lite (Carlini 2022) | synthetic | shadow generators + likelihood ratio | TPR @ FPR ∈ {0.001, 0.01}, AUC | P6 |
| Reconstruction / inversion (Buchholz 2022) | protected | MAP inversion of the known mechanism | Hausdorff, DTW, mean spatial error (m) | P6 |
| POI / home-work inference (Primault 2019) | protected, synthetic | stay-point clustering; night hours → home, day hours → work | est↔true home/work distance (m), fraction of users within threshold | P6.5 |

Note on the `poi_inference` synthetic scope: the Markov generator emits road-segment
sequences with no coordinates or timestamps, so the synthetic branch is not usable in
practice today — only `protected` releases are meaningful
(see the class docstring in `src/trajguard/attacks/attribute.py`).

Utility metrics for trade-off curves: cell-visit JS divergence, OD-matrix error,
length/duration/speed distribution error, range-count query error.

## Experiment config (design §8)

Top-level YAML keys: `experiment`, `map`, `dataset`, `cleaning`, `map_matching`,
`split`, `privacy_mechanisms`, `synthetic_generators`, `attacks`, `metrics`,
`reporting`. List-valued params (e.g. `epsilon: [0.1, 1, 10]`,
`known_points: [3, 5, 10]`) expand into a grid of runs, each with its own version
key and seed. Parsed with plain PyYAML + manual validation — no Hydra/OmegaConf.
Full annotated example: design §8. Entry point: `trajguard run <config>` (argparse,
registered under `[project.scripts]`).

`dataset.representation` selects the pipeline: `segments` (default; `map` and
`map_matching` mandatory, the pool is map-matched) or `cells` (`dataset.grid:
{n_rows, n_cols, bbox: [min_lon, min_lat, max_lon, max_lat]}` mandatory, `map` and
`map_matching` optional and never built, the pool is the grid-cell chain of every
clean trajectory). In `cells` only `membership_inference` is accepted,
`privacy_mechanisms` must be empty, and a generator arm may name `bbox` / `n_rows` /
`n_cols` only with the grid's own values. The pool-cache hash adds `representation`
and `grid` in `cells` only, so segments caches keep their keys.

Seeds come in two kinds: `experiment.split_seed` (defaults to `experiment.seed`)
pins the population — the optional `dataset.max_users` user subsample and the
train/test/shadow/attack split — while `experiment.seed` drives everything
stochastic downstream (mechanism noise, attacker knowledge, bootstrap). Repetition
runs therefore pin `split_seed` in the YAML and vary only the run seed via
`trajguard run <config> --seed N`, which shares the processed pool cache and
writes results to `<output_dir>/seedN`.

## Repo layout (design §9)

```
trajguard/
├── config/                  # experiment YAMLs (config/experiments/) + defaults
├── data/
│   ├── raw/                 # untouched source datasets — NEVER write here
│   ├── interim/             # CleanTrajectory        ┐
│   ├── processed/           # MatchedTrajectory      │ regenerable caches,
│   ├── protected/           # protected versions     │ keyed by version hash
│   └── synthetic/           # synthetic trajectories ┘
├── maps/                    # built road graphs (expensive OSM builds)
├── src/trajguard/
│   ├── maps/                # MapSource + OSM implementation
│   ├── datasets/            # DatasetLoader + Geolife, cleaning, split
│   ├── matching/            # MapMatcher + leuven (fmm later)
│   ├── representation/      # TrajectoryView adapters
│   ├── privacy/             # PrivacyMechanism + mechanisms
│   ├── synthesis/           # SyntheticGenerator + generators
│   ├── attacks/             # Attack + 4 attack families
│   ├── evaluation/          # Metric + metrics, bootstrap CI
│   ├── experiments/         # orchestrator, registry, seeding, versioning
│   ├── reporting/           # tables, plots, results-table schema + read-back I/O
│   └── datamodel/           # frozen dataclass entities
├── notebooks/               # sanity checks, pipeline walkthrough, S4 analysis
├── results/                 # experiment outputs
├── reports/                 # generated reports
├── tests/                   # fixture-based; runs in seconds, no network
├── pyproject.toml
└── README.md
```

## MVP boundaries (design §10; plan "horizon B")

Out of scope until explicitly requested: T-Drive/Porto loaders, PostGIS, MLflow,
k-anonymity, diffusion generators (Diff-RNTraj/ControlTraj), full attribute
inference with a classifier, federated approaches. `RNLDPSynth` has a working v1
prototype (registered as `rn_ldp_synth`; design in `docs/RN_LDP_SYNTH_DESIGN.md`);
further RN-LDP-Synth development happens only on explicit request, and the benchmark
must keep running on baseline mechanisms without it. The first external baseline
candidate is in: `LDPTraceGenerator` (registered as `ldptrace`, plan in
`docs/NACRT_MEHANIZMI.md` §2) synthesizes grid-cell walks under per-trajectory
ε-LDP and emits cell indices, not edge sequences — decoding cells back to roads is a
separate, later step. Everything else attaches later through the existing ABCs
without touching the core — that is the point of the interfaces.
