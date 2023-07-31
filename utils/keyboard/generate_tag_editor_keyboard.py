from telegram import ReplyKeyboardMarkup
from ..i18n.translate_key_to import translate_key_to


def generate_tag_editor_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create and return an instance of `tag_editor_keyboard`


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