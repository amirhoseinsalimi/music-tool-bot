"""Shared rolling user statistics for Telegram, snapshots and Admin."""

from datetime import datetime, timedelta, timezone


def stats_counts(now: datetime, users, known_languages=()):
    """Reduce user rows to the same status and activity windows shown by /stats."""
    statuses = {'active': 0, 'blocked': 0, 'deleted': 0}
    activity = {
        'daily_active_users': 0, 'weekly_active_users': 0,
        'monthly_active_users': 0, 'active_90d_users': 0,
        'inactive_users': 0, 'churned_90d_users': 0,
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
        if not isinstance(last_interaction, datetime):
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
        else:
            activity['churned_90d_users'] += 1
    return statuses, activity, language_counts
