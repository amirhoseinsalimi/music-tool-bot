# Repository Guidelines

## Context and Scope

Read [shared context](../docs/README.md), [decisions](../docs/decisions.md), [code findings](../docs/current-state.md), and [next steps](../docs/next-steps.md). The public bot must run without commercial services. Do not treat the stale `modules/premium/README.md` as an implemented extension contract or stage private code from that scaffold.

## Structure and Style

`bot.py` registers feature handlers before core catch-all handlers. Each `modules/<feature>/` separates handlers, services, utilities and registration. Shared helpers live in `utils/`, configuration in `config/`, core models/migrations/seeds in `database/`, and eight translations in `i18n/`.

Use four-space indentation, snake_case functions/modules and PascalCase classes. Follow surrounding Python conventions; Poetry includes pylint and autopep8. Keep core schema ownership here; private services must not duplicate User/Admin models. Preserve lowercase status slugs `active`, `blocked`, `deleted` and their existing display names.

## Commands and Tests

Run here: `make install` for Poetry dependencies; `make dev` for hot reload with local ffmpeg/PostgreSQL, or `docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up` for the stack. `make db-migrate` and `make db-seed` modify the configured database; `make db-refresh` is destructive.

`make test` is unimplemented. `poetry run python -m unittest discover -s tests/unit` runs sample `test_*.py` tests, including the known `7 != 8` failure. Add meaningful regression tests for changed behavior; no coverage threshold is configured.

## Review and Data Accuracy

Use focused Conventional Commits and describe validation in PRs. Audio counts are submissions, filesystem timestamps are modification times, and latest interaction cannot reconstruct historical daily activity. Preserve current retention unless a change is authorized. Keep tokens, user files and backups out of commits; check public staging before adding optional integrations.
