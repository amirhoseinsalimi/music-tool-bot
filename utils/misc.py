from PIL import Image
from telegram import Message, Update
from telegram.ext import CallbackContext
from telegram.ext._utils.types import UD

from config.modules import Module
from utils.fs import delete_all_user_files
from .i18n import t


def get_effective_user_id(update: Update) -> int:
    """
    Get the ``user_id`` of an update.

    :param update: Update: The ``update`` object
    :return: int: The `user_id` of the user who triggered the update
    """
    return update.effective_user.id


def get_effective_user_username(update: Update) -> str | None:
    """
    Get the ``username`` of an ``update``. If no `username` is available, it returns None.

    :param update: Update: The ``update`` object
    :return: str | None: The ``username`` of the user who triggered the update
    """
    return update.effective_user.username


def get_chat_id(update: Update) -> int:
    """
    Get the ``chat_id`` of an update.

    :param update: Update: The ``update`` object
    :return: int: The ``chat_id`` of which the update has been triggered in
    """
    return update.effective_message.chat_id


def get_message(update: Update) -> Message | None:
    """
    Get the ``message`` object of an update.

    :param update: Update: The ``update`` object
    :return: Message | None: The possible ``message`` object of which the update has been triggered from
    """
    return update.message


def get_effective_message_id(update: Update) -> int | None:
    """
    Get the ``message_id`` object of an update.

    :param update: Update: The ``update`` object
    :return: int | None: The possible ``message_id`` of which the update has been triggered from
    """
    if not update.effective_message:
        return

    return update.effective_message.message_id


def get_message_text(update: Update) -> str | None:
    """
    Get the text object of an update of type ``Message``.

    :param update: Update: The ``update`` object
    :return: int | None: The possible text message of which the update has been triggered from
    """
    if not update.message:
        return

    return update.message.text


def get_user_data(context: CallbackContext) -> UD | None:
    """
    Get the `user_data` object. Can be ``None``.

    :param context: CallbackContext: The ``context`` object
    :return: UD | None: The possible ``user_data``
    """
    return context.user_data


def is_user_data_empty(user_data: UD) -> bool:
    """
    Checks if a user's ``user_data`` is empty.

    Can be used to determine if a user has started the bot or not. It does so by evaluating the length of ``user_data``
    of the user.

    :param user_data: UD: The ``user_data`` object of the user that we want to check its emptiness
    :return: bool: Whether the user has data
    """
    return len(user_data) == 1


def get_user_language_or_fallback(user_data: UD) -> str:
    """
    Get the user's language if it is present in the `user_data` dictionary, otherwise it returns "en" (English) as
    the fallback.

    :param user_data: UD: The ``user_data`` object
    :return: str: The language of the user or the fallback
    """
    return user_data['language'] if 'language' in user_data else 'en'


def set_current_module(user_data: UD, module: Module) -> None:
    """
    Sets the current module for a user in their session.

    :param user_data: UD: The ``user_data`` object
    :param module: Module: The module to be set
    """
    user_data['current_module'] = module.value


def unset_current_module(user_data: UD) -> None:
    """
    Unsets the user's ``current_module`` by setting it to an empty string.

    :param user_data: UD: The ``user_data`` object
    """
    user_data['current_module'] = ''


def reset_user_data_context(user_id: int, user_data: UD) -> None:
    """
    Resets the user data session. It deletes all files that were created by the bot for this user, and resets all
    values in the ``user_data`` dictionary. The language value is not reset, as it should be kept between sessions.

    :param user_id: int: The user's ``user_id``
    :param user_data: UD: The ``user_data`` object
    """
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


async def reply_default_message(update: Update, language: str) -> None:
    """
    Reply the default message.

    :param update: Update: The ``update`` object
    :param language: str: The language of the message
    """
    message_text = t(language, 'defaultMessage')

    await update.message.reply_text(text=message_text)


def resize_image(image_path: str, output_path: str, size=(640, 640)):
    """
    Resize an image to a specific size.

    :param image_path: The path of the input image
    :param output_path: The path for the output image
    :param size (Optional): The size in which the output should be
    """
    with Image.open(image_path) as img:
        img = img.resize(size, Image.Resampling.LANCZOS)
        img.save(output_path, format="JPEG")


def get_file_name(music_tags: dict):
    """
    Return a formatted filename based on audio tags with fallbacks

    :param music_tags: dict: The dictionary containing the music tags
    :return: str: A formatted filename based on audio tags with fallbacks
    """
    return f"{music_tags.get('artist') or 'Unknown'} - {music_tags.get('title') or 'Unknown'}"
