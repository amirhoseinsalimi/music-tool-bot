from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import (
    ChatAction,
)
from telegram.ext import (
    CallbackContext,
)

from database.models import (
    User,
)
from modules.cutter import (
    handle_cutter,
    is_current_module_music_cutter,
)
from modules.tag_editor.handlers import (
    handle_tag_editor,
)
from modules.tag_editor.service import (
    read_and_store_music_tags,
)
from modules.tag_editor.utils import (
    is_current_module_tag_editor,
)
from utils import (
    download_file,
    get_chat_id,
    get_effective_message_id,
    get_message,
    get_message_text,
    get_user_data,
    get_user_language_or_fallback,
    is_user_data_empty,
    logger,
    reply_default_message,
    reset_user_data_context,
    unset_current_module,
    t,
    upsert_user,
)
from .utils import (
    generate_module_selector_keyboard,
    increment_file_counter_for_user,
    generate_start_over_keyboard,
    create_user_directory,
    throw_not_implemented,
    does_user_have_music_file,
)


@upsert_user
async def command_start(update: Update, context: CallbackContext) -> None:
    """
    The first function that gets called when a user starts using the bot.

    This function initialized a ``user_data`` for the user, welcomes the user, and then asks them to select a language.
    Then it creates a new ``User`` in the database if it doesn't exist yet.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id

    user_data = get_user_data(context)

    reset_user_data_context(user_id, user_data)

    await update.message.reply_text(
        text=t(get_user_language_or_fallback(user_data), 'startMessage'),
        reply_markup=ReplyKeyboardRemove()
    )

    await show_language_selector(update, context)


@upsert_user
async def start_over(update: Update, context: CallbackContext) -> None:
    """
    Resets all the user's data to initial values and asks them to send an audio file.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
    user_data = get_user_data(context)

    reset_user_data_context(user_id, user_data)

    await update.message.reply_text(
        text=t(get_user_language_or_fallback(user_data), 'startOverMessage'),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=ReplyKeyboardRemove()
    )


@upsert_user
async def command_about(update: Update, context: CallbackContext) -> None:
    """
    Handles the ``/about`` command. Replies to the user with a message containing information about the bot.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    await update.message.reply_text(
        text=t(get_user_language_or_fallback(get_user_data(context)), 'aboutMessage')
    )


@upsert_user
async def command_help(update: Update, context: CallbackContext) -> None:
    """
    Handles the ``/help`` command. Replies to the user with a guide on how to use the bot.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    await update.message.reply_text(text=t(get_user_language_or_fallback(get_user_data(context)), 'helpMessage'))


@upsert_user
async def show_language_selector(update: Update, _context: CallbackContext) -> None:
    """
    Handles the ``/language`` command. Asks the user to select a language.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: The ``context`` object
    """
    language_button_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ['🇬🇧 English', '🇮🇷 فارسی'],
            ['🇷🇺 Русский', '🇪🇸 Español'],
            ['🇫🇷 Français', '🇸🇦 العربية'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        text="\n\n".join([
            t("en", "chooseLanguage"),
            t("fa", "chooseLanguage"),
            t("ru", "chooseLanguage"),
            t("es", "chooseLanguage"),
            t("fr", "chooseLanguage"),
            t("ar", "chooseLanguage"),
        ]),
        reply_markup=language_button_keyboard
    )


@upsert_user
async def set_language(update: Update, context: CallbackContext) -> None:
    """
    Sets a language for a user. It reads the language from the user's message.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
    new_language = get_message_text(update).lower()
    user_data = get_user_data(context)

    match new_language:
        case language if "english" in language:
            user_data['language'] = 'en'
        case language if "فارسی" in language:
            user_data['language'] = 'fa'
        case language if "русский" in language:
            user_data['language'] = 'ru'
        case language if "español" in language:
            user_data['language'] = 'es'
        case language if "français" in language:
            user_data['language'] = 'fr'
        case language if "العربية" in language:
            user_data['language'] = 'ar'

    language = get_user_language_or_fallback(user_data)

    await update.message.reply_text(text=t(language, 'languageChanged'))

    await update.message.reply_text(
        text=t(language, 'startOverMessage'),
        reply_markup=ReplyKeyboardRemove()
    )

    user = User.where('user_id', '=', user_id).first()

    user.update({"language": language})


@upsert_user
async def show_module_selector(update: Update, context: CallbackContext) -> None:
    """
    Displays a keyboard with all the available modules and asks the user to select one.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    module_selector_keyboard = generate_module_selector_keyboard(language)

    await update.message.reply_text(
        text=t(language, 'askWhichModule'),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=module_selector_keyboard
    )

    unset_current_module(user_data)


