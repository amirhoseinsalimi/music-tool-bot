import os
import re
from persiantools import digits
from telegram import Message, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, filters, MessageHandler
from telegram.ext._utils.types import UD
from telegram.helpers import escape_markdown

from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from modules.tag_editor import save_tags_to_file
from utils import convert_seconds_to_human_readable_form, delete_file, generate_back_button_keyboard, \
    generate_start_over_keyboard, get_chat_id, get_effective_user_id, get_message, get_message_text, get_user_data, \
    get_user_language_or_fallback, logger, reset_user_data_context, set_current_module, t, reply_default_message, \
    resize_image, get_file_name


def convert_time_to_seconds(time: str) -> int:
    """
    Convert a string of the form 'mm:ss' to seconds.

    :param time: str: The string in form of 'mm:ss'
    :return: int: The number of seconds
    """
    return int(time.partition(':')[0].lstrip('0') if
               time.partition(':')[0].lstrip('0') else 0) * 60 \
        + int(time.partition(':')[2].lstrip('0') if
              time.partition(':')[2].lstrip('0') else 0)


def is_out_of_range(music_duration: int, beginning_sec: int, end_sec: int) -> bool:
    """
    Checks if a duration range of a music file is invalid. It returns `True` if either one is out of range, otherwise it
    returns `False`.

    :param music_duration: int: Total duration of the file
    :param beginning_sec: int: Beginning of the range
    :param end_sec: int: End of the range
    :return: bool: Whether if the beginning or ending seconds are out of range
    """
    if beginning_sec < 0:
        return True

    return beginning_sec > music_duration or end_sec > music_duration


def is_range_malformed(beginning_sec: int, end_sec: int) -> bool:
    """
    Checks if a range is malformed, end is before start.

    :param beginning_sec: int: Beginning of the range
    :param end_sec: int: End of the range
    :return: bool: Whether the range is malformed
    """
    return beginning_sec >= end_sec


def is_current_module_music_cutter(current_module: str) -> bool:
    """
    Checks if the current module is "music_cutter".

    :param current_module: str: Current module name stored in user's ``user_data``
    :return: bool: Whether the current module is "music_cutter"
    """
    return current_module == 'music_cutter'


def parse_cutting_range(text: str) -> (int, int):
    """
    Parse a cutting range which is in the form of "start - end" or "start_m:start_s - end_m:end_s". The first integer
    is the beginning of the range, and the second integer is the end of it.

    :param text: str: The string to get
    :raises ValueError: Malformed music range
    :return: (int, int): A tuple containing the beginning and the end of the range
    """
    text = re.sub(' ', '', text)

    if '-' not in text:
        raise ValueError('Malformed music range')

    beginning, _, ending = text.partition('-')

    if ':' in text:
        beginning_sec = convert_time_to_seconds(beginning)
        ending_sec = convert_time_to_seconds(ending)
    else:
        beginning_sec = int(beginning)
        ending_sec = int(ending)

    return beginning_sec, ending_sec


async def send_out_of_range_message(message: Message, user_data: UD) -> None:
    """
    Send a message to the user informing them that their input is out of range. It also sends a help message and the
    back button keyboard.

    :param message: Message: The ``message`` object
    :param user_data: UD: The ``user_data`` object
    """
    language = get_user_language_or_fallback(user_data)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])
    back_button_keyboard = generate_back_button_keyboard(language)

    reply_message = t(language, 'errOutOfRange', length=music_duration)

    await message.reply_text(text=reply_message)

    await message.reply_text(
        text=t(language, 'musicCutterHelp', length=music_duration),
        reply_markup=back_button_keyboard
    )


async def send_beginning_is_greater_message(message: Message, user_data: UD) -> None:
    """
    Send a message to the user informing them that the beginning point they entered is greater than the end point. It
    also sends a help message and the back button keyboard.

    :param message: Message: The ``message`` object
    :param user_data: UD: The ``user_data`` object
    """
    language = get_user_language_or_fallback(user_data)
    back_button_keyboard = generate_back_button_keyboard(language)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])

    reply_message = t(language, 'errBeginningPointIsGreater')

    await message.reply_text(text=reply_message)

    await message.reply_text(
        text=t(language, 'musicCutterHelp', length=music_duration),
        reply_markup=back_button_keyboard
    )


