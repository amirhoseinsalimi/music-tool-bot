from telegram.ext import MessageHandler, BaseHandler, filters

from .handlers import send_file_as_voice


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        MessageHandler(
            (
                    filters.Regex('^(🗣 Music to Voice Converter)$') |
                    filters.Regex('^(🗣 تبدیل موزیک به ویس)$') |
                    filters.Regex('^(🗣 Конвертер музыки в голос)$') |
                    filters.Regex('^(🗣 Convertidor de Música a Voz)$') |
                    filters.Regex('^(🗣 Convertisseur Musique en Voix)$') |
                    filters.Regex('^(🗣 تحويل الموسيقى إلى صوت)$') |
                    filters.Regex('^(🗣 म्यूज़िक से वॉइस कन्वर्टर)$') |
                    filters.Regex('^(🗣 Konverter Musik ke Suara)$')
            ),
            send_file_as_voice
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
