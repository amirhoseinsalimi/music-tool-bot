from telegram import (
    ReplyKeyboardMarkup,
)

from config import envs

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


def generate_donation_keyboard() -> ReplyKeyboardMarkup | None:
    """
    Creates and returns an instance of ``donation_keyboard``

    :return: ReplyKeyboardMarkup: Donation keyboard
    """
    addresses = donation_destinations()
    donation_methods = []

    if addresses["BTC_WALLET_ADDRESS"]: donation_methods.append("Bitcoin")
    if addresses["ETH_WALLET_ADDRESS"]: donation_methods.append("Ethereum")
    if addresses["TRX_WALLET_ADDRESS"]: donation_methods.append("TRON")
    if addresses["USDT_TRC20_WALLET_ADDRESS"] or addresses["USDT_ERC20_WALLET_ADDRESS"]: donation_methods.append("Tether")
    if addresses["SHIBA_BEP20_WALLET_ADDRESS"] or addresses["SHIBA_ERC20_WALLET_ADDRESS"]: donation_methods.append("Shiba")
    if addresses["DOGE_WALLET_ADDRESS"]: donation_methods.append("Dogecoin")
    if addresses["ZARIN_LINK_ADDRESS"]: donation_methods.append("ZarinPal")

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
