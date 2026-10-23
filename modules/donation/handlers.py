import re

from telegram import (
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
)

from utils import (
    get_message_text,
    get_user_data,
    get_user_language_or_fallback,
    t,
    upsert_user,
)
from utils.logging import get_logger
from .utils import (
    donation_destinations,
    generate_donation_keyboard,
)

logger = get_logger(__name__)


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
    logger.info("User %s opened donation methods", context.user_data['user'].user_id)

    if donation_keyboard is None:
        logger.warning("No donation methods are configured")
        await update.message.reply_text(t(language, 'donationUnavailable'))
        return

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
    addresses = donation_destinations()
    keyboard = generate_donation_keyboard()
    available = {button.text for row in keyboard.keyboard for button in row} if keyboard else set()
    if message_text not in available:
        await update.message.reply_text(
            text=t(language, 'donationUnavailable'),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    reply_text = None

    if re.match(r'^Bitcoin$', message_text):
        logger.info("User %s selected donation method Bitcoin", context.user_data['user'].user_id)
        reply_text = f"{t(language, 'donateMessageBitcoin', btc_wallet_address=addresses['BTC_WALLET_ADDRESS'])}"

    elif re.match(r'^Ethereum$', message_text):
        logger.info("User %s selected donation method Ethereum", context.user_data['user'].user_id)
        reply_text = f"{t(language, 'donateMessageEthereum', eth_wallet_address=addresses['ETH_WALLET_ADDRESS'])}"

    elif re.match(r'^TRON$', message_text):
        logger.info("User %s selected donation method TRON", context.user_data['user'].user_id)
        reply_text = f"{t(language, 'donateMessageTron', trx_wallet_address=addresses['TRX_WALLET_ADDRESS'])}"

    elif re.match(r'^Tether$', message_text):
        logger.info("User %s selected donation method Tether", context.user_data['user'].user_id)
        reply_text = f"""{t(language, 'donateMessageTether',
                            usdt_trc20_wallet_address=addresses['USDT_TRC20_WALLET_ADDRESS'],
                            usdt_erc20_wallet_address=addresses['USDT_ERC20_WALLET_ADDRESS'])}"""

    elif re.match(r'^Shiba$', message_text):
        logger.info("User %s selected donation method Shiba", context.user_data['user'].user_id)
        reply_text = f"""{t(language, 'donateMessageShiba',
                            shiba_bep20_wallet_address=addresses['SHIBA_BEP20_WALLET_ADDRESS'],
                            shiba_erc20_wallet_address=addresses['SHIBA_ERC20_WALLET_ADDRESS'])}"""

    elif re.match(r'^Dogecoin$', message_text):
        logger.info("User %s selected donation method Dogecoin", context.user_data['user'].user_id)
        reply_text = f"{t(language, 'donateMessageDogeCoin', doge_wallet_address=addresses['DOGE_WALLET_ADDRESS'])}"

    elif re.match(r'^ZarinPal$', message_text):
        logger.info("User %s selected donation method ZarinPal", context.user_data['user'].user_id)
        reply_text = f"{t(language, 'donateMessageZarinPal', zarin_link_address=addresses['ZARIN_LINK_ADDRESS'])}"

    await update.message.reply_text(text=reply_text, reply_markup=ReplyKeyboardRemove())
