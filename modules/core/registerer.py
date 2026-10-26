import re

from telegram.ext import (
    CommandHandler,
    filters,
    MessageHandler,
    BaseHandler,
)
from pathlib import Path

from database.models import Language
from utils.logging import get_logger
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

logger = get_logger(__name__)


class AudioDocumentFilter(filters.MessageFilter):
    """Match audio documents by MIME type or a supported audio filename."""
    _extensions = {'.aac', '.flac', '.m4a', '.mp3', '.ogg', '.wav'}

    def filter(self, message):
        document = message.document
        if not document:
            return False
        mime_type = (document.mime_type or '').lower()
        extension = Path(document.file_name or '').suffix.lower()
        return mime_type.startswith('audio/') or extension in self._extensions


def build_language_button_filter() -> filters.BaseFilter | None:
    """
    Build a filter matching every language button label in the ``languages`` table.

    Returns ``None`` when the table is empty, so the bot still boots on an unseeded database.
    """
    labels = [language.label for language in Language.ordered()]

    if not labels:
        return None

    return filters.Regex('^(' + '|'.join(re.escape(label) for label in labels) + ')$')


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    handlers: list[BaseHandler] = [
        CommandHandler('start', command_start),
        CommandHandler('new', start_over),
        CommandHandler('language', show_language_selector),
        CommandHandler('help', command_help),
        CommandHandler('about', command_about),
    ]

    language_button_filter = build_language_button_filter()

    if language_button_filter:
        handlers.append(MessageHandler(language_button_filter, set_language))
    else:
        logger.warning("The languages table is empty; language buttons will not be handled. Run `make db-seed`.")

    handlers.extend([
        MessageHandler(
            (filters.Regex('^(🔙 Back)$') |
             filters.Regex('^(🔙 برگشت)$') |
             filters.Regex('^(🔙 Назад)$') |
             filters.Regex('^(🔙 Atrás)$') |
             filters.Regex('^(🔙 Retour)$') |
             filters.Regex('^(🔙 رجوع)$') |
             filters.Regex('^(🔙 वापस)$') |
             filters.Regex('^(🔙 Kembali)$')),
            show_module_selector),
        MessageHandler(
            (filters.Regex('^(🆕 New File)$') |
             filters.Regex('^(🆕 فایل جدید)$') |
             filters.Regex('^(🆕 Новый файл)$') |
             filters.Regex('^(🆕 Nuevo Archivo)$') |
             filters.Regex('^(🆕 Nouveau fichier)$') |
             filters.Regex('^(🆕 ملف جديد)$') |
             filters.Regex('^(🆕 नई फ़ाइल)$') |
             filters.Regex('^(🆕 Berkas Baru)$')),
            start_over),

        MessageHandler(filters.AUDIO | AudioDocumentFilter(), handle_music_message),
        MessageHandler(filters.TEXT, handle_responses),
        MessageHandler(
            filters.VIDEO | filters.CONTACT |
            (filters.Document.ALL & ~filters.Document.IMAGE & ~AudioDocumentFilter()),
            ignore_file),
    ])

    return handlers


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
