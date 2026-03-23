#!/usr/bin/env bash
set -euo pipefail

: "${DATA_DIR:=/data}"
mkdir -p "${DATA_DIR}"
mkdir -p "${DATA_DIR}/downloads"

if [[ $# -gt 0 ]]; then
  exec "$@"
fi

if [[ -n "${START_CMD:-}" ]]; then
  echo ">> Starting via START_CMD: ${START_CMD}"
  exec bash -lc "${START_CMD}"
fi

try_run() {
  local candidate="$1"
  if [[ -f "$candidate" ]]; then
    echo ">> Starting: ${candidate}"
    exec bash -lc "python '${candidate}'"
  fi
}

try_run "bot.py"
try_run "main.py"
try_run "app.py"
try_run "src/main.py"

echo ">> No startup target found. Set START_CMD or provide an explicit command."
exit 1
