import re

from telegram import (
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
)

from config.envs import (
    BTC_WALLET_ADDRESS,
    DOGE_WALLET_ADDRESS,
    ETH_WALLET_ADDRESS,
    SHIBA_BEP20_WALLET_ADDRESS,
    TRX_WALLET_ADDRESS,
    USDT_ERC20_WALLET_ADDRESS,
    USDT_TRC20_WALLET_ADDRESS,
    ZARIN_LINK_ADDRESS,
    SHIBA_ERC20_WALLET_ADDRESS,
)
from utils import (
    get_message_text,
    get_user_data,
    get_user_language_or_fallback,
    t,
    upsert_user,
)
from .utils import (
    generate_donation_keyboard,
)


@upsert_user
async def show_donation_methods(update: Update, context: CallbackContext) -> None:
    """
    Displays a keyboard with all available donation methods and sends it to the user.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)

    language = get_user_language_or_fallback(user_data)
    donation_keyboard = generate_donation_keyboard()

    await update.message.reply_text(
        text=f"{t(language, 'donationMessage')}\n",
        reply_markup=donation_keyboard
    )


@upsert_user
async def show_addresses(update: Update, context: CallbackContext) -> None:
    """
    Displays the corresponding addresses of the selected donation methods.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    message_text = get_message_text(update)

    reply_text = None

    if re.match(r'^Bitcoin$', message_text):
        reply_text = f"{t(language, 'donateMessageBitcoin', btc_wallet_address=BTC_WALLET_ADDRESS)}"

    elif re.match(r'^Ethereum$', message_text):
        reply_text = f"{t(language, 'donateMessageEthereum', eth_wallet_address=ETH_WALLET_ADDRESS)}"

    elif re.match(r'^TRON$', message_text):
        reply_text = f"{t(language, 'donateMessageTron', trx_wallet_address=TRX_WALLET_ADDRESS)}"

    elif re.match(r'^Tether$', message_text):
        reply_text = f"""{t(language, 'donateMessageTether',
                            usdt_trc20_wallet_address=USDT_TRC20_WALLET_ADDRESS,
                            usdt_erc20_wallet_address=USDT_ERC20_WALLET_ADDRESS)}"""

    elif re.match(r'^Shiba$', message_text):
        reply_text = f"""{t(language, 'donateMessageShiba',
                            shiba_bep20_wallet_address=SHIBA_BEP20_WALLET_ADDRESS,
                            shiba_erc20_wallet_address=SHIBA_ERC20_WALLET_ADDRESS)}"""

    elif re.match(r'^Dogecoin$', message_text):
        reply_text = f"{t(language, 'donateMessageDogeCoin', doge_wallet_address=DOGE_WALLET_ADDRESS)}"

    elif re.match(r'^ZarinPal$', message_text):
        reply_text = f"{t(language, 'donateMessageZarinPal', zarin_link_address=ZARIN_LINK_ADDRESS)}"

    await update.message.reply_text(text=reply_text, reply_markup=ReplyKeyboardRemove())
