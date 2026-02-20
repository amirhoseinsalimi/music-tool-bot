#!/usr/bin/env python

import re
import sys
from datetime import datetime

from config.envs import DEBUGGER
from config.telegram_bot import app
from modules.admin import register as register_admin
from modules.bitrate_changer import register as register_bitrate_changer
from modules.core import register as register_core
from modules.cutter import register as register_cutter
from modules.donation import register as register_donation
from modules.tag_editor import register as register_tag_editor
from modules.voice_converter import register as register_voice_converter
from utils import logger, logging


def main():
    if DEBUGGER.lower() == "true" or DEBUGGER == "1":
        try:
            import pydevd_pycharm as pydevd

            pydevd.settrace(
                '172.17.0.1',
                port=5400,
                stdoutToServer=True,
                stderrToServer=True,
                suspend=False
            )
        except ImportError as e:
            print("Debugger not attached. pydevd_pycharm not found:", e)

    now = datetime.now()
    now = re.sub(':', '_', str(now))

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
