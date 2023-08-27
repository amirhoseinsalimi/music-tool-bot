import re

import music_tag
from persiantools import digits
from telegram import ChatAction, ReplyKeyboardRemove, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler
from telegram.ext.utils.types import UD

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import download_file, generate_module_selector_keyboard, generate_start_over_keyboard, \
    generate_tag_editor_keyboard, get_chat_id, get_effective_message_id, get_effective_user_id, get_message, \
    get_message_text, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, reply_default_message, \
    reset_user_data_context, set_current_module, t, unset_current_module


def unset_current_tag(user_data: UD):
    user_data['tag_editor']['current_tag'] = ''


def did_user_select_a_tag(current_tag: str) -> bool:
    return bool(current_tag)


def is_current_tag_album_art(current_tag: str) -> bool:
    return current_tag == 'album_art'


def is_current_module_tag_editor(current_module: str):
    return current_module == 'tag_editor'


def save_text_into_tag(
        value: str,
        current_tag: str,
        user_data: UD,
        is_number: bool = False
) -> None:
    """Store a value of the given tag in the corresponding context.

    **Keyword arguments:**
     - value (str) -- The value to be stored as the value of `current_tag`
     - current_tag (str) -- The key to store the value into
     - context (CallbackContext) -- The context of a user to store the key:value pair into
    """
    if is_number:
        if isinstance(int(value), int):
            user_data['tag_editor'][current_tag] = value
        else:
            user_data['tag_editor'][current_tag] = 0
    else:
        user_data['tag_editor'][current_tag] = value


def save_tags_to_file(file: str, tags: dict, new_art_path: str) -> str:
    """Create and return an instance of `tag_editor_keyboard`

    **Keyword arguments:**
     - file (str) -- The path of the file
     - tags (str) -- The dictionary containing the tags and their values
     - new_art_path (str) -- The new album art to set

    **Returns:**
     The path of the file
    """
    music = music_tag.load_file(file)

    try:
        if new_art_path:
            with open(new_art_path, 'rb') as art:
                music['artwork'] = art.read()
    except OSError as error:
        raise Exception("Couldn't set hashtags") from error

    music['artist'] = tags['artist'] if tags['artist'] else ''
    music['title'] = tags['title'] if tags['title'] else ''
    music['album'] = tags['album'] if tags['album'] else ''
    music['genre'] = tags['genre'] if tags['genre'] else ''
    music['year'] = int(tags['year']) if tags['year'] else 0
    music['disknumber'] = int(tags['disknumber']) if tags['disknumber'] else 0
    music['tracknumber'] = int(tags['tracknumber']) if tags['tracknumber'] else 0

    music.save()

    return file


def generate_music_info(tag_editor_context: dict) -> str:
    """Generate the details of the music based on the values in `tag_editor_context`
    dictionary

    **Keyword arguments:**
     - tag_editor_context (dict) -- The context object of the user

    **Returns:**
     `str`
    """
    ctx = tag_editor_context

    return (
        f"*🗣 Artist:* {ctx['artist'] if ctx['artist'] else '-'}\n"
        f"*🎵 Title:* {ctx['title'] if ctx['title'] else '-'}\n"
        f"*🎼 Album:* {ctx['album'] if ctx['album'] else '-'}\n"
        f"*🎹 Genre:* {ctx['genre'] if ctx['genre'] else '-'}\n"
        f"*📅 Year:* {ctx['year'] if ctx['year'] else '-'}\n"
        f"*💿 Disk Number:* {ctx['disknumber'] if ctx['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {ctx['tracknumber'] if ctx['tracknumber'] else '-'}\n"
        "{}\n"
    )


