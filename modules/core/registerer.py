from telegram.ext import (
    CommandHandler,
    filters,
    MessageHandler,
    BaseHandler,
)

from .handlers import (
    command_start,
    start_over,
    command_help,
    command_about,
    show_module_selector,
    set_language,
    show_language_selector,
    handle_responses,
    ignore_file,
    handle_music_message,
)


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        CommandHandler('start', command_start),
        CommandHandler('new', start_over),
        CommandHandler('language', show_language_selector),
        CommandHandler('help', command_help),
        CommandHandler('about', command_about),

        MessageHandler(filters.Regex('^(🇬🇧 English)$'), set_language),
        MessageHandler(filters.Regex('^(🇮🇷 فارسی)$'), set_language),
        MessageHandler(filters.Regex('^(🇷🇺 Русский)$'), set_language),
        MessageHandler(filters.Regex('^(🇪🇸 Español)$'), set_language),
        MessageHandler(filters.Regex('^(🇫🇷 Français)$'), set_language),
        MessageHandler(filters.Regex('^(🇸🇦 العربية)$'), set_language),

        MessageHandler(
            (filters.Regex('^(🔙 Back)$') |
             filters.Regex('^(🔙 برگشت)$') |
             filters.Regex('^(🔙 Назад)$') |
             filters.Regex('^(🔙 Atrás)$') |
             filters.Regex('^(🔙 Retour)$') |
             filters.Regex('^(🔙 رجوع)$')),
            show_module_selector),
        MessageHandler(
            (filters.Regex('^(🆕 New File)$') |
             filters.Regex('^(🆕 فایل جدید)$') |
             filters.Regex('^(🆕 Новый файл)$') |
             filters.Regex('^(🆕 Nuevo Archivo)$') |
             filters.Regex('^(🆕 Nouveau fichier)$') |
             filters.Regex('^(🆕 ملف جديد)$')),
            start_over),

        MessageHandler(filters.AUDIO, handle_music_message),
        MessageHandler(filters.TEXT, handle_responses),
        MessageHandler(
            (filters.VIDEO | filters.Document.ALL | filters.CONTACT & (
                    ~filters.AUDIO | ~filters.PHOTO | ~filters.Document.IMAGE | ~filters.Document.JPG | ~filters.Document.MP3)),
            ignore_file),
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
