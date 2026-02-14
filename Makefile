BOT_NAME      ?= music-tool-bot
ENTRYPOINT    ?= bot.py
MIGRATIONS_DIR?= database/migrations
SEEDS_DIR     ?= database/seeds
SEED_CLASS    ?= Owner

.DEFAULT_GOAL := help

.PHONY: help install dev start restart stop db-migrate db-refresh db-status db-seed test t show-python

help:
	@echo "Available commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sed -e 's/Makefile://g' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:
	poetry install

show-python:
	@echo "Python:" && poetry run python -V
	@echo "Path:  " && poetry run which python

dev:
	poetry run jurigged -v $(ENTRYPOINT)

start:
	pm2 start --name "$(BOT_NAME)" $(ENTRYPOINT) --time --interpreter python

restart:
	pm2 restart "$(BOT_NAME)"

stop:
	pm2 stop "$(BOT_NAME)"

db-migrate:
	poetry run masonite-orm migrate -d $(MIGRATIONS_DIR)

db-refresh:
	poetry run masonite-orm migrate:refresh -d $(MIGRATIONS_DIR)

db-status:
	poetry run masonite-orm migrate:status -d $(MIGRATIONS_DIR)

db-seed:
	poetry run masonite-orm seed:run $(SEED_CLASS) -d $(SEEDS_DIR)

test:
	@echo "Not implemented yet"

t: test