def show_module_selector(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)

    lang = get_user_language_or_fallback(user_data)

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    unset_current_module(user_data)

    update.message.reply_text(
        t(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=get_effective_message_id(update),
        reply_markup=module_selector_keyboard
    )


def ask_for_artist(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'artist'
    message_text = t(lp.ASK_FOR_ARTIST, language)

    update.message.reply_text(message_text)


def ask_for_title(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'title'
    message_text = t(lp.ASK_FOR_TITLE, language)

    update.message.reply_text(message_text)


def ask_for_album(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'album'
    message_text = t(lp.ASK_FOR_ALBUM, language)

    update.message.reply_text(message_text)


def ask_for_genre(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'genre'
    message_text = t(lp.ASK_FOR_GENRE, language)

    update.message.reply_text(message_text)


def ask_for_year(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'year'
    message_text = t(lp.ASK_FOR_YEAR, language)

    update.message.reply_text(message_text)


def ask_for_album_art(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'album_art'
    message_text = t(lp.ASK_FOR_ALBUM_ART, language)

    update.message.reply_text(message_text)


def ask_for_disknumber(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'disknumber'
    message_text = t(lp.ASK_FOR_DISK_NUMBER, language)

    update.message.reply_text(message_text)


def ask_for_tracknumber(update: Update, user_data: UD, language: str) -> None:
    user_data['tag_editor']['current_tag'] = 'tracknumber'
    message_text = t(lp.ASK_FOR_TRACK_NUMBER, language)

    update.message.reply_text(message_text)


def read_and_store_music_tags(update: Update, user_data: UD) -> None:
    user_id = get_effective_user_id(update)
    file_download_path = user_data['music_path']
    lang = get_user_language_or_fallback(user_data)

    try:
        music = music_tag.load_file(file_download_path)
    except (OSError, NotImplementedError):
        update.message.reply_text(
            t(lp.ERR_ON_READING_TAGS, lang),
            reply_markup=generate_start_over_keyboard(lang)
        )
        logger.error(
            "Error on reading the tags %s's file. File path: %s",
            user_id,
            file_download_path,
            exc_info=True
        )

        return

    artist = music['artist']
    title = music['title']
    album = music['album']
    genre = music['genre']
    art = music['artwork']
    year = music.raw['year']
    disknumber = music.raw['disknumber']
    tracknumber = music.raw['tracknumber']

    tag_editor_context = user_data['tag_editor']

    tag_editor_context['artist'] = str(artist)
    tag_editor_context['title'] = str(title)
    tag_editor_context['album'] = str(album)
    tag_editor_context['genre'] = str(genre)
    tag_editor_context['year'] = str(year)
    tag_editor_context['disknumber'] = str(disknumber)
    tag_editor_context['tracknumber'] = str(tracknumber)

    if art:
        tag_editor_context['art_path'] = f"{file_download_path}.jpg"

        with open(tag_editor_context['art_path'], 'wb') as art_file:
            art_file.write(art.first.data)


def handle_tag_editor(update: Update, context: CallbackContext):
    user_data = get_user_data(context)
    music_tags = user_data['tag_editor']
    message = get_message(update)

    current_tag = music_tags.get('current_tag')

    lang = get_user_language_or_fallback(user_data)
    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if not did_user_select_a_tag(current_tag):
        reply_message = t(lp.ASK_WHICH_TAG, lang)
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

        return

    if is_current_tag_album_art(current_tag):
        reply_message = t(lp.ASK_FOR_ALBUM_ART, lang)
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

        return

    message_text = digits.ar_to_fa(digits.fa_to_en(message.text))

    save_text_into_tag(
        value=message_text,
        current_tag=current_tag,
        user_data=user_data,
        is_number=current_tag in ('year', 'disknumber', 'tracknumber')
    )

    reply_message = f"{t(lp.DONE, lang)} " \
                    f"{t(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                    f"{t(lp.OR, lang).upper()}" \
                    f" {t(lp.CLICK_DONE_MESSAGE, lang).lower()}"
    message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

    unset_current_tag(user_data)


def ask_which_tag_to_edit(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    message = get_message(update)
    lang = get_user_language_or_fallback(user_data)

    read_and_store_music_tags(update, user_data)

    set_current_module(user_data, Module.TAG_EDITOR)

    tag_editor_context = user_data['tag_editor']
    art_path = tag_editor_context.get('art_path')
    tag_editor_context['current_tag'] = ''

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if art_path:
        with open(art_path, 'rb') as art_file:
            message.reply_photo(
                photo=art_file,
                caption=generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
                reply_to_message_id=get_effective_message_id(update),
                reply_markup=tag_editor_keyboard,
                parse_mode='Markdown'
            )
    else:
        message.reply_text(
            generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
            reply_to_message_id=get_effective_message_id(update),
            reply_markup=tag_editor_keyboard
        )


def handle_photo_message(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    music_path = user_data['music_path']
    message = get_message(update)

    if not music_path:
        reply_message = t(lp.DEFAULT_MESSAGE, lang)
        message.reply_text(reply_message, reply_markup=ReplyKeyboardRemove())

        return

    user_id = get_effective_user_id(update)
    current_module = user_data['current_module']
    current_tag = user_data['tag_editor']['current_tag']
    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if not is_current_module_tag_editor(current_module):
        return

    if not did_user_select_a_tag(current_tag) or not is_current_tag_album_art(current_tag):
        reply_message = t(lp.ASK_WHICH_TAG, lang)
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

        return

    try:
        file_download_path = download_file(
            user_id=user_id,
            file_to_download=message.photo[len(message.photo) - 1],
            file_type='photo',
            context=context
        )

        user_data['tag_editor']['new_art_path'] = file_download_path
        reply_message = f"{t(lp.ALBUM_ART_CHANGED, lang)} " \
                        f"{t(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                        f"{t(lp.OR, lang).upper()} " \
                        f"{t(lp.CLICK_DONE_MESSAGE, lang).lower()}"

        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    except (ValueError, BaseException):
        message.reply_text(t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang))

        logger.error(
            "Error on downloading %s's file. File type: Photo",
            user_id,
            exc_info=True
        )

        return


def display_preview(update: Update, context: CallbackContext) -> None:
    message = get_message(update)
    user_data = get_user_data(context)
    tag_editor_context = user_data['tag_editor']
    art_path = tag_editor_context.get('art_path')
    new_art_path = tag_editor_context.get('new_art_path')
    lang = get_user_language_or_fallback(user_data)

    if art_path or new_art_path:
        with open(new_art_path if new_art_path else art_path, "rb") as art_file:
            message.reply_photo(
                photo=art_file,
                caption=f"{generate_music_info(tag_editor_context).format('')}"
                        f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
                        f"🆔 {BOT_USERNAME}",
                reply_to_message_id=get_effective_message_id(update),
            )

        return

    message.reply_text(
        f"{generate_music_info(tag_editor_context).format('')}"
        f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
        f"🆔 {BOT_USERNAME}",
        reply_to_message_id=get_effective_message_id(update),
    )


def finish_editing_tags(update: Update, context: CallbackContext) -> None:
    message = get_message(update)
    user_data = get_user_data(context)

    context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.UPLOAD_AUDIO
    )

    music_path = user_data['music_path']
    music_tags = user_data['tag_editor']
    new_art_path = music_tags.get('new_art_path')
    lang = get_user_language_or_fallback(user_data)

    start_over_button_keyboard = generate_start_over_keyboard(lang)

    try:
        save_tags_to_file(
            file=music_path,
            tags=music_tags,
            new_art_path=new_art_path
        )
    except (OSError, BaseException):
        message.reply_text(
            t(lp.ERR_ON_UPDATING_TAGS, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.error("Error on updating tags for file %s's file.", music_path, exc_info=True)
        return

    try:
        with open(music_path, 'rb') as music_file:
            context.bot.send_audio(
                audio=music_file,
                duration=user_data['music_duration'],
                chat_id=get_chat_id(update),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except (TelegramError, BaseException) as error:
        message.reply_text(
            t(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    reset_user_data_context(get_effective_user_id(update), user_data)


def ask_for_tag(update: Update, context: CallbackContext):
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        reply_default_message(update, lang)

        return

    message_text = get_message_text(update)

    if re.match('^(🎵 Title|🎵 عنوان)$', message_text):
        ask_for_title(update, user_data, lang)

        return

    if re.match('^(🗣 Artist|🗣 خواننده)$', message_text):
        ask_for_artist(update, user_data, lang)

        return

    if re.match('^(🎼 Album|🎼 آلبوم)$', message_text):
        ask_for_album(update, user_data, lang)

        return

    if re.match('(🖼 Album Art|🖼 عکس آلبوم)$', message_text):
        ask_for_album_art(update, user_data, lang)

        return

    if re.match('^(🎹 Genre|🎹 ژانر)$', message_text):
        ask_for_genre(update, user_data, lang)

        return

    if re.match('^(📅 Year|📅 سال)$', message_text):
        ask_for_year(update, user_data, lang)

        return

    if re.match('^(💿 Disk Number|💿 شماره دیسک)$', message_text):
        ask_for_disknumber(update, user_data, lang)

        return

    if re.match('^(▶️ Track Number|▶️ شماره ترک)$', message_text):
        ask_for_tracknumber(update, user_data, lang)

        return


class TagEditorModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('done', finish_editing_tags))
        add_handler(CommandHandler('preview', display_preview))

        add_handler(MessageHandler(Filters.photo, handle_photo_message))

        add_handler(MessageHandler(
            (Filters.regex('^(🎵 Tag Editor)$') | Filters.regex('^(🎵 تغییر تگ ها)$')),
            ask_which_tag_to_edit)
        )

        add_handler(MessageHandler(
            (
                    Filters.regex('^(🎵 Title)$') | Filters.regex('^(🎵 عنوان)$') |
                    Filters.regex('^(🗣 Artist)$') | Filters.regex('^(🗣 خواننده)$') |
                    Filters.regex('^(🎼 Album)$') | Filters.regex('^(🎼 آلبوم)$') |
                    Filters.regex('^(🖼 Album Art)$') | Filters.regex('^(🖼 عکس آلبوم)$') |
                    Filters.regex('^(🎹 Genre)$') | Filters.regex('^(🎹 ژانر)$') |
                    Filters.regex('^(📅 Year)$') | Filters.regex('^(📅 سال)$') |
                    Filters.regex('^(💿 Disk Number)$') | Filters.regex('^(💿 شماره دیسک)$') |
                    Filters.regex('^(▶️ Track Number)$') | Filters.regex('^(▶️ شماره ترک)$')
            ),
            ask_for_tag)
        )
