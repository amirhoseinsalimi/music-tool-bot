"""Remove aged user media from the core bot's downloads directory."""

import asyncio
import logging
import os
import stat
import time
from pathlib import Path

from config.constants import DOWNLOAD_DIR_PATH

logger = logging.getLogger(__name__)

# Run hourly and leave a full day for scheduling interruptions before day 60.
DEFAULT_FILE_RETENTION_DAYS = 20
MAX_FILE_RETENTION_DAYS = 60


def get_file_retention_days() -> int:
    """Read the shared retention setting with a safe bounded fallback."""
    raw_value = os.getenv("FILE_RETENTION_DAYS", str(DEFAULT_FILE_RETENTION_DAYS))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid FILE_RETENTION_DAYS; using default")
        return DEFAULT_FILE_RETENTION_DAYS
    if value < 1:
        logger.warning("FILE_RETENTION_DAYS below minimum; using 1")
        return 1
    if value > MAX_FILE_RETENTION_DAYS:
        logger.warning("FILE_RETENTION_DAYS above maximum; using %s", MAX_FILE_RETENTION_DAYS)
        return MAX_FILE_RETENTION_DAYS
    return value


FILE_RETENTION_DAYS = DEFAULT_FILE_RETENTION_DAYS


def purge_expired_downloads(root: Path = DOWNLOAD_DIR_PATH, now: float | None = None) -> int:
    cutoff = (time.time() if now is None else now) - get_file_retention_days() * 86400
    if root.is_symlink() or not root.is_dir():
        return 0
    removed = 0
    for user_dir in root.iterdir():
        if user_dir.is_symlink() or not user_dir.is_dir() or not user_dir.name.isdecimal():
            continue
        for path in user_dir.iterdir():
            try:
                info = path.lstat()
                if stat.S_ISREG(info.st_mode) and info.st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
            except OSError:
                logger.exception('Could not remove aged core media file')
    return removed


async def purge_expired_downloads_job(_context) -> None:
    await asyncio.to_thread(purge_expired_downloads)
