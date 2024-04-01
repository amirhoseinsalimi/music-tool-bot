import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, filters, MessageHandler

import utils.i18n as lp
from config.telegram_bot import add_handler
from utils import generate_donation_keyboard, get_message_text, get_user_data, get_user_language_or_fallback, t


async def show_donation_methods(update: Update, context: CallbackContext) -> None:
    """
    Displays a keyboard with all available donation methods and sends it to the user.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)

    lang = get_user_language_or_fallback(user_data)
    donation_keyboard = generate_donation_keyboard()

    await update.message.reply_text(
        f"{t(lp.DONATION_MESSAGE, lang)}\n",
        reply_markup=donation_keyboard
    )


async def show_addresses(update: Update, context: CallbackContext) -> None:
    """
    Displays the corresponding addresses of the selected donation methods.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    message_text = get_message_text(update)

    reply_text = None

    if re.match(r'^Bitcoin \(BTC\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_BITCOIN, lang)}"

    elif re.match(r'^Ethereum \(ETH\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_ETHEREUM, lang)}"

    elif re.match(r'^TRON \(TRX\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_TRON, lang)}"

    elif re.match(r'^Tether \(USDT\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_TETHER, lang)}"

    elif re.match(r'^Shiba \(SHIB\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_SHIBA, lang)}"

    elif re.match(r'^Dogecoin \(DOGE\)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_DOGECOIN, lang)}"

    elif re.match(r'^(ZarinPal)$', message_text):
        reply_text = f"{t(lp.DONATE_MESSAGE_ZARINPAL, lang)}"

    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())


class DonationModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Donation`` module, so that they can be used to respond to
        messages sent to the bot.
        """
        add_handler(CommandHandler('donate', show_donation_methods))

        add_handler(MessageHandler(
            (
                    filters.Regex(r'^(Bitcoin \(BTC\))$') | filters.Regex(r'^(Ethereum \(ETH\))$') |
                    filters.Regex(r'^(TRON \(TRX\))$') | filters.Regex(r'^(Tether \(USDT\))$') |
                    filters.Regex(r'^(Shiba \(SHIB\))$') | filters.Regex(r'^(Dogecoin \(DOGE\))$') |
                    filters.Regex(r'^(ZarinPal)$') | filters.Regex(r'^(زرین پال)$')),
            show_addresses)
        )
