import re
import subprocess
from pathlib import Path

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, filters, MessageHandler

from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import delete_file, generate_bitrate_selector_keyboard, generate_start_over_keyboard, get_chat_id, \
    get_effective_user_id, get_message, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, \
    reply_default_message, reset_user_data_context, set_current_module, t, resize_image, get_file_name


def parse_bitrate_number(message: str) -> int | None:
    """
    Parses, converts and returns a bitrate in a text.

    The ``message`` is expected to look like `320 kb/s`.

    :param message: str: A message text containing a bitrate
    :return: int | None: The extracted bitrate
    """
    number_pattern = r'^\d+'

    matches = re.findall(number_pattern, message)

    if matches:
        return int(matches[0])
    else:
        return None


def convert_bitrate(input_path: str, output_bitrate: int, output_path: str) -> None:
    """
    Re-encodes audio to the given bitrate while preserving metadata and album art.

    Notes:
    - This keeps tags (`-map_metadata 0`) and attempts to keep embedded cover art by mapping streams.
    - If the input contains multiple audio streams, this keeps the first audio stream.
    - If output is MP3, album art is stored as an attached picture (ID3 APIC) when supported by ffmpeg.

    :param input_path: Path to input audio file
    :param output_bitrate: Target audio bitrate (kbps)
    :param output_path: Path to output audio file
    """
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(in_path),

        "-map", "0:a:0",
        "-map", "0:v?",

        "-map_metadata", "0",

        "-c:a", "libmp3lame",
        "-b:a", f"{output_bitrate}k",
        "-ac", "2",
        "-ar", "44100",

        "-c:v", "copy",

        "-disposition:v:0", "attached_pic",

        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed.\n"
            f"Command: {' '.join(cmd)}\n\n"
            f"STDERR:\n{result.stderr}"
        )


async def show_bitrate_changer_keyboard(update: Update, context: CallbackContext) -> None:
    """
    sets the current module to `Module.BITRATE_CHANGER`, and displays a keyboard with buttons for each bitrate option.

    :param update: Update: The `update` object
    :param context: CallbackContext: The `context` object
    """
    user_data = get_user_data(context)

    language = get_user_language_or_fallback(user_data)
    bitrate_selector_keyboard = generate_bitrate_selector_keyboard(language)

    set_current_module(user_data, Module.BITRATE_CHANGER)

    await update.message.reply_text(
        text=f"{t(language, 'bitrateChangerHelp')}\n",
        reply_markup=bitrate_selector_keyboard
    )


async def change_bitrate(update: Update, context: CallbackContext) -> None:
    """
    Handles the change bitrate functionality.

    This is the main function of the ``bitrate_changer`` module that accepts the desired bitrate, generates a new file,
    and sends it to the user. It sends a default message if user has not started the bot.

    :param update: Update: The ``update`` object
    :param context: Update: The ``context`` object
    :raises TelegramError | BaseException
    """
    user_data = get_user_data(context)
    message = get_message(update)
    language = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, language)

        return

    start_over_button_keyboard = generate_start_over_keyboard(language)

    input_path = user_data['music_path']
    output_path = f"{input_path}_bitrate.mp3"
    output_bitrate = parse_bitrate_number(message.text)
    music_duration = user_data['music_duration']
    music_tags = user_data['tag_editor']
    possible_art = art_path = music_tags.get('art_path')

    try:
        convert_bitrate(input_path, output_bitrate, output_path)

        if art_path:
            original_art_path = art_path
            resized_art_path = f"{original_art_path}_resized.jpg"

            resize_image(original_art_path, resized_art_path)

            with open(resized_art_path, "rb") as art:
                possible_art = art.read()

        with open(output_path, 'rb') as music_file:
            await context.bot.send_audio(
                audio=music_file,
                chat_id=get_chat_id(update),
                thumbnail=possible_art,
                duration=music_duration,
                performer=music_tags.get('artist'),
                title=music_tags.get('title'),
                filename=get_file_name(music_tags),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except (TelegramError, BaseException) as error:
        await message.reply_text(
            text=t(language, 'errOnUploading'),
            reply_markup=start_over_button_keyboard
        )

        logger.exception("Telegram error: %s", error)

    delete_file(output_path)

    reset_user_data_context(get_effective_user_id(update), user_data)


class BitrateChangerModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``BitrateChanger`` module, so that they can be used to respond to
        messages sent to the bot.
        """
        add_handler(MessageHandler(
            filters.Regex(r'^(\d{3}\s{1}kb/s)$'),
            change_bitrate)
        )

        add_handler(MessageHandler(
            (filters.Regex('^(🎙 Bitrate Changer)$') |
             filters.Regex('^(🎙 تغییر بیت‌ریت)$') |
             filters.Regex('^(🎙 Изменение битрейта)$') |
             filters.Regex('^(🎙 Cambiador de Bitrate)$') |
             filters.Regex('^(🎙 Modificateur de Bitrate)$') |
             filters.Regex('^(🎙 تغيير معدل البت)$')),
            show_bitrate_changer_keyboard)
        )

