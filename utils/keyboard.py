from telegram import ReplyKeyboardMarkup

from config.envs import BTC_WALLET_ADDRESS, DOGE_WALLET_ADDRESS, ETH_WALLET_ADDRESS, SHIBA_BEP20_WALLET_ADDRESS, \
    TRX_WALLET_ADDRESS, USDT_ERC20_WALLET_ADDRESS, USDT_TRC20_WALLET_ADDRESS, ZARIN_LINK_ADDRESS, \
    SHIBA_ERC20_WALLET_ADDRESS
from modules.donation import to_matrix_2cols
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
                [t(language, 'btnNewFile')],
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
                [t(language, 'btnBack')],
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
                    t(language, 'btnTagAndArtEditor'),
                    t(language, 'btnMusicToVoiceConverter')
                ],
                [
                    t(language, 'btnMusicCutter'),
                    t(language, 'btnBitrateChanger')
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
                    t(language, 'btnBack')
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
    donation_methods = []

    if BTC_WALLET_ADDRESS: donation_methods.append("Bitcoin")
    if ETH_WALLET_ADDRESS: donation_methods.append("Ethereum")
    if TRX_WALLET_ADDRESS: donation_methods.append("TRON")
    if USDT_TRC20_WALLET_ADDRESS or USDT_ERC20_WALLET_ADDRESS: donation_methods.append("Tether")
    if SHIBA_BEP20_WALLET_ADDRESS or SHIBA_ERC20_WALLET_ADDRESS: donation_methods.append("Shiba")
    if DOGE_WALLET_ADDRESS: donation_methods.append("Dogecoin")
    if ZARIN_LINK_ADDRESS: donation_methods.append("ZarinPal")

    return (
        ReplyKeyboardMarkup(
            keyboard=to_matrix_2cols(donation_methods),
            resize_keyboard=True,
        )
    )
