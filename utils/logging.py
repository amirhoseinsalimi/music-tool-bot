import logging
import os
import shlex
import subprocess
import sys
from datetime import datetime

APP_LOGGER_NAME = "music_tool_bot"
FFMPEG_LOGGER_NAME = f"{APP_LOGGER_NAME}.ffmpeg"

logger = logging.getLogger(APP_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
ffmpeg_logger = logging.getLogger(FFMPEG_LOGGER_NAME)

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str | None = None) -> logging.Logger:
    if not name:
        return logger

    module_name = name if name.startswith(APP_LOGGER_NAME) else f"{APP_LOGGER_NAME}.{name}"

    return logging.getLogger(module_name)


def configure_logging() -> None:
    if getattr(logger, "_music_tool_bot_logging_configured", False):
        return

    logging.getLogger().setLevel(logging.WARNING)
    os.makedirs("logs", exist_ok=True)

    log_file_name = datetime.now().strftime("%Y-%m-%d_%H_%M_%S.%f.log")
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    output_file_handler = logging.FileHandler(f"logs/{log_file_name}", encoding="UTF-8")
    stdout_handler = logging.StreamHandler(sys.stdout)

    output_file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    logger.addHandler(output_file_handler)
    logger.addHandler(stdout_handler)
    logger.propagate = False
    logger._music_tool_bot_logging_configured = True


def run_ffmpeg(cmd: list[str], operation: str) -> subprocess.CompletedProcess[str]:
    ffmpeg_logger.debug("Running ffmpeg for %s: %s", operation, shlex.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    for stream_name, output in (("stdout", result.stdout), ("stderr", result.stderr)):
        if not output:
            continue

        for line in output.splitlines():
            ffmpeg_logger.debug("%s %s: %s", operation, stream_name, line)

    if result.returncode != 0:
        ffmpeg_logger.error("ffmpeg command failed for %s with exit code %s", operation, result.returncode)
        raise RuntimeError(
            "ffmpeg failed.\n"
            f"Command: {shlex.join(cmd)}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    ffmpeg_logger.debug("ffmpeg command completed for %s with exit code 0", operation)

    return result
