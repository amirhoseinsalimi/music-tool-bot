import os
from pathlib import Path

from telegram import Audio, PhotoSize
from telegram.ext import CallbackContext

from config.constants import DOWNLOAD_DIR_PATH
from .logging import get_logger

logger = get_logger(__name__)


def delete_all_user_files(user_id: int) -> None:
    """
    Deletes all file in a specified user's directory.

    :param user_id: int: The user's `id` whom we want to delete files
    """
    full_path = DOWNLOAD_DIR_PATH / str(user_id)

    if not full_path.is_dir():
        return

    for file_path in full_path.iterdir():
        delete_file(str(file_path))


def delete_file(file_path: str) -> None:
    """
    Deletes a file from the filesystem. Simply ignores the files that don't exist.

    :param file_path: str: The file path of the file to delete
    """
    if not os.path.exists(file_path):
        return

    os.remove(file_path)


async def download_file(
        user_id: int,
        file_to_download: Audio | PhotoSize,
        file_type: str,
        context: CallbackContext
) -> str | None:
    """
    Downloads a file using convenience methods of "python-telegram-bot"

    :param user_id: int: The user's `id` show sent the file
    :param file_to_download: Audio | PhotoSize: The file object to download
    :param file_type: str: The type of the file, either 'photo' or 'audio'
    :param context: CallbackContext: The ``context`` object of the user
    :raises ValueError: Couldn't download the file
    :return: The path of the downloaded file if the operation succeeds; ``None`` otherwise
    """
    user_download_dir = DOWNLOAD_DIR_PATH / str(user_id)
    file_extension = ''

    file_id = await context.bot.get_file(file_id=file_to_download.file_id)
    logger.debug("Resolved telegram file %s for user %s type=%s", file_id.file_id, user_id, file_type)

    if file_type == 'audio':
        file_extension = get_audio_file_extension(file_to_download)
    elif file_type == 'photo':
        file_extension = 'jpg'

    file_download_path = user_download_dir / f"{file_id.file_id}.{file_extension}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)

        await file_id.download_to_drive(str(file_download_path))

        logger.info("Downloaded %s file for user %s to %s", file_type, user_id, file_download_path)

        return str(file_download_path)
    except ValueError as error:

        logger.exception("Failed downloading %s file for user %s", file_type, user_id)
        raise Exception(f"Couldn't download the file with file_id: {file_id}") from error


def get_audio_file_extension(audio):
    """
    Determine the file type of Telegram audio object using `mime_type` and extension.

    This helper prioritizes `audio.mime_type` when available and pattern-matches common
    Telegram music containers (mpeg → mp3, ogg, flac, wav, aac/mp4 → m4a). If no known
    mime pattern matches, it falls back to the file extension from `audio.file_name`.

    :param audio: Audio: A Telegram audio object received from an update
    :return: str: The normalized audio format (e.g., "mp3", "ogg", "flac", "m4a", "wav") or `None`
    """
    mime_type = (audio.mime_type or "").lower()
    extension = os.path.splitext(audio.file_name or "")[1].lower().lstrip(".")

    match mime_type:
        case mime if "mpeg" in mime:
            return "mp3"
        case mime if "ogg" in mime:
            return "ogg"
        case mime if "flac" in mime:
            return "flac"
        case mime if "wav" in mime:
            return "wav"
        case mime if "aac" in mime or "mp4" in mime:
            return "m4a"
        case _:
            pass

    match extension:
        case "mp3" | "aac" | "m4a" | "ogg" | "flac" | "wav":
            return extension
        case _:
            return None
