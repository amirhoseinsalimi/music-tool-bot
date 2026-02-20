from telegram import Update
from telegram.ext import CallbackContext

from utils import get_user_language_or_fallback, generate_back_button_keyboard, get_user_data, t


def does_user_have_music_file(music_path: str) -> bool:
    """
    Checks if a user has a music file.

    :param music_path: str: The user's current music_path
    :return: bool: Whether the user has a music path
    """
    return bool(music_path)


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    """
    Displays an error message and offers the user to go back. It is called when the user tries to access a feature that
    has not been implemented yet.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    language = get_user_language_or_fallback(get_user_data(context))

    back_button_keyboard = generate_back_button_keyboard(language)

    update.message.reply_text(
        text=t(language, 'errNotImplemented'),
        reply_markup=back_button_keyboard
    )
