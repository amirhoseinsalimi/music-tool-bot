from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from database.models import User
from .context import SessionUser
from .logging import get_logger
from .misc import get_effective_user_id, get_effective_user_username

logger = get_logger(__name__)


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
                'language': 'en',
                'number_of_files_sent': 0,
            })

            logger.info("User %s started using the bot", user_id)
        else:
            if username and user.username != username:
                logger.info("User %s changed username from %s to %s", user_id, user.username, username)
                user.username = username
                user.save()

        context.user_data['user'] = SessionUser(
            user_id=user.user_id,
            username=user.username,
        )

        return await function(update, context, *args, **kwargs)

    return wrapper
