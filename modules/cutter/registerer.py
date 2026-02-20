from telegram.ext import MessageHandler, BaseHandler, filters

from .handlers import show_cutter_help


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        MessageHandler(
            (
                filters.Regex('^(✂️ Music Cutter)$') |
                filters.Regex('^(✂️ برش موزیک)$') |
                filters.Regex('^(✂️ Обрезка музыки)$') |
                filters.Regex('^(✂️ Cortador de Música)$') |
                filters.Regex('^(✂️ Découpe Musique)$') |
                filters.Regex('^(✂️ قصّ المقطع الموسيقي)$')
            ),
            show_cutter_help
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.\
    """
    for h in registry():
        add_handler(h)