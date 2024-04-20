from telegram.ext import Application, Defaults
from telegram.constants import ParseMode

from config.envs import BOT_TOKEN

defaults = Defaults(parse_mode=ParseMode.MARKDOWN_V2)

app = Application.builder().token(BOT_TOKEN).build()

add_handler = app.add_handler