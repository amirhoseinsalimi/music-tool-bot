import asyncio
import threading
import time

from telegram import Update
from telegram.error import Forbidden, RetryAfter
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler

from database.models import Language, User, UserStatus
from modules.admin.utils import is_admin_owner, is_user_admin
from utils import get_effective_user_id, get_message_text, get_user_language_or_fallback, t, upsert_user
from utils.logging import get_logger
from .service import add_admin, del_admin, list_users, show_stats
from .utils import get_list_limit

BROADCAST_INTERVAL_SECONDS = 0.04
MAX_RETRY_AFTER_ATTEMPTS = 3

AWAITING_MESSAGE = 1
CONFIRMING_BROADCAST = 2
CONVERSATION_TIMEOUT = 60
broadcast_lock = threading.Lock()
broadcast_state = {
    'active': False,
    'admin_id': None,
    'job_token': None,
    'thread': None,
    'cancel_requested': False,
    'sent': 0,
    'failed': 0,
}
logger = get_logger(__name__)


@upsert_user
async def add_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`add_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await add_admin(update)


@upsert_user
async def del_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, call :func:`del_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await del_admin(update)


@upsert_user
async def show_stats_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user is an admin. If they are, it calls :func:`show_stats` to display the stats of the bot.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await show_stats(update)


@upsert_user
async def list_users_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`list_users`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await list_users(update, get_list_limit(message=get_message_text(update)))


@upsert_user
async def broadcast_command(update: Update, context: CallbackContext) -> int:
    """
    Starts the process of sending a message to all users, optionally filtered by language.

    Usage:
        /broadcast      - broadcast to all users
        /broadcast en   - broadcast only to users with language 'en'
        /broadcast ru   - broadcast only to users with language 'ru'

    The language code should be an ISO-639-1 (two-letter) code.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object (uses ``context.args`` for language code)
    """
    user_id = update.effective_user.id

    if not is_user_admin(user_id):
        return ConversationHandler.END

    with broadcast_lock:
        active = broadcast_state['active']
    if active:
        await update.message.reply_text(t(get_user_language_or_fallback(context.user_data), 'broadcastAlreadyRunning'))
        return ConversationHandler.END

    language_code = context.args[0].lower() if context.args else None
    context.user_data['broadcast_language'] = language_code

    logger.info(
        "Admin %s opened broadcast flow%s",
        user_id,
        f" for language: {language_code}" if language_code else "",
    )

    language = get_user_language_or_fallback(context.user_data)
    prompt_key = 'broadcastPromptLanguage' if language_code else 'broadcastPrompt'
    await update.message.reply_text(t(language, prompt_key, language_code=language_code or ''))

    return AWAITING_MESSAGE


@upsert_user
async def handle_admin_message(update: Update, context: CallbackContext) -> int:
    """Preview the submitted message and require explicit confirmation."""
    if not is_user_admin(get_effective_user_id(update)):
        return ConversationHandler.END

    context.user_data['broadcast_pending_message_id'] = update.message.message_id
    context.user_data['broadcast_pending_chat_id'] = update.message.chat_id
    await update.message.reply_text(
        t(get_user_language_or_fallback(context.user_data), 'broadcastConfirm')
    )
    return CONFIRMING_BROADCAST


