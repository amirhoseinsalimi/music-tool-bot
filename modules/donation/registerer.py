import re

from telegram.ext import CommandHandler, MessageHandler, BaseHandler, filters

from .handlers import show_addresses, show_donation_methods
from .utils import all_donation_method_labels


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        CommandHandler('donate', show_donation_methods),

        MessageHandler(filters.Regex(
            r'^(?:' + '|'.join(re.escape(label) for label in all_donation_method_labels()) + r')$'
        ), show_addresses)
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
