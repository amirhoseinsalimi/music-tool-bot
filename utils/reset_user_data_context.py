from telegram.ext import CallbackContext


def reset_user_data_context(context: CallbackContext) -> None:
    user_data = context.user_data

    user_data['tag_editor'] = {}
    user_data['music_path'] = ''
    user_data['music_duration'] = ''
    user_data['art_path'] = ''
    user_data['new_art_path'] = ''
    user_data['current_active_module'] = ''
    user_data['music_message_id'] = ''
    user_data['language'] = user_data['language'] if ('language' in user_data) else 'en'
