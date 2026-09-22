---
name: orchestrate
description: Run a larger trajguard task as orchestrator (this session) + fresh Opus implementer subagents + one fresh Fable reviewer. Use when the user says /orchestrate, "orkestriraj", or asks for the orchestrator/implementer/reviewer setup. Not for small fixes.
---

# Orchestrate: plan, delegate, verify

You are the orchestrator. You do not write code yourself; you plan, delegate each
unit to a fresh implementer, and end with an independent review. The point is to keep
this session's context small, so every rule below is about what enters this context.

## 1. Plan (this session)

- Read `CLAUDE.md` (already loaded) and only the section of `docs/ARCHITECTURE.md`
  or the design doc the task needs. Never read a whole file under `docs/`.
- Split the task into units of at most ~5 files each. Show the plan and wait for
  approval before delegating.

## 2. Implement (one fresh subagent per unit)

Spawn with `Agent`, `subagent_type: "general-purpose"`, `model: "opus"`. Never use
`subagent_type: "fork"`. The prompt must contain, verbatim:

- The goal of the unit and the exact files to touch.
- The lines of documentation the unit needs, pasted in (typically 10–40 lines), with
  the instruction: "Do not read any other file under `docs/`."
- The repo rules that apply: subclass the ABC and `@register`; seeded
  `np.random.Generator` only; tests read only `tests/fixtures/`; English code and
  docstrings; `ruff check`, `mypy` and `pytest -q` must pass.
- The return format: "Reply with (a) a 5-line summary of what you changed and why,
  (b) the list of changed files, (c) the exact commands you ran and the last 10 lines
  of each output. No full logs, no file contents."

Run independent units in parallel in one message. Do not re-read the changed files
yourself; trust the summary and move on to the reviewer.

## 3. Review (one fresh subagent)

Spawn with `Agent`, `subagent_type: "general-purpose"`, `model: "fable"`. Prompt:

- "Review the working tree against `main` for correctness, repo-rule violations
  (`CLAUDE.md` golden rules, pasted below) and missing tests. Read `git diff main
  --stat`, then the full diff of the changed files only, run `ruff check`, `mypy` and
  `pytest -q`. Open at most one section of one document under `docs/` if the diff
  refers to it. Do not read anything else."
- Paste the Golden rules section of `CLAUDE.md` into the prompt.
- Return format: "Verdict (merge / fix first), then a numbered list of critical fixes
  with file and line, then minor notes. Under 40 lines."

If the reviewer asks for critical fixes, send them back to a fresh implementer with
the reviewer's list pasted in, then re-run the reviewer once.

## 4. Report to the user

In plain language, following the Communication style section of `CLAUDE.md`: what
was built, the reviewer's verdict, what you decided to leave open, and the evidence
(the last lines of the test output). Do not commit or open a PR unless asked.
