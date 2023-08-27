import os

from telegram import ChatAction, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import delete_file, generate_start_over_keyboard, get_chat_id, get_effective_user_id, get_message, \
    get_user_data, get_user_language_or_fallback, logger, reset_user_data_context, set_current_module, t


def convert_to_voice(input_path: str, output_path: str) -> int:
    return os.system(
        f"ffmpeg -i {input_path} -c:a libopus -b:a 32k -vbr on "
        f"-compression_level 10 -frame_duration 60 -application voip"
        f" {output_path}")


def send_file_as_voice(update: Update, context: CallbackContext) -> None:
    message = get_message(update)
    user_data = get_user_data(context)

    context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.RECORD_AUDIO
    )

    input_path = user_data['music_path']
    output_path = f"{input_path}.opus"

    convert_to_voice(input_path, output_path)

    lang = get_user_language_or_fallback(user_data)
    set_current_module(user_data, Module.VOICE_CONVERTER)

    context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.UPLOAD_AUDIO
    )

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    try:
        with open(output_path, 'rb') as voice_file:
            context.bot.send_voice(
                voice=voice_file,
                filename=output_path,
                duration=user_data['music_duration'],
                chat_id=get_chat_id(update),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except TelegramError as error:
        message.reply_text(
            t(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    delete_file(output_path)

    reset_user_data_context(get_effective_user_id(update), user_data)


class VoiceConverterModule:
    @staticmethod
    def register():
        add_handler(MessageHandler(
            (
                Filters.regex('^(🗣 Music to Voice Converter)$') |
                Filters.regex('^(🗣 تبدیل به پیام صوتی)$')
            ),
            send_file_as_voice)
        )
