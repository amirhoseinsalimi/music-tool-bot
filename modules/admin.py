import asyncio
import os
import re
import threading
import time
from typing import Optional

import psutil
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

from config.telegram_bot import add_handler
from database.models import Admin, User
from utils import get_dir_size_in_bytes, get_effective_user_id, get_message_text, is_admin_owner, is_user_admin, \
    pretty_print_size

DOWNLOADS_DIT_PATH = 'downloads'
SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None


def get_list_limit(message: str) -> int | None:
    number_pattern = r'\d+'

    limit = re.findall(number_pattern, message)

    if len(limit):
        limit = int(limit[0])
    else:
        limit = None

    return limit


def extract_user_id(message: str) -> str:
    """
    Extracts and returns the user ``id`` of `/{add/del}admin` commands.

    The `message` is expected to look like ``/addadmin <user_id>``.

    :param message: str: The ``/{add/del}admin`` command containing a user ``id``
    :return: int: The normalized user's ``id``
    """
    return message.partition(' ')[2]


async def add_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`add_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await add_admin(update)


async def add_admin(update: Update) -> None:
    """
    Adds a user ``id`` to the ``admins`` table. If succeeds, sends a success message.

    :param update: Update: The ``update`` object
    """
    admin_id_to_add = extract_user_id(get_message_text(update))

    if not admin_id_to_add.isdigit():
        await update.message.reply_text(f"The user ID {admin_id_to_add} is malformed")

    admin_id_to_add_int = int(admin_id_to_add)

    admin = Admin()
    admin.admin_user_id = admin_id_to_add_int

    admin.save()

    await update.message.reply_text(text=f"User {admin_id_to_add} has been added as admins.")


async def del_admin_if_user_is_owner(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, call :func:`del_admin`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_admin_owner(get_effective_user_id(update)):
        return

    await del_admin(update)


async def del_admin(update: Update) -> None:
    """
    Deletes a user ``id`` from the ``admins`` table. Then sends a message accordingly.

    :param update: Update: The ``update`` object
    """
    admin_id_to_delete = extract_user_id(get_message_text(update))

    if not admin_id_to_delete.isdigit():
        await update.message.reply_text(f"The user ID `{admin_id_to_delete}` is malformed")

    admin_id_to_delete_int = int(admin_id_to_delete)

    if is_user_admin(admin_id_to_delete_int):
        Admin.where('admin_user_id', '=', admin_id_to_delete).delete()

        await update.message.reply_text(text=f"User {admin_id_to_delete} is no longer an admin")
    else:
        await update.message.reply_text(text=f"User {admin_id_to_delete} is not an admin")


async def show_stats_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user is an admin. If they are, it calls :func:`show_stats` to display the stats of the bot.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await show_stats(update)


async def show_stats(update: Update) -> None:
    """
    Displays a summary about how the bot is being used:
     - The number of users using this bot
     - The number of English and Persian users
     - The number & size of the files on the disk
     - How much disk space is occupied.

    :param update: Update: The ``update`` object
    """
    english_users = User.all().where('language', 'en')
    persian_users = User.all().where('language', 'fa')
    russian_users = User.all().where('language', 'ru')
    spanish_users = User.all().where('language', 'es')
    french_users = User.all().where('language', 'fr')
    arabic_users = User.all().where('language', 'ar')

    downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(DOWNLOADS_DIT_PATH))
    number_of_downloaded_files = len(os.listdir(DOWNLOADS_DIT_PATH))
    occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
        psutil.disk_usage('/')[-3:]

    await update.message.reply_text(
        text=f"""👥 {len(english_users) + len(persian_users) + len(russian_users) +
                    len(spanish_users) + len(french_users) + len(arabic_users)} users 
        are using this bot!\n\n
        🇬🇧 English users: {len(english_users)}
        🇮🇷 Persian users: {len(persian_users)}
        🇷🇺 Russian users: {len(russian_users)}
        🇪🇸 Spanish users: {len(spanish_users)}
        🇫🇷 French users: {len(french_users)}
        🇸🇦 Arabic users: {len(arabic_users)}\n\n
        📁 There are {number_of_downloaded_files} files on the filesystem, occupying 
        {downloads_dir_size}
        💽 Occupied disk space: {pretty_print_size(occupied_disk_space_bytes)}, 
        available space: {pretty_print_size(available_disk_space_bytes)} 
        ({available_disk_space_percent}% used)\n"""
    )


async def list_users_if_user_is_admin(update: Update, _context: CallbackContext) -> None:
    """
    Checks if the user who sent the message is an owner of the bot. If so, calls :func:`list_users`.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: Unused
    """
    if not is_user_admin(get_effective_user_id(update)):
        return

    await list_users(update, get_list_limit(message=get_message_text(update)))


async def list_users(update: Update, limit: Optional[int] = None) -> None:
    """
    Displays a list of all or specified last users in groups of `90` users per message.

    :param update: Update: The ``update`` object
    :param limit: Optional[int]: Number of last users to return
    """
    if limit:
        users = User.all().take(-limit)
    else:
        users = User.all()

    users_per_message = 90
    user_chunks = [users[i:i + users_per_message] for i in range(0, len(users), users_per_message)]

    for index, chunk in enumerate(user_chunks):
        reply_message = "\n".join(
            f"{user.user_id}: {f'@{user.username}' if user.username else '-'}: {user.number_of_files_sent}"
            for user in chunk
        )

        await update.message.reply_text(
            text=f"👥 List of users ({len(users)} total) - Page {index + 1}/{len(user_chunks)}:\n\n"
                 f"{reply_message}",
            parse_mode='',
        )


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


class AdminModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Admin`` module, so that they can be used to respond to messages
        sent to the bot.
        """
        add_handler(ConversationHandler(
            entry_points=[CommandHandler('sendtoall', send_to_all_command)],
            states={
                AWAITING_MESSAGE: [MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_admin_message)]
            },
            fallbacks=[CommandHandler('cancel_sendtoall', cancel_send_to_all)],
            conversation_timeout=CONVERSATION_TIMEOUT
        ))
        add_handler(CommandHandler('addadmin', add_admin_if_user_is_owner))
        add_handler(CommandHandler('deladmin', del_admin_if_user_is_owner))
        add_handler(CommandHandler('stats', show_stats_if_user_is_admin))
        add_handler(CommandHandler('listusers', list_users_if_user_is_admin))
        add_handler(CommandHandler('cancel_sendtoall', cancel_send_to_all))
