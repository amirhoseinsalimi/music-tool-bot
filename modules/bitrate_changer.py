import os
import re

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import delete_file, generate_bitrate_selector_keyboard, generate_start_over_keyboard, get_chat_id, \
    get_effective_user_id, get_message, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, \
    reply_default_message, reset_user_data_context, set_current_module, t


def parse_bitrate_number(input_string: str) -> int | None:
    number_pattern = r'^\d+'

    matches = re.findall(number_pattern, input_string)

    if matches:
        return int(matches[0])
    else:
        return None


def convert_bitrate(input_path: str, output_bitrate: int, output_path: str):
    os.system(
        f"ffmpeg -v debug -i \"{input_path}\" -c:a libmp3lame \
                            -b:a {output_bitrate}k -ac 2 -ar 44100 -vn \"{output_path}\""
    )


def change_bitrate(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    message = get_message(update)
    lang = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        reply_default_message(update, lang)

        return

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    input_path = user_data['music_path']
    output_path = f"{input_path}_bitrate.mp3"
    output_bitrate = parse_bitrate_number(message.text)

    try:
        convert_bitrate(input_path, output_bitrate, output_path)

        with open(output_path, 'rb') as music_file:
            context.bot.send_audio(
                audio=music_file,
                chat_id=get_chat_id(update),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )

    except (TelegramError, BaseException) as error:
        message.reply_text(
            t(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )

        logger.exception("Telegram error: %s", error)

    delete_file(output_path)

    reset_user_data_context(get_effective_user_id(update), user_data)


def show_bitrate_changer_keyboard(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)

    lang = get_user_language_or_fallback(user_data)
    bitrate_selector_keyboard = generate_bitrate_selector_keyboard(lang)

    set_current_module(user_data, Module.BITRATE_CHANGER)

    update.message.reply_text(
        f"{t(lp.BITRATE_CHANGER_HELP, lang)}\n",
        reply_markup=bitrate_selector_keyboard
    )


class BitrateChangerModule:
    @staticmethod
    def register():
        add_handler(MessageHandler(
            Filters.regex(r'^(\d{3}\s{1}kb/s)$'),
            change_bitrate)
        )

        add_handler(MessageHandler(
            (Filters.regex('^(🎙 Bitrate Changer)$') | Filters.regex('^(🎙 تغییر بیت ریت)$')),
            show_bitrate_changer_keyboard)
        )
