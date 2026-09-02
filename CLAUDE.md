# trajguard — Claude Code project guide

Trajectory privacy attack & protection benchmark. Python research codebase for a
doctoral project. This file is the constitution for the repo; read it every session.

## Status

**All phases P0–P7 are implemented and merged; RN-LDP-Synth has a working v1
prototype. The S4 campaign is measured on all three rungs of the sample ladder
(20 / 50 / 182 users); the report reads from the 182-user reporting run of
18–21 Aug 2026 (threshold 0.3, budget 1200 s). Measured values per rung and the
list of open items: `docs/HANDOFF.md`. Protection-mechanism breadth per
`docs/NACRT_MEHANIZMI.md`: ZM-1 LDPTrace is implemented (generator `ldptrace`,
baseline candidate) and measured at the 20-user rung on 2 Sep 2026 (rows in
`docs/HANDOFF.md` §2.3); its validation against the authors' code is planned in
`docs/NACRT_LDPTRACE_VALIDACIJA.md` (not started); ZM-2 … ZM-4 are open.**
Whoever changes the project state (a new
run, a closed item, a new component) updates this line in the same PR.

## Doc map — read on demand, never all at once

Every session reads this file. Open a document below **only when its trigger
applies to the task at hand**, and open the smallest part that answers the
question (a section, not the file). For a typical coding task this file plus
`docs/ARCHITECTURE.md` is enough context.

- `docs/ARCHITECTURE.md` (English) — the seven ABCs and registry, datamodel, data
  flow, map/dataset consistency table, repo layout, config shape.
  **Read before writing any code.**
- `docs/RUNNING.md` (English, ~690 lines) — every runnable entry point with expected
  output and troubleshooting; table of contents at the top. **Read only the section
  for the command you are running or diagnosing** (find it by its § number), never
  the whole file.
- `docs/HANDOFF.md` (Slovenian) — measured record of the S4 campaign per rung
  (20/50/182) and the list of open items. **Read when planning the next piece of
  work, when the report needs a measured number, or when the user mentions S4, a
  rung, or a label such as S4-2, A3, M2.**
- `docs/NACRT_MEHANIZMI.md` (Slovenian) — implementation plan for the next protection
  mechanisms, one section per step: ZM-1 LDPTrace, ZM-2 point LDP, ZM-3 naive
  baselines, ZM-4 PrivTrace, with design decisions, files to touch, tests, and the
  session prompt. **Read only the section for the step you are implementing, or when
  the user mentions a ZM label.**
- `docs/NACRT_LDPTRACE_VALIDACIJA.md` (Slovenian) — plan and handoff for validating the
  `ldptrace` port against the authors' code: the paper's utility metrics, a raw-coordinate
  grid input mode (`dataset.representation: cells`), the Porto comparison run, and the
  session prompt. **Read in full only when implementing that validation or when the user
  mentions LDPTrace metrics, cells mode, or Porto.**
- `docs/REZULTATI_SHEMA.md` (Slovenian) — the `results.csv` column schema and its
  consumers. **Read only when touching `results.csv` columns or
  `reporting/results_schema.py`, `results_io.py`, `report.py`, `plots.py`, or
  notebook 03.** A test pins this doc to the code; the file must stay where it is.
- `docs/RN_LDP_SYNTH_DESIGN.md` (English) — design, privacy proof and fixture-scale
  evidence of RN-LDP-Synth. **Read only when working on `synthesis/rn_ldp_synth.py`
  or `privacy/ldp.py`, or when interpreting `rn_ldp_synth` results.**
- `docs/CODEBASE_STRUCTURE.md` (English) — the reasoning behind the layout and the
  design decisions, written for a new developer. **Read only when asked to explain
  the design, onboard someone, or justify why something is built the way it is.**
  Not needed for ordinary coding.
- `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` (Slovenian, ~550 lines) — the
  original design document. **Open one section by its § number only when
  ARCHITECTURE.md leaves a question open.** On conflict the design doc beats
  ARCHITECTURE.md (fix ARCHITECTURE.md in the same PR); the golden rules below beat
  both.
