BOT_NAME      ?= music-tool-bot
ENTRYPOINT    ?= bot.py
MIGRATIONS_DIR?= database/migrations
SEEDS_DIR     ?= database/seeds
SEED_CLASS    ?= Owner

COMPOSE       ?= docker compose
COMPOSE_PROD  ?= $(COMPOSE) -f docker-compose.yaml -f docker-compose.prod.yaml

.DEFAULT_GOAL := help

.PHONY: help install dev start restart stop deploy db-migrate db-refresh db-status db-seed test t show-python

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

start: ## Start the bot in production via pm2
	pm2 start --name "$(BOT_NAME)" $(ENTRYPOINT) --time --interpreter python

restart: ## Restart the pm2 bot process
	pm2 restart "$(BOT_NAME)"

stop: ## Stop the pm2 bot process
	pm2 stop "$(BOT_NAME)"

deploy: ## Deploy a new version (Docker): build the new image, then recreate only the bot with near-zero downtime
	$(COMPOSE_PROD) build bot
	$(COMPOSE_PROD) up -d bot

db-migrate: ## Run database migrations
	poetry run masonite-orm migrate -d $(MIGRATIONS_DIR)

db-refresh: ## Roll back all migrations and re-run them (destructive)
	poetry run masonite-orm migrate:refresh -d $(MIGRATIONS_DIR)

db-status: ## Print the status of migrations
	poetry run masonite-orm migrate:status -d $(MIGRATIONS_DIR)

db-seed: ## Seed the owner-level admin row
	poetry run masonite-orm seed:run $(SEED_CLASS) -d $(SEEDS_DIR)

test: ## Run the test suite (not implemented yet)
	@echo "Not implemented yet"

t: test
