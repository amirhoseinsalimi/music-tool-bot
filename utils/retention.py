"""Remove aged user media from the core bot's downloads directory."""

import asyncio
import logging
import stat
import time
from pathlib import Path

from config.constants import DOWNLOAD_DIR_PATH

logger = logging.getLogger(__name__)

# Run hourly and leave a full day for scheduling interruptions before day 60.
DEFAULT_FILE_RETENTION_DAYS = 20
MAX_FILE_RETENTION_DAYS = 60


def get_file_retention_days() -> int:
    """Read the owner setting, falling back to bounded environment config."""
    from runtime_controls import file_retention_days
    return file_retention_days()


FILE_RETENTION_DAYS = DEFAULT_FILE_RETENTION_DAYS


def purge_expired_downloads(root: Path = DOWNLOAD_DIR_PATH, now: float | None = None) -> int:
    current_time = time.time() if now is None else now
    cutoff = current_time - get_file_retention_days() * 86400
    removed = 0
    if not root.is_symlink() and root.is_dir():
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
    removed += purge_expired_log_files(now=current_time)
    try:
        from runtime_controls import record_retention_sweep
        record_retention_sweep(removed)
    except ImportError:
        logger.debug('Runtime controls unavailable; skipping retention sweep report')
    return removed


def purge_expired_log_files(root: Path = Path('logs'), now: float | None = None) -> int:
    """Remove aged local log files while preserving any file still open for writing."""
    cutoff = (time.time() if now is None else now) - get_file_retention_days() * 86400
    if root.is_symlink() or not root.is_dir():
        return 0
    active_logs = {
        Path(handler.baseFilename).resolve()
        for handler in logging.getLogger('music_tool_bot').handlers
        if isinstance(handler, logging.FileHandler)
    }
    removed = 0
    for path in root.iterdir():
        try:
            info = path.lstat()
            if (stat.S_ISREG(info.st_mode) and path.suffix == '.log'
                    and info.st_mtime < cutoff and path.resolve() not in active_logs):
                path.unlink()
                removed += 1
        except FileNotFoundError:
            continue
        except OSError:
            logger.exception('Could not remove aged local log file')
    return removed


async def purge_expired_downloads_job(_context) -> None:
    await asyncio.to_thread(purge_expired_downloads)
