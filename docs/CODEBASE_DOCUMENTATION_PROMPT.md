# Prompt for Fable 5: Phase-by-Phase Codebase Documentation

Use this prompt verbatim with Fable 5 (model: `claude-fable-5`). Point it at the `zazobyintent/rn-synth-gen-sandbox2` repository on the `claude/p7-review-fixes` branch (or any branch that contains the full history).

---

## Prompt

You are documenting a research codebase called **trajguard** for its author, who let an AI assistant build most of the code and now wants to understand what every piece does.

### Your task

Go through the entire git history of this repository **phase by phase** (P0 through P7) and produce a single Markdown document called `docs/CODEBASE_PHASE_GUIDE.md`. This document should explain, for each phase:

1. **What was the goal of this phase** — in plain, simple language. Assume the reader has no background in computer science, privacy research, or location data. Avoid abbreviations; when you must use a technical term, define it in parentheses on first use.
2. **Which files were added or significantly changed** — list every file with a one-paragraph explanation of what that file contains and why it exists.
3. **How the pieces connect** — after listing the files, write a short paragraph explaining how the new code in this phase fits together and connects to what was built in earlier phases.

### Repository structure

The commit history is linear. Each commit message starts with a phase label (P0, P1, ... P7). Some phases span multiple commits — group them together. Here is the full commit history in chronological order:

```
7c606c2 Initial commit
f12cd7a Naložen načrt izvedbe
180f0e1 P0: bootstrap skeleton — tooling, datamodel, registry, seven ABCs
59417e0 P1: OSM map source, Geolife loader, trajectory cleaning
e70a410 P2: Leuven map matcher, quality filter, sanity notebook
e201403 P3: by-user split, trajectory views, NoProtection baseline
7ffc735 P4: reidentification attack, metrics+CI, orchestrator, CLI (closes vertical slice)
e91c973 P4 review fixes: registry dispatch, mechanism apply, Parquet cache, loud config validation
5da6f83 Apply ruff format (fixes CI format check)
6b13df8 P5: planar-Laplace GeoIndistinguishability mechanism
620c170 P5: paired-bootstrap utility metrics (cell JSD, length W1)
ec96523 P5: fixed raw-probe population for reidentification across arms
1eaaf19 P5: tradeoff plot helper; matplotlib becomes a runtime dependency
67b4448 P5: mechanism param grid, protected re-matching + cache, utility wiring
4a29921 P5: geolife_geoind_reid experiment config (design §8)
452fff3 P5: readable tradeoff labels (short arm names, alternating offsets)
24ff6ad P6a: MarkovGenerator + shared geometry distances
330ae2b P6b: LiRA-lite membership-inference attack
5a07883 P6c: MAP reconstruction attack against planar-Laplace noise
ff73d61 P6 review fixes: fail fast on unconstructible attacks, Markov cleanups
e2622ef P6.5: PoiInferenceAttack (stay-point home/work inference)
3c41e01 P7: reporting layer — risk matrix, tidy tables, tradeoff plots, Markdown report
6033d06 Review fixes: MIA tie-safe TPR, orchestrator fail-fast for unwired attacks, cache/guard robustness
```

### Source file tree (for reference)

