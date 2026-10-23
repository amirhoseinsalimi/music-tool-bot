"""Admin-only summaries of forward-only Telegram Start source tags."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from .exceptions import BridgeError
from .utils import serialize_timestamp

ZONE = ZoneInfo('Asia/Tehran')


def _bounds(params):
    if set(params) - {'from', 'until'} or bool(params.get('from')) != bool(params.get('until')):
        raise BridgeError(400, 'invalid_request')
    if not params:
        return None, None
    try:
        start, end = date.fromisoformat(params['from']), date.fromisoformat(params['until'])
    except (KeyError, TypeError, ValueError):
        raise BridgeError(400, 'invalid_date_range') from None
    if start.isoformat() != params['from'] or end.isoformat() != params['until']:
        raise BridgeError(400, 'invalid_date_range')
    if start.year < 2000 or end.year > 2099:
        raise BridgeError(400, 'invalid_date_range')
    if end < start or (end - start).days > 365:
        raise BridgeError(400, 'invalid_date_range')
    lower = datetime.combine(start, time.min, ZONE).astimezone(timezone.utc)
    upper = datetime.combine(date.fromordinal(end.toordinal() + 1),
                             time.min, ZONE).astimezone(timezone.utc)
    return lower, upper


def sources(cursor, params):
    """Return new-user attribution and Start activity using one reporting range."""
    lower, upper = _bounds(params)
    # Masonite stores users.created_at as a UTC timestamp without a zone.
    user_where = ' WHERE u.created_at >= %s AND u.created_at < %s' if lower else ''
    user_values = [lower.replace(tzinfo=None), upper.replace(tzinfo=None)] if lower else []
    cursor.execute(
        'SELECT e.source_key, COUNT(*) AS new_users FROM users u '
        'LEFT JOIN bot_start_events e ON e.user_id=u.user_id AND e.is_new_user '
        + user_where + ' GROUP BY e.source_key', user_values,
    )
    rows = {row['source_key'] or '': {'key': row['source_key'] or '',
                                      'newUsers': row['new_users'], 'uniqueUsers': None,
                                      'botStarts': None} for row in cursor.fetchall()}
    event_where = ' AND started_at >= %s AND started_at < %s' if lower else ''
    cursor.execute(
        'SELECT source_key, COUNT(DISTINCT user_id) AS unique_users, COUNT(*) AS bot_starts '
        'FROM bot_start_events WHERE source_key IS NOT NULL' + event_where
        + ' GROUP BY source_key', [lower, upper] if lower else [],
    )
    for row in cursor.fetchall():
        key = row['source_key']
        item = rows.setdefault(key, {'key': key, 'newUsers': 0,
                                     'uniqueUsers': None, 'botStarts': None})
        item['uniqueUsers'] = row['unique_users']
        item['botStarts'] = row['bot_starts']
    for key, item in rows.items():
        if key:
            item['uniqueUsers'] = item['uniqueUsers'] or 0
            item['botStarts'] = item['botStarts'] or 0
    ordered = sorted(rows.values(), key=lambda row: (
        row['key'] == '', -row['newUsers'], row['key']))
    total = sum(row['newUsers'] for row in ordered)
    unknown = rows.get('', {}).get('newUsers', 0)
    cursor.execute('SELECT MIN(started_at) AS first FROM bot_start_events')
    first = cursor.fetchone()['first']
    return {'rows': ordered, 'totalNewUsers': total, 'taggedNewUsers': total - unknown,
            'unknownNewUsers': unknown,
            'websiteNewUsers': rows.get('website', {}).get('newUsers', 0),
            'historySince': serialize_timestamp(first), 'timezone': 'Asia/Tehran'}


def user_sources(cursor, user_id):
    """Return acquisition and latest tagged Start for one Telegram user."""
    cursor.execute(
        'SELECT source_key, started_at FROM bot_start_events '
        'WHERE user_id=%s AND is_new_user ORDER BY started_at LIMIT 1', (user_id,),
    )
    first = cursor.fetchone()
    cursor.execute(
        'SELECT source_key, started_at FROM bot_start_events '
        'WHERE user_id=%s AND source_key IS NOT NULL ORDER BY started_at DESC LIMIT 1', (user_id,),
    )
    latest = cursor.fetchone()
    return {'acquisitionSource': first['source_key'] if first else None,
            'acquisitionRecordedAt': serialize_timestamp(first['started_at']) if first else None,
            'latestTaggedSource': latest['source_key'] if latest else None,
            'latestTaggedAt': serialize_timestamp(latest['started_at']) if latest else None}
