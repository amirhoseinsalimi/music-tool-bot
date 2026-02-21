from telegram import ReplyKeyboardMarkup
from telegram.ext._utils.types import UD

from utils import t


def generate_tag_editor_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``tag_editor_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Tag editor keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [
                    t(language, 'btnArtist'),
                    t(language, 'btnTitle'),
                    t(language, 'btnAlbum')
                ],
                [
                    t(language, 'btnGenre'),
                    t(language, 'btnAlbumArt'),
                    t(language, 'btnRemoveAlbumArt')
                ],
                [
                    t(language, 'btnYear'),
                    t(language, 'btnDiskNumber'),
                    t(language, 'btnTrackNumber')
                ],
                [
                    t(language, 'btnBack')
                ]
            ],
            resize_keyboard=True,
        )
    )


def is_current_module_tag_editor(current_module: str) -> bool:
    """
    Checks if the current module is "tag_editor".

    :param current_module: str: Current module name stored in user's ``user_data``
    :return: bool: Whether the current module is "tag_editor"
    """
    return current_module == 'tag_editor'


def did_user_select_a_tag(current_tag: str) -> bool:
    """
    Checks if a user has selected a tag.

    :param current_tag: str: The current tag stored in user's ``user_data``
    :return: bool: Whether if a user has selected a tag
    """
    return bool(current_tag)


def is_current_tag_album_art(current_tag: str) -> bool:
    """
    Checks if the current tag is "album_art".

    :param current_tag: str: The current tag stored in user's ``user_data``
    :return: bool: Whether if a user's current tag is "album_art"
    """
    return current_tag == 'album_art'


def unset_current_tag(user_data: UD) -> None:
    """
    Sets the current tag to an empty string so the user has to select a tag again.

    :param user_data: UD: The ``user_data`` object
    """
    user_data['tag_editor']['current_tag'] = ''


def save_text_into_tag(
        value: str,
        current_tag: str,
        user_data: UD,
        is_number: bool = False
) -> None:
    """
    Sets a value in the user's ``user_data`` as their current tag. Sets it to `0` if the value should be ``int`` but
    it's not.

    :param value: str: The value to set as current tag
    :param current_tag: str: The current tag stored in user's ``user_data``
    :param user_data: UD: The ``user_data`` object
    :param is_number: bool: Whether the value should be treated as an ``int``
    """
    if is_number:
        if value.isdigit():
            user_data['tag_editor'][current_tag] = value
        else:
            user_data['tag_editor'][current_tag] = 0
    else:
        user_data['tag_editor'][current_tag] = value
