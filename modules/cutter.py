import os
import re

from persiantools import digits
from telegram import Message, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler
from telegram.ext.utils.types import UD

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import convert_seconds_to_human_readable_form, delete_file, generate_back_button_keyboard, \
    generate_start_over_keyboard, get_chat_id, get_effective_user_id, get_message, get_message_text, get_user_data, \
    get_user_language_or_fallback, logger, reset_user_data_context, set_current_module, t


def convert_time_to_seconds(time: str) -> int:
    return int(time.partition(':')[0].lstrip('0') if
               time.partition(':')[0].lstrip('0') else 0) * 60 \
        + int(time.partition(':')[2].lstrip('0') if
              time.partition(':')[2].lstrip('0') else 0)


def is_out_of_range(music_duration: int, beginning_sec: int, ending_sec: int):
    if beginning_sec < 0:
        return True

    return beginning_sec > music_duration or ending_sec > music_duration


def is_beginning_sec_after_ending_sec(beginning_sec: int, ending_sec: int):
    return beginning_sec >= ending_sec


def is_current_module_music_cutter(current_module: str):
    return current_module == 'music_cutter'


def parse_cutting_range(text: str) -> (int, int):
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


def send_out_of_range_message(message: Message, user_data: UD):
    lang = get_user_language_or_fallback(user_data)
    music_duration = user_data['music_duration']
    back_button_keyboard = generate_back_button_keyboard(lang)

    reply_message = t(lp.ERR_OUT_OF_RANGE, lang).format(
        convert_seconds_to_human_readable_form(music_duration))
    message.reply_text(reply_message)
    message.reply_text(
        t(lp.MUSIC_CUTTER_HELP, lang),
        reply_markup=back_button_keyboard
    )


def send_beginning_is_greater_message(message: Message, user_data: UD):
    lang = get_user_language_or_fallback(user_data)
    back_button_keyboard = generate_back_button_keyboard(lang)

    reply_message = t(lp.ERR_BEGINNING_POINT_IS_GREATER, lang)

    message.reply_text(reply_message)
    message.reply_text(
        t(lp.MUSIC_CUTTER_HELP, lang),
        reply_markup=back_button_keyboard
    )


def cut(input_path: str, beginning_sec: int, diff_sec: int, output_path: str):
    os.system(
        f"ffmpeg -y -ss {beginning_sec} -t {diff_sec} -i {input_path} -acodec copy \
                {output_path}"
    )


def handle_cutter(update: Update, context: CallbackContext):
    user_data = get_user_data(context)
    message = get_message(update)

    message_text = digits.ar_to_fa(digits.fa_to_en(get_message_text(update)))
    lang = get_user_language_or_fallback(user_data)
    back_button_keyboard = generate_back_button_keyboard(lang)

    try:
        beginning_sec, ending_sec = parse_cutting_range(message_text)
    except (ValueError, BaseException):
        reply_message = t(lp.ERR_MALFORMED_RANGE, lang).format(
            t(lp.MUSIC_CUTTER_HELP, lang),
        )
        message.reply_text(reply_message, reply_markup=back_button_keyboard)

        return

    music_duration = user_data['music_duration']

    if is_out_of_range(music_duration, beginning_sec, ending_sec):
        send_out_of_range_message(message, user_data)

        return

    if is_beginning_sec_after_ending_sec(beginning_sec, ending_sec):
        send_beginning_is_greater_message(message, user_data)

        return

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    input_path = user_data['music_path']
    output_path = f"{input_path}_cut.mp3"
    diff_sec = ending_sec - beginning_sec

    cut(input_path, beginning_sec, diff_sec, output_path)

    try:
        with open(output_path, 'rb') as music_file:
            # FIXME: After sending the file, the album art can't be read back
            context.bot.send_audio(
                audio=music_file,
                chat_id=get_chat_id(update),
                duration=diff_sec,
                caption=f"*From*: {convert_seconds_to_human_readable_form(beginning_sec)}\n"
                        f"*To*: {convert_seconds_to_human_readable_form(ending_sec)}\n\n"
                        f"🆔 {BOT_USERNAME}",
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


def show_cutter_help(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)

    lang = get_user_language_or_fallback(user_data)
    back_button_keyboard = generate_back_button_keyboard(lang)

    set_current_module(user_data, Module.CUTTER)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])

    message = get_message(update)

    # TODO: Send back the length of the music
    message.reply_text(
        f"{t(lp.MUSIC_CUTTER_HELP, lang).format(music_duration)}\n",
        reply_markup=back_button_keyboard
    )


class CutterModule:
    @staticmethod
    def register():
        add_handler(MessageHandler(
            (Filters.regex('^(✂️ Music Cutter)$') | Filters.regex('^(✂️ بریدن آهنگ)$')),
            show_cutter_help)
        )
