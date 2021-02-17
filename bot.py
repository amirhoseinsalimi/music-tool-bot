#!/usr/bin/env python

#############################
# Built-in modules #########
############################
import logging
import env
import os
import re
from pathlib import Path

############################
# Third-party modules ######
############################
import music_tag
from database import cursor, connection
from telegram import Update, ReplyKeyboardMarkup, ChatAction, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler, Defaults, PicklePersistence

############################
# My modules ###############
############################
from downloader import download_file

############################
# Bot Common Messages ######
############################
START_MESSAGE = "Hello there! 👋" \
                " Let's get started. Just send me a music and see how awesome I am!"
START_OVER_MESSAGE = "Send me a music and see how awesome I am!"
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
REPORT_BUG_MESSAGE = "That's my fault! Please send a bug report here: @amirhoseinsalimi"
ERR_CREATING_USER_FOLDER = f"Error initializing myself for you... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_AUDIO_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_ON_DOWNLOAD_PHOTO_MESSAGE = f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE}"
ERR_TOO_LARGE_FILE = f"This file is too big that I can process, sorry!"
ERR_ON_READING_TAGS = f"Sorry, I couldn't read the tags of the file... {REPORT_BUG_MESSAGE}"
ERR_ON_UPDATING_TAGS = f"Sorry, I couldn't update tags the tags of the file... {REPORT_BUG_MESSAGE}"
ERR_NOT_IMPLEMENTED = f"This feature has not been implemented yet. Sorry!"
ERR_OUT_OF_RANGE = "The range you entered is out of the actual file duration. The file length is: {} seconds"
ERR_MALFORMED_RANGE = "You have entered a malformed pattern. Please try again. {}"
ERR_BEGINNING_POINT_IS_GREATER = f"This feature has not been implemented yet. Sorry!"

############################
# Global variables #########
############################
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

