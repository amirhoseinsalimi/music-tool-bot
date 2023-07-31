from telegram import ReplyKeyboardMarkup
from ..i18n.translate_key_to import translate_key_to


def generate_start_over_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create and return an instance of `start_over_keyboard`


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