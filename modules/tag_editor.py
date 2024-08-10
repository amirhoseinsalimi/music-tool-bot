import re

import music_tag
from persiantools import digits
from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import CallbackContext, CommandHandler, filters, MessageHandler
from telegram.ext._utils.types import UD

import utils.i18n as lp
from config.envs import BOT_USERNAME
from config.modules import Module
from config.telegram_bot import add_handler
from utils import download_file, generate_start_over_keyboard, \
    generate_tag_editor_keyboard, get_chat_id, get_effective_message_id, get_effective_user_id, get_message, \
    get_message_text, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, reply_default_message, \
    reset_user_data_context, set_current_module, t


def is_current_module_tag_editor(current_module: str) -> bool:
    """
    Checks if the current module is "tag_editor".

    :param current_module: str: Current module name stored in user's ``user_data``
    :return: bool: Whether the current module is "tag_editor"
    """
    return current_module == 'tag_editor'


def did_user_select_a_tag(current_tag: str) -> bool:
    """
    Checks if a user has selected a tag.

    :param current_tag: str: The current tag stored in user's ``user_data``
    :return: bool: Whether if a user has selected a tag
    """
    return bool(current_tag)


def is_current_tag_album_art(current_tag: str) -> bool:
    """
    Checks if the current tag is "album_art".

    :param current_tag: str: The current tag stored in user's ``user_data``
    :return: bool: Whether if a user's current tag is "album_art"
    """
    return current_tag == 'album_art'


def unset_current_tag(user_data: UD) -> None:
    """
    Sets the current tag to an empty string so the user has to select a tag again.

    :param user_data: UD: The ``user_data`` object
    """
    user_data['tag_editor']['current_tag'] = ''


def save_text_into_tag(
        value: str,
        current_tag: str,
        user_data: UD,
        is_number: bool = False
) -> None:
    """
    Sets a value in the user's ``user_data`` as their current tag. Sets it to `0` if the value should be ``int`` but
    it's not.

    :param value: str: The value to set as current tag
    :param current_tag: str: The current tag stored in user's ``user_data``
    :param user_data: UD: The ``user_data`` object
    :param is_number: bool: Whether the value should be treated as an ``int``
    """
    if is_number:
        if value.isdigit():
            user_data['tag_editor'][current_tag] = value
        else:
            user_data['tag_editor'][current_tag] = 0
    else:
        user_data['tag_editor'][current_tag] = value