module_selector_keyboard = ReplyKeyboardMarkup(
    [
        ['🎵 Tag Editor', '🗣 Music to Voice Converter'],
        ['✂️ Music Cutter', '🎙 Bitrate Changer']
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

tag_editor_keyboard = ReplyKeyboardMarkup(
    [
        ['🗣 Artist', '🎵 Title', '🎼 Album'],
        ['🎹 Genre', '📅 Year', '🖼 Album Art'],
        ['💿 Disk Number', '▶️ Track Number'],
        ['🔙 Back']
    ],
    resize_keyboard=True,
)

back_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🔙 Back'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

start_over_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🆕 New File'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

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
def convert_seconds_to_human_readable_form(seconds: int) -> str:
    minutes = int(seconds / 60)
    remainder = seconds % 60

    minutes_formatted = str(minutes) if minutes >= 10 else "0" + str(minutes)
    seconds_formatted = str(seconds) if seconds >= 10 else "0" + str(seconds)

    return f"{minutes_formatted}:{seconds_formatted}"


def command_start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    reset_context_user_data(context)

    cursor.execute(f"SELECT * FROM `users` WHERE user_id={user_id}")

    users = cursor.fetchall()

    if not users:
        query = f"INSERT INTO users (user_id) VALUES ({user_id})"
        cursor.execute(query)

        connection.commit()

    update.message.reply_text(START_MESSAGE)


def start_over(update: Update, context: CallbackContext) -> None:
    reset_context_user_data(context)

    update.message.reply_text(
        START_OVER_MESSAGE,
        reply_to_message_id=update.effective_message.message_id,
    )


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(HELP_MESSAGE)


def delete_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print("The file does not exist")


def create_user_directory(user_id: int) -> str:
    user_download_dir = f"downloads/{user_id}"

    try:
        Path(user_download_dir).mkdir(parents=True, exist_ok=True)
    except:
        user_download_dir = None
        raise Exception(f"Can't create directory for user_id: {user_id}")

    return user_download_dir


def reset_context_user_data(context: CallbackContext) -> None:
    user_data = context.user_data

    user_data['tag_editor'] = {}
    user_data['music_path'] = ''
    user_data['music_duration'] = ''
    user_data['art_path'] = ''
    user_data['current_active_module'] = ''


def show_module_selector(update: Update, context: CallbackContext) -> None:
    context.user_data['current_active_module'] = ''

    update.message.reply_text(
        "What do you want to do with this file?",
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


def handle_music_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    file_download_path = ''
    music = None
    user_data = context.user_data
    music_duration = message.audio.duration

    if music_duration >= 3600:
        message.reply_text(ERR_TOO_LARGE_FILE)
        return

    context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING
    )

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

    reset_context_user_data(context)

    user_data['music_path'] = file_download_path
    user_data['art_path'] = ''
    user_data['music_duration'] = message.audio.duration

    tag_editor_context = context.user_data['tag_editor']

    artist = music['artist']
    title = music['title']
    album = music['album']
    genre = music['genre']
    art = music['artwork']
    year = music['year']
    disknumber = music['disknumber']
    tracknumber = music['tracknumber']

    if art:
        art_path = user_data['art_path'] = f"{file_download_path}.jpg"
        art_file = open(art_path, 'wb')
        art_file.write(art.first.data)
        art_file.close()

    tag_editor_context['artist'] = str(artist)
    tag_editor_context['title'] = str(title)
    tag_editor_context['album'] = str(album)
    tag_editor_context['genre'] = str(genre)
    tag_editor_context['year'] = str(year)
    tag_editor_context['disknumber'] = str(disknumber)
    tag_editor_context['tracknumber'] = str(tracknumber)

    show_module_selector(update, context)


def is_user_owner(user_id: int) -> bool:
    cursor.execute(f"SELECT * FROM `admins` WHERE user_id={user_id} AND is_owner=true")

    admin = cursor.fetchone()

    return bool(admin)


def is_user_admin(user_id: int) -> bool:
    cursor.execute(f"SELECT * FROM `admins` WHERE user_id={user_id}")

    admin = cursor.fetchone()

    return bool(admin)


def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        try:
            cursor.execute(f"INSERT IGNORE INTO `admins` (`user_id`) VALUES ({user_id})")

            update.message.reply_text(f"User {user_id} has been added as admins")
        except:
            update.message.reply_text("An error has been occurred")


def del_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        try:
            if is_user_admin(user_id):
                cursor.execute(f"DELETE FROM `admins` WHERE user_id={user_id}")

                update.message.reply_text(f"User {user_id} has been removed from admins")
            else:
                update.message.reply_text(f"User {user_id} is not admin")
        except:
            update.message.reply_text("An error has been occurred")


def send_to_all():
    pass


def count_users(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update.effective_user.id):
        try:
            cursor.execute(f"SELECT * FROM `users`")

            users = cursor.fetchall()

            update.message.reply_text(f"{len(users)} users are using this bot!")
        except:
            update.message.reply_text("An error has been occurred")


def handle_music_tag_editor(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    file_download_path = ''
    music = None
    user_data = context.user_data
    art_path = user_data['art_path']

    user_data['current_active_module'] = 'tag_editor'

    tag_editor_context = user_data['tag_editor']
    tag_editor_context['current_tag'] = ''

    if art_path:
        message.reply_photo(
            photo=open(art_path, 'rb'),
            caption=
            f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
            f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
            f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
            f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
            f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
            f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
            f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
            f"🆔 {BOT_USERNAME}\n",
            reply_to_message_id=update.effective_message.message_id,
            reply_markup=tag_editor_keyboard
        )
    else:
        message.reply_text(
            f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
            f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
            f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
            f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
            f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
            f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
            f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
            f"🆔 {BOT_USERNAME}\n",
            reply_to_message_id=update.effective_message.message_id,
            reply_markup=tag_editor_keyboard
        )


def handle_music_to_voice_converter(update: Update, context: CallbackContext) -> None:
    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.RECORD_AUDIO
    )

    user_data = context.user_data
    input_music_path = user_data['music_path']
    output_music_path = f"{user_data['music_path']}.ogg"
    art_path = user_data['art_path']
    user_data['current_active_module'] = 'mp3_to_voice_converter'  # TODO: Make modules a dict

    os.system(f"ffmpeg -i -y {input_music_path} -ac 1 -map 0:a -codec:a opus -b:a 128k -vbr off {input_music_path}")
    os.system(f"ffmpeg -i {input_music_path} -c:a libvorbis -q:a 4 {output_music_path}")

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    context.bot.send_voice(
        voice=open(output_music_path, 'rb'),
        chat_id=update.message.chat_id,
        caption=f"{BOT_USERNAME}",
        reply_markup=start_over_button_keyboard
    )

    delete_file(output_music_path)
    delete_file(input_music_path)
    if art_path:
        delete_file(art_path)

    reset_context_user_data(context)


def handle_music_cutter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'music_cutter'

    # TODO: Send back the length of the music
    # TODO: What about music file that are longer than 1 hour?
    update.message.reply_text("Now send me which part of the music you want to cut out?\n\n"
                              "Valid patterns are:\n"
                              "*mm:ss-mm:ss*: i.e. 00:10-02:30\n"
                              "*ss-ss*: i.e. 75-120\n\n"
                              "- m = minute, s = second\n"
                              "- Leading zeroes are optional\n"
                              "- Extra spaces are ignored",
                              reply_markup=back_button_keyboard
                              )


def handle_music_bitrate_changer(update: Update, context: CallbackContext) -> None:
    throw_not_implemented(update)
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


def throw_not_implemented(update: Update) -> None:
    update.message.reply_text(ERR_NOT_IMPLEMENTED, reply_markup=back_button_keyboard)


def prepare_for_album(update: Update, context: CallbackContext) -> None:
    throw_not_implemented(update)
    context.user_data['current_active_module'] = ''


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
    # TODO: Check if the value is of the correct type
    context.user_data['tag_editor'][current_tag] = value


def parse_cutting_range(text: str) -> (int, int):
    text = re.sub(' ', '', text)
    beginning, _, ending = text.partition('-')

    beginning_sec = 0
    ending_sec = 0

    if '-' not in text:
        raise Exception('Malformed music range')
    else:
        if ':' in text:
            beginning_sec = int(beginning.partition(':')[0].lstrip('0') if
                                beginning.partition(':')[0].lstrip('0') else 0) * 60 \
                            + int(beginning.partition(':')[2].lstrip('0') if
                                  beginning.partition(':')[2].lstrip('0') else 0)

            ending_sec = int(ending.partition(':')[0].lstrip('0') if
                             ending.partition(':')[0].lstrip('0') else 0) * 60 \
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
    art_path = user_data['art_path']
    music_tags = user_data['tag_editor']

    current_active_module = user_data['current_active_module']

    if current_active_module == 'tag_editor':
        if not user_data['tag_editor']['current_tag']:
            reply_message = ASK_WHICH_TAG
            update.message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
            return
        save_text_into_tag(update.message.text, user_data['tag_editor']['current_tag'], context)
        reply_message = f"{user_data['tag_editor']['current_tag'].capitalize()} changed. " \
                        f"{CLICK_PREVIEW_MESSAGE} Or {CLICK_DONE_MESSAGE.lower()}"
        update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
    elif current_active_module == 'music_cutter':
        beginning_sec = ending_sec = 0

        try:
            beginning_sec, ending_sec = parse_cutting_range(message_text)
        except:
            reply_message = ERR_MALFORMED_RANGE.format(
                "\n\nNow send me which part of the music you want to cut out?\n\n"
                "Valid patterns are:\n"
                "*mm:ss-mm:ss*: i.e. 00:10-02:30\n"
                "*ss-ss*: i.e. 75-120\n\n"
                "- m = minute, s = second\n"
                "- Leading zeroes are optional\n"
                "- Extra spaces are ignored"
            )
            update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
            return
        music_path_cut = f"{music_path}_cut.mp3"
        music_duration = user_data['music_duration']

        if beginning_sec > music_duration or ending_sec > music_duration:
            reply_message = ERR_OUT_OF_RANGE.format(music_duration)
            update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
        if beginning_sec >= ending_sec:
            reply_message = ERR_BEGINNING_POINT_IS_GREATER
            update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
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
                caption=f"*From*: {convert_seconds_to_human_readable_form(beginning_sec)}\n"
                        f"*To*: {convert_seconds_to_human_readable_form(ending_sec)}\n\n"
                        f"{BOT_USERNAME}",
                reply_markup=start_over_button_keyboard
            )

            delete_file(music_path_cut)
            delete_file(music_path)
            if art_path:
                delete_file(art_path)

            reset_context_user_data(context)
    else:
        if music_path:
            if user_data['current_active_module']:
                update.message.reply_text(
                    "What do you want to do with this file?",
                    reply_markup=module_selector_keyboard
                )
        elif not music_path:
            update.message.reply_text(START_OVER_MESSAGE)
        else:
            # Not implemented
            reply_message = ERR_NOT_IMPLEMENTED
            update.message.reply_text(reply_message)


def display_preview(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data
    tag_editor_context = user_data['tag_editor']
    art_path = user_data['art_path']

    if art_path:
        message.reply_photo(
            photo=open(art_path, "rb"),
            caption=
            f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
            f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
            f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
            f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
            f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
            f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
            f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
            f"{CLICK_DONE_MESSAGE}\n\n"
            f"🆔 {BOT_USERNAME}\n",
            reply_to_message_id=update.effective_message.message_id,
        )
    else:
        message.reply_text(
            f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
            f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
            f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
            f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
            f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
            f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
            f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
            f"{CLICK_DONE_MESSAGE}\n\n"
            f"🆔 {BOT_USERNAME}\n",
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
    user_data = context.user_data

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    music_path = user_data['music_path']
    art_path = user_data['art_path']
    music_tags = user_data['tag_editor']

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
        caption=f"{BOT_USERNAME}",
        reply_markup=start_over_button_keyboard
    )

    reset_context_user_data(context)
    delete_file(music_path)
    if art_path:
        delete_file(art_path)


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"This bot is created by Amir Hosein Salimi (@amirhoseinsalimii) in Python language.\n"
                              f"The source code of this project is available on"
                              f" [GitHub](https://github.com/amirhoseinsalimi/music-tool-bot).\n\n"
                              f"If you have any question or feedback feel free to message me on Telegram."
                              f" Or if you are a developer and have an idea to make this bot better, I appreciate your"
                              f" PRs.\n\n"
                              f"{BOT_USERNAME}",
                              )


def main():
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN, timeout=120)
    persistence = PicklePersistence('persistence_storage')

    updater = Updater(BOT_TOKEN, persistence=persistence, defaults=defaults)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', command_start))
    dispatcher.add_handler(CommandHandler('help', command_help))
    dispatcher.add_handler(CommandHandler('about', command_about))
    dispatcher.add_handler(CommandHandler('new', start_over))

    dispatcher.add_handler(CommandHandler('addadmin', add_admin))
    dispatcher.add_handler(CommandHandler('deladmin', del_admin))
    dispatcher.add_handler(CommandHandler('senttoall', send_to_all))
    dispatcher.add_handler(CommandHandler('countusers', count_users))

    dispatcher.add_handler(MessageHandler(Filters.audio & (~Filters.command), handle_music_message))
    # dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), handle_photo_message))

    dispatcher.add_handler(MessageHandler(Filters.regex('^(🔙 Back)$') & (~Filters.command),
                                          show_module_selector))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🆕 New File)$') & (~Filters.command),
                                          start_over))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 Tag Editor)$') & (~Filters.command),
                                          handle_music_tag_editor))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 Music to Voice Converter)$') & (~Filters.command),
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
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(💿 Disk Number)$') & (~Filters.command), prepare_for_disknumber))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(▶️ Track Number)$') & (~Filters.command), prepare_for_tracknumber))

    dispatcher.add_handler(CommandHandler('done', finish_editing_tags))
    dispatcher.add_handler(CommandHandler('preview', display_preview))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_responses))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
