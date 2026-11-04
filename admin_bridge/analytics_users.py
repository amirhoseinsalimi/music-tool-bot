"""User activity and daily snapshot reports from core-owned PostgreSQL data."""

import json
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .exceptions import BridgeError

ZONE = ZoneInfo('Asia/Tehran')
LANGUAGES = {'en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id'}
STATUSES = {'active', 'blocked', 'deleted'}


def _range(params):
    if set(params) - {'from', 'to', 'group', 'language', 'status'}:
        raise BridgeError(400, 'invalid_request')
    try:
        start, end = date.fromisoformat(params['from']), date.fromisoformat(params['to'])
    except (KeyError, TypeError, ValueError):
        raise BridgeError(400, 'invalid_date_range') from None
    group = params.get('group', 'day')
    language, status = params.get('language', ''), params.get('status', '')
    if (start.isoformat() != params['from'] or end.isoformat() != params['to']
            or start.year < 2000 or end.year > 2099 or end < start
            or (end - start).days > 365 or group not in {'day', 'week', '31-day'}
            or language not in {'', *LANGUAGES} or status not in {'', *STATUSES}):
        raise BridgeError(400, 'invalid_request')
    labels = _labels(start, end, group)
    if len(labels) < 2:
        raise BridgeError(400, 'range_requires_two_buckets')
    return start, end, group, language, status, labels


def _labels(start, end, group):
    if group == 'day':
        first, step = start, 1
    elif group == 'week':
        first, step = start - timedelta(days=start.weekday()), 7
    else:
        first, step = start, 31
    labels = []
    while first <= end:
        labels.append(first)
        first += timedelta(days=step)
    return labels


def _bucket_end(label, end, group):
    span = {'day': 1, 'week': 7, '31-day': 31}[group]
    return min(label + timedelta(days=span - 1), end)


def _user_filter(language, status):
    clauses, values = [], []
    if language:
        clauses.append('l.iso = %s')
        values.append(language)
    if status:
        clauses.append('s.slug = %s')
        values.append(status)
    return (' AND ' + ' AND '.join(clauses) if clauses else ''), values


