from telegram import (
    ReplyKeyboardMarkup,
)

from config import envs
from utils import t

SUPPORTED_LANGUAGES = ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id')
DONATION_METHOD_KEYS = (
    'donationMethodBitcoin', 'donationMethodEthereum', 'donationMethodTron',
    'donationMethodTether', 'donationMethodShiba', 'donationMethodDogecoin',
    'donationMethodZarinPal',
)

ADDRESS_NAMES = (
    "BTC_WALLET_ADDRESS", "ETH_WALLET_ADDRESS", "TRX_WALLET_ADDRESS",
    "USDT_TRC20_WALLET_ADDRESS", "USDT_ERC20_WALLET_ADDRESS",
    "SHIBA_BEP20_WALLET_ADDRESS", "SHIBA_ERC20_WALLET_ADDRESS",
    "DOGE_WALLET_ADDRESS", "ZARIN_LINK_ADDRESS",
)


def donation_destinations() -> dict[str, str]:
    """Use environment configuration, then optional private receiving defaults."""
    try:
        from premium.donation_defaults import DONATION_ADDRESSES
    except ImportError:
        DONATION_ADDRESSES = {}
    return {name: getattr(envs, name, "") or DONATION_ADDRESSES.get(name, "")
            for name in ADDRESS_NAMES}


def all_donation_method_labels() -> list[str]:
    """Return every localized label accepted by the donation handler."""
    return [t(language, key) for language in SUPPORTED_LANGUAGES for key in DONATION_METHOD_KEYS]


def generate_donation_keyboard(language: str = 'en') -> ReplyKeyboardMarkup | None:
    """
    Creates and returns an instance of ``donation_keyboard``

    :return: ReplyKeyboardMarkup: Donation keyboard
    """
    addresses = donation_destinations()
    donation_methods = []

    if addresses["BTC_WALLET_ADDRESS"]: donation_methods.append(t(language, 'donationMethodBitcoin'))
    if addresses["ETH_WALLET_ADDRESS"]: donation_methods.append(t(language, 'donationMethodEthereum'))
    if addresses["TRX_WALLET_ADDRESS"]: donation_methods.append(t(language, 'donationMethodTron'))
    if addresses["USDT_TRC20_WALLET_ADDRESS"] or addresses["USDT_ERC20_WALLET_ADDRESS"]:
        donation_methods.append(t(language, 'donationMethodTether'))
    if addresses["SHIBA_BEP20_WALLET_ADDRESS"] or addresses["SHIBA_ERC20_WALLET_ADDRESS"]:
        donation_methods.append(t(language, 'donationMethodShiba'))
    if addresses["DOGE_WALLET_ADDRESS"]: donation_methods.append(t(language, 'donationMethodDogecoin'))
    if addresses["ZARIN_LINK_ADDRESS"]: donation_methods.append(t(language, 'donationMethodZarinPal'))

    if not donation_methods:
        return None

    return (
        ReplyKeyboardMarkup(
            keyboard=to_matrix_2cols(donation_methods),
            resize_keyboard=True,
            is_persistent=True,
        )
    )


def to_matrix_2cols(lst):
    return [lst[i:i + 2] for i in range(0, len(lst), 2)]
