#!/usr/bin/env bash
set -euo pipefail

# Compose validates the bot service's `env_file: .env` path even when an
# alternate interpolation env file is supplied. Create an empty placeholder
# only when needed, and remove only the file this check created.
created_env_file=false
if [[ ! -e .env ]]; then
  : > .env
  created_env_file=true
fi

cleanup() {
  if [[ "$created_env_file" == true ]]; then
    python3 -c 'from pathlib import Path; Path(".env").unlink(missing_ok=True)'
  fi
}
trap cleanup EXIT

compose=(docker compose --env-file /dev/null)

for state in unset empty; do
  if [[ "$state" == unset ]]; then
    if env -u DB_PASSWORD "${compose[@]}" -f docker-compose.yaml config --quiet >/dev/null 2>&1; then
      echo "Compose accepted an unset DB_PASSWORD" >&2
      exit 1
    fi
  elif DB_PASSWORD= "${compose[@]}" -f docker-compose.yaml config --quiet >/dev/null 2>&1; then
    echo "Compose accepted an empty DB_PASSWORD" >&2
    exit 1
  fi
done

# Development and production overlays remain renderable when an operator supplies
# a password. This placeholder is used only for config validation and is not a secret.
env DB_PASSWORD=local-test-only DB_USERNAME=local_user DB_DATABASE=local_db \
  DATA_DIR=/data BACKUP_INTERVAL=86400 BACKUP_RETENTION=7 \
  SWEEPER_RETENTION_DAYS=30 SWEEPER_INTERVAL=86400 "${compose[@]}" \
  -f docker-compose.yaml -f docker-compose.dev.yaml config --quiet
env DB_PASSWORD=local-test-only DB_USERNAME=local_user DB_DATABASE=local_db \
  DATA_DIR=/data BACKUP_INTERVAL=86400 BACKUP_RETENTION=7 \
  SWEEPER_RETENTION_DAYS=30 SWEEPER_INTERVAL=86400 "${compose[@]}" \
  -f docker-compose.yaml -f docker-compose.prod.yaml config --quiet

env DB_PASSWORD=local-test-only DB_USERNAME=local_user DB_DATABASE=local_db \
  APP_ENV=production COMPOSE_PROJECT_NAME=music-tool-bot \
  GRAFANA_CLOUD_LOKI_URL=https://logs.example.invalid/loki/api/v1/push \
  GRAFANA_CLOUD_LOKI_USERNAME=local-test-user GRAFANA_CLOUD_API_KEY=local-test-key \
  DOCKER_CONTAINER_LOGS_DIR=/var/lib/docker/containers "${compose[@]}" \
  -f docker-compose.yaml -f docker-compose.grafana.yaml config --quiet

echo "Compose rejects a missing database password and renders development, production, and Grafana overlays."
