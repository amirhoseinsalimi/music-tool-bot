import re

from telegram import Message
from telegram.ext._utils.types import UD

from utils import get_user_language_or_fallback, generate_back_button_keyboard, \
    convert_seconds_to_human_readable_form, t


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
