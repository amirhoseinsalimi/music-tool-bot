#!/usr/bin/env python

import logging
import os
import socket
from psycopg2 import Error as DatabaseError

from telegram import Update

from config.envs import APP_ENV, DEBUGGER, DEBUGGER_HOST, DEBUGGER_PORT, DEBUGGER_SUSPEND
from config.telegram_bot import app
from modules.admin import register as register_admin
from modules.bitrate_changer import register as register_bitrate_changer
from modules.core import register as register_core
from modules.cutter import register as register_cutter
from modules.donation import register as register_donation
from modules.tag_editor import register as register_tag_editor
from modules.voice_converter import register as register_voice_converter
from utils.logging import configure_logging, get_logger
from utils.extensions import register_optional_extension
from utils.retention import purge_expired_downloads, purge_expired_downloads_job

logger = get_logger(__name__)


def resolve_debugger_host() -> str:
    if DEBUGGER_HOST:
        return DEBUGGER_HOST

    if not os.path.exists("/.dockerenv"):
        return "127.0.0.1"

    try:
        socket.gethostbyname("host.docker.internal")

        return "host.docker.internal"
    except socket.gaierror:
        return "172.17.0.1"


def main():
    configure_logging()

    if DEBUGGER:
        debugger_host = resolve_debugger_host()

        logger.info("Debugger enabled. Connecting to %s:%s", debugger_host, DEBUGGER_PORT)

        try:
            import pydevd_pycharm as pydevd

            pydevd.settrace(
                debugger_host,
                port=DEBUGGER_PORT,
                suspend=DEBUGGER_SUSPEND
            )
        except ImportError as e:
            logger.warning("Debugger not attached. pydevd_pycharm not found: %s", e)
        except Exception as e:
            logger.warning(
                "Debugger not attached. Failed to connect to %s:%s: %s",
                debugger_host,
                DEBUGGER_PORT,
                e
            )
    else:
        logger.debug("Debugger disabled. Set DEBUGGER=true to enable PyCharm attach.")

    if APP_ENV == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    from runtime_controls import bot_settings
    try:
        bot_settings()
    except (OSError, ValueError, DatabaseError):
        logger.error("Runtime controls unavailable; controlled tools will fail closed")

    logger.info("Starting bot polling")
    logger.info("Removed %s aged core media files", purge_expired_downloads())
    app.job_queue.run_repeating(purge_expired_downloads_job, interval=3600, first=3600)
    # Temporary proxy outages must not leave startup permanently disconnected.
    app.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=-1)


if __name__ == '__main__':
    register_admin(app.add_handler)
    register_bitrate_changer(app.add_handler)
    register_cutter(app.add_handler)
    register_donation(app.add_handler)
    register_tag_editor(app.add_handler)
    register_voice_converter(app.add_handler)
    register_optional_extension(app)
    register_core(app.add_handler)

    main()
