import asyncio
import threading
import time

from telegram import Update
from telegram.error import Forbidden, BadRequest
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler

from database.models import Language, User, UserStatus
from modules.admin.utils import is_admin_owner, is_user_admin
from utils import get_effective_user_id, get_message_text
from utils.logging import get_logger
from .service import add_admin, del_admin, list_users, show_stats
from .utils import get_list_limit

SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None
logger = get_logger(__name__)


async def add_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`add_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await add_admin(update)


async def del_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, call :func:`del_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await del_admin(update)


async def show_stats_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user is an admin. If they are, it calls :func:`show_stats` to display the stats of the bot.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await show_stats(update)


async def list_users_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`list_users`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await list_users(update, get_list_limit(message=get_message_text(update)))


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

    language_code = context.args[0].lower() if context.args else None
    context.user_data['broadcast_language'] = language_code

    logger.info(
        "Admin %s opened broadcast flow%s",
        user_id,
        f" for language: {language_code}" if language_code else "",
    )

    msg = "✅ Now send the message you want to send to all users."
    if language_code:
        msg += f"\n🌐 Broadcast will be limited to users with language: <code>{language_code}</code>"
    msg += "\n\n❌ Use /cancel_broadcast to cancel."

    await update.message.reply_text(msg, parse_mode="HTML")

    return AWAITING_MESSAGE


async def handle_admin_message(update: Update, context: CallbackContext) -> int:
    """
    Starts a new thread to broadcast the message to users (optionally filtered by language)
    without blocking the bot.

    If a language filter was set via ``/broadcast <lang>``, the broadcast will only be sent
    to users whose stored language code matches. Otherwise, it broadcasts to all users.

    This function retrieves the target users and starts broadcasting the message to them
    in a background thread. The broadcasting process can be canceled at any time
    using ``/cancel_broadcast``. Messages will stop sending as soon as cancellation is triggered.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    :return: ConversationHandler.END: Ends the conversation state.
    """
    global broadcasting_active, broadcast_thread
    broadcasting_active = True

    user_id = update.effective_user.id
    language_code = context.user_data.pop("broadcast_language", None)

    if language_code:
        language = Language.where('iso', '=', language_code).first()
        users = User.where('language_id', '=', language.id).get() if language else []
    else:
        users = User.all()

    message_to_send = update.message
    admin_chat_id = update.message.chat_id
    loop = asyncio.get_event_loop()

    logger.info(
        "Admin %s started broadcast%s to %s users",
        user_id,
        f" (language: {language_code})" if language_code else "",
        len(users),
    )

    def broadcast():
        """
        Runs the broadcast process in a separate thread.

        This function iterates through the target users and sends the provided message.
        Messages are sent using ``asyncio.run_coroutine_threadsafe()`` to ensure
        they execute safely in the main event loop. A delay is added between
        messages to avoid hitting Telegram's rate limits.

        If the admin's message is forwarded, it re-forwards it to each user.
        If it's an original message, it sends the content directly.

        When a delivery fails, the user's status is updated accordingly:
        - ``Forbidden`` with "user is deactivated" → status set to ``deleted``
        - ``Forbidden`` (other) → status set to ``blocked``
        - ``BadRequest`` → logged but no status change
        """
        global broadcasting_active
        success_count = 0
        failed_count = 0
        is_forwarded = message_to_send.forward_origin is not None

        blocked_status = UserStatus.where('slug', 'blocked').first()
        deleted_status = UserStatus.where('slug', 'deleted').first()

        for user in users:
            if not broadcasting_active:
                break

            try:
                if is_forwarded:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.forward_message(
                            chat_id=user.user_id,
                            from_chat_id=message_to_send.chat_id,
                            message_id=message_to_send.message_id,
                        ),
                        loop
                    ).result()
                elif message_to_send.text:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_message(
                            chat_id=user.user_id,
                            text=message_to_send.text,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.photo:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_photo(
                            chat_id=user.user_id,
                            photo=message_to_send.photo[-1].file_id,
                            caption=message_to_send.caption,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.video:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_video(
                            chat_id=user.user_id,
                            video=message_to_send.video.file_id,
                            caption=message_to_send.caption,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.document:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_document(
                            chat_id=user.user_id,
                            document=message_to_send.document.file_id,
                            caption=message_to_send.caption,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.audio:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_audio(
                            chat_id=user.user_id,
                            audio=message_to_send.audio.file_id,
                            caption=message_to_send.caption,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.voice:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_voice(
                            chat_id=user.user_id,
                            voice=message_to_send.voice.file_id,
                            caption=message_to_send.caption,
                            disable_notification=True
                        ),
                        loop
                    ).result()
                elif message_to_send.sticker:
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_sticker(
                            chat_id=user.user_id,
                            sticker=message_to_send.sticker.file_id,
                            disable_notification=True
                        ),
                        loop
                    ).result()

                success_count += 1
                time.sleep(SLEEP_TIME_TO_NEXT_USER_IN_SECONDS)

            except Forbidden as error:
                failed_count += 1
                error_message = str(error).lower()

                if "user is deactivated" in error_message:
                    logger.warning(
                        "User %s has deleted their account. Marking as deleted.",
                        user.user_id,
                    )

                    if deleted_status:
                        user.user_status_id = deleted_status.id
                        user.save()
                else:
                    logger.warning(
                        "User %s has blocked the bot. Marking as blocked.",
                        user.user_id,
                    )

                    if blocked_status:
                        user.user_status_id = blocked_status.id
                        user.save()

            except BadRequest as error:
                logger.warning("Broadcast delivery to user %s failed: %s", user.user_id, error)
                failed_count += 1

            except Exception as error:
                logger.warning("Broadcast delivery to user %s failed: %s", user.user_id, error)
                failed_count += 1

        broadcasting_active = False
        logger.info(
            "Broadcast finished for admin %s: sent=%s failed=%s",
            user_id,
            success_count,
            failed_count
        )

        asyncio.run_coroutine_threadsafe(
            context.bot.send_message(
                chat_id=admin_chat_id,
                text=f"✅ Broadcast complete:\n✔️ {success_count} sent\n❌ {failed_count} failed."
            ),
            loop
        )

    broadcast_thread = threading.Thread(target=broadcast, daemon=True)
    broadcast_thread.start()

    await update.message.reply_text("🚀 Broadcasting started in the background.")

    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: CallbackContext) -> int:
    """
    Cancels the broadcasting process immediately.

    This function sets ``broadcasting_active`` to False, signaling the broadcast
    thread to stop processing further messages. It also ensures that no further
    messages are sent. If no broadcast is active, it informs the admin.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    :return: ConversationHandler.END: Ends the conversation state.
    """
    user_id = update.effective_user.id

    if not is_user_admin(user_id):
        return -1

    global broadcasting_active, broadcast_thread

    context.user_data.pop("broadcast_language", None)

    if broadcasting_active:
        broadcasting_active = False
        logger.info("Admin %s canceled active broadcast", user_id)

        if broadcast_thread and broadcast_thread.is_alive():
            broadcast_thread = None

        await update.message.reply_text("❌ Broadcasting canceled. No further messages will be sent.")
    else:
        await update.message.reply_text("ℹ️ No active broadcast to cancel.")

    return ConversationHandler.END
