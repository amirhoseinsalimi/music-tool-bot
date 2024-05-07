from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CallbackContext, CommandHandler, filters, MessageHandler

import utils.i18n as lp
from config.telegram_bot import add_handler
from database.models import User
from modules.cutter import handle_cutter, is_current_module_music_cutter
from modules.tag_editor import handle_tag_editor, is_current_module_tag_editor
from utils import create_user_directory, download_file, generate_back_button_keyboard, \
    generate_module_selector_keyboard, generate_start_over_keyboard, get_chat_id, get_effective_message_id, \
    get_effective_user_id, get_effective_user_username, get_message, get_message_text, get_user_data, \
    get_user_language_or_fallback, increment_file_counter_for_user, is_user_data_empty, logger, reply_default_message, \
    reset_user_data_context, t, unset_current_module, update_user_username_if_updated


def does_user_have_music_file(music_path: str) -> bool:
    """
    Checks if a user has a music file.

    :param music_path: str: The user's current music_path
    :return: bool: Whether the user has a music path
    """
    return bool(music_path)


async def command_start(update: Update, context: CallbackContext) -> None:
    """
    The first function that gets called when a user starts using the bot.

    This function initialized a ``user_data`` for the user, welcomes the user, and then asks them to select a language.
    Then it creates a new ``User`` in the database if it doesn't exist yet.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_id = get_effective_user_id(update)
    username = get_effective_user_username(update)
    chat_id = get_chat_id(update)

    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)

    await update.message.reply_text(
        t(lp.START_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_markup=ReplyKeyboardRemove()
    )

    await show_language_selector(update, context)

    user = User.where('user_id', '=', user_id).first()

    if user:
        return

    User.create({
        'user_id': user_id,
        'chat_id': chat_id,
        'username': username,
        'language': 'en',
        'number_of_files_sent': 0,
    })

    logger.info('A user with id %s has started using the bot.', user_id)


async def start_over(update: Update, context: CallbackContext) -> None:
    """
    Resets all the user's data to initial values and asks them to send an audio file.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)

    await update.message.reply_text(
        t(lp.START_OVER_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=ReplyKeyboardRemove()
    )


async def command_about(update: Update, context: CallbackContext) -> None:
    """
    Handles the ``/about`` command. Replies to the user with a message containing information about the bot.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    await update.message.reply_text(
        t(lp.ABOUT_MESSAGE, get_user_language_or_fallback(get_user_data(context))),
        parse_mode=ParseMode.MARKDOWN
    )


async def command_help(update: Update, context: CallbackContext) -> None:
    """
    Handles the ``/help`` command. Replies to the user with a guide on how to use the bot.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    await update.message.reply_text(t(lp.HELP_MESSAGE, get_user_language_or_fallback(get_user_data(context))))


async def show_language_selector(update: Update, _context: CallbackContext) -> None:
    """
    Handles the ``/language`` command. Asks the user to select a language.

    :param update: Update: The ``update`` object
    :param _context: CallbackContext: The ``context`` object
    """
    language_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🇬🇧 English', '🇮🇷 فارسی'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        "Please choose a language:\n\n"
        "لطفا زبان را انتخاب کنید:",
        reply_markup=language_button_keyboard,
    )


