from telegram.ext import CallbackContext
from utils.fs.delete_file import delete_file


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