import os
from pathlib import Path

from telegram.ext import CallbackContext

from models.admin import Admin
from models.user import User
from utils.lang import keys


def translate_key_to(key: str, destination_lang: str) -> str:
    """Find the specified key in the `keys` dictionary and returns the corresponding
    value for the given language

    **Keyword arguments:**
     - file_path (str) -- The file path of the file to delete

    **Returns:**
     - The value of the requested key in the dictionary
    """
    if key in keys:
        return keys[key][destination_lang]


def delete_file(file_path: str) -> None:
    """Deletes a file from the filesystem. Simply ignores the files that don't exist.

    **Keyword arguments:**
     - file_path (str) -- The file path of the file to delete
    """
    if os.path.exists(file_path):
        os.remove(file_path)


def generate_music_info(tag_editor_context: dict) -> str:
    """Generate the details of the music based on the values in `tag_editor_context`
    dictionary

    **Keyword arguments:**
     - tag_editor_context (dict) -- The context object of the user

    **Returns:**
     `str`
    """
    return (
        f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
        f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
        f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
        f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
        f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
        f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
        "🆔 {}\n"
    )


def increment_usage_counter_for_user(user_id: int) -> int:
    """Increment the `number_of_files_sent` column of user with the specified `user_id`.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     The new value for `user.number_of_files_sent`
    """
    try:
        user = User.where('user_id', '=', user_id).first()

        user.number_of_files_sent = user.number_of_files_sent + 1

        user.push()

        return user.number_of_files_sent
    except:
        return 0


def is_user_admin(user_id: int) -> bool:
    """Check if the user with `user_id` is admin or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)


def is_user_owner(user_id: int) -> bool:
    """Check if the user with `user_id` is owner or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False


def reset_user_data_context(context: CallbackContext) -> None:
    user_data = context.user_data

    delete_file(user_data['music_path'])
    delete_file(user_data['art_path'])
    delete_file(user_data['new_art_path'])

    user_data['tag_editor'] = {}
    user_data['music_path'] = ''
    user_data['music_duration'] = ''
    user_data['art_path'] = ''
    user_data['new_art_path'] = ''
    user_data['current_active_module'] = ''
    user_data['music_message_id'] = ''
    user_data['language'] = user_data['language'] if ('language' in user_data) else 'en'


def save_text_into_tag(value: str, current_tag: str, context: CallbackContext) -> None:
    """Store a value of the given tag in the corresponding context.

    **Keyword arguments:**
     - value (str) -- The value to be stored as the value of `current_tag`
     - current_tag (str) -- The key to store the value into
     - context (CallbackContext) -- The context of a user to store the key:value pair into
    """
    # TODO: Check if the value is of the correct type
    context.user_data['tag_editor'][current_tag] = value


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
    except:
        user_download_dir = None
        raise Exception(f"Can't create directory for user_id: {user_id}")

    return user_download_dir


def convert_seconds_to_human_readable_form(seconds: int) -> str:
    """Convert seconds to human readable time format, e.g. 02:30

    **Keyword arguments:**
     - seconds (int) -- Seconds to convert

    **Returns:**
     Formatted string
    """
    minutes = int(seconds / 60)
    remainder = seconds % 60

    minutes_formatted = str(minutes) if minutes >= 10 else "0" + str(minutes)
    seconds_formatted = str(remainder) if remainder >= 10 else "0" + str(remainder)

    return f"{minutes_formatted}:{seconds_formatted}"


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
    except:
        file_download_path = None
        raise Exception(f"Couldn't download the file with file_id: {file_id}")

    return file_download_path
