import os

from telegram import ChatAction, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.telegram_bot import add_handler
from utils import delete_file, generate_start_over_keyboard, logger, reset_user_data_context, translate_key_to


def handle_music_to_voice_converter(update: Update, context: CallbackContext) -> None:
    message = update.message
    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.RECORD_AUDIO
    )

    user_data = context.user_data
    input_music_path = user_data['music_path']
    voice_path = f"{user_data['music_path']}.ogg"
    lang = user_data['language']
    user_data['current_active_module'] = 'mp3_to_voice_converter'  # TODO: Make modules a dict

    os.system(
        f"ffmpeg -i -y {input_music_path} -ac 1 -map 0:a -codec:a opus -b:a 128k -vbr off \
         {input_music_path}"
    )
    os.system(f"ffmpeg -i {input_music_path} -c:a libvorbis -q:a 4 {voice_path}")

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    try:
        with open(voice_path, 'rb') as voice_file:
            context.bot.send_voice(
                voice=voice_file,
                duration=user_data['music_duration'],
                chat_id=message.chat_id,
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except TelegramError as error:
        message.reply_text(
            translate_key_to(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    delete_file(voice_path)

    reset_user_data_context(context)


class VoiceConverterModule:
    @staticmethod
    def register():
        add_handler(MessageHandler(
            (
                    Filters.regex('^(🗣 Music to Voice Converter)$')
                    | Filters.regex('^(🗣 تبدیل به پیام صوتی)$')
            ),
            handle_music_to_voice_converter)
        )