@upsert_user
async def handle_music_message(update: Update, context: CallbackContext) -> None:
    """
    Checks if the audio file is too large, and if it isn't, downloads it and saves its path in the user's data context.
    Then, shows the module selector keyboard to let the user choose what they want to do with their audio.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    message = get_message(update)
    user = context.user_data['user']
    user_id = user.user_id
    user_data = get_user_data(context)

    reset_user_data_context(user_id, user_data)
    increment_file_counter_for_user(user_id=user_id)

    music_duration = message.audio.duration.total_seconds()
    music_file_size = message.audio.file_size

    language = get_user_language_or_fallback(user_data)

    if music_duration >= 3600 and music_file_size > 48000000:
        await message.reply_text(
            text=t(language, 'errTooLargeFile'),
            reply_markup=generate_start_over_keyboard(language)
        )

        return

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.TYPING
    )

    try:
        create_user_directory(user_id)
    except OSError:
        await message.reply_text(text=t(language, 'errCreatingUserFolder'))

        logger.error("Couldn't create directory for user %s", user_id, exc_info=True)

        return

    try:
        file_download_path = await download_file(
            user_id=user_id,
            file_to_download=message.audio,
            file_type='audio',
            context=context
        )
    except ValueError:
        await message.reply_text(
            text=t(language, 'errOnDownloadAudioMessage'),
            reply_markup=generate_start_over_keyboard(language)
        )

        logger.error("Error on downloading %s's file. File type: Audio", user_id, exc_info=True)

        return

    user_data['music_path'] = file_download_path
    user_data['music_message_id'] = message.message_id
    user_data['music_duration'] = music_duration

    try:
        await read_and_store_music_tags(update, user_data)
    except (KeyError, Exception):
        reset_user_data_context(user_id, user_data)

        await message.reply_text(text=t(language, 'errOnReadingTags'))

        return

    await show_module_selector(update, context)


@upsert_user
async def handle_responses(update: Update, context: CallbackContext) -> None:
    """
    Handles all other the responses from users and decides what to do with them.

    Some modules like ``cutter`` or ``tag_editor`` take a direct input of the user, so these inputs should be accepted
    by a single function like this and then passed to dedicated functions. This function accepts all other inputs that
    are uncaught by other handlers. Then reads ``user_data`` to check what is the user is doing and delegates rest of
    the work to appropriate functions. It sends a default message if user has not started the bot.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
    username = user.username
    message = get_message(update)
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, language)

        return

    music_path = user_data['music_path']

    logger.info(
        "%s:%s:%s",
        user_id,
        username,
        get_message_text(update)
    )

    current_module = user_data['current_module']

    if is_current_module_tag_editor(current_module):
        await handle_tag_editor(update, context)

        return

    if is_current_module_music_cutter(current_module):
        await handle_cutter(update, context)

        return

    if not does_user_have_music_file(music_path):
        await message.reply_text(text=t(language, 'startOverMessage'))

        return

    if does_user_have_music_file(music_path):
        module_selector_keyboard = generate_module_selector_keyboard(language)

        await message.reply_text(
            text=t(language, 'askWhichModule'),
            reply_markup=module_selector_keyboard
        )

        return

    throw_not_implemented(update, context)


@upsert_user
async def ignore_file(update: Update, context: CallbackContext) -> None:
    """
    Sends a message to tell users to start over when they send a file format that the bot is not interested in.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
    user_data = get_user_data(context)
    reset_user_data_context(user_id, user_data)

    await update.message.reply_text(
        text=t(get_user_language_or_fallback(user_data), 'startOverMessage'),
        reply_markup=ReplyKeyboardRemove()
    )
