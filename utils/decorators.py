from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from database.models import User
from .logging import logger
from .misc import get_effective_user_id, get_effective_user_username


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

            logger.info("A user with id %s has started using the bot.", user_id)
        else:
            if username and user.username != username:
                user.username = username
                user.save()

        context.user_data['user'] = user

        return await function(update, context, *args, **kwargs)

    return wrapper
