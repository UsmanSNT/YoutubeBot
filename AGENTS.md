# Repository Guidelines

## Project Structure & Module Organization
- bot/: source code (handlers/, services/, telegram_api/, utils/)
- tests/: pytest suites (unit/, integration/, security/)
- data/: app state (bot.db, temp/ for downloads)
- run.py: local entrypoint; Makefile: common tasks; pyproject.toml: deps and tooling; docker-compose.yml/Dockerfile for container use.

## Build, Test, and Development Commands
- `make init`: install runtime deps with uv and create `.env` from example.
- `make init-dev`: install with dev extras (pytest, ruff, mypy, WPS).
- `make run`: start the Telegram bot (`aiogram` polling).
- `make tests`: run pytest with coverage and HTML report.
- `make test tests/unit/test_config.py::test_validate_all_success`: run a specific test.
- `make format` / `make lint` / `make lint-all`: format and lint (Ruff, wemake).
- `make mypy` / `make check`: type-check, or all checks (format+lint+mypy).
- `make docker-start`: run via Docker; `make docker-stop` to stop.

## Coding Style & Naming Conventions
- Python 3.13+, 4-space indent, max line length 120, double quotes.
- Tools: Ruff (with isort), wemake-python-styleguide (via flake8), mypy (strict).
- Naming: modules/files snake_case; functions/methods snake_case; classes PascalCase; constants UPPER_SNAKE.
- Prefer type hints and small, focused functions; use `loguru` for logging.

## Testing Guidelines
- Framework: pytest (+ pytest-asyncio, xdist, coverage). Minimum coverage enforced at 85%.
- Locations: `tests/unit/**`, `tests/integration/**`, `tests/security/**`.
- Markers: `unit`, `integration`, `slow`, `smoke`. Example: `uv run pytest -m "unit and not slow" -nauto`.
- Naming: files `test_*.py`, classes `Test*`, functions `test_*`.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:` (matches git history).
- Before opening a PR: run `make check` and `make tests`; update/add tests; update docs when behavior changes.
- PR description: purpose, scope, linked issues, test notes (include failing/reproducing command), and config changes (update `.env.example`).

## Security & Configuration Tips
- Do not commit secrets. Configure via `.env` (see `.env.example`): `TELEGRAM_TOKEN`, `ADMIN_USER_ID`, etc.
- Keep downloads/temp files under `data/` only. Avoid network calls in unit tests; mock external services and I/O.
- When adding settings, validate in `bot/config.py` and document defaults.

