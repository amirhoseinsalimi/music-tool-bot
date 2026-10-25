import time

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import CallbackContext

from config.envs import OWNER_USER_ID_INT
from database.models import User, UserStatus
from modules.core.utils import generate_start_over_keyboard
from utils import delete_all_user_files, get_effective_user_id, get_user_language_or_fallback, reset_user_data_context, t
from utils.logging import get_logger

logger = get_logger(__name__)
_alerted: dict[str, float] = {}

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
    user_id = get_effective_user_id(update)
    if isinstance(error, Forbidden):
        _mark_blocked(user_id)
        return
    if isinstance(error, (RetryAfter, NetworkError, TimedOut)):
        logger.warning('Telegram transient error class=%s update_id=%s', type(error).__name__, getattr(update, 'update_id', None))
        return
    if isinstance(error, BadRequest) and 'message is not modified' in str(error).lower():
        return
    update_id = getattr(update, 'update_id', None)
    logger.exception('Unhandled handler error class=%s update_id=%s', type(error).__name__, update_id)
    user_data = getattr(context, 'user_data', None)
    language = get_user_language_or_fallback(user_data or {})
    if user_data is not None and user_id is not None:
        reset_user_data_context(user_id, user_data)
        delete_all_user_files(user_id)
    message = getattr(update, 'effective_message', None)
    if message is not None:
        await message.reply_text(text=t(language, 'unexpectedError'), reply_markup=generate_start_over_keyboard(language))
    fingerprint = f'{type(error).__name__}:{getattr(error.__traceback__, "tb_lineno", "unknown")}'
    now = time.monotonic()
    if now - _alerted.get(fingerprint, 0) >= 600 and OWNER_USER_ID_INT:
        _alerted[fingerprint] = now
        await context.bot.send_message(chat_id=OWNER_USER_ID_INT, text=f'Unhandled error {fingerprint} (update {update_id})')