```
src/trajguard/
├── __init__.py
├── geometry.py
├── datamodel/
│   ├── __init__.py
│   └── entities.py
├── datasets/
│   ├── __init__.py
│   ├── base.py
│   ├── cleaning.py
│   ├── geolife.py
│   └── split.py
├── maps/
│   ├── __init__.py
│   ├── base.py
│   ├── build.py
│   └── osm.py
├── matching/
│   ├── __init__.py
│   ├── base.py
│   └── leuven.py
├── privacy/
│   ├── __init__.py
│   ├── base.py
│   ├── geoind.py
│   └── none.py
├── attacks/
│   ├── __init__.py
│   ├── base.py
│   ├── reidentification.py
│   ├── membership.py
│   ├── reconstruction.py
│   └── attribute.py
├── evaluation/
│   ├── __init__.py
│   ├── base.py
│   ├── metrics.py
│   ├── roc.py
│   └── utility.py
├── synthesis/
│   ├── __init__.py
│   ├── base.py
│   └── markov.py
├── representation/
│   ├── __init__.py
│   └── views.py
├── experiments/
│   ├── __init__.py
│   ├── builtins.py
│   ├── cli.py
│   ├── orchestrator.py
│   └── registry.py
└── reporting/
    ├── __init__.py
    ├── report.py
    └── tradeoff.py

tests/
├── conftest.py
├── test_attribute.py
├── test_cleaning.py
├── test_geoind.py
├── test_geolife.py
├── test_geometry.py
├── test_maps.py
├── test_markov.py
├── test_matching.py
├── test_membership.py
├── test_orchestrator.py
├── test_reconstruction.py
├── test_registry.py
├── test_reidentification.py
├── test_reporting.py
├── test_split.py
├── test_utility.py
└── test_views.py

config/
├── maps.yaml
├── defaults/.gitkeep
└── experiments/
    ├── geolife_reid_baseline.yaml
    └── geolife_geoind_reid.yaml

docs/
├── IMPLEMENTATION_PLAN.md
├── PROMPTS.md
└── Tehnicna_zasnova_eksperimentalno_okolje.md
```

### Writing rules

- **Write in plain English.** No jargon without an immediate definition. For example, do not write "LDP" — write "Local Differential Privacy (a mathematical guarantee that limits how much any single person's data can influence the output)."
- **No abbreviations on first use.** After you have defined an abbreviation once, you may use it in later sections.
- **Explain "why", not just "what".** For each file, explain why it needs to exist — what problem does it solve, and what would happen if it were missing.
- **Use analogies where helpful.** For example: "A map matcher is like GPS navigation in reverse — instead of telling you where to go, it figures out which roads you actually drove on based on your recorded GPS dots."
- **Keep paragraphs short** — 3-5 sentences maximum.
- **Use headers and bullet points** for scannability.
- **For each phase, show which files were added or changed** in a bulleted list with the file path in backticks.

### Document structure

Use this exact structure:

```markdown
# Trajguard Codebase Guide — Phase by Phase

> This document explains the entire trajguard codebase, built incrementally
> across eight development phases (P0–P7). It is written for someone with
> no prior knowledge of the project, privacy research, or location data.

## How to read this document
(Brief explanation of what the project is about and how the phases build on each other)

## Pre-phase: Initial setup
(The initial commit and the design document upload — what the repo started with)

## Phase 0 — Project skeleton and building blocks
### Goal
### Files added
### How it fits together

## Phase 1 — Loading real-world data and maps
### Goal
### Files added
### How it fits together

## Phase 2 — Matching GPS points to roads
### Goal
### Files added
### How it fits together

## Phase 3 — Splitting data and preparing for experiments
### Goal
### Files added
### How it fits together

## Phase 4 — The first privacy attack and experiment runner
### Goal
### Files added or changed
### How it fits together

## Phase 5 — Adding a real privacy protection and measuring quality
### Goal
### Files added or changed
### How it fits together

## Phase 6 — More attacks and synthetic data generation
### Goal
### Files added or changed
### How it fits together

## Phase 7 — Automated reporting
### Goal
### Files added or changed
### How it fits together

## Summary: the full picture
(A final section that ties everything together — what the complete system does
from start to finish when you run an experiment)
```

### How to do the work

1. For each phase, use `git diff` or `git show` on the relevant commits to see exactly what changed. You can also read the current state of each file.
2. Read each source file carefully. Understand what every class and function does.
3. Read the corresponding test file to understand the expected behavior.
4. Read the config files to understand how experiments are configured.
5. Cross-reference with `docs/IMPLEMENTATION_PLAN.md` and `docs/Tehnicna_zasnova_eksperimentalno_okolje.md` for context on why things were built the way they were.

### Important notes

- The design document (`Tehnicna_zasnova_eksperimentalno_okolje.md`) is written in Slovenian. You can read it for structural context (section numbers, diagrams, formulas) but focus on the actual code for your explanations.
- Some files were modified across multiple phases. When a file appears again in a later phase, explain what was added or changed and why.
- The test files are important — they show how each component is meant to be used. Mention what the tests verify.
- The config YAML files define experiments. Explain what each config key means in plain language.
- Be thorough. This is meant to be a complete reference that lets someone understand every file in the project without reading the code.
