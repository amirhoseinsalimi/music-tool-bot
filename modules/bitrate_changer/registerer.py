from telegram.ext import filters, MessageHandler, BaseHandler

from .handlers import show_bitrate_changer_keyboard, change_bitrate


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        MessageHandler(
            filters.Regex(r'^(\d{3}\s{1}kb/s)$'),
            change_bitrate),
        MessageHandler(
            (filters.Regex('^(🎙 Bitrate Changer)$') |
             filters.Regex('^(🎙 تغییر بیت‌ریت)$') |
             filters.Regex('^(🎙 Изменение битрейта)$') |
             filters.Regex('^(🎙 Cambiador de Bitrate)$') |
             filters.Regex('^(🎙 Modificateur de Bitrate)$') |
             filters.Regex('^(🎙 تغيير معدل البت)$') |
             filters.Regex('^(🎙 बिटरेट चेंजर)$') |
             filters.Regex('^(🎙 Pengubah Bitrate)$')),
            show_bitrate_changer_keyboard),
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
