import re
from functools import lru_cache
from pathlib import Path

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

from config.constants import DOWNLOAD_DIR_PATH
from database.models import User
from utils import get_user_language_or_fallback, reset_user_data_context, t
from utils.extensions import optional_keyboard_rows

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / 'pyproject.toml'
VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$')


def create_user_directory(user_id: int) -> str | None:
    """
    Creates a directory for a user with a given id.

    :param user_id: int: The ``user_id`` of the user we want to create directory for
    :raises OSError | FileNotFoundError: Can't create directory for the user
    :return: str | None: The path of the user's directory if succeeds; ``None`` otherwise
    """
    user_download_dir = DOWNLOAD_DIR_PATH / str(user_id)

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)

        return str(user_download_dir)
    except (OSError, FileNotFoundError) as error:
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


def generate_module_selector_keyboard(language: str, user_id=None) -> ReplyKeyboardMarkup:
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
            ] + optional_keyboard_rows(language, user_id),
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
    return bool(music_path and Path(music_path).is_file())


def has_active_music_file(user_data: dict, user_id: int) -> bool:
    """Return whether the current session points to an existing file owned by this user."""
    music_path = user_data.get('music_path')
    if not music_path:
        return False

    try:
        user_directory = (DOWNLOAD_DIR_PATH / str(user_id)).resolve()
        source_path = Path(music_path).resolve(strict=True)
        source_path.relative_to(user_directory)
    except (OSError, RuntimeError, TypeError, ValueError):
        return False

    return source_path.is_file()


async def require_active_music(update, context) -> bool:
    """Stop a music feature unless this user has a retained current track."""
    user_data = getattr(context, 'user_data', None) or {}
    user = user_data.get('user')
    user_id = getattr(user, 'user_id', None) or getattr(update.effective_user, 'id', None)
    language = get_user_language_or_fallback(user_data)

    if user_id is not None and has_active_music_file(user_data, user_id):
        return True

    if user_id is not None and user is not None:
        reset_user_data_context(user_id, user_data)

    await update.effective_message.reply_text(
        text=t(language, 'startOverMessage'),
        reply_markup=ReplyKeyboardRemove(),
    )
    return False


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


@lru_cache(maxsize=1)
def get_app_version() -> str:
    try:
        with PYPROJECT_PATH.open(mode='r', encoding='utf-8') as pyproject_file:
            for line in pyproject_file:
                match = VERSION_PATTERN.match(line)

                if match:
                    return match.group(1)
    except OSError:
        pass

    return 'unknown'
