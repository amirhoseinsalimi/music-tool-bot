import os
import re
from pathlib import Path

import music_tag
from telegram import ReplyKeyboardMarkup
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
    if key not in keys:
        raise KeyError("Specified key doesn't exist")

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
    ctx = tag_editor_context

    return (
        f"*🗣 Artist:* {ctx['artist'] if ctx['artist'] else '-'}\n"
        f"*🎵 Title:* {ctx['title'] if ctx['title'] else '-'}\n"
        f"*🎼 Album:* {ctx['album'] if ctx['album'] else '-'}\n"
        f"*🎹 Genre:* {ctx['genre'] if ctx['genre'] else '-'}\n"
        f"*📅 Year:* {ctx['year'] if ctx['year'] else '-'}\n"
        f"*💿 Disk Number:* {ctx['disknumber'] if ctx['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {ctx['tracknumber'] if ctx['tracknumber'] else '-'}\n"
        "{}\n"
    )


def increment_usage_counter_for_user(user_id: int) -> int:
    """Increment the `number_of_files_sent` column of user with the specified `user_id`.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     The new value for `user.number_of_files_sent`
    """
    user = User.where('user_id', '=', user_id).first()

    if user:
        user.number_of_files_sent = user.number_of_files_sent + 1
        user.push()

        return user.number_of_files_sent

    raise LookupError(f'User with id {user_id} not found.')


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
    language = user_data['language'] if ('language' in user_data) else 'en'

    if 'music_path' in user_data:
        delete_file(user_data['music_path'])
    if 'art_path' in user_data:
        delete_file(user_data['art_path'])
    if 'new_art_path' in user_data:
        delete_file(user_data['new_art_path'])

    new_user_data = {
        'tag_editor': {},
        'music_path': '',
        'music_duration': 0,
        'art_path': '',
        'new_art_path': '',
        'current_active_module': '',
        'music_message_id': 0,
        'language': language,
    }
    context.user_data.update(new_user_data)


def save_text_into_tag(
        value: str,
        current_tag: str,
        context: CallbackContext,
        is_number: bool = False
) -> None:
    """Store a value of the given tag in the corresponding context.

    **Keyword arguments:**
     - value (str) -- The value to be stored as the value of `current_tag`
     - current_tag (str) -- The key to store the value into
     - context (CallbackContext) -- The context of a user to store the key:value pair into
    """
    if is_number:
        if isinstance(int(value), int):
            context.user_data['tag_editor'][current_tag] = value
        else:
            context.user_data['tag_editor'][current_tag] = 0
    else:
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
    except (OSError, FileNotFoundError, BaseException) as error:
        raise Exception(f"Can't create directory for user_id: {user_id}") from error

    return user_download_dir


def convert_seconds_to_human_readable_form(seconds: int) -> str:
    """Convert seconds to human readable time format, e.g. 02:30

    **Keyword arguments:**
     - seconds (int) -- Seconds to convert

    **Returns:**
     Formatted string
    """
    if seconds <= 0:
        return "00:00"

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
    except ValueError as error:
        raise Exception(f"Couldn't download the file with file_id: {file_id}") from error

    return file_download_path


