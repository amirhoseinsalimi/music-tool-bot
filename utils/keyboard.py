from telegram import ReplyKeyboardMarkup

from .i18n import translate_key_to


def generate_back_button_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create and return an instance of `back_button_keyboard`


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
