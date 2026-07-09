from datetime import datetime, timezone
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from database.models import Language, User
from .context import SessionUser
from .logging import get_logger
from .misc import get_effective_user_id, get_effective_user_username

logger = get_logger(__name__)


def _get_default_language_id() -> int | None:
    """Get the ID of the default language, or ``None`` if none is marked as default."""
    default_language = Language.where('is_default', True).first()

    return default_language.id if default_language else None


def upsert_user(function):
    @wraps(function)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = get_effective_user_id(update)
        username = get_effective_user_username(update)

        user = User.where('user_id', '=', user_id).first()

        if not user:
            user = User.create({
                'user_id': user_id,
                'username': username,
                'language_id': _get_default_language_id(),
                'number_of_files_sent': 0,
                'user_status_id': 1,
            })

            logger.info("User %s started using the bot", user_id)
        else:
            if username and user.username != username:
                logger.info("User %s changed username from %s to %s", user_id, user.username, username)
                user.username = username

            if user.user_status_id != 1:
                logger.info("User %s is interacting again. Resetting status to active.", user_id)
                user.user_status_id = 1

            user.last_interaction_at = datetime.now(timezone.utc)
            user.save()

        context.user_data['user'] = SessionUser(
            user_id=user.user_id,
            username=user.username,
        )

        return await function(update, context, *args, **kwargs)

    return wrapper
