"""Authorized, forward-only free-tool usage aggregates."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from .exceptions import BridgeError

FREE_FEATURES = ('cutter', 'bitrate_changer', 'voice_converter', 'tag_editor')
ZONE = ZoneInfo('Asia/Tehran')
PERIODS = {'day': 'day', 'week': 'week', 'month': 'month'}


def range_filter(params):
    """Validate an inclusive Tehran reporting range and optional grouping."""
    if set(params) - {'from', 'until', 'group', 'feature'}:
        raise BridgeError(400, 'invalid_request')
    try:
        start = date.fromisoformat(params['from'])
        end = date.fromisoformat(params['until'])
    except (KeyError, ValueError, TypeError):
        raise BridgeError(400, 'invalid_date_range') from None
    if start.isoformat() != params['from'] or end.isoformat() != params['until']:
        raise BridgeError(400, 'invalid_date_range')
    if start.year < 2000 or end.year > 2099 or end < start or (end - start).days > 365:
        raise BridgeError(400, 'invalid_date_range')
    group = params.get('group', 'day')
    feature = params.get('feature', '')
    if group not in PERIODS or feature not in ('', *FREE_FEATURES):
        raise BridgeError(400, 'invalid_request')
    lower = datetime.combine(start, time.min, ZONE).astimezone(timezone.utc)
    upper = datetime.combine(date.fromordinal(end.toordinal() + 1),
                             time.min, ZONE).astimezone(timezone.utc)
    return lower, upper, group, feature


def usage(cursor, params):
    """Return dated completion totals from core-owned forward-only events."""
    lower, upper, group, feature = range_filter(params)
    feature_sql = ' AND feature = %s' if feature else ''
    values = [lower, upper, *([feature] if feature else [])]
    cursor.execute(
        'SELECT feature, COUNT(*) AS completed, COUNT(DISTINCT user_id) AS users '
        'FROM feature_usage_events WHERE completed_at >= %s AND completed_at < %s'
        + feature_sql + ' GROUP BY feature ORDER BY feature', values,
    )
    features = [dict(row) for row in cursor.fetchall()]
    local_day = "(completed_at AT TIME ZONE 'Asia/Tehran')::date"
    if group == 'month':
        # Owner-defined month: consecutive 31-day blocks starting at the selected From date.
        bucket = f"(%s::date + (({local_day} - %s::date) / 31) * 31)"
        bucket_values = [lower.astimezone(ZONE).date()] * 2
    else:
        bucket = f"date_trunc('{PERIODS[group]}', completed_at AT TIME ZONE 'Asia/Tehran')::date"
        bucket_values = []
    cursor.execute(
        f'SELECT {bucket} AS period, feature, COUNT(*) AS completed, '
        'COUNT(DISTINCT user_id) AS users FROM feature_usage_events '
        'WHERE completed_at >= %s AND completed_at < %s' + feature_sql
        + ' GROUP BY period, feature ORDER BY period, feature', [*bucket_values, *values],
    )
    periods = [{'period': row['period'].isoformat(), 'feature': row['feature'],
                'completed': row['completed'], 'users': row['users']}
               for row in cursor.fetchall()]
    cursor.execute('SELECT MIN(completed_at) AS first FROM feature_usage_events')
    first = cursor.fetchone()['first']
    return {'features': features, 'periods': periods,
            'historySince': first.isoformat() if first else None, 'timezone': 'Asia/Tehran'}
