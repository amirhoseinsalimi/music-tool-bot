# pylint: disable=line-too-long
from config.envs import BTC_WALLET_ADDRESS, DOGE_WALLET_ADDRESS, ETH_WALLET_ADDRESS, SHIBA_BEP20_WALLET_ADDRESS, \
    TRX_WALLET_ADDRESS, USDT_ERC20_WALLET_ADDRESS, USDT_TRC20_WALLET_ADDRESS, ZARIN_LINK_ADDRESS, SHIBA_ERC20_WALLET_ADDRESS


def t(key: str, destination_lang: str) -> str | None:
    """
    Finds a specified key in the ``keys`` dictionary and returns the corresponding value for the given language.

    :param key: str: Specify the key in the dictionary
    :param destination_lang: str: The language to translate to
    :raises KeyError: str: Specified ``key`` doesn't exist
    :return: The translation of the ``key``
    """
    if key not in keys:
        raise KeyError("Specified key doesn't exist")

    return keys[key][destination_lang]


START_MESSAGE = "START_MESSAGE"
START_OVER_MESSAGE = "START_OVER_MESSAGE"
HELP_MESSAGE = "HELP_MESSAGE"
ABOUT_MESSAGE = "ABOUT_MESSAGE"
DEFAULT_MESSAGE = "DEFAULT_MESSAGE"
ASK_WHICH_MODULE = "ASK_WHICH_MODULE"
ASK_WHICH_TAG = "ASK_WHICH_TAG"
ASK_FOR_ALBUM = "ASK_FOR_ALBUM"
ASK_FOR_ARTIST = "ASK_FOR_ARTIST"
ASK_FOR_TITLE = "ASK_FOR_TITLE"
ASK_FOR_GENRE = "ASK_FOR_GENRE"
ASK_FOR_YEAR = "ASK_FOR_YEAR"
ASK_FOR_ALBUM_ART = "ASK_FOR_ALBUM_ART"
ASK_FOR_DISK_NUMBER = "ASK_FOR_DISK_NUMBER"
ASK_FOR_TRACK_NUMBER = "ASK_FOR_TRACK_NUMBER"
ALBUM_ART_CHANGED = "ALBUM_ART_CHANGED"
EXPECTED_NUMBER_MESSAGE = "EXPECTED_NUMBER_MESSAGE"
CLICK_PREVIEW_MESSAGE = "CLICK_PREVIEW_MESSAGE"
CLICK_DONE_MESSAGE = "CLICK_DONE_MESSAGE"
LANGUAGE_CHANGED = "LANGUAGE_CHANGED"
MUSIC_LENGTH = "MUSIC_LENGTH"
REPORT_BUG_MESSAGE = "REPORT_BUG_MESSAGE"
ERR_CREATING_USER_FOLDER = "ERR_CREATING_USER_FOLDER"
ERR_ON_DOWNLOAD_AUDIO_MESSAGE = "ERR_ON_DOWNLOAD_AUDIO_MESSAGE"
ERR_ON_DOWNLOAD_PHOTO_MESSAGE = "ERR_ON_DOWNLOAD_PHOTO_MESSAGE"
ERR_TOO_LARGE_FILE = "ERR_TOO_LARGE_FILE"
ERR_ON_READING_TAGS = "ERR_ON_READING_TAGS"
ERR_ON_UPDATING_TAGS = "ERR_ON_UPDATING_TAGS"
ERR_ON_UPLOADING = "ERR_ON_UPLOADING"
ERR_NOT_IMPLEMENTED = "ERR_NOT_IMPLEMENTED"
ERR_OUT_OF_RANGE = "ERR_OUT_OF_RANGE"
ERR_MALFORMED_RANGE = "ERR_MALFORMED_RANGE"
ERR_BEGINNING_POINT_IS_GREATER = "ERR_BEGINNING_POINT_IS_GREATER"
BTN_TAG_EDITOR = "BTN_TAG_EDITOR"
BTN_MUSIC_TO_VOICE_CONVERTER = "BTN_MUSIC_TO_VOICE_CONVERTER"
BTN_MUSIC_CUTTER = "BTN_MUSIC_CUTTER"
BTN_BITRATE_CHANGER = "BTN_BITRATE_CHANGER"
BTN_ARTIST = "BTN_ARTIST"
BTN_TITLE = "BTN_TITLE"
BTN_ALBUM = "BTN_ALBUM"
BTN_GENRE = "BTN_GENRE"
BTN_YEAR = "BTN_YEAR"
BTN_ALBUM_ART = "BTN_ALBUM_ART"
BTN_DISK_NUMBER = "BTN_DISK_NUMBER"
BTN_TRACK_NUMBER = "BTN_TRACK_NUMBER"
BTN_BACK = "BTN_BACK"
BTN_NEW_FILE = "BTN_NEW_FILE"
MUSIC_CUTTER_HELP = "MUSIC_CUTTER_HELP"
BITRATE_CHANGER_HELP = "BITRATE_CHANGER_HELP"
DONATION_MESSAGE = "DONATION_MESSAGE"
THANK_YOU_IN_ADVANCE_EN = "Thank you in advance for your support"
THANK_YOU_IN_ADVANCE_FA = "پیشاپیش از حمایتت ممنونم"
DONATE_MESSAGE_BITCOIN = "DONATE_MESSAGE_BITCOIN"
DONATE_MESSAGE_ETHEREUM = "DONATE_MESSAGE_ETHEREUM"
DONATE_MESSAGE_TRON = "DONATE_MESSAGE_TRON"
DONATE_MESSAGE_TETHER = "DONATE_MESSAGE_TETHER"
DONATE_MESSAGE_SHIBA = "DONATE_MESSAGE_SHIBA"
DONATE_MESSAGE_DOGECOIN = "DONATE_MESSAGE_DOGECOIN"
DONATE_MESSAGE_ZARINPAL = "DONATE_MESSAGE_ZARINPAL"
DONE = "DONE"
OR = "OR"
REPORT_BUG_MESSAGE_EN = "That's my fault! Please send a bug report here: @amirhoseinsalimii"
REPORT_BUG_MESSAGE_FA = "این اشتباه منه! لطفا این باگ رو از اینجا گزارش کنید: @amirhoseinsalimii"
EG_EN = "e.g."
EG_FA = "مثل"