def cut(input_path: str, beginning_sec: int, duration: int, output_path: str) -> None:
    """
    The cut function takes in a path to an audio file, the beginning time of the cut
    in seconds, and the duration of the cut in seconds. It then uses ``ffmpeg`` to create
    a new audio file with only that portion of sound.

    :param input_path: str: The path of the input file
    :param beginning_sec: int: The starting point of the cut
    :param duration: int: Duration of the cut
    :param output_path: str: The path of the output file
    """
    os.system(
        f"ffmpeg -y -ss {beginning_sec} -t {duration} -i {input_path} -acodec copy \
                {output_path}"
    )


async def handle_cutter(update: Update, context: CallbackContext) -> None:
    """
    Handles the cut functionality. When a user enters a cutting range, this function parses it, and acts upon
    accordingly. If the range is valid, the new file with the selected range is sent to the user, otherwise an error
    message is sent.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    message = get_message(update)

    music_path = user_data.get('music_path')
    language = get_user_language_or_fallback(user_data)

    if not music_path:
        await reply_default_message(update, language)

        return

    message_text = digits.ar_to_fa(digits.fa_to_en(get_message_text(update)))
    language = get_user_language_or_fallback(user_data)
    music_duration = user_data['music_duration']
    music_duration_formatted = convert_seconds_to_human_readable_form(music_duration)
    back_button_keyboard = generate_back_button_keyboard(language)

    try:
        beginning_sec, ending_sec = parse_cutting_range(message_text)
    except (ValueError, BaseException):
        reply_message = t(language, 'errMalformedRange',
                          note=t(language, 'musicCutterHelp', length=music_duration_formatted))

        await message.reply_text(text=reply_message, reply_markup=back_button_keyboard)

        return

    if is_out_of_range(music_duration, beginning_sec, ending_sec):
        await send_out_of_range_message(message, user_data)

        return

    if is_range_malformed(beginning_sec, ending_sec):
        await send_beginning_is_greater_message(message, user_data)

        return

    start_over_button_keyboard = generate_start_over_keyboard(language)

    input_path = user_data['music_path']
    output_path = f"{input_path}_cut.mp3"
    diff_sec = ending_sec - beginning_sec

    cut(input_path, beginning_sec, diff_sec, output_path)

    music_tags = user_data['tag_editor']
    art_path = music_tags.get('art_path')
    new_art_path = music_tags.get('new_art_path')

    save_tags_to_file(
        file=output_path,
        tags=music_tags,
        new_art_path=new_art_path
    )

    try:
        possible_art = None

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
                duration=diff_sec,
                performer=music_tags.get('artist'),
                title=music_tags.get('title'),
                filename=get_file_name(music_tags),
                caption=f"{t(language, 'fromTo', fromSecond=convert_seconds_to_human_readable_form(beginning_sec), toSecond=convert_seconds_to_human_readable_form(ending_sec))}\n"
                        f"🆔 {BOT_USERNAME}",
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


async def show_cutter_help(update: Update, context: CallbackContext) -> None:
    """
    Displays the guide on how to use the cutter module, and set the current module to ``Module.CUTTER``.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)

    music_path = user_data.get('music_path')
    language = get_user_language_or_fallback(user_data)

    if not music_path:
        await reply_default_message(update, language)

        return

    back_button_keyboard = generate_back_button_keyboard(language)

    set_current_module(user_data, Module.CUTTER)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])

    message = get_message(update)

    music_duration = escape_markdown(music_duration, version=2)

    await message.reply_text(
        text=f"{t(language, 'musicCutterHelp', length=music_duration)}\n",
        reply_markup=back_button_keyboard
    )


class CutterModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Cutter`` module, so that they can be used to respond to
        messages sent to the bot.
        """
        add_handler(MessageHandler(
            (filters.Regex('^(✂️ Music Cutter)$') | filters.Regex('^(✂️ بریدن آهنگ)$')),
            show_cutter_help)
        )
