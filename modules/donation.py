import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler

import utils.i18n as lp
from config.telegram_bot import add_handler
from utils import generate_donation_keyboard, get_message_text, get_user_data, get_user_language_or_fallback, t


def show_donation_methods(update: Update, context: CallbackContext):
    user_data = get_user_data(context)

    lang = get_user_language_or_fallback(user_data)
    donation_keyboard = generate_donation_keyboard(lang)

    update.message.reply_text(
        f"{t(lp.DONATION_MESSAGE, lang)}\n",
        reply_markup=donation_keyboard
    )


def show_wallet_addresses(update: Update, context: CallbackContext):
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

    update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())


class DonationModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('donate', show_donation_methods))

        add_handler(MessageHandler(
            (
                    Filters.regex(r'^(Bitcoin \(BTC\))$') | Filters.regex(r'^(Ethereum \(ETH\))$') |
                    Filters.regex(r'^(TRON \(TRX\))$') | Filters.regex(r'^(Tether \(USDT\))$') |
                    Filters.regex(r'^(Shiba \(SHIB\))$') | Filters.regex(r'^(Dogecoin \(DOGE\))$') |
                    Filters.regex(r'^(ZarinPal)$') | Filters.regex(r'^(زرین پال)$')
            ),
            show_wallet_addresses)
        )
