import os
from typing import (
    Optional,
)

import psutil
from telegram import (
    Update,
)

from database.models import (
    Admin,
    User,
)
from utils import (
    get_message_text,
)
from .utils import (
    extract_user_id,
    is_user_admin,
    get_dir_size_in_bytes,
    pretty_print_size,
)

DOWNLOADS_DIT_PATH = 'downloads'
SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None


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
    total_users = (
        len(english_users)
        + len(persian_users)
        + len(russian_users)
        + len(spanish_users)
        + len(french_users)
        + len(arabic_users)
    )

    await update.message.reply_text(
        text=(
            f"👥 {total_users} users are using this bot!\n\n"
            f"🇬🇧 English users: {len(english_users)}\n"
            f"🇮🇷 Persian users: {len(persian_users)}\n"
            f"🇷🇺 Russian users: {len(russian_users)}\n"
            f"🇪🇸 Spanish users: {len(spanish_users)}\n"
            f"🇫🇷 French users: {len(french_users)}\n"
            f"🇸🇦 Arabic users: {len(arabic_users)}\n\n"
            f"📁 There are {number_of_downloaded_files} files on the filesystem, occupying {downloads_dir_size}\n"
            f"💽 Occupied disk space: {pretty_print_size(occupied_disk_space_bytes)}, "
            f"available space: {pretty_print_size(available_disk_space_bytes)} "
            f"({available_disk_space_percent}% used)"
        )
    )


async def list_users(update: Update, limit: Optional[int] = None) -> None:
    """
    Displays a list of all or specified last users in groups of `90` users per message.

    :param update: Update: The ``update`` object
    :param limit: Optional[int]: Number of last users to return
    """
    users = list(User.all())
    users.sort(
        key=lambda user: (
            getattr(user, 'created_at', None) is not None,
            getattr(user, 'created_at', None),
            getattr(user, 'id', 0),
        ),
        reverse=True,
    )

    if limit:
        users = users[:limit]

    users.reverse()

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
        )
