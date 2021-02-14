############################
# Built-in modules #########
############################
import os
import json
import logging
import re
import env
from pathlib import Path

############################
# Third-party modules ######
############################
from telegram import Update, ReplyKeyboardMarkup
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
ERR_ON_UPDATING_TAGS = f"Sorry, I couldn't update tags the tags of the file... {REPORT_BUG_MESSAGE}"
ERR_NOT_IMPLEMENTED = f"This feature has not been implemented yet. Sorry!"
ERR_BEGINNING_POINT_IS_GREATER = f"This feature has not been implemented yet. Sorry!"

############################
# Global variables #########
############################
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ORIGIN_URL = 'https://api.telegram.org'
updater = Updater(BOT_TOKEN, persistence=persistence)
dispatcher = updater.dispatcher
post = requests.post

############################
# Logger ###################
############################
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
logger = logging.getLogger(__name__)


############################
# Handlers #################
############################
def command_start(update: Update, context: CallbackContext) -> None:
    # Clear the user data here

    # Reset the bot for the user. No feature is activated yet
    context.user_data['current_active_module'] = ''
    update.message.reply_text(START_MESSAGE)


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(HELP_MESSAGE)


def create_user_directory(user_id: int) -> str:
    user_download_dir = f"downloads/{user_id}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)
    except:
        user_download_dir = None
        raise Exception(f"Can't create directory for user_id: {user_id}")

    return user_download_dir


