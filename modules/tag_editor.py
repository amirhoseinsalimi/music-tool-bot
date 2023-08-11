import music_tag
from persiantools import digits
from telegram import ChatAction, ReplyKeyboardRemove, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.telegram_bot import add_handler
from database.models import User
from utils import create_user_directory, delete_file, download_file, generate_module_selector_keyboard, \
    generate_start_over_keyboard, generate_tag_editor_keyboard, increment_file_counter_for_user, logger, \
    reset_user_data_context, t


def save_text_into_tag(
        value: str,
        current_tag: str,
        context: CallbackContext,
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
            context.user_data['tag_editor'][current_tag] = value
        else:
            context.user_data['tag_editor'][current_tag] = 0
    else:
        context.user_data['tag_editor'][current_tag] = value


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
    user_data = context.user_data
    context.user_data['current_active_module'] = ''
    lang = user_data['language']

    module_selector_keyboard = generate_module_selector_keyboard(lang)

    update.message.reply_text(
        t(lp.ASK_WHICH_MODULE, lang),
        reply_to_message_id=update.effective_message.message_id,
        reply_markup=module_selector_keyboard
    )


def prepare_for_album(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album'
        message_text = t(lp.ASK_FOR_ALBUM, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_genre(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'genre'
        message_text = t(lp.ASK_FOR_GENRE, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_year(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'year'
        message_text = t(lp.ASK_FOR_YEAR, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_album_art(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'album_art'
        message_text = t(lp.ASK_FOR_ALBUM_ART, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_disknumber(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'disknumber'
        message_text = t(lp.ASK_FOR_DISK_NUMBER, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_tracknumber(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'tracknumber'
        message_text = t(lp.ASK_FOR_TRACK_NUMBER, context.user_data['language'])

    update.message.reply_text(message_text)


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
            t(lp.ERR_TOO_LARGE_FILE, language),
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
        message.reply_text(t(lp.ERR_CREATING_USER_FOLDER, language))
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
            t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, language),
            reply_markup=generate_start_over_keyboard(language)
        )
        logger.error("Error on downloading %s's file. File type: Audio", user_id, exc_info=True)
        return

    try:
        music = music_tag.load_file(file_download_path)
    except (OSError, NotImplementedError):
        message.reply_text(
            t(lp.ERR_ON_READING_TAGS, language),
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

    increment_file_counter_for_user(user_id=user_id)

    user = User.where('user_id', '=', user_id).first()

    user.update({
        'username': update.effective_user.username,
    })

    delete_file(old_music_path)
    delete_file(old_art_path)
    delete_file(old_new_art_path)


def is_current_module_tag_editor(current_module: str):
    return current_module == 'tag_editor'


def handle_tag_editor(update: Update, context: CallbackContext):
    user_data = context.user_data
    music_tags = user_data['tag_editor']
    message = update.message
    lang = user_data['language']
    message_text = digits.ar_to_fa(digits.fa_to_en(message.text))
    current_tag = music_tags.get('current_tag')

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if not current_tag:
        reply_message = t(lp.ASK_WHICH_TAG, lang)
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    elif current_tag == 'album_art':
        reply_message = t(lp.ASK_FOR_ALBUM_ART, lang)
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    else:
        save_text_into_tag(
            value=message_text,
            current_tag=current_tag,
            context=context,
            is_number=current_tag in ('year', 'disknumber', 'tracknumber')
        )
        reply_message = f"{t(lp.DONE, lang)} " \
                        f"{t(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                        f"{t(lp.OR, lang).upper()}" \
                        f" {t(lp.CLICK_DONE_MESSAGE, lang).lower()}"
        message.reply_text(reply_message, reply_markup=tag_editor_keyboard)


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
                reply_message = t(lp.ASK_WHICH_TAG, lang)
                message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
            else:
                try:
                    file_download_path = download_file(
                        user_id=user_id,
                        file_to_download=message.photo[len(message.photo) - 1],
                        file_type='photo',
                        context=context
                    )
                    reply_message = f"{t(lp.ALBUM_ART_CHANGED, lang)} " \
                                    f"{t(lp.CLICK_PREVIEW_MESSAGE, lang)} " \
                                    f"{t(lp.OR, lang).upper()} " \
                                    f"{t(lp.CLICK_DONE_MESSAGE, lang).lower()}"
                    user_data['new_art_path'] = file_download_path
                    message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
                except (ValueError, BaseException):
                    message.reply_text(t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang))
                    logger.error(
                        "Error on downloading %s's file. File type: Photo",
                        user_id,
                        exc_info=True
                    )
                    return
    else:
        reply_message = t(lp.DEFAULT_MESSAGE, lang)
        message.reply_text(reply_message, reply_markup=ReplyKeyboardRemove())


def prepare_for_artist(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'artist'
        message_text = t(lp.ASK_FOR_ARTIST, context.user_data['language'])

    update.message.reply_text(message_text)


def prepare_for_title(update: Update, context: CallbackContext) -> None:
    if len(context.user_data) == 0:
        message_text = t(lp.DEFAULT_MESSAGE, context.user_data['language'])
    else:
        context.user_data['tag_editor']['current_tag'] = 'title'
        message_text = t(lp.ASK_FOR_TITLE, context.user_data['language'])

    update.message.reply_text(message_text)


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
                chat_id=update.message.chat_id,
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

    reset_user_data_context(context)


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
                        f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
                        f"🆔 {BOT_USERNAME}",
                reply_to_message_id=update.effective_message.message_id,
            )
    else:
        message.reply_text(
            f"{generate_music_info(tag_editor_context).format('')}"
            f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
            f"🆔 {BOT_USERNAME}",
            reply_to_message_id=update.effective_message.message_id,
        )


class TagEditorModule:
    @staticmethod
    def register():
        add_handler(CommandHandler('done', finish_editing_tags))
        add_handler(CommandHandler('preview', display_preview))

        add_handler(MessageHandler(Filters.audio, handle_music_message))
        add_handler(MessageHandler(Filters.photo, handle_photo_message))

        add_handler(MessageHandler(
            (Filters.regex('^(🎵 Tag Editor)$') | Filters.regex('^(🎵 تغییر تگ ها)$')),
            handle_music_tag_editor)
        )

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
