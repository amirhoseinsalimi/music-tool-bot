"""Best-effort, idempotent completion events for free bot tools.

The user receives the result before telemetry is written. Telemetry errors must
never turn a successful Telegram delivery into an apparent user-facing failure.
"""

import asyncio
import logging
from collections.abc import Awaitable
from contextlib import closing
from typing import TypeVar

import psycopg2

from config.envs import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USERNAME

logger = logging.getLogger(__name__)
FREE_FEATURES = frozenset({'cutter', 'bitrate_changer', 'voice_converter', 'tag_editor'})
_T = TypeVar('_T')


def _record(feature: str, user_id: int, update_id: int) -> None:
    with closing(psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_DATABASE,
        user=DB_USERNAME, password=DB_PASSWORD, connect_timeout=5,
    )) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO feature_usage_events (feature, update_id, user_id) '
                    'VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                    (feature, update_id, user_id),
                )


async def record_completion(feature: str, user_id: int, update_id: int | None) -> None:
    if feature not in FREE_FEATURES or type(user_id) is not int:
        raise ValueError('Invalid feature usage event')
    if type(update_id) is not int:
        logger.warning('No update ID for completed %s event', feature)
        return
    try:
        await asyncio.to_thread(_record, feature, user_id, update_id)
    except (OSError, psycopg2.Error):
        logger.exception('Could not record completed %s event', feature)


async def send_file_and_record_completion(send_file: Awaitable[_T], feature: str,
                                          user_id: int, update_id: int | None) -> _T:
    """Record a free-tool completion only after Telegram accepts its output."""
    sent_message = await send_file
    await record_completion(feature, user_id, update_id)
    return sent_message
