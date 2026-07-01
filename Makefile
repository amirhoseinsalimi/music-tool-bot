BOT_NAME      ?= music-tool-bot
ENTRYPOINT    ?= bot.py
MIGRATIONS_DIR?= database/migrations
SEEDS_DIR     ?= database/seeds

COMPOSE       ?= docker compose
COMPOSE_PROD  ?= $(COMPOSE) -f docker-compose.yaml -f docker-compose.prod.yaml

.DEFAULT_GOAL := help

.PHONY: help install dev deploy db-migrate db-refresh db-status db-seed test t show-python

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

deploy: ## Deploy a new version (Docker): rebuild and recreate the bot (near-zero downtime), then refresh the sidecar services
	$(COMPOSE_PROD) build bot
	$(COMPOSE_PROD) up -d bot
	$(COMPOSE_PROD) up -d --force-recreate sweeper backup

db-migrate: ## Run database migrations
	poetry run masonite-orm migrate -d $(MIGRATIONS_DIR)

db-refresh: ## Roll back all migrations and re-run them (destructive)
	poetry run masonite-orm migrate:refresh -d $(MIGRATIONS_DIR)

db-status: ## Print the status of migrations
	poetry run masonite-orm migrate:status -d $(MIGRATIONS_DIR)

db-seed: ## Run all database seeders (DatabaseSeeder)
	poetry run masonite-orm seed:run -d $(SEEDS_DIR)

test: ## Run the test suite (not implemented yet)
	@echo "Not implemented yet"

t: test
