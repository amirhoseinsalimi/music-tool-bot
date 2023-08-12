from telegram import Message, Update
from telegram.ext import CallbackContext
from telegram.ext.utils.types import UD

import utils.i18n as lp
from config.modules import Module
from utils import delete_all_user_files
from .i18n import t


def get_effective_user_id(update: Update) -> int:
    return update.effective_user.id


def get_effective_user_username(update: Update) -> str | None:
    return update.effective_user.username


def get_effective_message_id(update: Update) -> id:
    return update.effective_message.message_id


def get_user_data(context: CallbackContext) -> UD | None:
    return context.user_data


def set_current_module(user_data: UD, module: Module | str):
    user_data['current_module'] = module.value


def get_message(update: Update) -> Message | None:
    return update.message


def get_user_language_or_fallback(user_data: UD) -> str:
    return user_data['language'] if 'language' in user_data else 'en'


def get_message_text(update: Update) -> str | None:
    return update.message.text


def get_chat_id(update: Update) -> int:
    return update.effective_message.chat_id


def unset_current_module(user_data) -> None:
    user_data['current_module'] = ''


def reset_user_data_context(user_id: int, user_data: UD) -> None:
    language = get_user_language_or_fallback(user_data) if ('language' in user_data) else 'en'

    delete_all_user_files(user_id)

    new_user_data = {
        'tag_editor': {},
        'bitrate_changer': {},
        'music_path': '',
        'music_duration': 0,
        'art_path': '',
        'new_art_path': '',
        'current_module': '',
        'music_message_id': 0,
        'language': language,
    }

    user_data.update(new_user_data)


def is_user_data_empty(user_data: UD) -> bool:
    return len(user_data) == 0


def reply_default_message(update: Update, language: str) -> None:
    message_text = t(lp.DEFAULT_MESSAGE, language)
    update.message.reply_text(message_text)
