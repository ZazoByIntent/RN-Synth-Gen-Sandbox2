# trajguard

Trajectory privacy attack & protection benchmark (doctoral research project).

- Full design: `docs/Tehnicna_zasnova_eksperimentalno_okolje.md`
- Architecture quick reference: `docs/ARCHITECTURE.md`
- How to run everything: `docs/RUNNING.md`
- Project state and open items: `docs/HANDOFF.md`
- Doc map with "read when" rules: `CLAUDE.md`; closed documents: `arhiv/`

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```sh
uv sync
```

## Development

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
