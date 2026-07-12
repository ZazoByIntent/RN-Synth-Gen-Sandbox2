# trajguard — Claude Code project guide

Trajectory privacy attack & protection benchmark. Python research codebase for a
doctoral project. This file is the constitution for the repo; read it every session.

## Status

**All phases P0–P7 are implemented and merged; RN-LDP-Synth has a working v1
prototype (see `docs/RN_LDP_SYNTH_DESIGN.md`). Next: systematic parameter-sweep
runs (S4) and follow-up work.**
Whoever completes a phase updates this line in the same PR.

## Doc map (read on demand — do not load everything up front)

- `docs/ARCHITECTURE.md` — English quick reference: the seven ABCs and registry,
  datamodel, data flow, map/dataset consistency table, repo layout, config shape.
  Read this before writing any code.
- `docs/IMPLEMENTATION_PLAN.md` — phases P0→P7 with scope and definition of done.
  Read only the current phase (see Status above).
- `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` — full design rationale
  (Slovenian, ~550 lines). Open a specific section only when the two files above
  leave a question open. On conflict, the design doc beats ARCHITECTURE.md (then
  fix ARCHITECTURE.md in the same PR); the golden rules below beat both.
- `docs/PROMPTS.md` — per-phase prompts the maintainer pastes into fresh sessions.
  Not standing instructions — act on them only when pasted.
- `docs/RUNNING.md` — setup and every runnable entry point (tests, map builds,
  sanity notebook, experiments, report, RN-LDP-Synth sweep) with expected outputs
  and troubleshooting. Read when running things or diagnosing a run.
- `docs/CODEBASE_PHASE_GUIDE.md` — plain-language walkthrough of the whole codebase;
  `docs/CODEBASE_STRUCTURE.md` — layout and design decisions for new developers;
  `docs/RN_LDP_SYNTH_DESIGN.md` — design of the RN-LDP-Synth v1 mechanism.

For a typical task, this file + ARCHITECTURE.md + the current phase of the plan is
enough context.

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
- **RN-LDP-Synth stays a `NotImplementedError` hook** until explicitly told otherwise.
  The benchmark must run on baseline mechanisms without it.

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
