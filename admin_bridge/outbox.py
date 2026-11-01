"""Bot-owned delivery worker for owner messages queued through the core bridge."""

import asyncio
from contextlib import closing
from datetime import timedelta
from math import ceil
from typing import Any, Callable

from psycopg2.extras import RealDictCursor
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from .service import PostgresConnection, connect_core


def claim_message(
    connect: Callable[[], PostgresConnection] = connect_core,
) -> dict[str, Any] | None:
    """Atomically claim at most one due message so parallel workers cannot send it twice."""
    with closing(connect()) as connection:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    WITH candidate AS (
                        SELECT id FROM outbox_messages
                        WHERE status = 'queued' AND available_at <= now()
                        ORDER BY created_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE outbox_messages AS message
                    SET status = 'sending', attempts = attempts + 1
                    FROM candidate
                    WHERE message.id = candidate.id
                    RETURNING message.id, message.target_user_id, message.message_text,
                              message.attempts
                """)
                return cursor.fetchone()


# pylint: disable=too-many-arguments,too-many-positional-arguments
def finish_message(
    message_id: str,
    status: str,
    error: str | None = None,
    retry_after: int | None = None,
    blocked_user_id: int | None = None,
    connect: Callable[[], PostgresConnection] = connect_core,
) -> None:
    """Store a safe delivery state and erase text when no further send is allowed."""
    if status not in {'sent', 'failed', 'delivery_unknown', 'queued'}:
        raise ValueError('Invalid outbox status')
    with closing(connect()) as connection:
        with connection:
            with connection.cursor() as cursor:
                if blocked_user_id is not None:
                    cursor.execute("""
                        UPDATE users AS user_record
                        SET user_status_id = blocked.id
                        FROM user_statuses AS blocked
                        WHERE user_record.user_id = %s
                          AND blocked.slug = 'blocked'
                          AND NOT EXISTS (
                              SELECT 1 FROM user_statuses AS deleted
                              WHERE deleted.id = user_record.user_status_id
                                AND deleted.slug = 'deleted'
                          )
                    """, (blocked_user_id,))
                cursor.execute("""
                    UPDATE outbox_messages
                    SET status = %s,
                        message_text = CASE WHEN %s = 'queued' THEN message_text ELSE NULL END,
                        last_error = %s,
                        available_at = CASE WHEN %s = 'queued'
                            THEN now() + (%s * interval '1 second') ELSE available_at END,
                        sent_at = CASE WHEN %s = 'sent' THEN now() ELSE sent_at END
                    WHERE id = %s
                """, (status, status, error, status, retry_after or 0, status, message_id))


def expire_old_messages(connect: Callable[[], PostgresConnection] = connect_core) -> None:
    """Erase payloads and status rows after 14 days; mark abandoned sends uncertain."""
    with closing(connect()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE outbox_messages
                    SET status = 'delivery_unknown', message_text = NULL,
                        last_error = 'delivery_unknown'
                    WHERE status = 'sending' AND created_at < now() - interval '2 minutes'
                """)
                cursor.execute("""
                    DELETE FROM outbox_messages
                    WHERE status IN ('sent', 'failed', 'delivery_unknown')
                      AND created_at < now() - interval '14 days'
                """)
                cursor.execute("""
                    UPDATE outbox_messages
                    SET status = 'failed', message_text = NULL, last_error = 'expired'
                    WHERE status = 'queued' AND created_at < now() - interval '14 days'
                """)


async def deliver_outbox_message(context) -> None:
    """Claim and send one message; ambiguous responses are surfaced without retry."""
    try:
        message = await asyncio.to_thread(claim_message)
        if message is None:
            return
        message_id = str(message['id'])
        target_user_id = int(message['target_user_id'])
        text = message['message_text']
        try:
            await context.bot.send_message(chat_id=target_user_id, text=text)
        except Forbidden:
            await asyncio.to_thread(
                finish_message, message_id, 'failed', 'recipient_blocked',
                None, target_user_id,
            )
        except BadRequest:
            await asyncio.to_thread(
                finish_message, message_id, 'failed', 'telegram_rejected',
            )
        except RetryAfter as error:
            if int(message['attempts']) >= 3:
                await asyncio.to_thread(
                    finish_message, message_id, 'failed', 'rate_limited',
                )
            else:
                delay = (error.retry_after.total_seconds()
                         if isinstance(error.retry_after, timedelta)
                         else float(error.retry_after))
                seconds = max(1, ceil(delay))
                await asyncio.to_thread(
                    finish_message, message_id, 'queued', 'rate_limited', seconds,
                )
        except TelegramError:
            await asyncio.to_thread(
                finish_message, message_id, 'delivery_unknown', 'delivery_unknown',
            )
        else:
            await asyncio.to_thread(finish_message, message_id, 'sent')
    except Exception:  # pylint: disable=broad-exception-caught
        # Never log payloads, target IDs, or credentials.
        from utils.logging import get_logger  # pylint: disable=import-outside-toplevel
        get_logger(__name__).error('Owner message outbox processing failed')


async def cleanup_outbox_job(_context) -> None:
    """Run privacy cleanup without blocking Telegram polling."""
    try:
        await asyncio.to_thread(expire_old_messages)
    except Exception:  # pylint: disable=broad-exception-caught
        from utils.logging import get_logger  # pylint: disable=import-outside-toplevel
        get_logger(__name__).error('Owner message outbox cleanup failed')
