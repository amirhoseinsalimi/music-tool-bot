import re

from persiantools import digits
from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from config.envs import BOT_USERNAME
from config.modules import Module
from modules.core.utils import generate_start_over_keyboard
from modules.tag_editor.utils import generate_tag_editor_keyboard
from utils import download_file, get_chat_id, get_effective_message_id, get_message, \
    get_message_text, get_user_data, get_user_language_or_fallback, is_user_data_empty, logger, reply_default_message, \
    reset_user_data_context, set_current_module, t, resize_image, get_file_name, upsert_user
from .service import ask_for_title, ask_for_year, remove_album_art, ask_for_genre, ask_for_tracknumber, ask_for_artist, \
    ask_for_disknumber, ask_for_album, ask_for_album_art, generate_music_info, save_tags_to_file
from .utils import did_user_select_a_tag, is_current_tag_album_art, unset_current_tag, is_current_module_tag_editor, \
    save_text_into_tag


@upsert_user
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

    language = get_user_language_or_fallback(user_data)
    tag_editor_keyboard = generate_tag_editor_keyboard(language)

    if not did_user_select_a_tag(current_tag):
        reply_message = t(language, 'askWhichTag')

        await message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)

        return

    if is_current_tag_album_art(current_tag):
        reply_message = t(language, 'askForAlbumArt')

        await message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)

        return

    message_text = digits.ar_to_fa(digits.fa_to_en(message.text))

    save_text_into_tag(
        value=message_text,
        current_tag=current_tag,
        user_data=user_data,
        is_number=current_tag in ('year', 'disknumber', 'tracknumber')
    )

    reply_message = f"{t(language, 'done')} " \
                    f"{t(language, 'clickPreviewMessage')} " \
                    f"{t(language, 'or').upper()}" \
                    f" {t(language, 'clickDoneMessage').lower()}"

    await message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)

    unset_current_tag(user_data)


@upsert_user
async def handle_photo_message(update: Update, context: CallbackContext) -> None:
    """
    This function is responsible for handling the album arts that the user wants to be saved in their file.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    music_path = user_data.get('music_path')
    message = get_message(update)

    if not music_path:
        reply_message = t(language, 'defaultMessage')

        await message.reply_text(text=reply_message, reply_markup=ReplyKeyboardRemove())

        return

    user_id = user.user_id
    current_module = user_data['current_module']
    current_tag = user_data['tag_editor']['current_tag']
    tag_editor_keyboard = generate_tag_editor_keyboard(language)

    if not is_current_module_tag_editor(current_module):
        return

    if not did_user_select_a_tag(current_tag) or not is_current_tag_album_art(current_tag):
        reply_message = t(language, 'askWhichTag')

        await message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)

        return

    try:
        file_download_path = await download_file(
            user_id=user_id,
            file_to_download=message.photo[-1],
            file_type='photo',
            context=context
        )

        user_data['tag_editor']['new_art_path'] = file_download_path
        reply_message = f"{t(language, 'albumArtChanged')} " \
                        f"{t(language, 'clickPreviewMessage')} " \
                        f"{t(language, 'or').upper()}" \
                        f" {t(language, 'clickDoneMessage').lower()}"

        await message.reply_text(text=reply_message, reply_markup=tag_editor_keyboard)
    except (ValueError, BaseException):
        await message.reply_text(text=t(language, 'errOnDownloadAudioMessage'))

        logger.error(
            "Error on downloading %s's file. File type: Photo",
            user_id,
            exc_info=True
        )

        return


@upsert_user
async def ask_which_tag_to_edit(update: Update, context: CallbackContext) -> None:
    """
    This function is called when the user has selected the `Module.TAG_EDITOR module`.
    It displays the current tags of that music file and asks which tag should be edited next.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    message = get_message(update)
    language = get_user_language_or_fallback(user_data)

    try:
        tag_editor_context = user_data['tag_editor']
    except KeyError:
        await message.reply_text(text=t(language, 'defaultMessage'))

        return

    set_current_module(user_data, Module.TAG_EDITOR)

    art_path = tag_editor_context.get('art_path')
    tag_editor_context['current_tag'] = ''

    tag_editor_keyboard = generate_tag_editor_keyboard(language)

    if art_path:
        with open(art_path, 'rb') as art_file:
            await message.reply_photo(
                photo=art_file,
                caption=f"{generate_music_info(tag_editor_context, language)}"
                        f"\n\n🆔 {BOT_USERNAME}",
                reply_to_message_id=get_effective_message_id(update),
                reply_markup=tag_editor_keyboard,
            )
    else:
        await message.reply_text(
            text=f"{generate_music_info(tag_editor_context, language)}"
                 f"\n\n🆔 {BOT_USERNAME}",
            reply_to_message_id=get_effective_message_id(update),
            reply_markup=tag_editor_keyboard
        )