def users_report(cursor, params):
    """Return bucketed user counts; pre-tracking activity periods remain null."""
    start, end, group, language, status, labels = _range(params)
    condition, filter_values = _user_filter(language, status)
    lower = datetime.combine(start, time.min, ZONE).astimezone(timezone.utc)
    upper = datetime.combine(end + timedelta(days=1), time.min, ZONE).astimezone(timezone.utc)
    lower_naive, upper_naive = lower.replace(tzinfo=None), upper.replace(tzinfo=None)
    cursor.execute('SELECT MIN(day) AS first_day FROM user_activity_days')
    tracking_row = cursor.fetchone()
    tracking_from = tracking_row['first_day'] if tracking_row else None
    span = {'day': 1, 'week': 7, '31-day': 31}[group]
    activity_filter = ' AND '.join(
        (["l.iso = %s"] if language else []) + (["s.slug = %s"] if status else []),
    ) or 'TRUE'
    filter_values = [*filter_values]
    metric_filters = filter_values * 3
    cursor.execute(f'''
        WITH bounds AS (
            SELECT label, GREATEST(label, %s::date) AS bucket_start,
                   LEAST(label + %s * INTERVAL '1 day', %s::date)::date AS bucket_end
            FROM unnest(%s::date[]) AS label
        ), tracking AS (SELECT MIN(day) AS first_day FROM user_activity_days),
        newcomer_counts AS (
            SELECT b.label, COUNT(u.id) FILTER (WHERE {activity_filter}) AS count
            FROM bounds b LEFT JOIN users u
            ON u.created_at >= ((b.bucket_start::timestamp AT TIME ZONE 'Asia/Tehran') AT TIME ZONE 'UTC')
             AND u.created_at < (((b.bucket_end + 1)::timestamp AT TIME ZONE 'Asia/Tehran') AT TIME ZONE 'UTC')
            LEFT JOIN languages l ON l.id = u.language_id
            LEFT JOIN user_statuses s ON s.id = u.user_status_id
            GROUP BY b.label
        ), activity_counts AS (
            SELECT b.label, t.first_day, b.bucket_end,
              COUNT(DISTINCT a.user_id) FILTER (
                WHERE a.day BETWEEN GREATEST(b.bucket_end - 0, t.first_day) AND b.bucket_end
                  AND ({activity_filter})
              ) AS daily,
              COUNT(DISTINCT a.user_id) FILTER (
                WHERE a.day BETWEEN GREATEST(b.bucket_end - 6, t.first_day) AND b.bucket_end
                  AND ({activity_filter})
              ) AS weekly,
              COUNT(DISTINCT a.user_id) FILTER (
                WHERE a.day BETWEEN GREATEST(b.bucket_end - 30, t.first_day) AND b.bucket_end
                  AND ({activity_filter})
              ) AS monthly
            FROM bounds b CROSS JOIN tracking t
            LEFT JOIN user_activity_days a ON t.first_day IS NOT NULL
              AND b.bucket_end >= t.first_day
              AND a.day BETWEEN GREATEST(b.bucket_end - 30, t.first_day) AND b.bucket_end
            LEFT JOIN users u ON u.user_id = a.user_id
            LEFT JOIN languages l ON l.id = u.language_id
            LEFT JOIN user_statuses s ON s.id = u.user_status_id
            GROUP BY b.label, t.first_day, b.bucket_end
        )
        SELECT b.label, n.count AS newcomers,
          CASE WHEN a.first_day IS NULL OR a.bucket_end < a.first_day THEN NULL ELSE a.daily END AS daily,
          CASE WHEN a.first_day IS NULL OR a.bucket_end < a.first_day THEN NULL ELSE a.weekly END AS weekly,
          CASE WHEN a.first_day IS NULL OR a.bucket_end < a.first_day THEN NULL ELSE a.monthly END AS monthly,
          snap.blocked_users, snap.deleted_users, snap.total_users, snap.active_users,
          snap.language_status_counts
        FROM bounds b JOIN newcomer_counts n USING (label)
        JOIN activity_counts a USING (label)
        LEFT JOIN LATERAL (
          SELECT d.blocked_users, d.deleted_users, d.total_users, d.active_users,
                 d.language_status_counts
          FROM daily_stats_snapshot d
          WHERE d.day >= %s::date AND d.day <= b.bucket_end
          ORDER BY d.day DESC LIMIT 1
        ) snap ON TRUE
        ORDER BY b.label
    ''', [start, span - 1, end, labels,
          *filter_values, *metric_filters, start])
    periods = []
    for snapshot in cursor.fetchall():
        blocked_deleted = blocked_deleted_percent = None
        if snapshot and snapshot['blocked_users'] is not None:
            statuses = _snapshot_status(snapshot, language)
            filtered_statuses = ({status: statuses.get(status, 0)} if status else statuses)
            total = sum(filtered_statuses.values())
            blocked_deleted = filtered_statuses.get('blocked', 0) + filtered_statuses.get('deleted', 0)
            if total:
                blocked_deleted_percent = blocked_deleted / total * 100
        periods.append({
            'period': snapshot['label'].isoformat(), 'newcomers': snapshot['newcomers'],
            'dailyActive': snapshot['daily'], 'weeklyActive': snapshot['weekly'],
            'monthlyActive': snapshot['monthly'], 'blockedDeleted': blocked_deleted,
            'blockedDeletedPercent': blocked_deleted_percent,
        })

    cursor.execute(
        'SELECT COUNT(*) AS count FROM users u '
        'LEFT JOIN languages l ON l.id = u.language_id '
        'LEFT JOIN user_statuses s ON s.id = u.user_status_id '
        'WHERE u.created_at >= %s AND u.created_at < %s' + condition,
        (lower_naive, upper_naive, *filter_values),
    )
    newcomer_total = cursor.fetchone()['count']
    previous_upper = lower
    previous_lower = previous_upper - (upper - lower)
    cursor.execute(
        'SELECT COUNT(*) AS count FROM users u '
        'LEFT JOIN languages l ON l.id = u.language_id '
        'LEFT JOIN user_statuses s ON s.id = u.user_status_id '
        'WHERE u.created_at >= %s AND u.created_at < %s' + condition,
        (previous_lower.replace(tzinfo=None), previous_upper.replace(tzinfo=None), *filter_values),
    )
    previous_newcomers = cursor.fetchone()['count']
    cursor.execute(
        'SELECT total_users, active_users, blocked_users, deleted_users, '
        'daily_active_users, monthly_active_users, language_status_counts '
        'FROM daily_stats_snapshot '
        'WHERE day <= %s ORDER BY day DESC LIMIT 1', (end,),
    )
    latest = cursor.fetchone()
    latest_statuses = _snapshot_status(latest, language) if latest else {}
    selected_statuses = {status: latest_statuses.get(status, 0)} if status else latest_statuses
    latest_total = sum(selected_statuses.values()) if latest else None
    latest_blocked_deleted = (
        selected_statuses.get('blocked', 0) + selected_statuses.get('deleted', 0)
        if latest else None
    )
    last_period = periods[-1] if periods else {}
    filtered = bool(language or status)
    summary = {
        'totalUsers': {'value': latest_total},
        'newcomers': {'value': newcomer_total,
                      'changePercent': _change(newcomer_total, previous_newcomers)},
        'dailyActive24h': {'value': last_period.get('dailyActive') if filtered else (
            latest['daily_active_users'] if latest else None)},
        'monthlyActive': {'value': last_period.get('monthlyActive') if filtered else (
            latest['monthly_active_users'] if latest else None)},
        'blockedDeleted': {'value': latest_blocked_deleted},
    }
    return {'timezone': 'Asia/Tehran', 'historySince': tracking_from.isoformat() if tracking_from else None,
            'totalBuckets': len(labels), 'summary': summary, 'periods': periods}


