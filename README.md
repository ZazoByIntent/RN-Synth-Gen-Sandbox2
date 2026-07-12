# trajguard

Trajectory privacy attack & protection benchmark (doctoral research project).

- Full design: `docs/Tehnicna_zasnova_eksperimentalno_okolje.md`
- Phased implementation plan: `docs/IMPLEMENTATION_PLAN.md`

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