keys = {
    START_MESSAGE: {
        "en": "Hello there! 👋\n"
              "Let's get started. Just send me a music and see how awesome I am!",
        "fa": "سلام! 👋\n"
              "خب شروع کنیم. یه موزیک برام بفرست تا ببینی چقدر خفنم!",
    },
    START_OVER_MESSAGE: {
        "en": "Send me a music and see how awesome I am!",
        "fa": "یه موزیک برام بفرست تا ببینی چقدر خفنم!",
    },
    HELP_MESSAGE: {
        "en": "It's simple! Just send or forward me an audio track, an MP3 file or a music. I'm waiting... 😁\n\n"
              "By the way, if you're having problem processing your file, please enter /new command "
              "to start over.",
        "fa": "ساده س! یه فایل صوتی، یه MP3 یا یه موزیک برام بفرست. منتظرم... 😁\n\n"
              "راستی اگر مشکلی با پردازش فایلت داری، لطفا کامند /new رو بزن تا از اول شروع کنی.",
    },
    ABOUT_MESSAGE: {
        "en": "This bot is created by @amirhoseinsalimii in Python language.\n"
              "The source code of this project is available on"
              " [GitHub](https://github.com/amirhoseinsalimi/music-tool-bot).\n\n"
              "If you have any question or feedback feel free to message me on Telegram."
              " Or if you are a developer and have an idea to make this bot better, I appreciate your"
              " PRs.\n\n",
        "fa": "این ربات توسط @amirhoseinsalimii به زبان پایتون نوشته شده است."
              " سورس این برنامه از طریق [گیت هاب](https://github.com/amirhoseinsalimi/music-tool-bot)"
              " در دسترس است.\n\n"
              "اگر سوال یا بازخوردی دارید میتونید در تلگرام بهم پیام بدید. یا اگر برنامه نویس هستید و ایده "
              "ای برای بهتر کردن این ربات دارید، از PR هاتون استقبال میکنم."
    },
    DEFAULT_MESSAGE: {
        "en": "Send or forward me an audio track, an MP3 file or a music. I'm waiting... 😁",
        "fa": "یه فایل صوتی، یه MP3 یا یه موزیک برام بفرست... منتظرم... 😁",
    },
    ASK_WHICH_MODULE: {
        "en": "What do you want to do with this file?",
        "fa": "میخوای با این فایل چیکار کنی؟",
    },
    ASK_WHICH_TAG: {
        "en": "Which tag do you want to edit?",
        "fa": "چه تگی رو میخوای ویرایش کنی؟",
    },
    ASK_FOR_ALBUM: {
        "en": "Enter the name of the album:",
        "fa": "نام آلبوم را وارد کنید:",
    },
    ASK_FOR_ARTIST: {
        "en": "Enter the name of the artist:",
        "fa": "نام خواننده رو وارد کنید:",
    },
    ASK_FOR_TITLE: {
        "en": "Enter the title:",
        "fa": "عنوان رو وارد کنید:",
    },
    ASK_FOR_GENRE: {
        "en": "Enter the genre:",
        "fa": "ژانر رو وارد کنید:",
    },
    ASK_FOR_YEAR: {
        "en": "Enter the publish year:",
        "fa": "سال انتشار رو وارد کنید:",
    },
    ASK_FOR_ALBUM_ART: {
        "en": "Send me a photo:",
        "fa": "یک عکس برام بفرست:",
    },
    ASK_FOR_DISK_NUMBER: {
        "en": "Enter the disk number:",
        "fa": "شماره دیسک را وارد کنید:",
    },
    ASK_FOR_TRACK_NUMBER: {
        "en": "Enter the track number:",
        "fa": "شماره ترک را وارد کنید:",
    },
    ALBUM_ART_CHANGED: {
        "en": "Album art changed",
        "fa": "عکس آلبوم تغییر یافت.",
    },
    EXPECTED_NUMBER_MESSAGE: {
        "en": "You entered a string instead of a number. Although this is not a problem, "
              "I guess you entered this input by mistake.",
        "fa": "شما یک متن رو به جای عدد وارد کردید. اگر چه اشکالی نداره ولی حدس میزنم"
              " اشتباهی وارد کردی."},
    CLICK_PREVIEW_MESSAGE: {
        "en": "If you want to preview your changes click /preview.",
        "fa": "اگر میخوای تغییرات رو تا الان ببینی از دستور /preview استفاده کن.",
    },
    CLICK_DONE_MESSAGE: {
        "en": "Click /done to save your changes.",
        "fa": "روی /done کلیک کن تا تغییراتت ذخیره بشن.",
    },
    LANGUAGE_CHANGED: {
        "en": "Language has been changed. If you want to change the language later, use /language command.",
        "fa": "زبان تغییر یافت. اگر میخواهید زبان را مجددا تغییر دهید، از دستور /language استفاده کنید.",
    },
    MUSIC_LENGTH: {
        "en": "The file length is {}.",
        "fa": "طول کل فایل {} است.",
    },
    REPORT_BUG_MESSAGE: {
        "en": "That's my fault! Please send a bug report here: @amirhoseinsalimii",
        "fa": "این اشتباه منه! لطفا این باگ رو از اینجا گزارش کنید: @amirhoseinsalimii",
    },
    ERR_CREATING_USER_FOLDER: {
        "en": f"Error on starting... {REPORT_BUG_MESSAGE_EN}",
        "fa": f"به مشکل خوردم... {REPORT_BUG_MESSAGE_FA}",
    },
    ERR_ON_DOWNLOAD_AUDIO_MESSAGE: {
        "en": f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE_EN}",
        "fa": f"متاسفم، نتونستم فایلت رو دانلود کنم... {REPORT_BUG_MESSAGE_FA}",
    },
    ERR_ON_DOWNLOAD_PHOTO_MESSAGE: {
        "en": f"Sorry, I couldn't download your file... {REPORT_BUG_MESSAGE_EN}",
        "fa": f"متاسفم، نتونستم فایلت رو دانلود کنم... {REPORT_BUG_MESSAGE_FA}",
    },
    ERR_TOO_LARGE_FILE: {
        "en": "This file is too big that I can process, sorry!",
        "fa": "این فایل بزرگتر از چیزی هست که من بتونم پردازش کنم، شرمنده!",
    },
    ERR_ON_READING_TAGS: {
        "en": f"Sorry, I couldn't read the tags of the file... {REPORT_BUG_MESSAGE_EN}",
        "fa": f"متاسفم، نتونستم تگ های فایل رو بخونم... {REPORT_BUG_MESSAGE_FA}",
    },
    ERR_ON_UPDATING_TAGS: {
        "en": f"Sorry, I couldn't update tags the tags of the file... {REPORT_BUG_MESSAGE_EN}",
        "fa": f"متاسفم، نتونستم تگ های فایل رو آپدیت کنم... {REPORT_BUG_MESSAGE_FA}",
    },
    ERR_ON_UPLOADING: {
        "en": "Sorry, due to network issues, I couldn't upload your file. Please try again.",
        "fa": "متاسفم. به دلیل اشکالات شبکه نتونستم فایل رو آپلود کنم. لطفا دوباره امتحان کن.",
    },
    ERR_NOT_IMPLEMENTED: {
        "en": "This feature has not been implemented yet. Sorry!",
        "fa": "این قابلیت هنوز پیاده سازی نشده. شرمنده!",
    },
    ERR_OUT_OF_RANGE: {
        "en": "The range you entered is out of the actual file duration. The file length is {}.",
        "fa": "بازه ای که انتخاب کردید خارج از طول کل فایل هست. طول کل فایل {} است.",
    },
    ERR_MALFORMED_RANGE: {
        "en": "You have entered a malformed pattern. Please try again. {}",
        "fa": "شما یک الگوی اشتباه وارد کردید. لطفا دوباره امتحان کنید. {}",
    },
    ERR_BEGINNING_POINT_IS_GREATER: {
        "en": "The ending point should be greater than starting point",
        "fa": "زمان پایان باید از زمان شروع بزرگتر باشد.",
    },
    BTN_TAG_EDITOR: {
        "en": "🎵 Tag Editor",
        "fa": "🎵 تغییر تگ ها",
    },
    BTN_MUSIC_TO_VOICE_CONVERTER: {
        "en": "🗣 Music to Voice Converter",
        "fa": "🗣 تبدیل به پیام صوتی",
    },
    BTN_MUSIC_CUTTER: {
        "en": "✂️ Music Cutter",
        "fa": "✂️ بریدن آهنگ",
    },
    BTN_BITRATE_CHANGER: {
        "en": "🎙 Bitrate Changer",
        "fa": "🎙 تغییر بیت ریت",
    },
    BTN_ARTIST: {
        "en": "🗣 Artist",
        "fa": "🗣 خواننده",
    },
    BTN_TITLE: {
        "en": "🎵 Title",
        "fa": "🎵 عنوان",
    },
    BTN_ALBUM: {
        "en": "🎼 Album",
        "fa": "🎼 آلبوم",
    },
    BTN_GENRE: {
        "en": "🎹 Genre",
        "fa": "🎹 ژانر",
    },
    BTN_YEAR: {
        "en": "📅 Year",
        "fa": "📅 سال",
    },
    BTN_ALBUM_ART: {
        "en": "🖼 Album Art",
        "fa": "🖼 عکس آلبوم",
    },
    BTN_DISK_NUMBER: {
        "en": "💿 Disk Number",
        "fa": "💿 شماره دیسک",
    },
    BTN_TRACK_NUMBER: {
        "en": "▶️ Track Number",
        "fa": "▶️ شماره ترک",
    },
    BTN_BACK: {
        "en": "🔙 Back",
        "fa": "🔙 بازگشت",
    },
    BTN_NEW_FILE: {
        "en": "🆕 New File",
        "fa": "🆕 فایل جدید",
    },
    MUSIC_CUTTER_HELP: {
        "en": "\n\nNow send me which part of the music you want to cut out?\n"
              "The file length is {}.\n\n"
              "Valid patterns are:\n"
              f"*mm:ss-mm:ss*:\n{EG_EN} 00:10-02:30\n"
              F"*ss-ss*:\n{EG_EN} 75-120\n\n"
              "- m = minute, s = second\n"
              "- Leading zeroes are optional\n"
              "- Extra spaces are ignored\n"
              "- Only English numbers are valid",
        "fa": "\n\nحالا بهم بگو کجای موزیک رو میخوای ببری؟\n"
              "طول فایل {} است.\n\n"
              "الگو های مجاز:\n"
              f"*mm:ss-mm:ss*:\n{EG_FA} 00:10-02:30\n"
              f"*ss-ss*:\n{EG_FA} 75-120\n\n"
              "- دقیقه: m، ثانیه s\n"
              "- صفرهای ابتدایی دل بخواه هستن\n"
              "- فاصله های اضافی در نظر گرفته نمیشن\n"
              "- تنها اعداد انگلیسی مجاز هستند",
    },
    BITRATE_CHANGER_HELP: {
        "en": "\n\nNow tell me at which bitrate you would like to have your file.\n"
              "You can select your desired bitrate from the menu below.\n\n",
        "fa": "\n\nحالا بهم بگو فایلت رو به چه بیت ریتی تغییر بدم؟\n"
              "از منوی زیر می‌تونی بیت ریت مورد نظرت رو انتخاب کنی.\n"
    },
    "DONATION_MESSAGE": {
        "en": f"Thank you for your interest in supporting my work. I am a "
              f"developer and I run this Telegram bot as a hobby. \nYour "
              f"donation will help me to continue developing and improving this "
              f"bot. If you would like to donate, you can use the following "
              f"methods. {THANK_YOU_IN_ADVANCE_EN}.",
        "fa": "از این‌که مایل به دونیت هستی ممنونم. من این ربات رو در "
              "اوقات فراغتم توسعه می‌دم. دونیت شما به من کمک می‌کنه تا به "
              "توسعه و بهبود این ربات ادامه بدم. اگر مایل به دونیت هستی، "
              f"از روش‌های زیر می‌تونی استفاده کنی. {THANK_YOU_IN_ADVANCE_FA}."
    },
    "DONATE_MESSAGE_BITCOIN": {
        "en": f"Here's my BTC wallet.\n\n"
              f"```{BTC_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": "این آدرس بیت‌کوین منه:\n\n"
              f"```{BTC_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_FA}.",
    },
    "DONATE_MESSAGE_ETHEREUM": {
        "en": f"Here's my ETH wallet.\n\n"
              f"```{ETH_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": "این آدرس اتریوم منه:\n\n"
              f"```{ETH_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_FA}."
    },
    "DONATE_MESSAGE_TRON": {
        "en": f"Here's my TRX wallet.\n\n"
              f"```{TRX_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": "این آدرس ترون منه:\n\n"
              f"```{TRX_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_FA}."
    },
    "DONATE_MESSAGE_TETHER": {
        "en": f"Here are my USDT wallets.\n\n"
              f"TRC20:\n```{USDT_TRC20_WALLET_ADDRESS}```\n\n"
              f"ERC20:\n```{USDT_ERC20_WALLET_ADDRESS}```\n\n"
              f"{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": f"این آدرس‌های تتر منه:\n\n"
              f"TRC20:\n```{USDT_TRC20_WALLET_ADDRESS}```\n\n"
              f"ERC20:\n```{USDT_ERC20_WALLET_ADDRESS}```\n\n"
              f"{THANK_YOU_IN_ADVANCE_FA}.",
    },
    "DONATE_MESSAGE_SHIBA": {
        "en": f"Here are my SHIB wallets.\n\n"
              f"BEP20:\n```{SHIBA_BEP20_WALLET_ADDRESS}```\n\n"
              f"ERC20:\n```{SHIBA_ERC20_WALLET_ADDRESS}```\n\n"
              f"{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": f"این آدرس شیبای منه.\n\n"
              f"BEP20:\n```{SHIBA_BEP20_WALLET_ADDRESS}```\n\n"
              f"ERC20:\n```{SHIBA_ERC20_WALLET_ADDRESS}```\n\n"
              f"{THANK_YOU_IN_ADVANCE_FA}.",
    },
    "DONATE_MESSAGE_DOGECOIN": {
        "en": f"Here's my DOGE wallet.\n\n"
              f"```{DOGE_WALLET_ADDRESS}```n\n{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": "این آدرس دوج کوین منه:\n\n"
              f"```{DOGE_WALLET_ADDRESS}```\n\n{THANK_YOU_IN_ADVANCE_FA}."
    },
    "DONATE_MESSAGE_ZARINPAL": {
        "en": f"This is meant to be for Iranian users only. If you're outside "
              f"the country and want to donate, you can choose crypto options"
              f".\n\nHere's my ZarinLink: [ZarinLink]({ZARIN_LINK_ADDRESS})\n\n"
              f"{THANK_YOU_IN_ADVANCE_EN}.",
        "fa": f"این گزینه برای کاربران ایرانی تعبیه شده. اگر خارج از ایران "
              f"هستی و مایل هستی دونیت کنی، می‌تونی از روش‌های رمزارز استفاده "
              f"کنی.\n\nاین زرین لینک من هستش: "
              f"[زرین لینک]({ZARIN_LINK_ADDRESS})\n\n"
              f"{THANK_YOU_IN_ADVANCE_FA}.",
    },
    DONE: {
        "en": "Done!",
        "fa": "انجام شد!",
    },
    OR: {
        "en": "or",
        "fa": "یا",
    },
}
