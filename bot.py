#!/usr/bin/env python

#############################
# Built-in modules #########
############################
import logging
import os
import re
from pathlib import Path

############################
# Third-party modules ######
############################
import music_tag
from orator import Model
from telegram import Update, ReplyKeyboardMarkup, ChatAction, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler, Defaults, PicklePersistence

from dbconfig import db
############################
# My modules ###############
############################
from downloader import download_file
from language_service import translate_key_to
from models.admin import Admin
from models.user import User

############################
# Bot Common Messages ######
############################
Model.set_connection_resolver(db)

############################
# Global variables #########
############################
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

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

    user = User.where('user_id', '=', user_id).first()

    if not user:
        new_user = User()
        new_user.user_id = user_id
        new_user.number_of_files_sent = 0

        new_user.save()

    update.message.reply_text(translate_key_to('START_MESSAGE', context.user_data['language']))

    show_language_keyboard(update, context)


def start_over(update: Update, context: CallbackContext) -> None:
    reset_context_user_data(context)

    update.message.reply_text(
        translate_key_to('START_OVER_MESSAGE', context.user_data['language']),
        reply_to_message_id=update.effective_message.message_id,
    )


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to('HELP_MESSAGE', context.user_data['language']))


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
    user_data['new_art_path'] = ''
    user_data['current_active_module'] = ''
    user_data['music_message_id'] = ''
    user_data['language'] = user_data['language'] if ('language' in user_data) else 'en'


