from telegram.ext import Application

from config.envs import BOT_TOKEN

app = Application.builder().token(BOT_TOKEN).build()

add_handler = app.add_handler