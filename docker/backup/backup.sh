#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION="${BACKUP_RETENTION:-7}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_DATABASE="${DB_DATABASE:-}"
DB_USERNAME="${DB_USERNAME:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
DATA_DIR="${DATA_DIR:-/data}"
BACKUP_INTERVAL="${BACKUP_INTERVAL:-86400}"

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

do_backup() {
    log "=== Starting backup: ${TIMESTAMP} ==="

    if [[ -n "${DB_DATABASE}" && -n "${DB_USERNAME}" && -n "${DB_PASSWORD}" ]]; then
        DB_DUMP_FILE="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"
        log "Backing up PostgreSQL database '${DB_DATABASE}' -> ${DB_DUMP_FILE}"

        if PGPASSWORD="${DB_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USERNAME}" \
            -d "${DB_DATABASE}" \
            --clean \
            --if-exists \
            --no-owner \
            --no-privileges \
            | gzip > "${DB_DUMP_FILE}"; then
            log "PostgreSQL backup completed: $(du -h "${DB_DUMP_FILE}" | cut -f1)"
        else
            log "ERROR: PostgreSQL backup failed — removing partial dump"
            rm -f "${DB_DUMP_FILE}"
        fi
    else
        log "WARNING: DB_DATABASE, DB_USERNAME, or DB_PASSWORD not set — skipping PostgreSQL backup"
    fi

    DATA_ARCHIVE="${BACKUP_DIR}/bot_data_${TIMESTAMP}.tar.gz"
    if [[ -d "${DATA_DIR}" && -n "$(ls -A "${DATA_DIR}" 2>/dev/null)" ]]; then
        log "Archiving bot data '${DATA_DIR}' -> ${DATA_ARCHIVE}"

        # NOTE: this image is Alpine (postgres:16-alpine) and ships BusyBox tar,
        # which does NOT support GNU options like --transform. Archive the
        # directory contents directly (-C "${DATA_DIR}" .) instead. Success is
        # judged by "archive exists and is non-empty", not by exit code, since
        # tar exit-code semantics differ between BusyBox and GNU and a live data
        # dir can make tar exit non-zero even when the archive is fine.
        tar -czf "${DATA_ARCHIVE}" -C "${DATA_DIR}" . 2>/dev/null \
            && tar_status=0 || tar_status=$?

        if [[ -s "${DATA_ARCHIVE}" ]]; then
            log "Bot data archive completed (tar exit ${tar_status}): $(du -h "${DATA_ARCHIVE}" | cut -f1)"
        else
            log "ERROR: bot data archive failed (tar exit ${tar_status}) — removing partial archive"
            rm -f "${DATA_ARCHIVE}"
        fi
    else
        log "WARNING: '${DATA_DIR}' is empty or does not exist — skipping bot data archive"
    fi

    log "Cleaning up backups older than ${BACKUP_RETENTION} days..."
    find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +"${BACKUP_RETENTION}" -delete 2>/dev/null || true
    find "${BACKUP_DIR}" -type f -name "*.tar.gz" -mtime +"${BACKUP_RETENTION}" -delete 2>/dev/null || true

    log "=== Backup completed successfully ==="
    echo
}

log "Backup service started"
log "  Interval:  ${BACKUP_INTERVAL}s ($(( BACKUP_INTERVAL / 3600 ))h)"
log "  Retention: ${BACKUP_RETENTION} days"
log "  Backup dir: ${BACKUP_DIR}"
log "  DB host:    ${DB_HOST}:${DB_PORT}/${DB_DATABASE}"
log "  Data dir:   ${DATA_DIR}"
echo

do_backup || log "ERROR: backup cycle failed — will retry next interval"

while true; do
    log "Next backup in $(( BACKUP_INTERVAL / 3600 )) hour(s)..."
    sleep "${BACKUP_INTERVAL}"
    TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
    do_backup || log "ERROR: backup cycle failed — will retry next interval"
done