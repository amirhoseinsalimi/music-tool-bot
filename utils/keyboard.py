from telegram import ReplyKeyboardMarkup

from .i18n import t


def generate_start_over_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``start_over_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Start over keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [t('BTN_NEW_FILE', language)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_back_button_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``back_button_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Back button keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [t('BTN_BACK', language)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    )


def generate_module_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``module_selector_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Module selector keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [
                    t('BTN_TAG_AND_ART_EDITOR', language),
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
                    t('BTN_ARTIST', language),
                    t('BTN_TITLE', language),
                    t('BTN_ALBUM', language)
                ],
                [
                    t('BTN_GENRE', language),
                    t('BTN_ALBUM_ART', language),
                    t('BTN_REMOVE_ALBUM_ART', language)
                ],
                [
                    t('BTN_YEAR', language),
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


def generate_bitrate_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Create and returns an instance of ``bitrate_selector_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Bitrate selector keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
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


def generate_donation_keyboard() -> ReplyKeyboardMarkup:
    """
    Creates and returns an instance of ``donation_keyboard``

    :return: ReplyKeyboardMarkup: Donation keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
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