def _change(current, previous):
    if not previous:
        return 100.0 if current else 0.0
    return (current - previous) / previous * 100


def _snapshot_status(snapshot, language=''):
    if language:
        counts = snapshot['language_status_counts'] or {}
        if isinstance(counts, str):
            counts = json.loads(counts)
        return counts.get(language, {'active': 0, 'blocked': 0, 'deleted': 0})
    return {'active': snapshot['active_users'], 'blocked': snapshot['blocked_users'],
            'deleted': snapshot['deleted_users']}


def latest_snapshot(cursor, params):
    """Return the latest counts-only snapshot using the Users page contract."""
    if params:
        raise BridgeError(400, 'invalid_request')
    cursor.execute('''
        SELECT day, captured_at, total_users, active_users, blocked_users, deleted_users,
               daily_active_users, weekly_active_users, monthly_active_users,
               active_90d_users, inactive_users, language_status_counts, file_count,
               file_bytes, disk_used_bytes, disk_total_bytes
        FROM daily_stats_snapshot ORDER BY day DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    if row is None:
        return {}
    languages = row['language_status_counts'] or {}
    if isinstance(languages, str):
        languages = json.loads(languages)
    return {
        'capturedAt': row['captured_at'].isoformat(), 'totalUsers': row['total_users'],
        'status': {'active': row['active_users'], 'blocked': row['blocked_users'], 'deleted': row['deleted_users']},
        'activity': {'daily24h': row['daily_active_users'], 'weekly7d': row['weekly_active_users'],
                     'monthly31d': row['monthly_active_users'], 'active90d': row['active_90d_users'],
                     'inactive': row['inactive_users']},
        'languages': [{'language': language, **counts} for language, counts in languages.items()],
        'files': {'count': row['file_count'], 'downloadedMediaBytes': row['file_bytes']},
        'disk': {'usedBytes': row['disk_used_bytes'], 'totalBytes': row['disk_total_bytes']},
    }
