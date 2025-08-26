#!/usr/bin/env python

import re
import sys
from datetime import datetime

from config.envs import DEBUGGER
from config.telegram_bot import app
from modules import AdminModule, BitrateChangerModule, CoreModule, CutterModule, DonationModule, TagEditorModule, \
    VoiceConverterModule
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
    AdminModule().register()
    VoiceConverterModule().register()
    BitrateChangerModule().register()
    TagEditorModule().register()
    CutterModule().register()

    DonationModule().register()
    CoreModule().register()

    main()
