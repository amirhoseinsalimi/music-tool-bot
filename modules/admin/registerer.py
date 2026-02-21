from telegram.ext import BaseHandler
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

from .handlers import send_to_all_command, handle_admin_message, cancel_send_to_all, add_admin_if_user_is_owner, \
    list_users_if_user_is_admin, show_stats_if_user_is_admin, del_admin_if_user_is_owner

DOWNLOADS_DIT_PATH = 'downloads'
SLEEP_TIME_TO_NEXT_USER_IN_SECONDS = 3

AWAITING_MESSAGE = 1
CONVERSATION_TIMEOUT = 10
broadcasting_active = False
broadcast_thread = None


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        ConversationHandler(
            entry_points=[CommandHandler('sendtoall', send_to_all_command)],
            states={
                AWAITING_MESSAGE: [MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_admin_message)]
            },
            fallbacks=[CommandHandler('cancel_sendtoall', cancel_send_to_all)],
            conversation_timeout=CONVERSATION_TIMEOUT
        ),
        CommandHandler('addadmin', add_admin_if_user_is_owner),
        CommandHandler('deladmin', del_admin_if_user_is_owner),
        CommandHandler('stats', show_stats_if_user_is_admin),
        CommandHandler('listusers', list_users_if_user_is_admin),
        CommandHandler('cancel_sendtoall', cancel_send_to_all),
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
