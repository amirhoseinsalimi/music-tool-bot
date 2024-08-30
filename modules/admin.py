import os
import re
from typing import Optional

import psutil
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from config.telegram_bot import add_handler
from database.models import Admin, User
from utils import get_dir_size_in_bytes, get_effective_user_id, get_message_text, is_admin_owner, is_user_admin, \
    pretty_print_size

DOWNLOADS_DIT_PATH = 'downloads'


def get_list_limit(message: str) -> int | None:
    number_pattern = r'\d+'

    limit = re.findall(number_pattern, message)

    if len(limit):
        limit = int(limit[0])
    else:
        limit = None

    return limit


def parse_and_normalize_user_id(message: str) -> int:
    """
    Parses, converts and returns the user ``id`` of `/(add/del)admin` commands.

    The `message` is expected to look like ``/addadmin <user_id>``.

    :param message: str: The ``/(add/del)admin`` command containing a user ``id``
    :return: int: The normalized user's ``id``
    """
    return int(message.partition(' ')[2])


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
    admin_id_to_add = parse_and_normalize_user_id(get_message_text(update))

    admin = Admin()
    admin.admin_user_id = admin_id_to_add

    admin.save()

    await update.message.reply_text(text=f"User `{admin_id_to_add}` has been added as admins.")


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
    # TODO: Check if the value is of type `int`
    admin_id_to_delete = parse_and_normalize_user_id(get_message_text(update))

    if is_user_admin(admin_id_to_delete):
        Admin.where('admin_user_id', '=', admin_id_to_delete).delete()

        await update.message.reply_text(text=f"User `{admin_id_to_delete}` is no longer an admin")
    else:
        await update.message.reply_text(text=f"User `{admin_id_to_delete}` is not an admin")


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
    persian_users = User.all().where('language', 'fa')
    english_users = User.all().where('language', 'en')

    downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(DOWNLOADS_DIT_PATH))
    number_of_downloaded_files = len(os.listdir(DOWNLOADS_DIT_PATH))
    occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
        psutil.disk_usage('/')[-3:]

    await update.message.reply_text(
        text=f"👥 {len(persian_users) + len(english_users)} users are using this bot!\n\n"
        f"🇬🇧 English users: {len(english_users)}\n"
        f"🇮🇷 Persian users: {len(persian_users)}\n\n"


        f"📁 There are {number_of_downloaded_files} files on the filesystem, occupying"
        f" {downloads_dir_size}\n"
        f"💽 Occupied disk space {pretty_print_size(occupied_disk_space_bytes)}, available"
        " space: "
        f"{pretty_print_size(available_disk_space_bytes)} ({available_disk_space_percent}%"
        " used)\n"
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
    Displays a list of all or specified last users in the form of ``user_id:username``.

    :param update: Update: The ``update`` object
    :param limit: Update: Number of last users to return
    """
    if limit:
        users = User.all().take(-limit)
    else:
        users = User.all()

    reply_message = ''

    for user in users:
        reply_message += (f"{user.user_id}: {f'@{user.username}' if user.username else '-'}"
                          f": {user.number_of_files_sent}\n")

    await update.message.reply_text(
        text=f"👥 List of all users ({len(users)} in total):\n\n"
        f"{reply_message}",
        parse_mode='',
    )


async def send_to_all():
    pass


class AdminModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Admin`` module, so that they can be used to respond to messages
        sent to the bot.
        """
        add_handler(CommandHandler('addadmin', add_admin_if_user_is_owner))
        add_handler(CommandHandler('deladmin', del_admin_if_user_is_owner))
        add_handler(CommandHandler('stats', show_stats_if_user_is_admin))
        add_handler(CommandHandler('listusers', list_users_if_user_is_admin))
        add_handler(CommandHandler('senttoall', send_to_all))
