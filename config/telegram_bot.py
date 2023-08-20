from telegram import ParseMode
from telegram.ext import Defaults, PicklePersistence, Updater

from config.envs import BOT_TOKEN

defaults = Defaults(parse_mode=ParseMode.MARKDOWN, timeout=120)
persistence = PicklePersistence('persistence_storage')

updater = Updater(BOT_TOKEN, persistence=persistence, defaults=defaults)
add_handler = updater.dispatcher.add_handler
