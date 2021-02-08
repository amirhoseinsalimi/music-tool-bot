############################
# Built-in modules #########
############################
import os
import json
from pathlib import Path
import env

############################
# Third-party modules ######
############################
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler
import requests

############################
# My modules ###############
############################
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
ORIGIN_URL = 'https://api.telegram.org'
updater = Updater(BOT_TOKEN, persistence=persistence)
dispatcher = updater.dispatcher
post = requests.post


############################
# Handlers #################
############################
def command_start(update: Update, context: CallbackContext) -> None:
    # Clear the user data here
    update.message.reply_text(START_MESSAGE)


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(HELP_MESSAGE)


def echo_name(update: Update, context: CallbackContext) -> None:
    print(json.dumps(update, sort_keys=True, indent=4, default=str))
    update.message.reply_text(f'Hello {update.effective_user.first_name}')


def music_downloader(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_download_dir = f"downloads/{user_id}"

    file_id = context.bot.getFile(update.message.audio.file_id)
    file_name = update.message.audio.file_name
    file_extension = file_name.split(".")[-1]

    Path(user_download_dir).mkdir(parents=True, exist_ok=True)
    file_id.download(f"{user_download_dir}/{file_id.file_id}.{file_extension}")


def handle_music_message(update: Update, context: CallbackContext) -> None:
    music_downloader(update, context)


dispatcher.add_handler(CommandHandler('start', command_start))
dispatcher.add_handler(CommandHandler('help', command_help))
dispatcher.add_handler(CommandHandler('hello', echo_name))
dispatcher.add_handler(MessageHandler(Filters.audio & (~Filters.command), handle_music_message))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), handle_photo_message))

updater.start_polling()
updater.idle()
