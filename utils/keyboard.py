from telegram import ReplyKeyboardMarkup

from .i18n import t


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
                [t('BTN_BACK', language)],
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
                    t('BTN_BACK', language)
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
                    t('BTN_TAG_EDITOR', language),
                    t('BTN_MUSIC_TO_VOICE_CONVERTER', language)
                ],
                [
                    t('BTN_MUSIC_CUTTER', language),
                    t('BTN_BITRATE_CHANGER', language)
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
                [t('BTN_NEW_FILE', language)],
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
                    t('BTN_ARTIST', language),
                    t('BTN_TITLE', language),
                    t('BTN_ALBUM', language)
                ],
                [
                    t('BTN_GENRE', language),
                    t('BTN_YEAR', language),
                    t('BTN_ALBUM_ART', language)
                ],
                [
                    t('BTN_DISK_NUMBER', language),
                    t('BTN_TRACK_NUMBER', language)
                ],
                [
                    t('BTN_BACK', language)
                ]
            ],
            resize_keyboard=True,
        )
    )


def generate_donation_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Create and return an instance of `donation_keyboard`


    **Keyword arguments:**
     - language (str) -- The desired language to generate labels

    **Returns:**
     ReplyKeyboardMarkup instance
    """
    return (
        ReplyKeyboardMarkup(
            [
                [
                    'Bitcoin (BTC)',
                    'Ethereum (ETH)',
                ],
                [
                    'TRON (TRX)',
                    'Tether (USDT)',
                ],
                [
                    'Shiba (SHIB)',
                    'Dogecoin (DOGE)',
                ],
                [
                    'ZarinPal'
                ]
            ],
            resize_keyboard=True,
        )
    )