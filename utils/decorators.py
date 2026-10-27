from datetime import datetime, timezone
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from database.models import Language, User
from .context import SessionUser
from .logging import get_logger

logger = get_logger(__name__)


def _get_default_language_id() -> int | None:
    """Get the ID of the default language, or ``None`` if none is marked as default."""
    default_language = Language.where('is_default', True).first()

    return default_language.id if default_language else None


def upsert_user(function):
    @wraps(function)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        telegram_user = getattr(update, 'effective_user', None)
        if telegram_user is None:
            logger.warning('Skipping user-specific handler without an effective Telegram user: handler=%s update_id=%s',
                           function.__name__, getattr(update, 'update_id', None))
            return None

        user_id = telegram_user.id
        username = telegram_user.username
        display_name = ' '.join(
            part.strip()
            for part in (getattr(telegram_user, 'first_name', None),
                         getattr(telegram_user, 'last_name', None))
            if isinstance(part, str) and part.strip()
        ) or None
        interaction_at = datetime.now(timezone.utc)

        user = User.where('user_id', '=', user_id).first()
        new_user = user is None

        if not user:
            user = User.create({
                'user_id': user_id,
                'username': username,
                'display_name': display_name,
                'language_id': _get_default_language_id(),
                'number_of_files_sent': 0,
                'user_status_id': 1,
                'last_interaction_at': interaction_at,
            })

            logger.info("User %s started using the bot", user_id)
        else:
            if getattr(user, 'display_name', None) != display_name:
                user.display_name = display_name

            if username and user.username != username:
                logger.info("User %s changed username from %s to %s", user_id, user.username, username)
                user.username = username

            if user.user_status_id != 1:
                logger.info("User %s is interacting again. Resetting status to active.", user_id)
                user.user_status_id = 1

            user.last_interaction_at = interaction_at
            user.save()

        context.user_data['user'] = SessionUser(
            user_id=user.user_id,
            username=user.username,
        )
        # This value is only needed by the current update and must not be
        # persisted alongside the user's session.
        context._new_user_on_this_update = new_user

        return await function(update, context, *args, **kwargs)

    wrapper.upserts_user = True
    return wrapper
