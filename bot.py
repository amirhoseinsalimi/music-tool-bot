#!/usr/bin/env python

"""
Main Program
"""


####################
# Built-in modules #
####################
import logging
import os
import re
import sys
from datetime import datetime


#######################
# Third-party modules #
#######################
import psutil
import music_tag
from orator import Model
from persiantools import digits
from telegram.error import TelegramError
from telegram import Update, ReplyKeyboardMarkup, ChatAction, ParseMode, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler, \
    Defaults, PicklePersistence


##############
# My modules #
##############
import utils.lang as lp  # Language Pack
from utils import download_file, create_user_directory, convert_seconds_to_human_readable_form, \
    generate_music_info, is_user_owner, is_user_admin, reset_user_data_context, \
    save_text_into_tag, increment_usage_counter_for_user, translate_key_to, delete_file, \
    generate_back_button_keyboard, generate_start_over_keyboard, \
    generate_module_selector_keyboard, generate_tag_editor_keyboard, save_tags_to_file, \
    parse_cutting_range, pretty_print_size, get_dir_size_in_bytes

from models.admin import Admin
from models.user import User
from dbconfig import db

Model.set_connection_resolver(db)


####################
# Global variables #
####################
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")


##########
# Logger #
##########
now = datetime.now()
now = re.sub(':', '_', str(now))
logger = logging.getLogger()
logger.setLevel(logging.INFO)

output_file_handler = logging.FileHandler(f"logs/{now}.log", encoding='UTF-8')
stdout_handler = logging.StreamHandler(sys.stdout)

logger.addHandler(output_file_handler)
logger.addHandler(stdout_handler)


############
# Handlers #
############


def command_start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username

    reset_user_data_context(context)

    user = User.where('user_id', '=', user_id).first()

    update.message.reply_text(
        translate_key_to(lp.START_MESSAGE, context.user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )

    show_language_keyboard(update, context)

    if not user:
        new_user = User()
        new_user.user_id = user_id
        new_user.username = username
        new_user.number_of_files_sent = 0

        new_user.save()

        logger.info("A user with id %s has been started to use the bot.", user_id)


def start_over(update: Update, context: CallbackContext) -> None:
    reset_user_data_context(context)

    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, context.user_data['language']),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=ReplyKeyboardRemove()
    )


def command_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to(lp.HELP_MESSAGE, context.user_data['language']))


