from telegram import ReplyKeyboardMarkup
from ..i18n.translate_key_to import translate_key_to


def generate_module_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create and return an instance of `module_selector_keyboard`


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