def generate_back_button_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create an return an instance of `back_button_keyboard`


    **Keyword arguments:**
     - language (str) -- The desired language to generate labels

    **Returns:**
     ReplyKeyboardMarkup instance
    """
    return (
        ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_BACK', language)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_start_over_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create an return an instance of `start_over_keyboard`


    **Keyword arguments:**
     - language (str) -- The desired language to generate labels

    **Returns:**
     ReplyKeyboardMarkup instance
    """
    return (
        ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_NEW_FILE', language)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_module_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create an return an instance of `module_selector_keyboard`


    **Keyword arguments:**
     - language (str) -- The desired language to generate labels

    **Returns:**
     ReplyKeyboardMarkup instance
    """
    return (
        ReplyKeyboardMarkup(
            [
                [
                    translate_key_to('BTN_TAG_EDITOR', language),
                    translate_key_to('BTN_MUSIC_TO_VOICE_CONVERTER', language)
                ],
                [
                    translate_key_to('BTN_MUSIC_CUTTER', language),
                    translate_key_to('BTN_BITRATE_CHANGER', language)
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_tag_editor_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create an return an instance of `tag_editor_keyboard`


    **Keyword arguments:**
     - language (str) -- The desired language to generate labels

    **Returns:**
     ReplyKeyboardMarkup instance
    """
    return (
        ReplyKeyboardMarkup(
            [
                [
                    translate_key_to('BTN_ARTIST', language),
                    translate_key_to('BTN_TITLE', language),
                    translate_key_to('BTN_ALBUM', language)
                ],
                [
                    translate_key_to('BTN_GENRE', language),
                    translate_key_to('BTN_YEAR', language),
                    translate_key_to('BTN_ALBUM_ART', language)
                ],
                [
                    translate_key_to('BTN_DISK_NUMBER', language),
                    translate_key_to('BTN_TRACK_NUMBER', language)
                ],
                [
                    translate_key_to('BTN_BACK', language)
                ]
            ],
            resize_keyboard=True,
        )
    )


def save_tags_to_file(file: str, tags: dict, new_art_path: str) -> str:
    """Create an return an instance of `tag_editor_keyboard`


    **Keyword arguments:**
     - file (str) -- The path of the file
     - tags (str) -- The dictionary containing the tags and their values
     - new_art_path (str) -- The new album art to set

    **Returns:**
     The path of the file
    """
    music = music_tag.load_file(file)

    try:
        if new_art_path:
            with open(new_art_path, 'rb') as art:
                music['artwork'] = art.read()
    except OSError as error:
        raise Exception("Couldn't set hashtags") from error

    music['artist'] = tags['artist'] if tags['artist'] else ''
    music['title'] = tags['title'] if tags['title'] else ''
    music['album'] = tags['album'] if tags['album'] else ''
    music['genre'] = tags['genre'] if tags['genre'] else ''
    music['year'] = int(tags['year']) if tags['year'] else 0
    music['disknumber'] = int(tags['disknumber']) if tags['disknumber'] else 0
    music['tracknumber'] = int(tags['tracknumber']) if tags['tracknumber'] else 0

    music.save()

    return file


def parse_cutting_range(text: str) -> (int, int):
    text = re.sub(' ', '', text)
    beginning, _, ending = text.partition('-')

    if '-' not in text:
        raise ValueError('Malformed music range')

    if ':' in text:
        beginning_sec = int(beginning.partition(':')[0].lstrip('0') if
                            beginning.partition(':')[0].lstrip('0') else 0) * 60 \
                        + int(beginning.partition(':')[2].lstrip('0') if
                              beginning.partition(':')[2].lstrip('0') else 0)

        ending_sec = int(ending.partition(':')[0].lstrip('0') if
                         ending.partition(':')[0].lstrip('0') else 0) * 60 \
            + int(ending.partition(':')[2].lstrip('0') if
                  ending.partition(':')[2].lstrip('0') else 0)
    else:
        beginning_sec = int(beginning)
        ending_sec = int(ending)

    return beginning_sec, ending_sec


def pretty_print_size(number_of_bytes: float) -> str:
    """Pretty print file sizes


    **Keyword arguments:**
     - number_of_bytes (float) -- Number of bytes to convert

    **Returns:**
     A human-readable file size
    """
    units = [
        (1 << 50, ' PB'),
        (1 << 40, ' TB'),
        (1 << 30, ' GB'),
        (1 << 20, ' MB'),
        (1 << 10, ' KB'),
        (1, (' byte', ' bytes')),
    ]

    for factor, suffix in units:
        if number_of_bytes >= factor:
            break
    amount = int(number_of_bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix


def get_dir_size_in_bytes(dir_path: str) -> float:
    """Return the size of a directory and its sub-directories in bytes


    **Keyword arguments:**
     - dir_path (str) -- The path of the directory

    **Returns:**
     Size of the directory
    """
    root_directory = Path(dir_path)
    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())
