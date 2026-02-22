from telegram import Update
from telegram.constants import (
    ChatAction,
)
from telegram.error import (
    TelegramError,
)
from telegram.ext import (
    CallbackContext,
)

from config.envs import (
    BOT_USERNAME,
)
from config.modules import (
    Module,
)
from modules.core.utils import (
    generate_start_over_keyboard,
)
from utils import (
    delete_file,
    get_chat_id,
    get_message,
    get_user_data,
    get_user_language_or_fallback,
    logger,
    reset_user_data_context,
    set_current_module,
    t,
    get_file_name,
    upsert_user,
)
from .service import (
    convert_to_voice,
)


@upsert_user
async def send_file_as_voice(update: Update, context: CallbackContext) -> None:
    """
    Handles the voice conversion functionality. This is the main function of the ``voice_converter`` module that
    generates a voice message out of the current file and sends it to the user.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    :raises TelegramError | BaseException
    """
    user = context.user_data['user']
    user_id = user.user_id
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

    reset_user_data_context(user_id, user_data)
