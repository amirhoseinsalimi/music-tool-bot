"""Best-effort recording of Telegram /start source keys."""

import asyncio
import logging
import os
import re
from contextlib import closing

import psycopg2

logger = logging.getLogger(__name__)
SOURCE_KEY = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')


def source_key(args):
    """Accept one Telegram deep-link parameter, never an arbitrary URL or identity."""
    if len(args or []) != 1 or not isinstance(args[0], str):
        return None
    return args[0] if SOURCE_KEY.fullmatch(args[0]) else None


def _record(update_id, user_id, key, is_new_user):
    with closing(psycopg2.connect(
        host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_DATABASE'), user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'), connect_timeout=5,
    )) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO bot_start_events (update_id,user_id,source_key,is_new_user) '
                    'VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (update_id, user_id, key, is_new_user),
                )


async def record_start(update_id, user_id, args, is_new_user):
    """Record the Start press without blocking the bot when telemetry is unavailable."""
    if type(update_id) is not int or type(user_id) is not int:
        logger.warning('Could not record start without Telegram update and user IDs')
        return
    try:
        await asyncio.to_thread(_record, update_id, user_id, source_key(args), bool(is_new_user))
    except (OSError, psycopg2.Error):
        logger.exception('Could not record Telegram start source')