def show_module_selector(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    context.user_data['current_active_module'] = ''
    lang = user_data['language']

    module_selector_keyboard = ReplyKeyboardMarkup(
        [
            [translate_key_to('BTN_TAG_EDITOR', lang), translate_key_to('BTN_MUSIC_TO_VOICE_CONVERTER', lang)],
            [translate_key_to('BTN_MUSIC_CUTTER', lang), translate_key_to('BTN_BITRATE_CHANGER', lang)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.message.reply_text(
        translate_key_to('ASK_WHICH_MODULE', lang),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


def increment_usage_counter_for_user(user_id: int) -> int:
    try:
        user = User.where('user_id', '=', user_id).first()

        user.number_of_files_sent = user.number_of_files_sent + 1

        user.push()

        return user.number_of_files_sent
    except:
        return 0


def handle_music_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    file_download_path = ''
    music = None
    user_data = context.user_data
    music_duration = message.audio.duration
    old_music_path = user_data['music_path']

    if music_duration >= 3600:
        message.reply_text(translate_key_to('ERR_TOO_LARGE_FILE', user_data['language']))
        return

    context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING
    )

    try:
        create_user_directory(user_id)
    except:
        message.reply_text(translate_key_to('ERR_CREATING_USER_FOLDER', user_data['language']))
        return

    try:
        file_download_path = download_file(
            user_id=user_id,
            file_to_download=message.audio,
            file_type='audio',
            context=context
        )
    except:
        message.reply_text(translate_key_to('ERR_ON_DOWNLOAD_AUDIO_MESSAGE', user_data['language']))
        return

    try:
        music = music_tag.load_file(file_download_path)
    except:
        message.reply_text(translate_key_to('ERR_ON_READING_TAGS', user_data['language']))
        return

    reset_context_user_data(context)

    user_data['music_path'] = file_download_path
    user_data['art_path'] = ''
    user_data['music_message_id'] = message.message_id
    user_data['music_duration'] = message.audio.duration

    tag_editor_context = user_data['tag_editor']

    artist = music['artist']
    title = music['title']
    album = music['album']
    genre = music['genre']
    art = music['artwork']
    year = music.raw['year']
    disknumber = music.raw['disknumber']
    tracknumber = music.raw['tracknumber']

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

    increment_usage_counter_for_user(user_id=user_id)
    delete_file(old_music_path)


def is_user_owner(user_id: int) -> bool:
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False


def is_user_admin(user_id: int) -> bool:
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)


def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        try:
            admin = Admin()
            admin.admin_user_id = user_id

            admin.save()

            update.message.reply_text(f"User {user_id} has been added as admins")
        except:
            update.message.reply_text("An error has been occurred")


def del_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        try:
            if is_user_admin(user_id):
                Admin.where('admin_user_id', '=', user_id).delete()

                update.message.reply_text(f"User {user_id} is no longer an admin")
            else:
                update.message.reply_text(f"User {user_id} is not admin")
        except:
            update.message.reply_text("An error has been occurred")


def send_to_all():
    pass


def count_users(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update.effective_user.id):
        try:
            users = User.all()

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
    lang = user_data['language']

    user_data['current_active_module'] = 'tag_editor'

    tag_editor_context = user_data['tag_editor']
    tag_editor_context['current_tag'] = ''

    tag_editor_keyboard = ReplyKeyboardMarkup(
        [
            [translate_key_to('BTN_ARTIST', lang), translate_key_to('BTN_TITLE', lang),
             translate_key_to('BTN_ALBUM', lang)],
            [translate_key_to('BTN_GENRE', lang), translate_key_to('BTN_YEAR', lang),
             translate_key_to('BTN_ALBUM_ART', lang)],
            [translate_key_to('BTN_DISK_NUMBER', lang), translate_key_to('BTN_TRACK_NUMBER', lang)],
            [translate_key_to('BTN_BACK', lang)]
        ],
        resize_keyboard=True,
    )

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
            reply_markup=tag_editor_keyboard,
            parse_mode='Markdown'
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
    new_art_path = user_data['new_art_path']
    lang = user_data['language']
    user_data['current_active_module'] = 'mp3_to_voice_converter'  # TODO: Make modules a dict

    os.system(f"ffmpeg -i -y {input_music_path} -ac 1 -map 0:a -codec:a opus -b:a 128k -vbr off {input_music_path}")
    os.system(f"ffmpeg -i {input_music_path} -c:a libvorbis -q:a 4 {output_music_path}")

    start_over_button_keyboard = ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_NEW_FILE', lang)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    context.bot.send_voice(
        voice=open(output_music_path, 'rb'),
        chat_id=update.message.chat_id,
        caption=f"{BOT_USERNAME}",
        reply_markup=start_over_button_keyboard,
        reply_to_message_id=user_data['music_message_id']
    )

    delete_file(output_music_path)
    delete_file(input_music_path)
    if art_path:
        delete_file(art_path)
    if new_art_path:
        delete_file(new_art_path)

    reset_context_user_data(context)


def handle_music_cutter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'music_cutter'
    lang = user_data['language']

    back_button_keyboard = ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_BACK', lang)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

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
    throw_not_implemented(update, context)
    context.user_data['current_active_module'] = ''


def handle_photo_message(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    message = update.message
    user_id = update.effective_user.id
    music_path = user_data['music_path']
    current_active_module = user_data['current_active_module']
    current_tag = user_data['tag_editor']['current_tag']
    lang = user_data['language']

    tag_editor_keyboard = ReplyKeyboardMarkup(
        [
            [translate_key_to('BTN_ARTIST', lang), translate_key_to('BTN_TITLE', lang),
             translate_key_to('BTN_ALBUM', lang)],
            [translate_key_to('BTN_GENRE', lang), translate_key_to('BTN_YEAR', lang),
             translate_key_to('BTN_ALBUM_ART', lang)],
            [translate_key_to('BTN_DISK_NUMBER', lang), translate_key_to('BTN_TRACK_NUMBER', lang)],
            [translate_key_to('BTN_BACK', lang)]
        ],
        resize_keyboard=True,
    )

    if music_path:
        if current_active_module == 'tag_editor':
            if not current_tag or current_tag != 'album_art':
                reply_message = translate_key_to('ASK_WHICH_TAG', lang)
                update.message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
                return
            else:
                try:
                    file_download_path = download_file(
                        user_id=user_id,
                        file_to_download=message.photo[0],
                        file_type='photo',
                        context=context
                    )
                    reply_message = "Album art changed. " \
                                    f"{translate_key_to('CLICK_PREVIEW_MESSAGE', lang)} " \
                                    f"{translate_key_to('OR', lang).upper()} " \
                                    f"{translate_key_to('CLICK_DONE_MESSAGE', lang).lower()}"
                    user_data['new_art_path'] = file_download_path
                    message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
                except:
                    message.reply_text(translate_key_to('ERR_ON_DOWNLOAD_AUDIO_MESSAGE', lang))
    else:
        reply_message = translate_key_to('DEFAULT_MESSAGE', lang)
        message.reply_text(reply_message)


def prepare_for_artist(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'artist'
        message_text = translate_key_to('ASK_FOR_ARTIST', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_title(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'title'
        message_text = translate_key_to('ASK_FOR_TITLE', context.user_data['language'])

    update.message.reply_text(message_text)


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    lang = context.user_data['language']

    back_button_keyboard = ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_BACK', lang)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    update.message.reply_text(translate_key_to('ERR_NOT_IMPLEMENTED', lang), reply_markup=back_button_keyboard)


def prepare_for_album(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album'
        message_text = translate_key_to('ASK_FOR_ALBUM', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_genre(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'genre'
        message_text = translate_key_to('ASK_FOR_GENRE', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_year(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'year'
        message_text = translate_key_to('ASK_FOR_YEAR', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_album_art(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album_art'
        message_text = translate_key_to('ASK_FOR_ALBUM_ART', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_disknumber(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'disknumber'
        message_text = translate_key_to('ASK_FOR_DISK_NUMBER', context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_tracknumber(update: Update, context: CallbackContext) -> None:
    message_text = ''

    if len(context.user_data) == 0:
        message_text = translate_key_to('DEFAULT_MESSAGE', context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'tracknumber'
        message_text = translate_key_to('ASK_FOR_TRACK_NUMBER', context.user_data['language'])

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
    new_art_path = user_data['new_art_path']
    music_tags = user_data['tag_editor']
    lang = user_data['language']

    current_active_module = user_data['current_active_module']

    tag_editor_keyboard = ReplyKeyboardMarkup(
        [
            [translate_key_to('BTN_ARTIST', lang), translate_key_to('BTN_TITLE', lang),
             translate_key_to('BTN_ALBUM', lang)],
            [translate_key_to('BTN_GENRE', lang), translate_key_to('BTN_YEAR', lang),
             translate_key_to('BTN_ALBUM_ART', lang)],
            [translate_key_to('BTN_DISK_NUMBER', lang), translate_key_to('BTN_TRACK_NUMBER', lang)],
            [translate_key_to('BTN_BACK', lang)]
        ],
        resize_keyboard=True,
    )

    module_selector_keyboard = ReplyKeyboardMarkup(
        [
            [translate_key_to('BTN_TAG_EDITOR', lang), translate_key_to('BTN_MUSIC_TO_VOICE_CONVERTER', lang)],
            [translate_key_to('BTN_MUSIC_CUTTER', lang), translate_key_to('BTN_BITRATE_CHANGER', lang)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    back_button_keyboard = ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_BACK', lang)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    if current_active_module == 'tag_editor':
        if not user_data['tag_editor']['current_tag']:
            reply_message = translate_key_to('ASK_WHICH_TAG', lang)
            update.message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
            return
        if user_data['tag_editor']['current_tag'] == 'album_art':
            reply_message = translate_key_to('ASK_FOR_ALBUM_ART', lang)
            update.message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
        else:
            save_text_into_tag(update.message.text, user_data['tag_editor']['current_tag'], context)
            reply_message = f"{translate_key_to('DONE', lang)} " \
                            f"{translate_key_to('CLICK_PREVIEW_MESSAGE', lang)} " \
                            f"{translate_key_to('OR', lang).upper()}" \
                            f" {translate_key_to('CLICK_DONE_MESSAGE', lang).lower()}"
            update.message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    elif current_active_module == 'music_cutter':
        beginning_sec = ending_sec = 0

        try:
            beginning_sec, ending_sec = parse_cutting_range(message_text)
        except:
            reply_message = translate_key_to('ERR_MALFORMED_RANGE', lang).format(
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
            reply_message = translate_key_to('ERR_OUT_OF_RANGE', lang).format(music_duration)
            update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
        if beginning_sec >= ending_sec:
            reply_message = translate_key_to('ERR_BEGINNING_POINT_IS_GREATER', lang)
            update.message.reply_text(reply_message, reply_markup=back_button_keyboard)
        else:
            diff_sec = ending_sec - beginning_sec

            os.system(f"ffmpeg -y -ss {beginning_sec} -t {diff_sec} -i {music_path} -acodec copy {music_path_cut}")

            save_tags_to_file(
                file=music_path_cut,
                tags=music_tags,
                new_art_path=art_path if art_path else ''
            )

            start_over_button_keyboard = ReplyKeyboardMarkup(
                    [
                        [translate_key_to('BTN_NEW_FILE', lang)],
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )

            # FIXME: After sending the file, the album art can't be read back
            context.bot.send_audio(
                audio=open(music_path_cut, 'rb'),
                chat_id=update.message.chat_id,
                caption=f"*From*: {convert_seconds_to_human_readable_form(beginning_sec)}\n"
                        f"*To*: {convert_seconds_to_human_readable_form(ending_sec)}\n\n"
                        f"{BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )

            delete_file(music_path_cut)
            delete_file(music_path)
            if art_path:
                delete_file(art_path)
            if new_art_path:
                delete_file(new_art_path)

            reset_context_user_data(context)
    else:
        if music_path:
            if user_data['current_active_module']:
                update.message.reply_text(
                    translate_key_to('ASK_WHICH_MODULE', lang),
                    reply_markup=module_selector_keyboard
                )
        elif not music_path:
            update.message.reply_text(translate_key_to('START_OVER_MESSAGE', lang))
        else:
            # Not implemented
            reply_message = translate_key_to('ERR_NOT_IMPLEMENTED', lang)
            update.message.reply_text(reply_message)


def display_preview(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data
    lang = user_data['language']
    tag_editor_context = user_data['tag_editor']
    art_path = user_data['art_path']
    new_art_path = user_data['new_art_path']

    if art_path or new_art_path:
        message.reply_photo(
            photo=open(new_art_path if new_art_path else art_path, "rb"),
            caption=
            f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
            f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
            f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
            f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
            f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
            f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
            f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
            f"{translate_key_to('CLICK_DONE_MESSAGE', lang)}\n\n"
            f"🆔 {BOT_USERNAME}\n",
            reply_to_message_id=update.effective_message.message_id,
            parse_mode='Markdown'
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
            f"{translate_key_to('CLICK_DONE_MESSAGE', lang)}\n\n"
            f"🆔 {BOT_USERNAME}\n",
            reply_to_message_id=update.effective_message.message_id,
        )


def save_tags_to_file(file: str, tags: dict, new_art_path: str) -> str:
    music = music_tag.load_file(file)

    try:
        if new_art_path:
            with open(new_art_path, 'rb') as art:
                music['artwork'] = art.read()
    except:
        raise Exception("Couldn't set hashtags")

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
    new_art_path = user_data['new_art_path']
    music_tags = user_data['tag_editor']
    lang = user_data['language']

    try:
        save_tags_to_file(
            file=music_path,
            tags=music_tags,
            new_art_path=new_art_path
        )
    except:
        update.message.reply_text(translate_key_to('ERR_ON_UPDATING_TAGS', lang))

    start_over_button_keyboard = ReplyKeyboardMarkup(
            [
                [translate_key_to('BTN_NEW_FILE', lang)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

    context.bot.send_audio(
        audio=open(music_path, 'rb'),
        chat_id=update.message.chat_id,
        caption=f"{BOT_USERNAME}",
        reply_markup=start_over_button_keyboard,
        reply_to_message_id=user_data['music_message_id']
    )

    reset_context_user_data(context)
    delete_file(music_path)
    if art_path:
        delete_file(art_path)
    if new_art_path:
        delete_file(new_art_path)


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to('ABOUT_MESSAGE', context.user_data['language']))


def show_language_keyboard(update: Update, context: CallbackContext) -> None:
    language_button_keyboard = ReplyKeyboardMarkup(
        [
            ['🇬🇧 English', '🇮🇷 فارسی'],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.message.reply_text(
        "Please choose a language:\n\n"
        "لطفا زبان را انتخاب کنید:",
        reply_markup=language_button_keyboard,
    )


def set_language(update: Update, context: CallbackContext) -> None:
    lang = update.message.text.lower()
    user_data = context.user_data

    if "english" in lang:
        user_data['language'] = 'en'
    elif "فارسی" in lang:
        user_data['language'] = 'fa'
    else:
        user_data['language'] = 'en'

    update.message.reply_text(translate_key_to('LANGUAGE_CHANGED', user_data['language']))
    update.message.reply_text(translate_key_to('START_OVER_MESSAGE', user_data['language']))


def main():
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN, timeout=120)
    persistence = PicklePersistence('persistence_storage')

    updater = Updater(BOT_TOKEN, persistence=persistence, defaults=defaults)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', command_start))
    dispatcher.add_handler(CommandHandler('new', start_over))
    dispatcher.add_handler(CommandHandler('language', show_language_keyboard))
    dispatcher.add_handler(CommandHandler('help', command_help))
    dispatcher.add_handler(CommandHandler('about', command_about))

    dispatcher.add_handler(CommandHandler('addadmin', add_admin))
    dispatcher.add_handler(CommandHandler('deladmin', del_admin))
    dispatcher.add_handler(CommandHandler('senttoall', send_to_all))
    dispatcher.add_handler(CommandHandler('countusers', count_users))

    dispatcher.add_handler(MessageHandler(Filters.audio & (~Filters.command), handle_music_message))
    dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), handle_photo_message))

    dispatcher.add_handler(MessageHandler(Filters.regex('^(🇬🇧 English)$') & (~Filters.command),
                                          set_language))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🇮🇷 فارسی)$') & (~Filters.command),
                                          set_language))

    dispatcher.add_handler(MessageHandler(Filters.regex('^(🔙 Back)$') & (~Filters.command),
                                          show_module_selector))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🔙 بازگشت)$') & (~Filters.command),
                                          show_module_selector))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🆕 New File)$') & (~Filters.command),
                                          start_over))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🆕 فایل جدید)$') & (~Filters.command),
                                          start_over))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 Tag Editor)$') & (~Filters.command),
                                          handle_music_tag_editor))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 تغییر تگ ها)$') & (~Filters.command),
                                          handle_music_tag_editor))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 Music to Voice Converter)$') & (~Filters.command),
                                          handle_music_to_voice_converter))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 تبدیل به پیام ویس)$') & (~Filters.command),
                                          handle_music_to_voice_converter))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(✂️ Music Cutter)$') & (~Filters.command),
                                          handle_music_cutter))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(✂️ بریدن آهنگ)$') & (~Filters.command),
                                          handle_music_cutter))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎙 Bitrate Changer)$') & (~Filters.command),
                                          handle_music_bitrate_changer))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎙 تغییر بیت ریت)$') & (~Filters.command),
                                          handle_music_bitrate_changer))

    dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 Artist)$') & (~Filters.command), prepare_for_artist))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🗣 خواننده)$') & (~Filters.command), prepare_for_artist))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 Title)$') & (~Filters.command), prepare_for_title))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎵 عنوان)$') & (~Filters.command), prepare_for_title))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎼 Album)$') & (~Filters.command), prepare_for_album))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎼 آلبوم)$') & (~Filters.command), prepare_for_album))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎹 Genre)$') & (~Filters.command), prepare_for_genre))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🎹 ژانر)$') & (~Filters.command), prepare_for_genre))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🖼 Album Art)$') & (~Filters.command), prepare_for_album_art))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(🖼 عکس آلبوم)$') & (~Filters.command), prepare_for_album_art))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(📅 Year)$') & (~Filters.command), prepare_for_year))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(📅 سال)$') & (~Filters.command), prepare_for_year))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(💿 Disk Number)$') & (~Filters.command), prepare_for_disknumber))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(💿  شماره دیسک)$') & (~Filters.command), prepare_for_disknumber))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(▶️ Track Number)$') & (~Filters.command), prepare_for_tracknumber))
    dispatcher.add_handler(
        MessageHandler(Filters.regex('^(▶️ شماره ترک)$') & (~Filters.command), prepare_for_tracknumber))

    dispatcher.add_handler(CommandHandler('done', finish_editing_tags))
    dispatcher.add_handler(CommandHandler('preview', display_preview))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_responses))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