def save_tags_to_file(file: str, tags: dict, new_art_path: str) -> None:
    """
    Saves the tags in a file. If there is an optional new artwork path it will set that as well.

    :param file: str: The path of the file
    :param tags: dict: The tags to be saved in the file
    :param new_art_path: str (optional): The album art to be saved
    :raises LookupError: No Such a user in the database
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
    music['year'] = int(tags['year']) if tags['year'] and tags['year'].isdigit() else 0
    music['disknumber'] = int(tags['disknumber']) if tags['disknumber'] and tags['disknumber'].isdigit() else 0
    music['tracknumber'] = int(tags['tracknumber']) if tags['tracknumber'] and tags['tracknumber'].isdigit() else 0

    music.save()


def generate_music_info(tag_editor_context: dict) -> str:
    """
    Returns the metadata of a music as a formatted string.

    :param tag_editor_context: dict: A dictionary representing the metadata of a music
    :return: str: The metadata of a music.
    """
    default_value = ''
    ctx = tag_editor_context

    music_info = (
        f"*🗣 Artist:* {ctx.get('artist') if ctx.get('artist') else default_value}\n"
        f"*🎵 Title:* {ctx.get('title') if ctx.get('title') else default_value}\n"
        f"*🎼 Album:* {ctx.get('album') if ctx.get('album') else default_value}\n"
        f"*🎹 Genre:* {ctx.get('genre') if ctx.get('genre') else default_value}\n"
        f"*📅 Year:* {ctx.get('year') if ctx.get('year') else default_value}\n"
        f"*💿 Disk Number:* {ctx.get('disknumber') if ctx.get('disknumber') else default_value}\n"
        f"*▶️ Track Number:* {ctx.get('tracknumber') if ctx.get('tracknumber') else default_value}\n"
        "{}\n"
    )

    escaped_music_info = re.sub(r'([-_()!])', r'\\\1', music_info)

    return escaped_music_info


async def ask_for_artist(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an artist name to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'artist'
    message_text = t(lp.ASK_FOR_ARTIST, language)

    await update.message.reply_text(message_text)


async def ask_for_title(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a title to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'title'
    message_text = t(lp.ASK_FOR_TITLE, language)

    await update.message.reply_text(message_text)


async def ask_for_album(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an album name to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'album'
    message_text = t(lp.ASK_FOR_ALBUM, language)

    await update.message.reply_text(message_text)


async def ask_for_genre(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a genre to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'genre'
    message_text = t(lp.ASK_FOR_GENRE, language)

    await update.message.reply_text(message_text)


async def ask_for_year(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a year to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'year'
    message_text = t(lp.ASK_FOR_YEAR, language)

    await update.message.reply_text(message_text)


async def ask_for_album_art(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an album art to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'album_art'
    message_text = t(lp.ASK_FOR_ALBUM_ART, language)

    await update.message.reply_text(message_text)


async def ask_for_disknumber(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a disknumber to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'disknumber'
    message_text = t(lp.ASK_FOR_DISK_NUMBER, language)

    await update.message.reply_text(message_text)


async def ask_for_tracknumber(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a track number to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'tracknumber'
    message_text = t(lp.ASK_FOR_TRACK_NUMBER, language)

    await update.message.reply_text(message_text)


async def read_and_store_music_tags(update: Update, user_data: UD) -> None:
    """
    Reads the tags of a music file and stores them in the user's ``user_data`` dictionary.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    """
    user_id = get_effective_user_id(update)
    file_download_path = user_data['music_path']
    lang = get_user_language_or_fallback(user_data)

    try:
        music = music_tag.load_file(file_download_path)
    except (OSError, NotImplementedError):
        await update.message.reply_text(
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


async def handle_tag_editor(update: Update, context: CallbackContext) -> None:
    """
    This function is responsible for handling the user's input when they are editing a tag. It first checks if the user
    has selected a tag to edit, and if not, it asks them to do so. If the current tag is album art, then it asks them
    for an image file (which will be handled by :func:`handle_photo_message`). Otherwise, it saves their text into the
    selected tag and sends back a message saying that everything went well.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    music_tags = user_data['tag_editor']
    message = get_message(update)

    current_tag = music_tags.get('current_tag')

    lang = get_user_language_or_fallback(user_data)
    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if not did_user_select_a_tag(current_tag):
        reply_message = t(lp.ASK_WHICH_TAG, lang)
        await message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

        return

    if is_current_tag_album_art(current_tag):
        reply_message = t(lp.ASK_FOR_ALBUM_ART, lang)
        await message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

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
    await message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

    unset_current_tag(user_data)


async def handle_photo_message(update: Update, context: CallbackContext) -> None:
    """
    This function is responsible for handling the album arts that the user wants to be saved in their file.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    music_path = user_data['music_path']
    message = get_message(update)

    if not music_path:
        reply_message = t(lp.DEFAULT_MESSAGE, lang)
        await message.reply_text(reply_message, reply_markup=ReplyKeyboardRemove())

        return

    user_id = get_effective_user_id(update)
    current_module = user_data['current_module']
    current_tag = user_data['tag_editor']['current_tag']
    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if not is_current_module_tag_editor(current_module):
        return

    if not did_user_select_a_tag(current_tag) or not is_current_tag_album_art(current_tag):
        reply_message = t(lp.ASK_WHICH_TAG, lang)
        await message.reply_text(reply_message, reply_markup=tag_editor_keyboard)

        return

    try:
        file_download_path = await download_file(
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

        await message.reply_text(reply_message, reply_markup=tag_editor_keyboard)
    except (ValueError, BaseException):
        await message.reply_text(t(lp.ERR_ON_DOWNLOAD_AUDIO_MESSAGE, lang))

        logger.error(
            "Error on downloading %s's file. File type: Photo",
            user_id,
            exc_info=True
        )

        return


async def ask_which_tag_to_edit(update: Update, context: CallbackContext) -> None:
    """
    This function is called when the user has selected the `Module.TAG_EDITOR module`.
    It displays the current tags of that music file and asks which tag should be edited next.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    message = get_message(update)
    lang = get_user_language_or_fallback(user_data)

    try:
        await read_and_store_music_tags(update, user_data)

        tag_editor_context = user_data['tag_editor']
    except KeyError:
        await message.reply_text(t(lp.DEFAULT_MESSAGE, lang))

        return

    set_current_module(user_data, Module.TAG_EDITOR)

    art_path = tag_editor_context.get('art_path')
    tag_editor_context['current_tag'] = ''

    tag_editor_keyboard = generate_tag_editor_keyboard(lang)

    if art_path:
        with open(art_path, 'rb') as art_file:
            await message.reply_photo(
                photo=art_file,
                caption=generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
                reply_to_message_id=get_effective_message_id(update),
                reply_markup=tag_editor_keyboard,
                parse_mode=ParseMode.MARKDOWN_V2
            )
    else:
        await message.reply_text(
            generate_music_info(tag_editor_context).format(f"\n🆔 {BOT_USERNAME}"),
            reply_to_message_id=get_effective_message_id(update),
            reply_markup=tag_editor_keyboard
        )


async def display_preview(update: Update, context: CallbackContext) -> None:
    """
    Handles ``/preview`` command. Displays a caption with all the information about the music file, and if there's
    an album art, it also displays that.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    message = get_message(update)
    user_data = get_user_data(context)
    tag_editor_context = user_data['tag_editor']
    art_path = tag_editor_context.get('art_path')
    new_art_path = tag_editor_context.get('new_art_path')
    lang = get_user_language_or_fallback(user_data)

    if art_path or new_art_path:
        with open(new_art_path if new_art_path else art_path, "rb") as art_file:
            await message.reply_photo(
                photo=art_file,
                caption=f"{generate_music_info(tag_editor_context).format('')}"
                        f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
                        f"🆔 {BOT_USERNAME}",
                reply_to_message_id=get_effective_message_id(update),
                parse_mode=ParseMode.MARKDOWN
            )

        return

    await message.reply_text(
        f"{generate_music_info(tag_editor_context).format('')}"
        f"{t(lp.CLICK_DONE_MESSAGE, lang)}\n\n"
        f"🆔 {BOT_USERNAME}",
        reply_to_message_id=get_effective_message_id(update),
    )


async def finish_editing_tags(update: Update, context: CallbackContext) -> None:
    """
    Handles ``/finish`` command.

    This function saves the tags to the music file and uploads it with a caption containing its metadata, and updates
    the chat action to indicate that the bot uploading an audio file. It also resets all the user's data.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    message = get_message(update)
    user_data = get_user_data(context)

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.UPLOAD_VOICE
    )

    music_path = user_data['music_path']
    music_tags = user_data['tag_editor']
    art_path = music_tags.get('art_path')
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
        await message.reply_text(
            t(lp.ERR_ON_UPDATING_TAGS, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.error("Error on updating tags for file %s's file.", music_path, exc_info=True)
        return

    try:
        possible_art = None

        if new_art_path or art_path:
            with open(new_art_path if new_art_path else art_path, "rb") as art:
                possible_art = art.read()

        with open(music_path, 'rb') as music_file:
            await context.bot.send_audio(
                audio=music_file,
                thumbnail=possible_art,
                duration=user_data['music_duration'],
                chat_id=get_chat_id(update),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data['music_message_id']
            )
    except (TelegramError, BaseException) as error:
        await message.reply_text(
            t(lp.ERR_ON_UPLOADING, lang),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    reset_user_data_context(get_effective_user_id(update), user_data)


async def ask_for_tag(update: Update, context: CallbackContext) -> None:
    """
    Asks the user to input a value based on the tag that they just selected.

    It first checks if the user has started the bot, and if so, it asks for a value; otherwise, it sends the default
    message.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    lang = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, lang)

        return

    message_text = get_message_text(update)

    if re.match('^(🎵 Title|🎵 عنوان)$', message_text):
        await ask_for_title(update, user_data, lang)

        return

    if re.match('^(🗣 Artist|🗣 خواننده)$', message_text):
        await ask_for_artist(update, user_data, lang)

        return

    if re.match('^(🎼 Album|🎼 آلبوم)$', message_text):
        await ask_for_album(update, user_data, lang)

        return

    if re.match('(🖼 Album Art|🖼 عکس آلبوم)$', message_text):
        await ask_for_album_art(update, user_data, lang)

        return

    if re.match('^(🎹 Genre|🎹 ژانر)$', message_text):
        await ask_for_genre(update, user_data, lang)

        return

    if re.match('^(📅 Year|📅 سال)$', message_text):
        await ask_for_year(update, user_data, lang)

        return

    if re.match('^(💿 Disk Number|💿 شماره دیسک)$', message_text):
        await ask_for_disknumber(update, user_data, lang)

        return

    if re.match('^(▶️ Track Number|▶️ شماره ترک)$', message_text):
        await ask_for_tracknumber(update, user_data, lang)

        return


class TagEditorModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``TagEditor`` module, so that they can be used to respond to
        messages sent to the bot.
        """
        add_handler(CommandHandler('done', finish_editing_tags))
        add_handler(CommandHandler('preview', display_preview))

        add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

        add_handler(MessageHandler(
            (filters.Regex('^(🎵 Tag Editor)$') | filters.Regex('^(🎵 تغییر تگ ها)$')),
            ask_which_tag_to_edit)
        )

        add_handler(MessageHandler(
            (
                    filters.Regex('^(🎵 Title)$') | filters.Regex('^(🎵 عنوان)$') |
                    filters.Regex('^(🗣 Artist)$') | filters.Regex('^(🗣 خواننده)$') |
                    filters.Regex('^(🎼 Album)$') | filters.Regex('^(🎼 آلبوم)$') |
                    filters.Regex('^(🖼 Album Art)$') | filters.Regex('^(🖼 عکس آلبوم)$') |
                    filters.Regex('^(🎹 Genre)$') | filters.Regex('^(🎹 ژانر)$') |
                    filters.Regex('^(📅 Year)$') | filters.Regex('^(📅 سال)$') |
                    filters.Regex('^(💿 Disk Number)$') | filters.Regex('^(💿 شماره دیسک)$') |
                    filters.Regex('^(▶️ Track Number)$') | filters.Regex('^(▶️ شماره ترک)$')),
            ask_for_tag)
        )
