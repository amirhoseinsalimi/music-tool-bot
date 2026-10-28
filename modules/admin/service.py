import os
from datetime import datetime, timedelta, timezone
from typing import (
    Optional,
)

import psutil
from telegram import (
    Update,
)

from config.constants import DOWNLOAD_DIR_PATH
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

SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None

ACTIVE_DAYS = 90
MONTHLY_ACTIVE_DAYS = 31
CHURN_DAYS = 90


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
    language_counts: dict[str, int] = {
        'en': 0,
        'fa': 0,
        'ru': 0,
        'es': 0,
        'fr': 0,
        'ar': 0,
        'hi': 0,
        'id': 0,
    }

    active_status = UserStatus.where('slug', 'active').first()
    blocked_status = UserStatus.where('slug', 'blocked').first()
    deleted_status = UserStatus.where('slug', 'deleted').first()

    language_iso_by_id: dict[int, str] = {
        language.id: language.iso for language in Language.all()
    }

    status_by_language: dict[str, dict[str, int]] = {
        lang: {'active': 0, 'blocked': 0, 'deleted': 0}
        for lang in language_counts
    }
    status_totals: dict[str, int] = {'active': 0, 'blocked': 0, 'deleted': 0}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    daily_cutoff = now - timedelta(hours=24)
    weekly_cutoff = now - timedelta(hours=168)
    monthly_active_cutoff = now - timedelta(days=MONTHLY_ACTIVE_DAYS)
    active_cutoff = now - timedelta(days=ACTIVE_DAYS)

    total_users = 0
    daily_users = 0
    weekly_users = 0
    monthly_active_users = 0
    active_users_90d = 0
    inactive_users = 0
    churned_users = 0

    for user in User.all():
        iso = language_iso_by_id.get(getattr(user, 'language_id', None))
        lang = iso if iso in language_counts else None

        user_status_id = getattr(user, 'user_status_id', None)

        if user_status_id == (active_status.id if active_status else None):
            status = 'active'
        elif user_status_id == (blocked_status.id if blocked_status else None):
            status = 'blocked'
        elif user_status_id == (deleted_status.id if deleted_status else None):
            status = 'deleted'
        else:
            status = 'active'

        if lang:
            language_counts[lang] += 1
            status_by_language[lang][status] += 1

        status_totals[status] += 1
        total_users += 1

        last_interaction_at = getattr(user, 'last_interaction_at', None)

        if last_interaction_at is None:
            inactive_users += 1
        elif isinstance(last_interaction_at, datetime):
            if last_interaction_at.tzinfo is not None:
                last_interaction_at = last_interaction_at.replace(tzinfo=None)

            if last_interaction_at >= daily_cutoff:
                daily_users += 1
                weekly_users += 1
                monthly_active_users += 1
                active_users_90d += 1
            elif last_interaction_at >= weekly_cutoff:
                weekly_users += 1
                monthly_active_users += 1
                active_users_90d += 1
            elif last_interaction_at >= monthly_active_cutoff:
                monthly_active_users += 1
                active_users_90d += 1
            elif last_interaction_at >= active_cutoff:
                active_users_90d += 1
            else:
                churned_users += 1

    downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(DOWNLOAD_DIR_PATH))
    number_of_downloaded_files = len(os.listdir(DOWNLOAD_DIR_PATH))
    occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
        psutil.disk_usage('/')[-3:]

    language_lines = '\n'.join(
        t(language, 'adminLanguageStatsLine', language_code=lang.upper(),
          active=status_by_language[lang]['active'], blocked=status_by_language[lang]['blocked'],
          deleted=status_by_language[lang]['deleted'])
        for lang in language_counts
    )

    await update.message.reply_text(
        text=t(
            language,
            'adminStatsReport',
            total_users=total_users,
            status_active=status_totals['active'],
            status_blocked=status_totals['blocked'],
            status_deleted=status_totals['deleted'],
            daily_users=daily_users,
            weekly_users=weekly_users,
            monthly_active_users=monthly_active_users,
            active_users=active_users_90d,
            inactive_users=inactive_users,
            churned_users=churned_users,
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
