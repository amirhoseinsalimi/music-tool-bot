#!/usr/bin/env python

import logging
import os
import re
import socket
import sys
from datetime import datetime

from config.envs import APP_ENV, DEBUGGER, DEBUGGER_HOST, DEBUGGER_PORT, DEBUGGER_SUSPEND
from config.telegram_bot import app
from modules.admin import register as register_admin
from modules.bitrate_changer import register as register_bitrate_changer
from modules.core import register as register_core
from modules.cutter import register as register_cutter
from modules.donation import register as register_donation
from modules.tag_editor import register as register_tag_editor
from modules.voice_converter import register as register_voice_converter
from utils import logger


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
    if DEBUGGER:
        debugger_host = resolve_debugger_host()

        print(f"Debugger enabled. Connecting to {debugger_host}:{DEBUGGER_PORT}")

        try:
            import pydevd_pycharm as pydevd

            pydevd.settrace(
                debugger_host,
                port=DEBUGGER_PORT,
                suspend=DEBUGGER_SUSPEND
            )
        except ImportError as e:
            print("Debugger not attached. pydevd_pycharm not found:", e)
        except Exception as e:
            print(
                f"Debugger not attached. Failed to connect to "
                f"{debugger_host}:{DEBUGGER_PORT}:",
                e
            )
    else:
        print("Debugger disabled. Set DEBUGGER=true to enable PyCharm attach.")

    if APP_ENV == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    now = datetime.now()
    now = re.sub(':', '_', str(now))
    os.makedirs("logs", exist_ok=True)

    output_file_handler = logging.FileHandler(f"logs/{now}.log", encoding='UTF-8')
    stdout_handler = logging.StreamHandler(sys.stdout)

    logger.addHandler(output_file_handler)
    logger.addHandler(stdout_handler)

    app.run_polling()
    app.idle()


if __name__ == '__main__':
    register_admin(app.add_handler)
    register_bitrate_changer(app.add_handler)
    register_cutter(app.add_handler)
    register_donation(app.add_handler)
    register_tag_editor(app.add_handler)
    register_voice_converter(app.add_handler)
    register_core(app.add_handler)

    main()
