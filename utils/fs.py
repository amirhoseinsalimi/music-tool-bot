import os
from pathlib import Path

from telegram.ext import CallbackContext


def create_user_directory(user_id: int) -> str:
    """Create a directory for a user with a given id.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     The path of the created directory
    """
    user_download_dir = f"downloads/{user_id}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)
    except (OSError, FileNotFoundError, BaseException) as error:
        raise Exception(f"Can't create directory for user_id: {user_id}") from error

    return user_download_dir


def delete_all_user_files(user_id: int):
    absolute_path = os.getcwd()
    user_path = f"downloads/{user_id}/"
    full_path = os.path.join(absolute_path, user_path)

    if not os.path.isdir(full_path):
        return

    for f in os.listdir(full_path):
        delete_file(os.path.join(full_path, f))


def delete_file(file_path: str) -> None:
    """Deletes a file from the filesystem. Simply ignores the files that don't exist.

    **Keyword arguments:**
     - file_path (str) -- The file path of the file to delete
    """
    if not os.path.exists(file_path):
        return

    os.remove(file_path)


def download_file(user_id: int, file_to_download, file_type: str, context: CallbackContext) -> str:
    """Download a file using convenience methods of "python-telegram-bot"

    **Keyword arguments:**
     - user_id (int) -- The user's id
     - file_to_download (*) -- The file object to download
     - file_type (str) -- The type of the file, either 'photo' or 'audio'
     - context (CallbackContext) -- The context object of the user

    **Returns:**
     The path of the downloaded file
    """
    user_download_dir = f"downloads/{user_id}"
    file_id = ''
    file_extension = ''

    if file_type == 'audio':
        file_id = context.bot.get_file(file_to_download.file_id)
        file_name = file_to_download.file_name
        file_extension = file_name.split(".")[-1]
    elif file_type == 'photo':
        file_id = context.bot.get_file(file_to_download.file_id)
        file_extension = 'jpg'

    file_download_path = f"{user_download_dir}/{file_id.file_id}.{file_extension}"

    try:
        file_id.download(f"{user_download_dir}/{file_id.file_id}.{file_extension}")
    except ValueError as error:
        raise Exception(f"Couldn't download the file with file_id: {file_id}") from error

    return file_download_path


def get_dir_size_in_bytes(dir_path: str) -> float:
    """Return the size of a directory and its subdirectories in bytes


    **Keyword arguments:**
     - dir_path (str) -- The path of the directory

    **Returns:**
     Size of the directory
    """
    root_directory = Path(dir_path)

    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())