def show_module_selector(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    context.user_data['current_active_module'] = ''
    lang = user_data['language']

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    update.message.reply_text(
        translate_key_to(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


def handle_music_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = update.effective_user.id
    user_data = context.user_data
    music_duration = message.audio.duration
    music_file_size = message.audio.file_size
    old_music_path = user_data['music_path']
    old_art_path = user_data['art_path']
    old_new_art_path = user_data['new_art_path']
    language = user_data['language']

    if music_duration >= 3600 and music_file_size > 48000000:
        message.reply_text(
            translate_key_to(lp.ERR_TOO_LARGE_FILE, language),
            reply_markup=generate_start_over_keyboard(language)
        )
        return

    context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING
    )

    try:
        create_user_directory(user_id)
    except OSError:
        message.reply_text(translate_key_to(lp.ERR_CREATING_USER_FOLDER, language))
        logger.error("Couldn't create directory for user %s", user_id, exc_info=True)
        return

    try:
        file_download_path = download_file(
            user_id=user_id,
            file_to_download=message.audio,
            file_type='audio',
            context=context
        )
    except ValueError:
        message.reply_text(
            translate_key_to(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, language),
            reply_markup=generate_start_over_keyboard(language)
        )
        logger.error("Error on downloading %s's file. File type: Audio", user_id, exc_info=True)
        return

    try:
        music = music_tag.load_file(file_download_path)
    except (OSError, NotImplementedError):
        message.reply_text(
            translate_key_to(lp.ERR_ON_READING_TAGS, language),
            reply_markup=generate_start_over_keyboard(language)
        )
        logger.error(
            "Error on reading the tags %s's file. File path: %s",
            user_id,
            file_download_path,
            exc_info=True
        )
        return

    reset_user_data_context(context)

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
        with open(art_path, 'wb') as art_file:
            art_file.write(art.first.data)

    tag_editor_context['artist'] = str(artist)
    tag_editor_context['title'] = str(title)
    tag_editor_context['album'] = str(album)
    tag_editor_context['genre'] = str(genre)
    tag_editor_context['year'] = str(year)
    tag_editor_context['disknumber'] = str(disknumber)
    tag_editor_context['tracknumber'] = str(tracknumber)

    show_module_selector(update, context)

    increment_usage_counter_for_user(user_id=user_id)

    user = User.where('user_id', '=', user_id).first()
    user.username = update.effective_user.username
    user.push()

    delete_file(old_music_path)
    delete_file(old_art_path)
    delete_file(old_new_art_path)


def add_admin(update: Update, _context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        admin = Admin()
        admin.admin_user_id = user_id

        admin.save()

        update.message.reply_text(f"User {user_id} has been added as admins")


def del_admin(update: Update, _context: CallbackContext) -> None:
    user_id = update.message.text.partition(' ')[2]
    # TODO: Check if the value is of type `int`
    user_id = int(user_id)

    if is_user_owner(update.effective_user.id):
        if is_user_admin(user_id):
            Admin.where('admin_user_id', '=', user_id).delete()

            update.message.reply_text(f"User {user_id} is no longer an admin")
        else:
            update.message.reply_text(f"User {user_id} is not admin")


def send_to_all():
    pass


def command_stats(update: Update, _context: CallbackContext) -> None:
    if is_user_admin(update.effective_user.id):
        downloads_dir_path = 'downloads'

        persian_users = User.all().where('language', 'fa')
        english_users = User.all().where('language', 'en')

        downloads_dir_size = pretty_print_size(get_dir_size_in_bytes(downloads_dir_path))
        number_of_downloaded_files = len(os.listdir(downloads_dir_path))
        occupied_disk_space_bytes, available_disk_space_bytes, available_disk_space_percent = \
            psutil.disk_usage('/')[-3:]

        update.message.reply_text(
            f"👥 {len(persian_users) + len(english_users)} users are using this bot!\n\n"
            f"🇬🇧 English users: {len(english_users)}\n"
            f"🇮🇷 Persian users: {len(persian_users)}\n\n"


            f"📁 There are {number_of_downloaded_files} files on the filesystem, occupying"
            f" {downloads_dir_size}\n"
            f"💽 Occupied disk space {pretty_print_size(occupied_disk_space_bytes)}, available"
            " space: "
            f"{pretty_print_size(available_disk_space_bytes)} ({available_disk_space_percent}%"
            " used)\n"
        )


def command_list_users(update: Update, _context: CallbackContext) -> None:
    if is_user_admin(update.effective_user.id):
        users = User.all()

        reply_message = ''

        for user in users:
            reply_message += f"{user.user_id}: {f'@{user.username}' if user.username else '-'}\n"

        update.message.reply_text(
            f"👥 List of all users ({len(users)} in total):\n\n"
            f"{reply_message}",
            parse_mode='',
        )


def handle_music_tag_editor(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data
    art_path = user_data['art_path']
    lang = user_data['language']

    user_data['current_active_module'] = 'tag_editor'

    tag_editor_context = user_data['tag_editor']
    tag_editor_context['current_tag'] = ''

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if art_path:
        with open(art_path, 'rb') as art_file:
            message.reply_photo(
                photo=art_file,
                caption=generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
                reply_to_message_id=update.effective_message.message_id,
                reply_markup=tag_editor_keyboard,
                parse_mode='Markdown'
            )
    else:
        message.reply_text(
            generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
            reply_to_message_id=update.effective_message.message_id,
            reply_markup=tag_editor_keyboard
        )


def handle_music_to_voice_converter(update: Update, context: CallbackContext) -> None:
    message = update.message
    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.RECORD_AUDIO
    )

    user_data = context.user_data
    input_music_path = user_data['music_path']
    voice_path = f"{user_data['music_path']}.ogg"
    lang = user_data['language']
    user_data['current_active_module'] = 'mp3_to_voice_converter'  # TODO: Make modules a dict

    os.system(
        f"ffmpeg -i -y {input_music_path} -ac 1 -map 0:a -codec:a opus -b:a 128k -vbr off \
         {input_music_path}"
    )
    os.system(f"ffmpeg -i {input_music_path} -c:a libvorbis -q:a 4 {voice_path}")

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    try:
        with open(voice_path, 'rb') as voice_file:
            context.bot.send_voice(
                voice=voice_file,
                duration=user_data['music_duration'],
                chat_id=message.chat_id,
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except TelegramError as error:
        message.reply_text(
            translate_key_to(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    delete_file(voice_path)

    reset_user_data_context(context)


def handle_music_cutter(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    user_data['current_active_module'] = 'music_cutter'
    lang = user_data['language']

    back_button_keyboard = generate_back_button_keyboard(lang)
    music_duration = convert_seconds_to_human_readable_form(user_data['music_duration'])

    # TODO: Send back the length of the music
    update.message.reply_text(
        f"{translate_key_to(lp.MUSIC_CUTTER_HELP, lang).format(music_duration)}\n",
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

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if music_path:
        if current_active_module == 'tag_editor':
            if not current_tag or current_tag != 'album_art':
                reply_message = translate_key_to(lp.ASK_WHICH_TAG, lang)
                message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
            else:
                try:
                    file_download_path = download_file(
                        user_id=user_id,
                        file_to_download=message.photo[len(message.photo) - 1],
                        file_type='photo',
                        context=context
                    )
                    reply_message = f"{translate_key_to(lp.ALBUM_ART_CHANGED, lang)} " \
                                    f"{translate_key_to(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                                    f"{translate_key_to(lp.OR, lang).upper()} " \
                                    f"{translate_key_to(lp.CLICK_DONE_MESSAGE, lang).lower()}"
                    user_data['new_art_path'] = file_download_path
                    message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
                except (ValueError, BaseException):
                    message.reply_text(translate_key_to(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang))
                    logger.error(
                        "Error on downloading %s's file. File type: Photo",
                        user_id,
                        exc_info=True
                    )
                    return
    else:
        reply_message = translate_key_to(lp.DEFAULT_MESSAGE, lang)
        message.reply_text(reply_message, reply_markup=ReplyKeyboardRemove())


def prepare_for_artist(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'artist'
        message_text = translate_key_to(lp.ASK_FOR_ARTIST, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_title(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'title'
        message_text = translate_key_to(lp.ASK_FOR_TITLE, context.user_data['language'])

    update.message.reply_text(message_text)


def throw_not_implemented(update: Update, context: CallbackContext) -> None:
    lang = context.user_data['language']

    back_button_keyboard = generate_back_button_keyboard(lang)

    update.message.reply_text(
        translate_key_to(lp.ERR_NOT_IMPLEMENTED, lang),
        reply_markup=back_button_keyboard
    )


def prepare_for_album(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album'
        message_text = translate_key_to(lp.ASK_FOR_ALBUM, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_genre(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'genre'
        message_text = translate_key_to(lp.ASK_FOR_GENRE, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_year(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'year'
        message_text = translate_key_to(lp.ASK_FOR_YEAR, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_album_art(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album_art'
        message_text = translate_key_to(lp.ASK_FOR_ALBUM_ART, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_disknumber(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'disknumber'
        message_text = translate_key_to(lp.ASK_FOR_DISK_NUMBER, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_tracknumber(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = translate_key_to(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'tracknumber'
        message_text = translate_key_to(lp.ASK_FOR_TRACK_NUMBER, context.user_data['language'])

    update.message.reply_text(message_text)


def handle_responses(update: Update, context: CallbackContext) -> None:
    message = update.message
    message_text = digits.ar_to_fa(digits.fa_to_en(message.text))
    user_data = context.user_data
    music_path = user_data['music_path']
    art_path = user_data['art_path']
    music_tags = user_data['tag_editor']
    current_tag = music_tags.get('current_tag')
    lang = user_data['language']

    logging.info(
        "%s:%s:%s",
        update.effective_user.id,
        update.effective_user.username,
        update.message.text
    )

    current_active_module = user_data['current_active_module']

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    back_button_keyboard = generate_back_button_keyboard(lang)
    start_over_button_keyboard = generate_start_over_keyboard(lang)

    if current_active_module == 'tag_editor':
        if not current_tag:
            reply_message = translate_key_to(lp.ASK_WHICH_TAG, lang)
            message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
        elif current_tag == 'album_art':
            reply_message = translate_key_to(lp.ASK_FOR_ALBUM_ART, lang)
            message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
        else:
            save_text_into_tag(
                value=message_text,
                current_tag=current_tag,
                context=context,
                is_number=current_tag in ('year', 'disknumber', 'tracknumber')
            )
            reply_message = f"{translate_key_to(lp.DONE, lang)} " \
                            f"{translate_key_to(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                            f"{translate_key_to(lp.OR, lang).upper()}" \
                            f" {translate_key_to(lp.CLICK_DONE_MESSAGE, lang).lower()}"
            message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    elif current_active_module == 'music_cutter':
        try:
            beginning_sec, ending_sec = parse_cutting_range(message_text)
        except (ValueError, BaseException):
            reply_message = translate_key_to(lp.ERR_MALFORMED_RANGE, lang).format(
                translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
            )
            message.reply_text(reply_message, reply_markup=back_button_keyboard)
            return
        music_path_cut = f"{music_path}_cut.mp3"
        music_duration = user_data['music_duration']

        if beginning_sec > music_duration or ending_sec > music_duration:
            reply_message = translate_key_to(lp.ERR_OUT_OF_RANGE, lang).format(
                convert_seconds_to_human_readable_form(music_duration))
            message.reply_text(reply_message)
            message.reply_text(
                translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
                reply_markup=back_button_keyboard
            )
        elif beginning_sec >= ending_sec:
            reply_message = translate_key_to(lp.ERR_BEGINNING_POINT_IS_GREATER, lang)
            message.reply_text(reply_message)
            message.reply_text(
                translate_key_to(lp.MUSIC_CUTTER_HELP, lang),
                reply_markup=back_button_keyboard
            )
        else:
            diff_sec = ending_sec - beginning_sec

            os.system(
                f"ffmpeg -y -ss {beginning_sec} -t {diff_sec} -i {music_path} -acodec copy \
                {music_path_cut}"
            )

            try:
                save_tags_to_file(
                    file=music_path_cut,
                    tags=music_tags,
                    new_art_path=art_path if art_path else ''
                )
            except (OSError, BaseException):
                update.message.reply_text(translate_key_to(lp.ERR_ON_UPDATING_TAGS, lang))
                logger.error(
                    "Error on updating tags for file %s's file.",
                    music_path_cut,
                    exc_info=True
                )

            try:
                with open(music_path_cut, 'rb') as music_file:
                    # FIXME: After sending the file, the album art can't be read back
                    context.bot.send_audio(
                        audio=music_file,
                        chat_id=update.message.chat_id,
                        duration=diff_sec,
                        caption=f"*From*: {convert_seconds_to_human_readable_form(beginning_sec)}\n"
                                f"*To*: {convert_seconds_to_human_readable_form(ending_sec)}\n\n"
                                f"🆔 {BOT_USERNAME}",
                        reply_markup=start_over_button_keyboard,
                        reply_to_message_id=user_data['music_message_id']
                    )
            except (TelegramError, BaseException) as error:
                message.reply_text(
                    translate_key_to(lp.ERR_ON_UPLOADING, lang),
                    reply_markup=start_over_button_keyboard
                )
                logger.exception("Telegram error: %s", error)

            delete_file(music_path_cut)

            reset_user_data_context(context)
    else:
        if music_path:
            if user_data['current_active_module']:
                message.reply_text(
                    translate_key_to(lp.ASK_WHICH_MODULE, lang),
                    reply_markup=module_selector_keyboard
                )
        elif not music_path:
            message.reply_text(translate_key_to(lp.START_OVER_MESSAGE, lang))
        else:
            # Not implemented
            reply_message = translate_key_to(lp.ERR_NOT_IMPLEMENTED, lang)
            message.reply_text(reply_message)


def display_preview(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data
    tag_editor_context = user_data['tag_editor']
    art_path = user_data['art_path']
    new_art_path = user_data['new_art_path']
    lang = user_data['language']

    if art_path or new_art_path:
        with open(new_art_path if new_art_path else art_path, "rb") as art_file:
            message.reply_photo(
                photo=art_file,
                caption=f"{generate_music_info(tag_editor_context).format('')}"
                        f"{translate_key_to(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
                        f"🆔 {BOT_USERNAME}",
                reply_to_message_id=update.effective_message.message_id,
            )
    else:
        message.reply_text(
            f"{generate_music_info(tag_editor_context).format('')}"
            f"{translate_key_to(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
            f"🆔 {BOT_USERNAME}",
            reply_to_message_id=update.effective_message.message_id,
        )


def finish_editing_tags(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_data = context.user_data

    context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action=ChatAction.UPLOAD_AUDIO
    )

    music_path = user_data['music_path']
    new_art_path = user_data['new_art_path']
    music_tags = user_data['tag_editor']
    lang = user_data['language']

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    try:
        save_tags_to_file(
            file=music_path,
            tags=music_tags,
            new_art_path=new_art_path
        )
    except (OSError, BaseException):
        message.reply_text(
            translate_key_to(lp.ERR_ON_UPDATING_TAGS, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.error("Error on updating tags for file %s's file.", music_path, exc_info=True)
        return

    try:
        with open(music_path, 'rb') as music_file:
            context.bot.send_audio(
                audio=music_file,
                duration=user_data['music_duration'],
                chat_id=update.message.chat_id,
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except (TelegramError, BaseException) as error:
        message.reply_text(
            translate_key_to(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    reset_user_data_context(context)


def command_about(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(translate_key_to(lp.ABOUT_MESSAGE, context.user_data['language']))


def show_language_keyboard(update: Update, _context: CallbackContext) -> None:
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
    user_id = update.effective_user.id

    if "english" in lang:
        user_data['language'] = 'en'
    elif "فارسی" in lang:
        user_data['language'] = 'fa'

    update.message.reply_text(translate_key_to(lp.LANGUAGE_CHANGED, user_data['language']))
    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )

    user = User.where('user_id', '=', user_id).first()
    user.language = user_data['language']
    user.push()


def ignore_file(update: Update, context: CallbackContext) -> None:
    reset_user_data_context(context)
    update.message.reply_text(
        translate_key_to(lp.START_OVER_MESSAGE, context.user_data['language']),
        reply_markup=ReplyKeyboardRemove()
    )


def main():
    """
    Start Bot
    """
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN, timeout=120)
    persistence = PicklePersistence('persistence_storage')

    updater = Updater(BOT_TOKEN, persistence=persistence, defaults=defaults)
    add_handler = updater.dispatcher.add_handler

    ##########################
    # Users Command Handlers #
    ##########################
    add_handler(CommandHandler('start', command_start))
    add_handler(CommandHandler('new', start_over))
    add_handler(CommandHandler('language', show_language_keyboard))
    add_handler(CommandHandler('help', command_help))
    add_handler(CommandHandler('about', command_about))

    add_handler(CommandHandler('done', finish_editing_tags))
    add_handler(CommandHandler('preview', display_preview))

    ##########################
    # Admin Command Handlers #
    ##########################
    add_handler(CommandHandler('addadmin', add_admin))
    add_handler(CommandHandler('deladmin', del_admin))
    add_handler(CommandHandler('senttoall', send_to_all))
    add_handler(CommandHandler('stats', command_stats))
    add_handler(CommandHandler('listusers', command_list_users))

    #################
    # File Handlers #
    #################
    add_handler(MessageHandler(Filters.audio, handle_music_message))
    add_handler(MessageHandler(Filters.photo, handle_photo_message))

    ############################
    # Change Language Handlers #
    ############################
    add_handler(MessageHandler(Filters.regex('^(🇬🇧 English)$'), set_language))
    add_handler(MessageHandler(Filters.regex('^(🇮🇷 فارسی)$'), set_language))

    ############################
    # Module Selector Handlers #
    ############################
    add_handler(MessageHandler(
            (Filters.regex('^(🔙 Back)$') | Filters.regex('^(🔙 بازگشت)$')),
            show_module_selector)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🆕 New File)$') | Filters.regex('^(🆕 فایل جدید)$')),
        start_over)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🎵 Tag Editor)$') | Filters.regex('^(🎵 تغییر تگ ها)$')),
        handle_music_tag_editor)
    )
    add_handler(MessageHandler(
            (
                Filters.regex('^(🗣 Music to Voice Converter)$')
                | Filters.regex('^(🗣 تبدیل به پیام صوتی)$')
            ),
            handle_music_to_voice_converter)
    )
    add_handler(MessageHandler(
            (Filters.regex('^(✂️ Music Cutter)$') | Filters.regex('^(✂️ بریدن آهنگ)$')),
            handle_music_cutter)
    )
    add_handler(MessageHandler(
            (Filters.regex('^(🎙 Bitrate Changer)$') | Filters.regex('^(🎙 تغییر بیت ریت)$')),
            handle_music_bitrate_changer)
    )

    #######################
    # Tag Editor Handlers #
    #######################
    add_handler(MessageHandler(
        (Filters.regex('^(🗣 Artist)$') | Filters.regex('^(🗣 خواننده)$')),
        prepare_for_artist)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🎵 Title)$') | Filters.regex('^(🎵 عنوان)$')),
        prepare_for_title)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🎼 Album)$') | Filters.regex('^(🎼 آلبوم)$')),
        prepare_for_album)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🎹 Genre)$') | Filters.regex('^(🎹 ژانر)$')),
        prepare_for_genre)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(🖼 Album Art)$') | Filters.regex('^(🖼 عکس آلبوم)$')),
        prepare_for_album_art)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(📅 Year)$') | Filters.regex('^(📅 سال)$')),
        prepare_for_year)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(💿 Disk Number)$') | Filters.regex('^(💿  شماره دیسک)$')),
        prepare_for_disknumber)
    )
    add_handler(MessageHandler(
        (Filters.regex('^(▶️ Track Number)$') | Filters.regex('^(▶️ شماره ترک)$')),
        prepare_for_tracknumber)
    )

    #####################
    # Catch-all Handler #
    #####################
    add_handler(MessageHandler(Filters.text, handle_responses))
    add_handler(MessageHandler((Filters.video | Filters.document | Filters.contact), ignore_file))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
