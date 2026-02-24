#!/usr/bin/env bash
set -euo pipefail

: "${DATA_DIR:=/data}"
DB_CONNECTION="${DB_CONNECTION:-sqlite}"
mkdir -p "${DATA_DIR}"

if [[ "${DB_CONNECTION}" == "sqlite" ]]; then
  if [[ -n "${DB_NAME:-}" ]] && [[ "${DB_NAME}" != /* ]]; then
    DB_NAME="${DATA_DIR}/${DB_NAME}"
  fi

  if [[ -z "${DB_DATABASE:-}" && -n "${DB_NAME:-}" ]]; then
    export DB_DATABASE="${DB_NAME}"
  fi

  if [[ -n "${DB_DATABASE:-}" && "${DB_DATABASE}" != /* ]]; then
    DB_DATABASE="${DATA_DIR}/${DB_DATABASE}"
    export DB_DATABASE
  fi

  if [[ -n "${DB_DATABASE:-}" ]]; then
    mkdir -p "$(dirname "${DB_DATABASE}")"
  fi
fi

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
