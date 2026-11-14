from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import CallbackContext

from database.models import User, UserStatus
from modules.core.utils import generate_start_over_keyboard
from utils import delete_all_user_files, get_user_language_or_fallback, reset_user_data_context, t
from utils.logging import get_logger

logger = get_logger(__name__)

def _mark_blocked(user_id: int | None) -> None:
    if user_id is None:
        return
    user = User.where('user_id', '=', user_id).first()
    status = UserStatus.where('slug', '=', 'blocked').first()
    if user and status:
        user.user_status_id = status.id
        user.save()

async def on_error(update: Update, context: CallbackContext) -> None:
    error = context.error
    update_id = getattr(update, 'update_id', None)
    telegram_user = getattr(update, 'effective_user', None) if update is not None else None
    user_id = getattr(telegram_user, 'id', None)
    if isinstance(error, Forbidden):
        _mark_blocked(user_id)
        return
    if isinstance(error, BadRequest):
        if 'message is not modified' in str(error).lower():
            return
    elif isinstance(error, (RetryAfter, NetworkError, TimedOut)):
        logger.warning('Telegram transient error class=%s update_id=%s', type(error).__name__, update_id)
        return
    origin = None
    if update is None:
        traceback = error.__traceback__
        frames = []
        while traceback:
            frame = traceback.tb_frame
            frames.append(f'{frame.f_code.co_filename.rsplit("/", 1)[-1]}:{traceback.tb_lineno}:{frame.f_code.co_name}')
            traceback = traceback.tb_next
        origin = ' > '.join(frames[-5:]) or 'unknown'
    logger.error('Unhandled handler error class=%s update_id=%s origin=%s',
                 type(error).__name__, update_id, origin)
    if update is None or user_id is None:
        return
    user_data = getattr(context, 'user_data', None)
    language = get_user_language_or_fallback(user_data or {})
    if user_data is not None and user_id is not None:
        reset_user_data_context(user_id, user_data)
        delete_all_user_files(user_id)
    message = getattr(update, 'effective_message', None)
    if message is not None:
        await message.reply_text(text=t(language, 'unexpectedError'), reply_markup=generate_start_over_keyboard(language))
