import os
import re

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.telegram_bot import add_handler
from utils import delete_file, generate_bitrate_selector_keyboard, generate_start_over_keyboard, logger, \
    reset_user_data_context, translate_key_to


def change_bitrate(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    message = update.message

    lang = user_data['language']
    music_path = user_data['music_path']
    music_path_bitrate = f"{music_path}_bitrate.mp3"
    bitrate_output = parse_bitrate_number(message.text)

    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])

        update.message.reply_text(message_text)
    else:
        os.system(
            f"ffmpeg -v debug -i \"{music_path}\" -c:a libmp3lame \
                    -b:a {bitrate_output}k -ac 2 -ar 44100 -vn \"{music_path_bitrate}\""
        )

        start_over_button_keyboard = generate_start_over_keyboard(lang)

        try:
            with open(music_path_bitrate, 'rb') as music_file:
                context.bot.send_audio(
                    audio=music_file,
                    chat_id=update.message.chat_id,
                    caption=f"🆔 {BOT_USERNAME}",
                    reply_markup=start_over_button_keyboard,
                    reply_to_message_id=user_data['music_message_id']
                )
        except (TelegramError, BaseException) as error:
            message.reply_text(
                translate_key_to(lp.ERR_ON_UPLOADING, lang),
                reply_markup=start_over_button_keyboard
            )
            logger.exception("Telegram error: %s", error)

        delete_file(music_path_bitrate)

        reset_user_data_context(context)


def parse_bitrate_number(input_string: str) -> int | None:
    pattern = r'^\d+'

    matches = re.findall(pattern, input_string)

    if matches:
        return int(matches[0])
    else:
        return None


def handle_music_bitrate_changer(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'bitrate_changer'
    lang = user_data['language']

    bitrate_selector_keyboard = generate_bitrate_selector_keyboard(lang)

    update.message.reply_text(
        f"{translate_key_to(lp.BITRATE_CHANGER_HELP, lang)}\n",
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
            handle_music_bitrate_changer)
        )
