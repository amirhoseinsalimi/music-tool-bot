"""Remove aged user media from the core bot's downloads directory."""

import asyncio
import logging
import stat
import time
from pathlib import Path

from config.constants import DOWNLOAD_DIR_PATH

logger = logging.getLogger(__name__)

# Run hourly and leave a full day for scheduling interruptions before day 60.
FILE_RETENTION_DAYS = 59


def purge_expired_downloads(root: Path = DOWNLOAD_DIR_PATH, now: float | None = None) -> int:
    cutoff = (time.time() if now is None else now) - FILE_RETENTION_DAYS * 86400
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