def show_module_selector(update: Update, context: CallbackContext) -> None:
    context.user_data['current_active_module'] = ''

    module_selector_keyboard = ReplyKeyboardMarkup(
        [
            ['🎵 Tag Editor', '🗣 MP3 to Voice Converter'],
            ['✂️ Music Cutter', '🎙 Bitrate Changer']
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.message.reply_text(
        "What do you want to do with this file?",
        parse_mode='Markdown',
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


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

    try:
        music = music_tag.load_file(file_download_path)
    except:
        message.reply_text(ERR_ON_READING_TAGS)
        return

    user_data['tag_editor'] = {}

    # Store value
    user_data['tag_editor']['music_path'] = file_download_path
    user_data['music_path'] = file_download_path
    user_data['music_duration'] = message.audio.duration

    tag_editor_context = context.user_data['tag_editor']

    artist = music['artist']
    title = music['title']
    album = music['album']
    genre = music['genre']
    year = music['year']
    disknumber = music['disknumber']
    tracknumber = music['tracknumber']

    tag_editor_context['artist'] = str(artist)
    tag_editor_context['title'] = str(title)
    tag_editor_context['album'] = str(album)
    tag_editor_context['genre'] = str(genre)
    tag_editor_context['year'] = str(year)
    tag_editor_context['disknumber'] = str(disknumber)
    tag_editor_context['tracknumber'] = str(tracknumber)

    show_module_selector(update, context)


def handle_music_tag_editor(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    file_download_path = ''
    music = None
    user_data = context.user_data

    try:
        music = music_tag.load_file(user_data['music_path'])
    except:
        message.reply_text(ERR_ON_READING_TAGS)
        return

    tag_editor_context = context.user_data['tag_editor']

    tag_editor_keyboard = ReplyKeyboardMarkup(
        [
            ['🗣 Artist', '🎵 Title', '🎼 Album'],
            ['🎹 Genre', '📅 Year', '🖼 Album Art'],
            ['💿 Disk Number', '▶️ Track Number'],
            ['🔙 Back']
        ],
        resize_keyboard=True,
    )

    message.reply_text(
        f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
        f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
        f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
        f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
        f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
        # f"*🖼 Album Art:* {music['artist']}\n"
        f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
        f"🆔 {BOT_USERNAME}\n",
        parse_mode='Markdown',
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=tag_editor_keyboard
    )


def handle_music_to_voice_converter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    input_music_path = user_data['music_path']
    output_music_path = f"{user_data['music_path']}.ogg"
    user_data['current_active_module'] = 'mp3_to_voice_converter'  # TODO: Make modules a dict

    os.system(f"ffmpeg -i -y {input_music_path} -ac 1 -map 0:a -codec:a opus -b:a 128k -vbr off {input_music_path}")
    os.system(f"ffmpeg -i {input_music_path} -c:a libvorbis -q:a 4 {output_music_path}")

    context.bot.send_voice(
        voice=open(output_music_path, 'rb'),
        chat_id=update.message.chat_id,
        caption=f"{BOT_USERNAME}"
    )


def handle_music_cutter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'music_cutter'

    back_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🔙 Back'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    # TODO: What about music file that are longer than 1 hour?
    update.message.reply_text("Now send me which part of the music you want to cut out?\n\n"
                              "Valid patterns are:\n"
                              "*mm:ss-mm:ss*: i.e. 00:10-02:30\n"
                              "*ss-ss*: i.e. 75-120\n\n"
                              "- m = minute, s = second\n"
                              "- Leading zeroes are optional\n"
                              "- Extra spaces are ignored",
                              parse_mode='Markdown',
                              reply_markup=back_button_keyboard
                              )


def handle_music_bitrate_changer(update: Update, context: CallbackContext) -> None:
    context.user_data['current_active_module'] = 'bitrate_changer'

    update.message.reply_text(ERR_NOT_IMPLEMENTED)

    context.user_data['current_active_module'] = ''


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


def prepare_for_artist_name(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'artist'
        message_text = "Enter the name of the artist:"

    update.message.reply_text(message_text)


def prepare_for_title(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'title'
        message_text = "Enter the title of the music:"

    update.message.reply_text(message_text)


def prepare_for_album(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'album'
        message_text = "Enter the name of the album:"

    update.message.reply_text(message_text)


def prepare_for_genre(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'genre'
        message_text = "Enter the Genre:"

    update.message.reply_text(message_text)


def prepare_for_year(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'year'
        message_text = "Enter the publish year:"

    update.message.reply_text(message_text)


def prepare_for_disknumber(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'disknumber'
        message_text = "Now send me a number as the disk number:"

    update.message.reply_text(message_text)


def prepare_for_tracknumber(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = DEFAULT_MESSAGE
    else:
        context.user_data['tag_editor']['current_tag'] = 'tracknumber'
        message_text = "Now send me a number as the track number:"

    update.message.reply_text(message_text)


def save_text_into_tag(value: str, current_tag: str, context: CallbackContext) -> None:
    context.user_data['tag_editor'][current_tag] = value


def parse_cutting_scope(text: str) -> (int, int):
    text = re.sub(' ', '', text)
    beginning, _, ending = text.partition('-')

    beginning_sec = 0
    ending_sec = 0

    if ':' in text:
        beginning_sec = int(beginning.partition(':')[0].lstrip('0') if
                            beginning.partition(':')[0].lstrip('0') else 0)*60\
                        + int(beginning.partition(':')[2].lstrip('0') if
                              beginning.partition(':')[2].lstrip('0') else 0)

        ending_sec = int(ending.partition(':')[0].lstrip('0') if
                         ending.partition(':')[0].lstrip('0') else 0)*60\
            + int(ending.partition(':')[2].lstrip('0') if
                  ending.partition(':')[2].lstrip('0') else 0)
    else:
        beginning_sec = int(beginning)
        ending_sec = int(ending)

    return beginning_sec, ending_sec


def handle_responses(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text
    user_data = context.user_data
    music_path = user_data['music_path']
    music_path = context.user_data['music_path']
    music_tags = context.user_data['tag_editor']

    current_active_module = user_data['current_active_module']

    if current_active_module == 'tag_editor':
        save_text_into_tag(update.message.text, user_data['tag_editor']['current_tag'], context)
        reply_message = f"{user_data['tag_editor']['current_tag'].capitalize()} changed. " \
                        f"{CLICK_PREVIEW_MESSAGE} Or {CLICK_DONE_MESSAGE.lower()}"
        update.message.reply_text(reply_message)
    elif current_active_module == 'music_cutter':
        beginning_sec, ending_sec = parse_cutting_scope(message_text)
        music_path_cut = f"{music_path}_cut.mp3"

        if beginning_sec >= ending_sec:
            reply_message = ERR_BEGINNING_POINT_IS_GREATER
            update.message.reply_text(reply_message)
        else:
            diff_sec = ending_sec - beginning_sec

            os.system(f"ffmpeg -y -ss {beginning_sec} -t {diff_sec} -i {music_path} -acodec copy {music_path_cut}")

            save_tags_to_file(
                file=music_path_cut,
                tags=music_tags,
            )

            context.bot.send_document(
                document=open(music_path_cut, 'rb'),
                chat_id=update.message.chat_id,
                caption=f"*From*: {beginning_sec} sec\n"
                        f"*To*: {ending_sec} sec\n\n"
                        f"{BOT_USERNAME}",
                parse_mode='Markdown'
            )
    else:
        # Not implemented
        reply_message = ERR_NOT_IMPLEMENTED
        update.message.reply_text(reply_message)


def display_preview(update: Update, context: CallbackContext) -> None:
    message = update.message
    tag_editor_context = context.user_data['tag_editor']

    message.reply_text(
        f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
        f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
        f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
        f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
        f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
        # f"*🖼 Album Art:* {music['artist']}\n"
        f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
        f"{CLICK_DONE_MESSAGE}\n\n"
        f"🆔 {BOT_USERNAME}\n",
        parse_mode='Markdown',
        reply_to_message_id=update.effective_message.message_id,
    )


def save_tags_to_file(file: str, tags: dict) -> str:
    music = music_tag.load_file(file)

    try:
        music['artist'] = tags['artist'] if tags['artist'] else ''
        music['title'] = tags['title'] if tags['title'] else ''
        music['album'] = tags['album'] if tags['album'] else ''
        music['genre'] = tags['genre'] if tags['genre'] else ''
        music['year'] = int(tags['year']) if tags['year'] else 0
        music['disknumber'] = int(tags['disknumber']) if tags['disknumber'] else 0
        music['tracknumber'] = int(tags['tracknumber']) if tags['tracknumber'] else 0
    except:
        raise Exception("Couldn't set hashtags")

    music.save()

    return file


def finish_editing_tags(update: Update, context: CallbackContext) -> None:
    music_path = context.user_data['tag_editor']['music_path']
    music_tags = context.user_data['tag_editor']

    try:
        save_tags_to_file(
            file=music_path,
            tags=music_tags,
        )
    except:
        update.message.reply_text(ERR_ON_UPDATING_TAGS)

    context.bot.send_document(
        document=open(music_path, 'rb'),
        chat_id=update.message.chat_id,
        caption=f"{BOT_USERNAME}"
    )


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"This bot is created by Amir Hosein Salimi (@amirhoseinsalimi) in Python language.\n"
                              f"The source code of this project is available on"
                              f" [GitHub](https://github.com/amirhoseinsalimi/music-tool-bot).\n\n"
                              f"If you have any question or feedback feel free to message me on Telegram."
                              f" Or if you are a developer and have an idea to make this bot better, I appreciate your"
                              f" PRs.\n\n"
                              f"{BOT_USERNAME}",
                              parse_mode='Markdown'
                              )


dispatcher.add_handler(CommandHandler('start', command_start))
dispatcher.add_handler(CommandHandler('help', command_help))
dispatcher.add_handler(CommandHandler('about', command_about))
dispatcher.add_handler(MessageHandler(Filters.audio & (~Filters.command), handle_music_message))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), handle_photo_message))

dispatcher.add_handler(MessageHandler(Filters.regex('^(🔙 Back)$') & (~Filters.command),
                                      show_module_selector))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 Tag Editor)$') & (~Filters.command),
                                      handle_music_tag_editor))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 MP3 to Voice Converter)$') & (~Filters.command),
                                      handle_music_to_voice_converter))
dispatcher.add_handler(MessageHandler(Filters.regex('^(✂️ Music Cutter)$') & (~Filters.command),
                                      handle_music_cutter))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🎙 Bitrate Changer)$') & (~Filters.command),
                                      handle_music_bitrate_changer))

dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 Artist)$') & (~Filters.command), prepare_for_artist_name))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 Title)$') & (~Filters.command), prepare_for_title))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🎼 Album)$') & (~Filters.command), prepare_for_album))
dispatcher.add_handler(MessageHandler(Filters.regex('^(🎹 Genre)$') & (~Filters.command), prepare_for_genre))
dispatcher.add_handler(MessageHandler(Filters.regex('^(📅 Year)$') & (~Filters.command), prepare_for_year))
dispatcher.add_handler(MessageHandler(Filters.regex('^(💿 Disk Number)$') & (~Filters.command), prepare_for_disknumber))
dispatcher.add_handler(MessageHandler(Filters.regex('^(▶️ Track Number)$') & (~Filters.command), prepare_for_tracknumber))

dispatcher.add_handler(CommandHandler('done', finish_editing_tags))
dispatcher.add_handler(CommandHandler('preview', display_preview))
dispatcher.add_handler(MessageHandler(Filters.text, handle_responses))

updater.start_polling()
updater.idle()
