from telegram.ext import CommandHandler, MessageHandler, BaseHandler, filters

from .handlers import show_addresses, show_donation_methods


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        CommandHandler('donate', show_donation_methods),

        MessageHandler(
            (
                    filters.Regex(r'^Bitcoin$') |
                    filters.Regex(r'^Ethereum$') |
                    filters.Regex(r'^TRON$') |
                    filters.Regex(r'^Tether$') |
                    filters.Regex(r'^Shiba$') |
                    filters.Regex(r'^Dogecoin$') |
                    filters.Regex(r'^ZarinPal$')
            ),
            show_addresses
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
