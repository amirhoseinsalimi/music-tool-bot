import os
from pathlib import Path

from telegram import Audio, PhotoSize
from telegram.ext import CallbackContext


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


def delete_all_user_files(user_id: int) -> None:
    """
    Deletes all file in a specified user's directory.

    :param user_id: int: The user's `id` whom we want to delete files
    """
    absolute_path = os.getcwd()
    user_path = f"downloads/{user_id}/"
    full_path = os.path.join(absolute_path, user_path)

    if not os.path.isdir(full_path):
        return

    for f in os.listdir(full_path):
        delete_file(os.path.join(full_path, f))


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
    user_download_dir = f"downloads/{user_id}"
    file_extension = ''

    file_id = await context.bot.get_file(file_to_download.file_id)

    if file_type == 'audio':
        file_name = file_to_download.file_name
        file_extension = file_name.split(".")[-1]
    elif file_type == 'photo':
        file_extension = 'jpg'

    file_download_path = f"{user_download_dir}/{file_id.file_id}.{file_extension}"

    try:
        await file_id.download_to_drive(f"{user_download_dir}/{file_id.file_id}.{file_extension}")

        return file_download_path
    except ValueError as error:
        raise Exception(f"Couldn't download the file with file_id: {file_id}") from error


def get_dir_size_in_bytes(dir_path: str) -> float:
    """
    Get the size of a directory and its subdirectories in bytes.

    :param dir_path: str: The path of the directory to get its size
    :return: float: The size of a directory and its subdirectories in bytes
    """
    root_directory = Path(dir_path)

    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())
