#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
SWEEPER_RETENTION_DAYS="${SWEEPER_RETENTION_DAYS:-30}"
SWEEPER_INTERVAL="${SWEEPER_INTERVAL:-86400}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

do_sweep() {
    log "=== Starting sweep cycle ==="

    DOWNLOADS_DIR="${DATA_DIR}/downloads"

    if [[ ! -d "${DOWNLOADS_DIR}" ]]; then
        log "Downloads directory '${DOWNLOADS_DIR}' does not exist — nothing to sweep"
        return
    fi

    log "Sweeping files older than ${SWEEPER_RETENTION_DAYS} days in ${DOWNLOADS_DIR}..."

    OLD_FILES=$(find "${DOWNLOADS_DIR}" -type f -mtime +"${SWEEPER_RETENTION_DAYS}" 2>/dev/null || true)

    if [[ -z "${OLD_FILES}" ]]; then
        log "No files older than ${SWEEPER_RETENTION_DAYS} days found"
    else
        COUNT=$(echo "${OLD_FILES}" | wc -l)
        find "${DOWNLOADS_DIR}" -type f -mtime +"${SWEEPER_RETENTION_DAYS}" -delete 2>/dev/null || true
        log "Deleted ${COUNT} file(s) older than ${SWEEPER_RETENTION_DAYS} days"
    fi

    find "${DOWNLOADS_DIR}" -type d -empty -delete 2>/dev/null || true
    log "Removed empty user directories"

    log "=== Sweep cycle completed ==="
    echo
}

log "Sweeper service started"
log "  Interval:     ${SWEEPER_INTERVAL}s ($(( SWEEPER_INTERVAL / 3600 ))h)"
log "  Retention:    ${SWEEPER_RETENTION_DAYS} days"
log "  Data dir:     ${DATA_DIR}"
log "  Downloads:    ${DOWNLOADS_DIR}"
echo

do_sweep

while true; do
    log "Next sweep in $(( SWEEPER_INTERVAL / 3600 )) hour(s)..."
    sleep "${SWEEPER_INTERVAL}"
    do_sweep
done