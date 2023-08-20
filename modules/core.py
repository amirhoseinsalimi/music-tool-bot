from telegram import ChatAction, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler

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
    return bool(music_path)


def command_start(update: Update, context: CallbackContext) -> None:
    user_id = get_effective_user_id(update)
    username = get_effective_user_username(update)
    chat_id = get_chat_id(update)

    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)

    update.message.reply_text(
        t(lp.START_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_markup=ReplyKeyboardRemove()
    )

    show_language_selector(update, context)

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


def start_over(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)

    update.message.reply_text(
        t(lp.START_OVER_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=ReplyKeyboardRemove()
    )


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(t(lp.ABOUT_MESSAGE, get_user_language_or_fallback(get_user_data(context))))


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(t(lp.HELP_MESSAGE, get_user_language_or_fallback(get_user_data(context))))


def show_language_selector(update: Update, _context: CallbackContext) -> None:
    language_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🇬🇧 English', '🇮🇷 فارسی'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.message.reply_text(
        "Please choose a language:\n\n"
        "لطفا زبان را انتخاب کنید:",
        reply_markup=language_button_keyboard,
    )


def show_module_selector(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    update.message.reply_text(
        t(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=module_selector_keyboard
    )

    unset_current_module(user_data)


def set_language(update: Update, context: CallbackContext) -> None:
    new_lang = get_message_text(update).lower()
    user_data = get_user_data(context)
    user_id = get_effective_user_id(update)

    if "english" in new_lang:
        user_data['language'] = 'en'
    elif "فارسی" in new_lang:
        user_data['language'] = 'fa'

    lang = get_user_language_or_fallback(user_data)

    update.message.reply_text(t(lp.LANGUAGE_CHANGED, lang))
    update.message.reply_text(
        t(lp.START_OVER_MESSAGE, lang),
        reply_markup=ReplyKeyboardRemove()
    )

    user = User.where('user_id', '=', user_id).first()

    user.update({"language": lang})


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    lang = get_user_language_or_fallback(get_user_data(context))

    back_button_keyboard = generate_back_button_keyboard(lang)

    update.message.reply_text(
        t(lp.ERR_NOT_IMPLEMENTED, lang),
        reply_markup=back_button_keyboard
    )


def handle_music_message(update: Update, context: CallbackContext) -> None:
    message = get_message(update)
    user_id = get_effective_user_id(update)
    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)
    increment_file_counter_for_user(user_id=user_id)

    music_duration = message.audio.duration
    music_file_size = message.audio.file_size

    lang = get_user_language_or_fallback(user_data)

    if music_duration >= 3600 and music_file_size > 48000000:
        message.reply_text(
            t(lp.ERR_TOO_LARGE_FILE, lang),
            reply_markup=generate_start_over_keyboard(lang)
        )

        return

    context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.TYPING
    )

    try:
        create_user_directory(user_id)
    except OSError:
        message.reply_text(t(lp.ERR_CREATING_USER_FOLDER, lang))
        logger.error("Couldn't create directory for user %s", user_id, exc_info=True)
        return

    try:
        file_download_path = download_file(
            user_id=user_id,
            file_to_download=message.audio,
            file_type='audio',
            context=context
        )
    except ValueError:
        message.reply_text(
            t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang),
            reply_markup=generate_start_over_keyboard(lang)
        )
        logger.error("Error on downloading %s's file. File type: Audio", user_id, exc_info=True)

        return

    user_data['music_path'] = file_download_path
    user_data['music_message_id'] = message.message_id
    user_data['music_duration'] = message.audio.duration

    show_module_selector(update, context)

    update_user_username_if_updated(user_id, get_effective_user_username(update))


def handle_responses(update: Update, context: CallbackContext) -> None:
    message = get_message(update)
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        reply_default_message(update, lang)

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
        handle_tag_editor(update, context)

        return

    if is_current_module_music_cutter(current_module):
        handle_cutter(update, context)

        return

    if not does_user_have_music_file(music_path):
        message.reply_text(t(lp.START_OVER_MESSAGE, lang))

        return

    if does_user_have_music_file(music_path):
        module_selector_keyboard = generate_module_selector_keyboard(lang)

        message.reply_text(
            t(lp.ASK_WHICH_MODULE, lang),
            reply_markup=module_selector_keyboard
        )

        return

    throw_not_implemented(update, context)


def ignore_file(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)

    reset_user_data_context(get_effective_user_id(update), user_data)

    update.message.reply_text(
        t(lp.START_OVER_MESSAGE, get_user_language_or_fallback(user_data)),
        reply_markup=ReplyKeyboardRemove()
    )


class CoreModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('new', start_over))
        add_handler(CommandHandler('help', command_help))
        add_handler(CommandHandler('start', command_start))
        add_handler(CommandHandler('about', command_about))
        add_handler(CommandHandler('language', show_language_selector))

        add_handler(MessageHandler(Filters.regex('^(🇬🇧 English)$'), set_language))
        add_handler(MessageHandler(Filters.regex('^(🇮🇷 فارسی)$'), set_language))

        add_handler(MessageHandler(
            (Filters.regex('^(🔙 Back)$') | Filters.regex('^(🔙 بازگشت)$')),
            show_module_selector)
        )
        add_handler(MessageHandler(
            (Filters.regex('^(🆕 New File)$') | Filters.regex('^(🆕 فایل جدید)$')),
            start_over)
        )

        add_handler(MessageHandler(Filters.audio, handle_music_message))

        add_handler(MessageHandler(Filters.text, handle_responses))
        add_handler(MessageHandler((Filters.video | Filters.document | Filters.contact), ignore_file))
