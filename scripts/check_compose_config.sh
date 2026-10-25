#!/usr/bin/env bash
set -euo pipefail

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

echo "Compose rejects a missing database password and renders both overlays with one supplied."
