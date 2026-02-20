from persiantools import digits
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config.envs import BOT_USERNAME
from config.modules import Module
from modules.tag_editor.service import save_tags_to_file
from utils import convert_seconds_to_human_readable_form, delete_file, generate_back_button_keyboard, \
    generate_start_over_keyboard, get_chat_id, get_message, get_message_text, get_user_data, \
    get_user_language_or_fallback, logger, reset_user_data_context, set_current_module, t, reply_default_message, \
    resize_image, get_file_name, upsert_user
from .service import cut
from .utils import parse_cutting_range, is_range_malformed, send_out_of_range_message, \
    send_beginning_is_greater_message, is_out_of_range


@upsert_user
async def handle_cutter(update: Update, context: CallbackContext) -> None:
    """
    Handles the cut functionality. When a user enters a cutting range, this function parses it, and acts upon
    accordingly. If the range is valid, the new file with the selected range is sent to the user, otherwise an error
    message is sent.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
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
                filename=f"{get_file_name(music_tags)}.mp3",
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

    reset_user_data_context(user_id, user_data)


@upsert_user
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
