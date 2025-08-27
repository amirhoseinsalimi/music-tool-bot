from telegram.constants import ParseMode
from telegram.ext import Application, Defaults

from config.envs import BOT_TOKEN

defaults = Defaults(parse_mode=ParseMode.MARKDOWN_V2)

app = (
    Application.builder()
    .token(BOT_TOKEN)
    .defaults(defaults)
    .concurrent_updates(False)
    .build()
)

add_handler = app.add_handler
