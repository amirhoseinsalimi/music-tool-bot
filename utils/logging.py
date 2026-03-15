import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    if getattr(logger, "_music_tool_bot_logging_configured", False):
        return

    os.makedirs("logs", exist_ok=True)

    log_file_name = datetime.now().strftime("%Y-%m-%d_%H_%M_%S.%f.log")
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    output_file_handler = logging.FileHandler(f"logs/{log_file_name}", encoding="UTF-8")
    stdout_handler = logging.StreamHandler(sys.stdout)

    output_file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    logger.addHandler(output_file_handler)
    logger.addHandler(stdout_handler)
    logger._music_tool_bot_logging_configured = True
