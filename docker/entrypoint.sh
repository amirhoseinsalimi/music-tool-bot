#!/usr/bin/env bash
set -euo pipefail

: "${DATA_DIR:=/data}"
mkdir -p "${DATA_DIR}"

if [[ $# -gt 0 ]]; then
  exec bash -lc "$*"
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

echo ">> Falling back to running package as a module"
exec bash -lc "python -m music_tool_bot"
