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
                    filters.Regex(r'^(Bitcoin \(BTC\))$') |
                    filters.Regex(r'^(Ethereum \(ETH\))$') |
                    filters.Regex(r'^(TRON \(TRX\))$') |
                    filters.Regex(r'^(Tether \(USDT\))$') |
                    filters.Regex(r'^(Shiba \(SHIB\))$') |
                    filters.Regex(r'^(Dogecoin \(DOGE\))$') |
                    filters.Regex(r'^(ZarinPal)$') |
                    filters.Regex(r'^(زرین پال)$')
            ),
            show_addresses
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.\
    """
    for h in registry():
        add_handler(h)
