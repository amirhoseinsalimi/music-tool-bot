import os
import re

from persiantools import digits
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.telegram_bot import add_handler
from modules.tag_editor import save_tags_to_file
from utils import convert_seconds_to_human_readable_form, delete_file, generate_back_button_keyboard, \
    generate_start_over_keyboard, logger, reset_user_data_context, translate_key_to


def handle_cutter(update: Update, context: CallbackContext):
    message = update.message
    message_text = digits.ar_to_fa(digits.fa_to_en(message.text))
    user_data = context.user_data
    music_path = user_data['music_path']
    art_path = user_data['art_path']
    music_tags = user_data['tag_editor']
    lang = user_data['language']

    back_button_keyboard = generate_back_button_keyboard(lang)
    start_over_button_keyboard = generate_start_over_keyboard(lang)

    try:
        beginning_sec, ending_sec = parse_cutting_range(message_text)
    except (ValueError, BaseException):
        reply_message = translate_key_to(lp.ERR_MALFORMED_RANGE, lang).format(
            translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
        )
        message.reply_text(reply_message, reply_markup=back_button_keyboard)
        return
    music_path_cut = f"{music_path}_cut.mp3"
    music_duration = user_data['music_duration']

    if beginning_sec > music_duration or ending_sec > music_duration:
        reply_message = translate_key_to(lp.ERR_OUT_OF_RANGE, lang).format(
            convert_seconds_to_human_readable_form(music_duration))
        message.reply_text(reply_message)
        message.reply_text(
            translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
            reply_markup=back_button_keyboard
        )
    elif beginning_sec >= ending_sec:
        reply_message = translate_key_to(lp.ERR_BEGINNING_POINT_IS_GREATER, lang)
        message.reply_text(reply_message)
        message.reply_text(
            translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
            reply_markup=back_button_keyboard
        )
    else:
        diff_sec = ending_sec - beginning_sec

        os.system(
            f"ffmpeg -y -ss {beginning_sec} -t {diff_sec} -i {music_path} -acodec copy \
            {music_path_cut}"
        )

        try:
            save_tags_to_file(
                file=music_path_cut,
                tags=music_tags,
                new_art_path=art_path if art_path else ''
            )
        except (OSError, BaseException):
            update.message.reply_text(translate_key_to(lp.ERR_ON_UPDATING_TAGS, lang))
            logger.error(
                "Error on updating tags for file %s's file.",
                music_path_cut,
                exc_info=True
            )

        try:
            with open(music_path_cut, 'rb') as music_file:
                # FIXME: After sending the file, the album art can't be read back
                context.bot.send_audio(
                    audio=music_file,
                    chat_id=update.message.chat_id,
                    duration=diff_sec,
                    caption=f"*From*: {convert_seconds_to_human_readable_form(beginning_sec)}\n"
                            f"*To*: {convert_seconds_to_human_readable_form(ending_sec)}\n\n"
                            f"🆔 {BOT_USERNAME}",
                    reply_markup=start_over_button_keyboard,
                    reply_to_message_id=user_data['music_message_id']
                )
        except (TelegramError, BaseException) as error:
            message.reply_text(
                translate_key_to(lp.ERR_ON_UPLOADING, lang),
                reply_markup=start_over_button_keyboard
            )
            logger.exception("Telegram error: %s", error)

        delete_file(music_path_cut)

        reset_user_data_context(context)


def parse_cutting_range(text: str) -> (int, int):
    text = re.sub(' ', '', text)
    beginning, _, ending = text.partition('-')

    if '-' not in text:
        raise ValueError('Malformed music range')

    if ':' in text:
        # TODO: Move this to a function
        beginning_sec = int(beginning.partition(':')[0].lstrip('0') if
                            beginning.partition(':')[0].lstrip('0') else 0) * 60 \
                        + int(beginning.partition(':')[2].lstrip('0') if
                              beginning.partition(':')[2].lstrip('0') else 0)

        ending_sec = int(ending.partition(':')[0].lstrip('0') if
                         ending.partition(':')[0].lstrip('0') else 0) * 60 \
                     + int(ending.partition(':')[2].lstrip('0') if
                           ending.partition(':')[2].lstrip('0') else 0)
    else:
        beginning_sec = int(beginning)
        ending_sec = int(ending)

    return beginning_sec, ending_sec


def is_current_module_music_cutter(current_module: str):
    return current_module == 'music_cutter'


def handle_music_cutter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'music_cutter'
    lang = user_data['language']

    back_button_keyboard = generate_back_button_keyboard(lang)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])

    # TODO: Send back the length of the music
    update.message.reply_text(
        f"{translate_key_to(lp.MUSIC_CUTTER_HELP, lang).format(music_duration)}\n",
        reply_markup=back_button_keyboard
    )


class CutterModule:
    @staticmethod
    def register():
        add_handler(MessageHandler(
            (Filters.regex('^(✂️ Music Cutter)$') | Filters.regex('^(✂️ بریدن آهنگ)$')),
            handle_music_cutter)
        )
