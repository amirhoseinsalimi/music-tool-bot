BOT_NAME      ?= music-tool-bot
ENTRYPOINT    ?= bot.py
MIGRATIONS_DIR?= database/migrations
SEEDS_DIR     ?= database/seeds

COMPOSE       ?= docker compose
COMPOSE_PROD  ?= $(COMPOSE) -f docker-compose.yaml -f docker-compose.prod.yaml
TEST_DB_PORT  ?= 6013

.DEFAULT_GOAL := help

.PHONY: help install dev deploy db-migrate db-refresh db-status db-seed db-schema-check db-upgrade test t show-python
.PHONY: admin-bridge test-admin-bridge

help:
	@echo "Available commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sed -e 's/Makefile://g' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies into the Poetry venv
	poetry install

show-python: ## Print the Python interpreter Poetry resolves to
	@echo "Python:" && poetry run python -V
	@echo "Path:  " && poetry run which python

dev: ## Run the bot locally with hot reload (jurigged)
	poetry run jurigged -v $(ENTRYPOINT)

deploy: ## Deploy a new version (Docker): rebuild and recreate the bot (near-zero downtime), then refresh the backup service
	$(COMPOSE_PROD) build bot
	$(COMPOSE_PROD) up -d bot
	$(COMPOSE_PROD) up -d --force-recreate backup

db-migrate: ## Run database migrations
	poetry run masonite-orm migrate -d $(MIGRATIONS_DIR)

db-refresh: ## Roll back all migrations and re-run them (destructive)
	poetry run masonite-orm migrate:refresh -d $(MIGRATIONS_DIR)

db-status: ## Print the status of migrations
	poetry run masonite-orm migrate:status -d $(MIGRATIONS_DIR)

db-seed: ## Run all database seeders (DatabaseSeeder)
	poetry run masonite-orm seed:run -d $(SEEDS_DIR)

db-schema-check: ## Refuse to proceed unless every migration in this release is applied
	poetry run python -m utils.schema_guard

db-upgrade: ## Apply migrations, idempotent reference seeds, and verify the schema
	$(MAKE) db-migrate
	$(MAKE) db-seed
	$(MAKE) db-schema-check

test: ## Run the test suite (not implemented yet)
	@echo "Not implemented yet"

t: test

admin-bridge: ## Run the optional read-only admin bridge on loopback
	poetry run python -m admin_bridge

test-admin-bridge: ## Run bridge tests with an isolated disposable PostgreSQL container
	@set -eu; \
	cleanup() { $(COMPOSE) -f docker-compose.test.yaml down --remove-orphans; }; \
	trap cleanup EXIT INT TERM; \
	$(COMPOSE) -f docker-compose.test.yaml up -d --wait db_test; \
	TEST_DATABASE_URL=postgresql://musictoolbot_test:disposable-test-only@127.0.0.1:$(TEST_DB_PORT)/musictoolbot_tests \
	PYTHONPATH=tests/runtime:tests poetry run python -m unittest discover -s tests/bridge -v; \
	TEST_DATABASE_URL=postgresql://musictoolbot_test:disposable-test-only@127.0.0.1:$(TEST_DB_PORT)/musictoolbot_tests \
	PYTHONPATH=tests/runtime:tests poetry run python -m unittest -v \
	test_control_handlers.RegisteredControlTests.test_control_database_outage_uses_cached_values_for_free_tools_only
