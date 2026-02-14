import os
import subprocess
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import CallbackContext, filters, MessageHandler

from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import delete_file, generate_start_over_keyboard, get_chat_id, get_effective_user_id, get_message, \
    get_user_data, get_user_language_or_fallback, logger, reset_user_data_context, set_current_module, t, get_file_name


def convert_to_voice(input_path: str, output_path: str) -> None:
    """
    Creates a new file with `opus` format using `libopus` plugin. The new file can be recognized as a voice message by
    Telegram.

    :param input_path: str: The path of the input file
    :param output_path: str: The output path of the converted file
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-map", "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata", "-1",
            "-ac", "1",
            "-c:a", "libopus",
            "-b:a", "32k",
            "-vbr", "on",
            "-compression_level", "10",
            "-frame_duration", "60",
            "-application", "voip",
            output_path,
        ],
        check=True,
    )


async def send_file_as_voice(update: Update, context: CallbackContext) -> None:
    """
    Handles the voice conversion functionality. This is the main function of the ``voice_converter`` module that
    generates a voice message out of the current file and sends it to the user.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    :raises TelegramError | BaseException
    """
    message = get_message(update)
    user_data = get_user_data(context)

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.RECORD_VOICE
    )

    input_path = user_data['music_path']
    output_path = f"{input_path}.opus"

    convert_to_voice(input_path, output_path)

    language = get_user_language_or_fallback(user_data)
    set_current_module(user_data, Module.VOICE_CONVERTER)

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.UPLOAD_VOICE
    )

    start_over_button_keyboard = generate_start_over_keyboard(language)

    music_tags = user_data['tag_editor']

    try:
        with open(output_path, 'rb') as voice_file:
            await context.bot.send_voice(
                voice=voice_file,
                filename=f"{get_file_name(music_tags)}.opus",
                chat_id=get_chat_id(update),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except TelegramError as error:
        await message.reply_text(
            text=t(language, 'errOnUploading'),
            reply_markup=start_over_button_keyboard
        )

        logger.exception("Telegram error: %s", error)

    delete_file(output_path)

    reset_user_data_context(get_effective_user_id(update), user_data)


class VoiceConverterModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``VoiceConverter`` module, so that they can be used to respond
        to messages sent to the bot.
        """
        add_handler(MessageHandler(
            (
                    filters.Regex('^(🗣 Music to Voice Converter)$') |
                    filters.Regex('^(🗣 تبدیل موزیک به ویس)$') |
                    filters.Regex('^(🗣 Конвертер музыки в голос)$') |
                    filters.Regex('^(🗣 Convertidor de Música a Voz)$') |
                    filters.Regex('^(🗣 Convertisseur Musique en Voix)$') |
                    filters.Regex('^(🗣 تحويل الموسيقى إلى صوت)$')
            ),
            send_file_as_voice)
        )
