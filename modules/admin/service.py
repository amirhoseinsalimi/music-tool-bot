import os
from datetime import datetime, timezone
from typing import (
    Optional,
)

import psutil
from telegram import (
    Update,
)

from config.constants import DOWNLOAD_DIR_PATH
from user_stats import stats_counts
from database.models import (
    Admin,
    Language,
    User,
    UserStatus,
)
from utils import (
    get_message_text,
    t,
)
from .utils import (
    extract_user_id,
    is_user_admin,
    get_dir_size_in_bytes,
    pretty_print_size,
)

async def add_admin(update: Update, language: str = 'en') -> None:
    """
    Adds a user ``id`` to the ``admins`` table. If succeeds, sends a success message.

    :param update: Update: The ``update`` object
    """
    admin_id_to_add = extract_user_id(get_message_text(update))

    if not admin_id_to_add.isdigit():
        await update.message.reply_text(t(language, 'adminMalformedUserId', user_id=admin_id_to_add))

    admin_id_to_add_int = int(admin_id_to_add)

    admin = Admin()
    admin.admin_user_id = admin_id_to_add_int

    admin.save()

    await update.message.reply_text(text=t(language, 'adminUserAdded', user_id=admin_id_to_add))


async def del_admin(update: Update, language: str = 'en') -> None:
    """
    Deletes a user ``id`` from the ``admins`` table. Then sends a message accordingly.

    :param update: Update: The ``update`` object
    """
    admin_id_to_delete = extract_user_id(get_message_text(update))

    if not admin_id_to_delete.isdigit():
        await update.message.reply_text(t(language, 'adminMalformedUserId', user_id=admin_id_to_delete))

    admin_id_to_delete_int = int(admin_id_to_delete)

    if is_user_admin(admin_id_to_delete_int):
        Admin.where('admin_user_id', '=', admin_id_to_delete).delete()

        await update.message.reply_text(text=t(language, 'adminUserRemoved', user_id=admin_id_to_delete))
    else:
        await update.message.reply_text(text=t(language, 'adminUserNotAdmin', user_id=admin_id_to_delete))


async def show_stats(update: Update, language: str = 'en') -> None:
    """
    Displays a summary about how the bot is being used:
     - The number of users using this bot
     - The number of English and Persian users
     - The number & size of the files on the disk
     - How much disk space is occupied.
     - Daily / weekly / monthly active / active / inactive / churned user counts

    :param update: Update: The ``update`` object
    """
    language_codes = ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id')
    status_by_id = {}
    for slug in ('active', 'blocked', 'deleted'):
        status = UserStatus.where('slug', slug).first()
        if status is not None:
            status_by_id[status.id] = slug
    language_by_id = {row.id: row.iso for row in Language.all() if row.iso in language_codes}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    statuses, activity, status_by_language = stats_counts(now, (
        (status_by_id.get(getattr(user, 'user_status_id', None), 'active'),
         language_by_id.get(getattr(user, 'language_id', None)),
         getattr(user, 'last_interaction_at', None))
        for user in User.all()
    ), language_codes)

    downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(DOWNLOAD_DIR_PATH))
    number_of_downloaded_files = len(os.listdir(DOWNLOAD_DIR_PATH))
    occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
        psutil.disk_usage('/')[-3:]

    language_lines = '\n'.join(
        t(language, 'adminLanguageStatsLine', language_code=lang.upper(),
          active=status_by_language[lang]['active'], blocked=status_by_language[lang]['blocked'],
          deleted=status_by_language[lang]['deleted'])
        for lang in language_codes
    )

    await update.message.reply_text(
        text=t(
            language,
            'adminStatsReport',
            total_users=sum(statuses.values()),
            status_active=statuses['active'],
            status_blocked=statuses['blocked'],
            status_deleted=statuses['deleted'],
            daily_users=activity['daily_active_users'],
            weekly_users=activity['weekly_active_users'],
            monthly_active_users=activity['monthly_active_users'],
            active_users=activity['active_90d_users'],
            inactive_users=activity['inactive_users'],
            churned_users=activity['churned_90d_users'],
            language_lines=language_lines,
            downloaded_files=number_of_downloaded_files,
            downloads_dir_size=downloads_dir_size,
            occupied_disk_space=pretty_print_size(occupied_disk_space_bytes),
            available_disk_space=pretty_print_size(available_disk_space_bytes),
            disk_used_percent=available_disk_space_percent,
        )
    )


async def list_users(update: Update, limit: Optional[int] = None, language: str = 'en') -> None:
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
            t(language, 'adminUserRow', user_id=user.user_id,
              username=f'@{user.username}' if user.username else t(language, 'adminNoUsername'),
              file_count=user.number_of_files_sent)
            for user in chunk
        )

        await update.message.reply_text(
            text=t(language, 'adminUserListPage', total_users=len(users), page=index + 1,
                   pages=len(user_chunks), user_lines=reply_message),
        )