async def set_language(update: Update, context: CallbackContext) -> None:
    """
    Sets a language for a user. It reads the language from the user's message.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    new_lang = get_message_text(update).lower()
    user_data = get_user_data(context)
    user_id = get_effective_user_id(update)

    if "english" in new_lang:
        user_data['language'] = 'en'
    elif "فارسی" in new_lang:
        user_data['language'] = 'fa'

    lang = get_user_language_or_fallback(user_data)

    await update.message.reply_text(t(lp.LANGUAGE_CHANGED, lang))

    await update.message.reply_text(
        t(lp.START_OVER_MESSAGE, lang),
        reply_markup=ReplyKeyboardRemove()
    )

    user = User.where('user_id', '=', user_id).first()

    user.update({"language": lang})


async def show_module_selector(update: Update, context: CallbackContext) -> None:
    """
    Displays a keyboard with all the available modules and asks the user to select one.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    await update.message.reply_text(
        t(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=module_selector_keyboard
    )

    unset_current_module(user_data)


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    """
    Displays an error message and offers the user to go back. It is called when the user tries to access a feature that
    has not been implemented yet.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    lang = get_user_language_or_fallback(get_user_data(context))

    back_button_keyboard = generate_back_button_keyboard(lang)

    update.message.reply_text(
        t(lp.ERR_NOT_IMPLEMENTED, lang),
        reply_markup=back_button_keyboard
    )


async def handle_music_message(update: Update, context: CallbackContext) -> None:
    """
    Checks if the audio file is too large, and if it isn't, downloads it and saves its path in the user's data context.
    Then, shows the module selector keyboard to let the user choose what they want to do with their audio.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    message = get_message(update)
    user_id = get_effective_user_id(update)
    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)
    increment_file_counter_for_user(user_id=user_id)

    music_duration = message.audio.duration
    music_file_size = message.audio.file_size

    lang = get_user_language_or_fallback(user_data)

    if music_duration >= 3600 and music_file_size > 48000000:
        await message.reply_text(
            t(lp.ERR_TOO_LARGE_FILE, lang),
            reply_markup=generate_start_over_keyboard(lang)
        )

        return

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.TYPING
    )

    try:
        create_user_directory(user_id)
    except OSError:
        await message.reply_text(t(lp.ERR_CREATING_USER_FOLDER, lang))
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
            t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang),
            reply_markup=generate_start_over_keyboard(lang)
        )
        logger.error("Error on downloading %s's file. File type: Audio", user_id, exc_info=True)

        return

    user_data['music_path'] = file_download_path
    user_data['music_message_id'] = message.message_id
    user_data['music_duration'] = message.audio.duration

    await show_module_selector(update, context)

    update_user_username_if_updated(user_id, get_effective_user_username(update))


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
    message = get_message(update)
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, lang)

        return

    music_path = user_data['music_path']

    logger.info(
        "%s:%s:%s",
        get_effective_user_id(update),
        get_effective_user_username(update),
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
        await message.reply_text(t(lp.START_OVER_MESSAGE, lang))

        return

    if does_user_have_music_file(music_path):
        module_selector_keyboard = generate_module_selector_keyboard(lang)

        await message.reply_text(
            t(lp.ASK_WHICH_MODULE, lang),
            reply_markup=module_selector_keyboard
        )

        return

    throw_not_implemented(update, context)


async def ignore_file(update: Update, context: CallbackContext) -> None:
    """
    Sends a message to tell users to start over when they send a file format that the bot is not interested in.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    reset_user_data_context(get_effective_user_id(update), user_data)

    await update.message.reply_text(
        t(lp.START_OVER_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_markup=ReplyKeyboardRemove()
    )


class CoreModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Core`` module, so that they can be used to respond to messages
        sent to the bot.
        """
        add_handler(CommandHandler('start', command_start))
        add_handler(CommandHandler('new', start_over))
        add_handler(CommandHandler('language', show_language_selector))
        add_handler(CommandHandler('help', command_help))
        add_handler(CommandHandler('about', command_about))

        add_handler(MessageHandler(filters.Regex('^(🇬🇧 English)$'), set_language))
        add_handler(MessageHandler(filters.Regex('^(🇮🇷 فارسی)$'), set_language))

        add_handler(MessageHandler(
            (filters.Regex('^(🔙 Back)$') | filters.Regex('^(🔙 بازگشت)$')),
            show_module_selector)
        )
        add_handler(MessageHandler(
            (filters.Regex('^(🆕 New File)$') | filters.Regex('^(🆕 فایل جدید)$')),
            start_over)
        )

        add_handler(MessageHandler(filters.AUDIO, handle_music_message))

        add_handler(MessageHandler(filters.TEXT, handle_responses))
        add_handler(MessageHandler(
            (filters.VIDEO | filters.Document.ALL | filters.CONTACT & (
                    ~filters.AUDIO | ~filters.PHOTO | ~filters.Document.IMAGE | ~filters.Document.JPG | ~filters.Document.MP3)),
            ignore_file))
