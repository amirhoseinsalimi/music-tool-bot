import os

import psutil
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from config.telegram_bot import add_handler
from database.models import Admin, User
from utils import get_dir_size_in_bytes, get_effective_user_id, get_message_text, is_admin_owner, is_user_admin, \
    pretty_print_size

DOWNLOADS_DIT_PATH = 'downloads'


def parse_and_normalize_user_id(message: str) -> int:
    return int(message.partition(' ')[2])


def add_admin_if_user_is_owner(update: Update, _context: CallbackContext):
    if not is_admin_owner(get_effective_user_id(update)):
        return

    add_admin(update)


def add_admin(update: Update):
    admin_id_to_add = parse_and_normalize_user_id(get_message_text(update))

    admin = Admin()
    admin.admin_user_id = admin_id_to_add

    admin.save()

    update.message.reply_text(f"User {admin_id_to_add} has been added as admins.")


def del_admin_if_user_is_owner(update: Update, _context: CallbackContext):
    if not is_admin_owner(get_effective_user_id(update)):
        return

    del_admin(update)


def del_admin(update: Update):
    # TODO: Check if the value is of type `int`
    admin_id_to_delete = parse_and_normalize_user_id(get_message_text(update))

    if is_user_admin(admin_id_to_delete):
        Admin.where('admin_user_id', '=', admin_id_to_delete).delete()

        update.message.reply_text(f"User {admin_id_to_delete} is no longer an admin")
    else:
        update.message.reply_text(f"User {admin_id_to_delete} is not admin")


def show_stats_if_user_is_admin(update: Update, _context: CallbackContext):
    if not is_user_admin(get_effective_user_id(update)):
        return

    show_stats(update)


def show_stats(update: Update):
    persian_users = User.all().where('language', 'fa')
    english_users = User.all().where('language', 'en')

    downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(DOWNLOADS_DIT_PATH))
    number_of_downloaded_files = len(os.listdir(DOWNLOADS_DIT_PATH))
    occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
        psutil.disk_usage('/')[-3:]

    update.message.reply_text(
        f"👥 {len(persian_users) + len(english_users)} users are using this bot!\n\n"
        f"🇬🇧 English users: {len(english_users)}\n"
        f"🇮🇷 Persian users: {len(persian_users)}\n\n"


        f"📁 There are {number_of_downloaded_files} files on the filesystem, occupying"
        f" {downloads_dir_size}\n"
        f"💽 Occupied disk space {pretty_print_size(occupied_disk_space_bytes)}, available"
        " space: "
        f"{pretty_print_size(available_disk_space_bytes)} ({available_disk_space_percent}%"
        " used)\n"
    )


def list_users_if_user_is_admin(update: Update, _context: CallbackContext):
    if not is_user_admin(get_effective_user_id(update)):
        return

    list_users(update)


def list_users(update: Update):
    users = User.all()

    reply_message = ''

    for user in users:
        reply_message += f"{user.user_id}: {f'@{user.username}' if user.username else '-'}\n"

    update.message.reply_text(
        f"👥 List of all users ({len(users)} in total):\n\n"
        f"{reply_message}",
        parse_mode='',
    )


def send_to_all():
    pass


class AdminModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('addadmin', add_admin_if_user_is_owner))
        add_handler(CommandHandler('deladmin', del_admin_if_user_is_owner))
        add_handler(CommandHandler('stats', show_stats_if_user_is_admin))
        add_handler(CommandHandler('listusers', list_users_if_user_is_admin))
        add_handler(CommandHandler('senttoall', send_to_all))
