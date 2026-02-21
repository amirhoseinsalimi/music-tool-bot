from telegram import ReplyKeyboardMarkup

from config.envs import BTC_WALLET_ADDRESS, DOGE_WALLET_ADDRESS, ETH_WALLET_ADDRESS, SHIBA_BEP20_WALLET_ADDRESS, \
    TRX_WALLET_ADDRESS, USDT_ERC20_WALLET_ADDRESS, USDT_TRC20_WALLET_ADDRESS, ZARIN_LINK_ADDRESS, \
    SHIBA_ERC20_WALLET_ADDRESS


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


def to_matrix_2cols(lst):
    return [lst[i:i + 2] for i in range(0, len(lst), 2)]
