import os
from html import (
    escape as html_escape,
)

import music_tag
from telegram import (
    Update,
)
from telegram.ext._utils.types import (
    UD,
)

from modules.core.utils import (
    generate_start_over_keyboard,
)
from modules.tag_editor.utils import (
    generate_tag_editor_keyboard,
)
from utils import (
    get_effective_user_id,
    get_user_language_or_fallback,
    logger,
    t,
)


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


def generate_music_info(tag_editor_context: dict, language: str) -> str:
    """
    Returns the metadata of a music as an HTML string.

    :param tag_editor_context: dict: A dictionary representing the metadata of a music
    :return: str: The metadata of a music.
    """
    default_value = ''
    ctx = tag_editor_context

    def escape(val):
        return html_escape(str(val) if val is not None else default_value)

    return t(language, 'musicMetadataTemplate',
             artist=escape(ctx.get("artist")),
             title=escape(ctx.get("title")),
             album=escape(ctx.get("album")),
             genre=escape(ctx.get("genre")),
             year=escape(ctx.get("year")),
             disknumber=escape(ctx.get("disknumber")),
             tracknumber=escape(ctx.get("tracknumber")),
             )


async def ask_for_artist(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an artist name to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'artist'
    message_text = t(language, 'askForArtist')

    await update.message.reply_text(text=message_text)


async def ask_for_title(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a title to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'title'
    message_text = t(language, 'askForTitle')

    await update.message.reply_text(text=message_text)


async def ask_for_album(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an album name to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'album'
    message_text = t(language, 'askForAlbum')

    await update.message.reply_text(text=message_text)


async def ask_for_genre(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a genre to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'genre'
    message_text = t(language, 'askForGenre')

    await update.message.reply_text(text=message_text)


async def ask_for_year(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a year to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'year'
    message_text = t(language, 'askForYear')

    await update.message.reply_text(text=message_text)


async def ask_for_album_art(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for an album art to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'album_art'
    message_text = t(language, 'askForAlbumArt')

    await update.message.reply_text(text=message_text)


async def remove_album_art(update: Update, user_data: UD, language: str) -> None:
    """
    Removes the album art from the music file. It first creates a temp file, then it replaces it.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    tag_editor_keyboard = generate_tag_editor_keyboard(language)
    user_data['tag_editor']['current_tag'] = 'remove_album'

    temp_path = user_data.get('music_path') + "_temp.mp3"
    return_code = os.system(f"ffmpeg -i {user_data.get('music_path')} -map 0:a -c:a copy {temp_path} -y")
    user_data['tag_editor']['new_art_path'] = None
    user_data['tag_editor']['art_path'] = None

    if return_code == 0:
        os.replace(temp_path, user_data.get('music_path'))
        reply_message = f"{t(language, 'done')} " \
                        f"{t(language, 'clickPreviewMessage')} " \
                        f"{t(language, 'or').upper()}" \
                        f" {t(language, 'clickDoneMessage').lower()}"

        await update.message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)


async def ask_for_disknumber(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a disknumber to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'disknumber'
    message_text = t(language, 'askForDiskNumber')

    await update.message.reply_text(text=message_text)


async def ask_for_tracknumber(update: Update, user_data: UD, language: str) -> None:
    """
    Asks the user for a track number to save into their file.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    :param language: str: The language to ask
    """
    user_data['tag_editor']['current_tag'] = 'tracknumber'
    message_text = t(language, 'askForTrackNumber')

    await update.message.reply_text(text=message_text)


async def read_and_store_music_tags(update: Update, user_data: UD) -> None:
    """
    Reads the tags of a music file and stores them in the user's ``user_data`` dictionary.

    :param update: Update: The ``update`` object
    :param user_data: UD: The ``user_data`` object
    """
    user_id = get_effective_user_id(update)
    file_download_path = user_data['music_path']
    language = get_user_language_or_fallback(user_data)

    try:
        music = music_tag.load_file(file_download_path)
    except (OSError, NotImplementedError):
        await update.message.reply_text(
            text=t(language, 'errOnReadingTags'),
            reply_markup=generate_start_over_keyboard(language)
        )

        logger.error(
            "Error on reading the tags %s's file. File path: %s",
            user_id,
            file_download_path,
            exc_info=True
        )

        return

    artist = music.get('artist')
    title = music.get('title')
    album = music.get('album')
    genre = music.get('genre')

    raw = getattr(music, "raw", {}) or {}
    year = raw.get('year')
    disknumber = raw.get('disknumber')
    tracknumber = raw.get('tracknumber')

    art = None

    try:
        possible_art = music['artwork']

        if possible_art:
            art = possible_art
    except KeyError:
        pass

    if not art:
        thumbnail = getattr(getattr(update.message, "audio", None), "thumbnail", None)

        if thumbnail:
            thumbnail_path = f"{file_download_path}.thumb.jpg"
            thumbnail_file = await update.get_bot().get_file(file_id=thumbnail.file_id)

            await thumbnail_file.download_to_drive(thumbnail_path)

            with open(thumbnail_path, "rb") as art_file:
                art = art_file.read()

            os.remove(thumbnail_path)

    tag_editor_context = user_data['tag_editor']
    tag_editor_context['artist'] = str(artist or "")
    tag_editor_context['title'] = str(title or "")
    tag_editor_context['album'] = str(album or "")
    tag_editor_context['genre'] = str(genre or "")
    tag_editor_context['year'] = str(year or "")
    tag_editor_context['disknumber'] = str(disknumber or "")
    tag_editor_context['tracknumber'] = str(tracknumber or "")

    if art:
        tag_editor_context['art_path'] = f"{file_download_path}.jpg"

        with open(tag_editor_context['art_path'], 'wb') as art_file:
            art_file.write(art.first.data if hasattr(art, "first") else art)
    else:
        tag_editor_context.pop('art_path', None)
