from telegram import ReplyKeyboardMarkup
from ..i18n.translate_key_to import translate_key_to


def generate_bitrate_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
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
                    '128 kb/s',
                    '192 kb/s',
                ],
                [

                    '256 kb/s',
                    '320 kb/s',
                ],
                [
                    translate_key_to('BTN_BACK', language)
                ]
            ],
            resize_keyboard=True,
        )
    )