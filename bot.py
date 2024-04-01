#!/usr/bin/env python

import re
import sys
from datetime import datetime

from config.telegram_bot import app
from modules import AdminModule, BitrateChangerModule, CoreModule, CutterModule, DonationModule, TagEditorModule, \
    VoiceConverterModule
from utils import logger, logging


def main():
    now = datetime.now()
    now = re.sub(':', '_', str(now))

    output_file_handler = logging.FileHandler(f"logs/{now}.log", encoding='UTF-8')
    stdout_handler = logging.StreamHandler(sys.stdout)

    logger.addHandler(output_file_handler)
    logger.addHandler(stdout_handler)

    app.run_polling()
    app.idle()


if __name__ == '__main__':
    VoiceConverterModule().register()
    BitrateChangerModule().register()
    TagEditorModule().register()
    CutterModule().register()

    DonationModule().register()
    AdminModule().register()
    CoreModule().register()

    main()
