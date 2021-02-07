# Built-in modules
import os
import json
import env

# Third-party modules
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# My modules
from redisconfig import persistence

############################
# Bot Common Messages ######
############################
START_MESSAGE = "Hello there! 👋" \
                " Let's get started. Just send me a music and see how awesome I am!"
HELP_MESSAGE = "It's simple! Just send or forward me an audio track, an MP3 file or a music. I'm waiting... 😁"
DEFAULT_MESSAGE = "Send or forward me an audio track, an MP3 file or a music. I'm waiting... 😁"
ASK_WHICH_TAG = "Which tag do you want to edit?"
EXPECTED_NUMBER_MESSAGE = "You entered a string instead of a number. Although this is not a problem," \
                          "I guess you entered this input by mistake."
CLICK_PREVIEW_MESSAGE = "If you want to preview your changes click /preview."
CLICK_DONE_MESSAGE = "Click /done to save your changes."

############################
# Bot Common Errors ########
############################
REPORT_BUG_MESSAGE = "That's my fault!. This bug will be reported and fixed very soon!"
REPORT_CREATING_USER_FOLDER = f"Error initializing myself for you... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_MP3_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_PHOTO_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_ON_READING_TAGS = "Sorry, I couldn't read the tags of the file... {REPORT_BUG_MESSAGE}"
ERR_ON_UPDATING_TAGS = "Sorry, I couldn't tags the tags of the file... {REPORT_BUG_MESSAGE}"

############################
# Global variables #########
############################
BOT_TOKEN = os.getenv("BOT_TOKEN")
updater = Updater(BOT_TOKEN, persistence=persistence)
dispatcher = updater.dispatcher


def hello(update: Update, context: CallbackContext) -> None:
    print(json.dumps(update, sort_keys=True, indent=4, default=str))
    update.message.reply_text(f'Hello {update.effective_user.first_name}')


dispatcher.add_handler(CommandHandler('hello', hello))

updater.start_polling()
updater.idle()
