from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler

import utils.i18n as lp
from config.telegram_bot import add_handler
from database.models import User
from modules.cutter import handle_cutter, is_current_module_music_cutter
from modules.tag_editor import handle_tag_editor, is_current_module_tag_editor
from utils import generate_back_button_keyboard, generate_module_selector_keyboard, reset_user_data_context, \
    translate_key_to, logger

def command_start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username

    reset_user_data_context(context)

    user = User.where('user_id', '=', user_id).first()

    update.message.reply_text(
        translate_key_to(lp.START_MESSAGE, context.user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )

    show_language_keyboard(update, context)

    if not user:
        User.create({
            'user_id': user_id,
            'username': username,
            'language': 'en',
            'number_of_files_sent': 0,
        })

        logger.info('A user with id %s has started using the bot.', user_id)


def start_over(update: Update, context: CallbackContext) -> None:
    reset_user_data_context(context)

    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, context.user_data['language']),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=ReplyKeyboardRemove()
    )


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to(lp.ABOUT_MESSAGE, context.user_data['language']))


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to(lp.HELP_MESSAGE, context.user_data['language']))


def show_language_keyboard(update: Update, _context: CallbackContext) -> None:
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
    print('show_module_selector')

    user_data = context.user_data
    context.user_data['current_active_module'] = ''
    lang = user_data['language']

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    update.message.reply_text(
        translate_key_to(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


def set_language(update: Update, context: CallbackContext) -> None:
    lang = update.message.text.lower()
    user_data = context.user_data
    user_id = update.effective_user.id

    if "english" in lang:
        user_data['language'] = 'en'
    elif "فارسی" in lang:
        user_data['language'] = 'fa'

    update.message.reply_text(translate_key_to(lp.LANGUAGE_CHANGED, user_data['language']))
    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )

    user = User.where('user_id', '=', user_id).first()

    user.update({"language": user_data['language']})


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    lang = context.user_data['language']

    back_button_keyboard = generate_back_button_keyboard(lang)

    update.message.reply_text(
        translate_key_to(lp.ERR_NOT_IMPLEMENTED, lang),
        reply_markup=back_button_keyboard
    )


def handle_responses(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data
    music_path = user_data['music_path']
    lang = user_data['language']

    logger.info(
        "%s:%s:%s",
        update.effective_user.id,
        update.effective_user.username,
        update.message.text
    )

    current_active_module = user_data['current_active_module']

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    if is_current_module_tag_editor(current_active_module):
        handle_tag_editor(update, context)
    elif is_current_module_music_cutter(current_active_module):
        handle_cutter(update, context)
    else:
        if music_path:
            if user_data['current_active_module']:
                message.reply_text(
                    translate_key_to(lp.ASK_WHICH_MODULE, lang),
                    reply_markup=module_selector_keyboard
                )
        elif not music_path:
            message.reply_text(translate_key_to(lp.START_OVER_MESSAGE, lang))
        else:
            throw_not_implemented(update, context)


def ignore_file(update: Update, context: CallbackContext) -> None:
    reset_user_data_context(context)
    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, context.user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )


class CoreModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('new', start_over))
        add_handler(CommandHandler('help', command_help))
        add_handler(CommandHandler('start', command_start))
        add_handler(CommandHandler('about', command_about))
        add_handler(CommandHandler('language', show_language_keyboard))

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

        add_handler(MessageHandler(Filters.text, handle_responses))
        add_handler(MessageHandler((Filters.video | Filters.document | Filters.contact), ignore_file))
