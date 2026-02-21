from pathlib import Path

from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext

from database.models import User
from utils import get_user_language_or_fallback, get_user_data, t


def create_user_directory(user_id: int) -> str | None:
    """
    Creates a directory for a user with a given id.

    :param user_id: int: The ``user_id`` of the user we want to create directory for
    :raises OSError | FileNotFoundError | BaseException: Can't create directory for the user
    :return: str | None: The relative path of the user's directory if succeeds; ``None`` otherwise
    """
    user_download_dir = f"downloads/{user_id}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)

        return user_download_dir
    except (OSError, FileNotFoundError, BaseException) as error:
        raise Exception(f"Can't create directory for user_id: {user_id}") from error


def generate_start_over_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``start_over_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Start over keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [t(language, 'btnNewFile')],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_back_button_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``back_button_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Back button keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [t(language, 'btnBack')],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_module_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``module_selector_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Module selector keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [
                    t(language, 'btnTagAndArtEditor'),
                    t(language, 'btnMusicToVoiceConverter')
                ],
                [
                    t(language, 'btnMusicCutter'),
                    t(language, 'btnBitrateChanger')
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def does_user_have_music_file(music_path: str) -> bool:
    """
    Checks if a user has a music file.

    :param music_path: str: The user's current music_path
    :return: bool: Whether the user has a music path
    """
    return bool(music_path)


def increment_file_counter_for_user(user_id: int) -> None:
    """
    Increments the ``number_of_files_sent`` field for a given user.

    :param user_id: int: The ``user_id`` of the user whose file count we want to increment
    :raises LookupError: No Such a user in the database
    """
    user = User.where('user_id', '=', user_id).first()

    if not user:
        raise LookupError(f'User with id {user_id} not found.')

    user.update({
        "number_of_files_sent": user.number_of_files_sent + 1
    })


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
