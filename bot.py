# Built-in modules
import os
import json
import env

# Third-party modules
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# My modules
from redisconfig import persistence

# Global variables
BOT_TOKEN = os.getenv("BOT_TOKEN")


def hello(update: Update, context: CallbackContext) -> None:
    print(json.dumps(update, sort_keys=True, indent=4, default=str))
    update.message.reply_text(f'Hello {update.effective_user.first_name}')


updater = Updater(os.getenv("BOT_TOKEN"), persistence=persistence)

updater.dispatcher.add_handler(CommandHandler('hello', hello))

updater.start_polling()
updater.idle()
