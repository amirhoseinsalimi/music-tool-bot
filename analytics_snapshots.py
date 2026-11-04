"""PostgreSQL-only daily user activity and aggregate stats snapshots."""

import asyncio
import json
import logging
import os
import shutil
from contextlib import closing
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2

from config.constants import DOWNLOAD_DIR_PATH
from config.envs import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USERNAME

logger = logging.getLogger(__name__)
REPORTING_TIMEZONE = ZoneInfo('Asia/Tehran')


def reporting_day(now: datetime | None = None):
    """Return the Tehran calendar date for an aware instant (or the current time)."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    return instant.astimezone(REPORTING_TIMEZONE).date()


def _connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_DATABASE,
        user=DB_USERNAME, password=DB_PASSWORD, connect_timeout=5,
    )


def _record_user_activity_day(user_id: int, day, connect=None):
    with closing((connect or _connect)()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO user_activity_days (user_id, day) VALUES (%s, %s) '
                    'ON CONFLICT (user_id, day) DO NOTHING',
                    (user_id, day),
                )


async def record_user_activity_day(user_id: int, now: datetime | None = None):
    """Idempotently record this user's interaction on the Tehran calendar day."""
    await asyncio.to_thread(_record_user_activity_day, user_id, reporting_day(now))


def _stats_counts(now: datetime, users, known_languages=()):
    """Reduce user rows to the same status and activity windows shown by /stats."""
    statuses = {'active': 0, 'blocked': 0, 'deleted': 0}
    activity = {
        'daily_active_users': 0, 'weekly_active_users': 0,
        'monthly_active_users': 0, 'active_90d_users': 0,
        'inactive_users': 0,
    }
    language_counts = {
        language: {'active': 0, 'blocked': 0, 'deleted': 0}
        for language in known_languages if language
    }
    cutoffs = {
        'day': now - timedelta(hours=24),
        'week': now - timedelta(hours=168),
        'month': now - timedelta(hours=31 * 24),
        'active': now - timedelta(days=90),
    }
    for status, language, last_interaction in users:
        status = status if status in statuses else 'active'
        statuses[status] += 1
        if language:
            counts = language_counts.setdefault(
                language, {'active': 0, 'blocked': 0, 'deleted': 0},
            )
            counts[status] += 1
        if last_interaction is None:
            activity['inactive_users'] += 1
            continue
        if last_interaction.tzinfo is not None:
            last_interaction = last_interaction.astimezone(timezone.utc).replace(tzinfo=None)
        if last_interaction >= cutoffs['day']:
            activity['daily_active_users'] += 1
            activity['weekly_active_users'] += 1
            activity['monthly_active_users'] += 1
            activity['active_90d_users'] += 1
        elif last_interaction >= cutoffs['week']:
            activity['weekly_active_users'] += 1
            activity['monthly_active_users'] += 1
            activity['active_90d_users'] += 1
        elif last_interaction >= cutoffs['month']:
            activity['monthly_active_users'] += 1
            activity['active_90d_users'] += 1
        elif last_interaction >= cutoffs['active']:
            activity['active_90d_users'] += 1
    return statuses, activity, language_counts


def _filesystem_counts(downloads_dir: Path, disk_usage):
    file_count = len(os.listdir(downloads_dir)) if downloads_dir.is_dir() else 0
    file_bytes = 0
    if downloads_dir.is_dir():
        for path in downloads_dir.rglob('*'):
            try:
                if path.is_file() and not path.is_symlink():
                    file_bytes += path.stat().st_size
            except OSError:
                logger.warning('Could not count a file in the downloads directory')
    usage = disk_usage('/')
    return file_count, file_bytes, usage.used, usage.total


def _write_daily_stats_snapshot(now: datetime, downloads_dir: Path, disk_usage, connect):
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    captured_at = now.astimezone(timezone.utc)
    day = captured_at.astimezone(REPORTING_TIMEZONE).date()
    query_now = captured_at.replace(tzinfo=None)
    with closing(connect()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT COALESCE(s.slug, 'active'), l.iso, u.last_interaction_at
                    FROM users AS u
                    LEFT JOIN user_statuses AS s ON s.id = u.user_status_id
                    LEFT JOIN languages AS l ON l.id = u.language_id
                ''')
                users = [
                    tuple(row.values()) if hasattr(row, 'values') else row
                    for row in cursor.fetchall()
                ]
                cursor.execute('SELECT iso FROM languages ORDER BY id')
                known_languages = [row['iso'] if hasattr(row, 'keys') else row[0]
                                   for row in cursor.fetchall()]
                statuses, activity, language_counts = _stats_counts(
                    query_now, users, known_languages,
                )
                file_count, file_bytes, disk_used, disk_total = _filesystem_counts(
                    downloads_dir, disk_usage,
                )
                values = (
                    day, len(users), statuses['active'], statuses['blocked'], statuses['deleted'],
                    activity['daily_active_users'], activity['weekly_active_users'],
                    activity['monthly_active_users'], activity['active_90d_users'],
                    activity['inactive_users'],
                    json.dumps(language_counts), file_count, file_bytes, disk_used, disk_total,
                    captured_at,
                )
                cursor.execute('''
                    INSERT INTO daily_stats_snapshot (
                        day, total_users, active_users, blocked_users, deleted_users,
                        daily_active_users, weekly_active_users, monthly_active_users,
                        active_90d_users, inactive_users,
                        language_status_counts, file_count, file_bytes,
                        disk_used_bytes, disk_total_bytes, captured_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s, %s, %s, %s
                    ) ON CONFLICT (day) DO UPDATE SET
                        total_users = EXCLUDED.total_users,
                        active_users = EXCLUDED.active_users,
                        blocked_users = EXCLUDED.blocked_users,
                        deleted_users = EXCLUDED.deleted_users,
                        daily_active_users = EXCLUDED.daily_active_users,
                        weekly_active_users = EXCLUDED.weekly_active_users,
                        monthly_active_users = EXCLUDED.monthly_active_users,
                        active_90d_users = EXCLUDED.active_90d_users,
                        inactive_users = EXCLUDED.inactive_users,
                        language_status_counts = EXCLUDED.language_status_counts,
                        file_count = EXCLUDED.file_count,
                        file_bytes = EXCLUDED.file_bytes,
                        disk_used_bytes = EXCLUDED.disk_used_bytes,
                        disk_total_bytes = EXCLUDED.disk_total_bytes,
                        captured_at = EXCLUDED.captured_at
                ''', values)


async def write_daily_stats_snapshot_job(
    _context, *, now=None, downloads_dir=None, disk_usage=None, connect=None,
):
    """Capture /stats counters once per scheduled Tehran reporting day."""
    try:
        await asyncio.to_thread(
            _write_daily_stats_snapshot,
            now or datetime.now(timezone.utc),
            downloads_dir or DOWNLOAD_DIR_PATH,
            disk_usage or shutil.disk_usage,
            connect or _connect,
        )
    except (OSError, psycopg2.Error):
        logger.exception('Could not write the daily stats snapshot')


def schedule_daily_stats_snapshot(job_queue):
    """Schedule the aggregate snapshot shortly after midnight in Tehran."""
    job_queue.run_daily(
        write_daily_stats_snapshot_job,
        time=time(hour=0, minute=5, tzinfo=REPORTING_TIMEZONE),
        name='daily-stats-snapshot',
    )
