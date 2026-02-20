import asyncio
import threading
import time

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler

from database.models import User
from utils import get_effective_user_id, get_message_text, is_admin_owner, is_user_admin
from .service import add_admin, del_admin, list_users, show_stats
from .utils import get_list_limit

DOWNLOADS_DIT_PATH = 'downloads'
SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None


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


async def send_to_all_command(update: Update, _context: CallbackContext) -> int:
    """
    Starts the process of sending a message to all users.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    user_id = update.effective_user.id

    if not is_user_admin(user_id):
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Now send the message you want to send to all users.\n"
        "❌ Use /cancel_sendtoall to cancel."
    )

    return AWAITING_MESSAGE


async def handle_admin_message(update: Update, context: CallbackContext) -> int:
    """
    Starts a new thread to broadcast the message to all users without blocking the bot.

    This function retrieves all bot users and starts broadcasting a message to them
    in a background thread. The broadcasting process can be canceled at any time
    using `/cancel_sendtoall`. Messages will stop sending as soon as cancellation is triggered.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    :return: ConversationHandler.END: Ends the conversation state.
    """
    global broadcasting_active, broadcast_thread
    broadcasting_active = True

    users = User.all()
    message_to_send = update.message
    admin_chat_id = update.message.chat_id
    loop = asyncio.get_event_loop()

    def broadcast():
        """
        Runs the broadcast process in a separate thread.

        This function iterates through all users and sends the provided message.
        Messages are sent using `asyncio.run_coroutine_threadsafe()` to ensure
        they execute safely in the main event loop. A delay is added between
        messages to avoid hitting Telegram's rate limits.
        """
        global broadcasting_active
        success_count = 0
        failed_count = 0

        for user in users:
            if not broadcasting_active:
                break

            try:
                if message_to_send.text:
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

            except Exception as e:
                print(f"Failed to send message to {user.user_id}: {e}")

                failed_count += 1

        broadcasting_active = False

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


async def cancel_send_to_all(update: Update, context: CallbackContext) -> int:
    """
    Cancels the broadcasting process immediately.

    This function sets `broadcasting_active` to False, signaling the broadcast
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

    if broadcasting_active:
        broadcasting_active = False

        if broadcast_thread and broadcast_thread.is_alive():
            broadcast_thread = None

        await update.message.reply_text("❌ Broadcasting canceled. No further messages will be sent.")
    else:
        await update.message.reply_text("ℹ️ No active broadcast to cancel.")

    return ConversationHandler.END
