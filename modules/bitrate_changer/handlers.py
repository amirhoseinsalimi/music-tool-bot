from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from config.envs import BOT_USERNAME
from config.modules import Module
from modules.core.utils import generate_start_over_keyboard
from utils import delete_file, get_chat_id, \
    get_message, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, \
    reply_default_message, reset_user_data_context, set_current_module, t, resize_image, get_file_name, upsert_user
from .service import convert_bitrate
from .utils import generate_bitrate_selector_keyboard
from .utils import parse_bitrate_number


@upsert_user
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


@upsert_user
async def change_bitrate(update: Update, context: CallbackContext) -> None:
    """
    Handles the change bitrate functionality.

    This is the main function of the ``bitrate_changer`` module that accepts the desired bitrate, generates a new file,
    and sends it to the user. It sends a default message if user has not started the bot.

    :param update: Update: The ``update`` object
    :param context: Update: The ``context`` object
    :raises TelegramError | BaseException
    """
    user = context.user_data['user']
    user_id = user.user_id
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

    reset_user_data_context(user_id, user_data)
