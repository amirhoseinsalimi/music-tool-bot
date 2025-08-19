from io import BytesIO
from typing import Optional

import whisper
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, filters, MessageHandler

from config.modules import Module
from config.telegram_bot import add_handler
from database.models.user import User
from utils import (
    get_effective_user_id,
    get_user_data,
    get_message,
    get_user_language_or_fallback,
    t,
    delete_file,
    reset_user_data_context,
    generate_start_over_keyboard,
    set_current_module,
    reply_default_message,
    is_user_data_empty,
    logger
)

model = whisper.load_model("turbo")

LANGUAGE_CODES = {
    "en": "English",
    "fa": "Persian",
    "ru": "Russian",
    "ar": "Arabic",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "tr": "Turkish",
    "hi": "Hindi",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

MAX_TELEGRAM = 4000


def insert_newlines(text: str) -> str:
    text = text.replace(",", ",\n").replace(".", ".\n")
    lines = [line.strip() for line in text.splitlines()]

    return "\n".join(lines)


def chunk_text(string: str, limit: int = MAX_TELEGRAM):
    parts = []

    while string:
        if len(string) <= limit:
            parts.append(string)

            break

        cut = string.rfind("\n", 0, limit)

        if cut == -1:
            cut = string.rfind(" ", 0, limit)

        if cut == -1:
            cut = limit

        parts.append(string[:cut])
        string = string[cut:].lstrip("\n ")

    return parts


async def send_text_or_file(message, text: str, language: str, caption: Optional[str] = None,
                            filename: str = "lyrics.txt"):
    start_over_button_keyboard = generate_start_over_keyboard(language)

    if len(text) <= MAX_TELEGRAM:
        await message.reply_text(text, disable_web_page_preview=True, reply_markup=start_over_button_keyboard)

        return

    parts = chunk_text(text)

    if len(parts) > 6:
        bio = BytesIO(text.encode("utf-8"))
        bio.name = filename

        await message.reply_document(document=bio, caption=caption or "Lyrics")
    else:
        if caption:
            await message.reply_text(caption, disable_web_page_preview=True)

        for i in range(len(parts)):
            if len(parts) == i + 1:
                await message.reply_text(parts[i], disable_web_page_preview=True,
                                         reply_markup=start_over_button_keyboard)

                continue

            await message.reply_text(parts[i], disable_web_page_preview=True)


async def show_language_selector(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    language = get_user_language_or_fallback(user_data)

    set_current_module(user_data, Module.Lyrics)

    buttons = [
        [KeyboardButton(LANGUAGE_CODES[code]), KeyboardButton(LANGUAGE_CODES[next_code])]
        for code, next_code in zip(list(LANGUAGE_CODES)[0::2], list(LANGUAGE_CODES)[1::2])
    ]

    if len(LANGUAGE_CODES) % 2 != 0:
        buttons.append([KeyboardButton(LANGUAGE_CODES[list(LANGUAGE_CODES)[-1]])])

    buttons.append([KeyboardButton(t(language, 'btnBack'))])

    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        text=f"{t(language, 'lyricsSelectLanguageHelp')}\n",
        reply_markup=keyboard
    )


async def handle_language_selection(update: Update, context: CallbackContext) -> None:
    user_data = get_user_data(context)
    user_id = get_effective_user_id(update)
    user = User.where('user_id', '=', user_id).first()
    message = get_message(update)
    language = get_user_language_or_fallback(user_data)

    if is_user_data_empty(user_data):
        await reply_default_message(update, language)

        return

    if not getattr(user, "premium_expires_at", None):
        await message.reply_text(text=f"{t(language, 'premiumFeatureMessageAdmin')}\n")

        return

    music_path = user_data.get("music_path")

    if not music_path:
        await message.reply_text("❌ No audio found. Please send a song first.")

        return

    selected_name = update.message.text.strip()
    language_code = None

    for code, name in LANGUAGE_CODES.items():
        if selected_name.startswith(name):
            language_code = code

            break

    if not language_code:
        await message.reply_text(t(language, "invalidLanguageSelection"))

        return

    try:
        result = model.transcribe(
            music_path,
            language=language_code,
            task="transcribe",
            condition_on_previous_text=False,
            temperature=0.0,
            beam_size=5,
            patience=1.0,
            compression_ratio_threshold=2.2,
            logprob_threshold=-0.4,
            no_speech_threshold=0.80,
        )

        text = insert_newlines(result.get("text", "").strip())
        detected = f"{t(language, 'lyricsLanguageChosen')}: {LANGUAGE_CODES[language_code]} ({language_code})"
        reply = f"{detected}\n\n{text}" if text else detected

        await send_text_or_file(message, reply, caption=detected, filename="lyrics.txt", language=language)

    except Exception as error:
        start_over_button_keyboard = generate_start_over_keyboard(language)

        await message.reply_text(
            text=t(language, 'errOnUploading'),
            reply_markup=start_over_button_keyboard
        )

        logger.exception("Telegram error: %s", error)

    delete_file(music_path)

    reset_user_data_context(get_effective_user_id(update), user_data)


class LyricsModule:
    @staticmethod
    def register():
        """
        Registers all the handlers that are defined in ``Lyrics`` module, so that they can be used to respond
        to messages sent to the bot.
        """
        add_handler(MessageHandler(
            (
                    filters.Regex(r'^📝 Lyrics \(AI ✨\)$') |
                    filters.Regex(r'^📝 متن ترانه \(هوش مصنوعی ✨\)$')
            ),
            show_language_selector)
        )

        add_handler(MessageHandler(
            filters.TEXT & filters.Regex("^(" + "|".join(LANGUAGE_CODES.values()) + ")$"),
            handle_language_selection)
        )
