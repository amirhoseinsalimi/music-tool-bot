############################
# Built-in modules #########
############################
import os
import json
import env
from pathlib import Path
from uuid import uuid4

############################
# Third-party modules ######
############################
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler
import requests
from downloader import download_file
import music_tag

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
ERR_CREATING_USER_FOLDER = f"Error initializing myself for you... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_AUDIO_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_PHOTO_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_ON_READING_TAGS = f"Sorry, I couldn't read the tags of the file... {REPORT_BUG_MESSAGE}"
ERR_ON_UPDATING_TAGS = f"Sorry, I couldn't tags the tags of the file... {REPORT_BUG_MESSAGE}"

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


def create_user_directory(user_id: int) -> str:
    user_download_dir = f"downloads/{user_id}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)
    except:
        user_download_dir = None
        raise Exception(f"Can't create directory for user_id: {user_id}")

    return user_download_dir


def handle_music_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    file_download_path = ''
    music = None
    user_data = context.user_data

    try:
        create_user_directory(user_id)
    except:
        message.reply_text(ERR_CREATING_USER_FOLDER)
        return

    try:
        file_download_path = download_file(
            user_id=user_id,
            file_to_download=message.audio,
            file_type='audio',
            context=context
        )
    except:
        message.reply_text(ERR_ON_DOWNLOAD_AUDIO_MESSAGE)
        return

    user_data['tag_editor'] = {}

    # Store value
    context.user_data['tag_editor']['music_path'] = file_download_path
    # Send the key to the user

    try:
        music = music_tag.load_file(file_download_path)
    except:
        message.reply_text(ERR_ON_READING_TAGS)
        return

    tag_editor_context = context.user_data['tag_editor']

    artist = music['artist']
    title = music['title']
    album = music['album']
    genre = music['genre']
    year = music['year']
    discnumber = music['discnumber']
    tracknumber = music['tracknumber']

    tag_editor_context['artist'] = str(artist)
    tag_editor_context['title'] = str(title)
    tag_editor_context['album'] = str(album)
    tag_editor_context['genre'] = str(genre)
    tag_editor_context['year'] = str(year)
    tag_editor_context['discnumber'] = str(discnumber)
    tag_editor_context['tracknumber'] = str(tracknumber)

    message.reply_text(
        f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
        f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
        f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
        f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
        f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
        # f"*🖼 Album Art:* {music['artist']}\n"
        f"*💿 Disk Number:* {tag_editor_context['discnumber'] if tag_editor_context['discnumber'] else '-'}\n"
        f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
        f"🆔 @MusicToolBot\n",
        parse_mode='Markdown',
        reply_to_message_id=update.effective_message.message_id
    )


def handle_photo_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id

    try:
        create_user_directory(user_id)
    except:
        message.reply_text(ERR_CREATING_USER_FOLDER)
        return

    try:
        download_file(
            user_id=user_id,
            file_to_download=message.photo[0],
            file_type='photo',
            context=context
        )
    except:
        message.reply_text(ERR_ON_DOWNLOAD_AUDIO_MESSAGE)


dispatcher.add_handler(CommandHandler('start', command_start))
dispatcher.add_handler(CommandHandler('help', command_help))
dispatcher.add_handler(CommandHandler('hello', echo_name))
dispatcher.add_handler(MessageHandler(Filters.audio & (~Filters.command), handle_music_message))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), handle_photo_message))

updater.start_polling()
updater.idle()