@upsert_user
async def send_broadcast(update: Update, context: CallbackContext) -> int:
    """Start the previewed message as a single-owner background job."""
    user_id = get_effective_user_id(update)
    user_data = context.user_data
    language = get_user_language_or_fallback(user_data)
    if not is_user_admin(user_id):
        return ConversationHandler.END

    message_id = user_data.get('broadcast_pending_message_id')
    source_chat_id = user_data.get('broadcast_pending_chat_id')
    if not message_id or not source_chat_id:
        await update.message.reply_text(t(language, 'broadcastNoPending'))
        return ConversationHandler.END

    language_code = user_data.get('broadcast_language')
    blocked_status = UserStatus.where('slug', 'blocked').first()
    deleted_status = UserStatus.where('slug', 'deleted').first()
    active_status = UserStatus.where('slug', 'active').first()

    users_query = None
    selected_language = None
    if language_code:
        selected_language = Language.where('iso', '=', language_code).first()
        if selected_language:
            users_query = User.where('language_id', '=', selected_language.id)
    if deleted_status and (not language_code or selected_language):
        users_query = users_query.where('user_status_id', '!=', deleted_status.id) if users_query else \
            User.where('user_status_id', '!=', deleted_status.id)
    users = users_query.get() if users_query else (User.all() if not language_code else [])

    with broadcast_lock:
        already_active = broadcast_state['active']
        job_token = object()
        if not already_active:
            broadcast_state.update({
                'active': True, 'admin_id': user_id, 'job_token': job_token,
                'thread': None, 'cancel_requested': False, 'sent': 0, 'failed': 0,
            })
    if already_active:
        await update.message.reply_text(t(language, 'broadcastAlreadyRunning'))
        return ConversationHandler.END
    user_data.pop('broadcast_language', None)
    user_data.pop('broadcast_pending_message_id', None)
    user_data.pop('broadcast_pending_chat_id', None)

    loop = asyncio.get_running_loop()
    admin_chat_id = update.message.chat_id
    bot = context.bot

    def cancellation_requested():
        with broadcast_lock:
            return (
                not broadcast_state['active']
                or broadcast_state['job_token'] is not job_token
                or broadcast_state['cancel_requested']
            )

    def broadcast():
        sent_count = failed_count = newly_blocked = newly_active = 0
        try:
            for user in users:
                if cancellation_requested():
                    break
                try:
                    delivered = False
                    for attempt in range(MAX_RETRY_AFTER_ATTEMPTS):
                        if cancellation_requested():
                            break
                        try:
                            asyncio.run_coroutine_threadsafe(
                                bot.copy_message(
                                    chat_id=user.user_id,
                                    from_chat_id=source_chat_id,
                                    message_id=message_id,
                                    disable_notification=True,
                                ), loop,
                            ).result()
                            delivered = True
                            break
                        except RetryAfter as error:
                            if attempt + 1 >= MAX_RETRY_AFTER_ATTEMPTS:
                                raise
                            retry_after = error.retry_after
                            delay = retry_after.total_seconds() if hasattr(retry_after, 'total_seconds') else float(retry_after)
                            time.sleep(delay)
                    if not delivered:
                        break
                    sent_count += 1
                    if blocked_status and active_status and user.user_status_id == blocked_status.id:
                        user.user_status_id = active_status.id
                        user.save()
                        newly_active += 1
                except Forbidden as error:
                    failed_count += 1
                    error_message = str(error).lower()
                    target_status = deleted_status if 'user is deactivated' in error_message else blocked_status
                    if target_status and user.user_status_id != target_status.id:
                        user.user_status_id = target_status.id
                        user.save()
                        if target_status is blocked_status:
                            newly_blocked += 1
                except Exception as error:
                    logger.warning("Broadcast delivery to user %s failed: %s", user.user_id, error)
                    failed_count += 1
                with broadcast_lock:
                    if broadcast_state['job_token'] is job_token:
                        broadcast_state['sent'] = sent_count
                        broadcast_state['failed'] = failed_count
                time.sleep(BROADCAST_INTERVAL_SECONDS)
        finally:
            with broadcast_lock:
                if broadcast_state['job_token'] is job_token:
                    broadcast_state.update({
                        'active': False, 'admin_id': None, 'job_token': None,
                        'thread': None, 'cancel_requested': False,
                        'sent': sent_count, 'failed': failed_count,
                    })
            logger.info(
                "Broadcast finished for admin %s: sent=%s failed=%s newly_blocked=%s newly_active=%s",
                user_id, sent_count, failed_count, newly_blocked, newly_active,
            )
            asyncio.run_coroutine_threadsafe(
                bot.send_message(
                    chat_id=admin_chat_id,
                    text=t(language, 'broadcastComplete', sent=sent_count, failed=failed_count,
                           blocked=newly_blocked, active=newly_active),
                ), loop,
            )

    worker = threading.Thread(target=broadcast, daemon=True)
    with broadcast_lock:
        broadcast_state['thread'] = worker
    worker.start()
    await update.message.reply_text(t(language, 'broadcastStarted', count=len(users)))
    return ConversationHandler.END


@upsert_user
async def broadcast_status(update: Update, context: CallbackContext) -> None:
    """Report the active broadcast and its delivery progress to an admin."""
    user_id = get_effective_user_id(update)
    if not is_user_admin(user_id):
        return
    with broadcast_lock:
        active = broadcast_state['active']
        owner = broadcast_state['admin_id']
        sent = broadcast_state['sent']
        failed = broadcast_state['failed']
    language = get_user_language_or_fallback(context.user_data)
    status = t(language, 'broadcastStatusActive', sent=sent, failed=failed, admin_id=owner) if active else \
        t(language, 'broadcastStatusIdle')
    await update.message.reply_text(status)


@upsert_user
async def cancel_broadcast(update: Update, context: CallbackContext) -> int:
    """Cancel a pending preview or the broadcast started by this admin."""
    user_id = get_effective_user_id(update)
    if not is_user_admin(user_id):
        return ConversationHandler.END

    language = get_user_language_or_fallback(context.user_data)
    context.user_data.pop('broadcast_language', None)
    context.user_data.pop('broadcast_pending_message_id', None)
    context.user_data.pop('broadcast_pending_chat_id', None)
    with broadcast_lock:
        active = broadcast_state['active']
        owner = broadcast_state['admin_id']
        if active and owner != user_id:
            not_owner = True
        else:
            not_owner = False
            if active:
                broadcast_state['cancel_requested'] = True

    if not_owner:
        await update.message.reply_text(t(language, 'broadcastNotOwner'))
    elif active:
        logger.info("Admin %s canceled the active broadcast", user_id)
        await update.message.reply_text(t(language, 'broadcastCancelled'))
    else:
        await update.message.reply_text(t(language, 'broadcastStatusIdle'))
    return ConversationHandler.END
