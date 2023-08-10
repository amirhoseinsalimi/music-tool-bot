#!/usr/bin/env python

import re
import sys
from datetime import datetime

from modules import CoreModule, TagEditorModule, AdminModule, VoiceConverterModule, BitrateChangerModule, CutterModule

from config.telegram import updater
from utils.logging import *

now = datetime.now()
now = re.sub(':', '_', str(now))

output_file_handler = logging.FileHandler(f"logs/{now}.log", encoding='UTF-8')
stdout_handler = logging.StreamHandler(sys.stdout)

logger.addHandler(output_file_handler)
logger.addHandler(stdout_handler)


def main():
    updater.start_polling()
    updater.idle()


print(__name__)

if __name__ == '__main__':
    VoiceConverterModule().register()
    BitrateChangerModule().register()
    TagEditorModule().register()
    CutterModule().register()

    AdminModule().register()
    CoreModule().register()

    main()