@upsert_user
async def display_preview(update: Update, context: CallbackContext) -> None:
    """
    Handles ``/preview`` command. Displays a caption with all the information about the music file, and if there's
    an album art, it also displays that.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    message = get_message(update)
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    if not user_data.get('music_path'):
        await reply_default_message(update, language)

        return

    tag_editor_context = user_data['tag_editor']
    art_path = tag_editor_context.get('art_path')
    new_art_path = tag_editor_context.get('new_art_path')

    if art_path or new_art_path:
        with open(new_art_path if new_art_path else art_path, "rb") as art_file:
            await message.reply_photo(
                photo=art_file,
                caption=f"{generate_music_info(tag_editor_context, language)}"
                        f"\n\n{t(language, 'clickDoneMessage')}"
                        f"\n\n🆔 {BOT_USERNAME}",
                reply_to_message_id=get_effective_message_id(update),
            )

        return

    await message.reply_text(
        text=f"{generate_music_info(tag_editor_context, language)}"
             f"\n\n{t(language, 'clickDoneMessage')}"
             f"\n\n🆔 {BOT_USERNAME}",
        reply_to_message_id=get_effective_message_id(update),
    )


@upsert_user
async def finish_editing_tags(update: Update, context: CallbackContext) -> None:
    """
    Handles ``/finish`` command.

    This function saves the tags to the music file and uploads it with a caption containing its metadata, and updates
    the chat action to indicate that the bot uploading an audio file. It also resets all the user's data.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user = context.user_data['user']
    user_id = user.user_id
    user_data = get_user_data(context)
    message = get_message(update)

    music_path = user_data.get('music_path')
    language = get_user_language_or_fallback(user_data)

    if not music_path:
        await reply_default_message(update, language)

        return

    await context.bot.send_chat_action(
        chat_id=get_chat_id(update),
        action=ChatAction.UPLOAD_VOICE
    )

    music_tags = user_data['tag_editor']
    art_path = music_tags.get('art_path')
    new_art_path = music_tags.get('new_art_path')

    start_over_button_keyboard = generate_start_over_keyboard(language)

    try:
        save_tags_to_file(
            file=music_path,
            tags=music_tags,
            new_art_path=new_art_path
        )
    except (OSError, BaseException):
        await message.reply_text(
            text=t(language, 'errOnUpdatingTags'),
            reply_markup=start_over_button_keyboard
        )

        logger.error("Error on updating tags for file %s's file.", music_path, exc_info=True)

        return

    try:
        possible_art = None

        if new_art_path or art_path:
            original_art_path = new_art_path if new_art_path else art_path
            resized_art_path = f"{original_art_path}_resized.jpg"

            resize_image(original_art_path, resized_art_path)

            with open(resized_art_path, "rb") as art:
                possible_art = art.read()

        with open(music_path, "rb") as music_file:
            await context.bot.send_audio(
                audio=music_file,
                thumbnail=possible_art,
                duration=user_data["music_duration"],
                chat_id=get_chat_id(update),
                performer=music_tags.get('artist'),
                title=music_tags.get('title'),
                filename=get_file_name(music_tags),
                caption=f"🆔 {BOT_USERNAME}",
                reply_markup=start_over_button_keyboard,
                reply_to_message_id=user_data["music_message_id"],
            )
    except (TelegramError, BaseException) as error:
        await message.reply_text(
            text=t(language, 'errOnUploading'),
            reply_markup=start_over_button_keyboard
        )
        logger.exception("Telegram error: %s", error)

    reset_user_data_context(user_id, user_data)


@upsert_user
async def ask_for_tag(update: Update, context: CallbackContext) -> None:
    """
    Asks the user to input a value based on the tag that they just selected.

    It first checks if the user has started the bot, and if so, it asks for a value; otherwise, it sends the default
    message.

    :param update: Update: The ``update`` object
    :param context: CallbackContext: The ``context`` object
    """
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, language)

        return

    message_text = get_message_text(update)

    if re.match('^(🎵 Title|🎵 عنوان|🎵 Название|🎵 Título|🎵 Titre|🎵 العنوان)$', message_text):
        await ask_for_title(update, user_data, language)
        return

    if re.match('^(🗣 Artist|🗣 آرتیست|🗣 Исполнитель|🗣 Artista|🗣 Artiste|🗣 الفنان)$', message_text):
        await ask_for_artist(update, user_data, language)
        return

    if re.match('^(🎼 Album|🎼 آلبوم|🎼 Альбом|🎼 Álbum|🎼 Album|🎼 الألبوم)$', message_text):
        await ask_for_album(update, user_data, language)
        return

    if re.match('^(🖼 Album Art|🖼 عکس آلبوم|🖼 Обложка альбома|🖼 Portada del Álbum|🖼 Pochette|🖼 صورة الألبوم)$',
                message_text):
        await ask_for_album_art(update, user_data, language)
        return

    if re.match(
            '^(🧹 Remove Album Art|🧹 حذف عکس آلبوم|🧹 Удалить обложку|🧹 Eliminar Portada|🧹 Supprimer la pochette|🧹 إزالة صورة الألبوم)$',
            message_text):
        await remove_album_art(update, user_data, language)
        return

    if re.match('^(🎹 Genre|🎹 سبک|🎹 Жанр|🎹 Género|🎹 Genre|🎹 النوع)$', message_text):
        await ask_for_genre(update, user_data, language)
        return

    if re.match('^(📅 Year|📅 سال|📅 Год|📅 Año|📅 Année|📅 السنة)$', message_text):
        await ask_for_year(update, user_data, language)
        return

    if re.match('^(💿 Disk Number|💿 شماره دیسک|💿 Номер диска|💿 Número de Disco|💿 Numéro de disque|💿 رقم القرص)$',
                message_text):
        await ask_for_disknumber(update, user_data, language)
        return

    if re.match('^(▶️ Track Number|▶️ شماره ترک|▶️ Номер трека|▶️ Número de Pista|▶️ Numéro de piste|▶️ رقم المقطع)$',
                message_text):
        await ask_for_tracknumber(update, user_data, language)
        return