- `arhiv/` — closed documents (phase plan and prompts P0–P7, the historical
  phase-by-phase codebase guide, the full HANDOFF history, the S4 fix plan);
  `arhiv/README.md` lists them. **Never read unless the user explicitly asks for
  history.** Nothing in there is a standing instruction.

## Golden rules

- Work in **vertical slices**: get one path running end-to-end before adding breadth.
  Never scaffold a module you are not about to use in the current phase.
- Every new attack / mechanism / dataset / matcher **subclasses the relevant ABC**
  (`MapSource`, `DatasetLoader`, `MapMatcher`, `PrivacyMechanism`,
  `SyntheticGenerator`, `Attack`, `Metric`) and registers via `@register(kind, name)`
  from `trajguard/experiments/registry.py`. Never bypass the interfaces.
- `data/raw/` is **immutable** — never write to it. `interim/ processed/ protected/
  synthetic/` are regenerable caches keyed by a version hash.
- **Determinism**: every stochastic step takes an explicit `seed` from config.
  No bare `random` / `np.random` — always a seeded `np.random.Generator`.
- The train/test/shadow/attack **split happens once**, at `CleanTrajectory` level,
  with a fixed seed; the `split` label propagates through every downstream artifact,
  and shadow models train strictly on their own split. This keeps MIA honest.
- **Map/dataset consistency**: the orchestrator must reject any run where
  `map.region != dataset.native_region`. Geolife/T-Drive → Beijing; Porto → Porto.
  Ljubljana is reserved for synthetic data / RN-LDP-Synth, never for Geolife attacks.
- **RN-LDP-Synth has a working v1 prototype** (`rn_ldp_synth` in the registry; design in
  `docs/RN_LDP_SYNTH_DESIGN.md`). Develop it further only when explicitly told to, and
  the benchmark must keep running on baseline mechanisms without it.

## Conventions

- Python 3.11+, package under `src/trajguard/`. Env with `uv`, lint/format with
  `ruff`, types with `mypy`, tests with `pytest`.
- Data on disk as **Parquet**; query with **DuckDB**. No PostGIS in the MVP.
- **Lean dependencies**: config via plain PyYAML (no Hydra/OmegaConf), datamodel as
  frozen dataclasses (no pydantic unless YAML validation demands it), CLI via argparse.
  Adding a new dependency requires a one-line justification in the PR description.
- Docs under `docs/` are in Slovenian; write all code, identifiers, docstrings,
  comments, and tests in English.
- Tests never hit the network and never read `data/` — they run only against the
  committed fixtures in `tests/fixtures/`.
- Public functions get type hints and a one-line docstring. No dead scaffolding,
  no speculative abstraction beyond the seven ABCs.
- Commits small and scoped. One phase = one branch = one PR.

## Definition of done (applies to every task)

1. `ruff check` and `mypy` are clean.
2. A test exists and passes against the `tests/` fixture (~20 trajectories);
   the whole suite runs in seconds.
3. You **show the evidence**: paste the exact command you ran and its output.
   Do not assert "it works" — prove it with the test output or a small run.

## How to work in this repo

- Start any non-trivial task in **plan mode**. Show the plan, wait for my approval
  before editing files.
- Use a **subagent** for research-heavy reading (e.g. how a library expects input),
  so the main context stays clean.
- If a task would touch more than ~5 files or mixes concerns, **stop and propose a
  split** instead of doing it all at once.
- Prefer editing existing files over creating new ones unless the design calls for a
  new module.

## Communication style

Applies to everything addressed to me: plans, proposals, highlighted issues, summaries.

- **Plain language.** I am technically capable but not an expert in every domain this
  project touches — explain as you would to a colleague from a neighbouring field.
- **No unexplained jargon or abbreviations.** If a technical term or acronym is
  unavoidable, spell it out and add a few words of explanation on first use.
- **Brief, but never at the cost of clarity**: lead with the main point, cut filler.
- When presenting a plan, an idea, or a problem, say what it means **in practice** —
  what changes, what could break, what I need to decide — not just its technical name.
- No sentence fragments, arrow chains, or shorthand invented mid-task; write full
  sentences that can be followed without re-reading.
