"""Read-only inventory and descriptor-based downloads from the bot's retained storage."""

import errno
import os
import stat
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping

from .exceptions import BridgeError
from .utils import parse_file_filters, validate_basename, validate_telegram_id

MAX_SCAN_ENTRIES = 100000
MAX_SCAN_SECONDS = 5
CHUNK_SIZE = 65536
MISSING_ENTRY_ERRORS = {errno.ENOENT, errno.ENOTDIR, errno.ELOOP}
ScanBudget = tuple[Iterator[int], float]


@dataclass
class FileDownload:
    """Owns an already authorized file descriptor and its observed length."""

    stream: BinaryIO
    size: int
    basename: str

    def __iter__(self) -> Iterator[bytes]:
        """Streams bounded chunks and closes the descriptor on completion or cancellation."""
        remaining = self.size

        try:
            while remaining:
                chunk = self.stream.read(min(CHUNK_SIZE, remaining))

                if not chunk:
                    raise OSError('Stored file changed during download')

                remaining -= len(chunk)
                yield chunk
        finally:
            self.close()

    def close(self) -> None:
        """Closes the file even when the WSGI server cancels an unconsumed response."""
        self.stream.close()


class FileStore:
    """Lists regular retained files and rejects links, special files and unsafe paths."""

    def __init__(self, root: Path) -> None:
        """
        Selects the existing downloads directory without creating or modifying it.

        :param root: Path: The bot-owned downloads directory
        """
        self.root = root

    def list_files(self, params: Mapping[str, str]) -> dict[str, Any]:
        """
        Returns a filtered page sorted by observed modification time, newest first.

        :param params: Mapping[str, str]: Search, exact Telegram ID and pagination filters
        :raises BridgeError: Filters are invalid or the scan exceeds its entry budget
        :return: dict[str, Any]: Files, total, page and page size from this filesystem scan
        """
        query, telegram_id, page, page_size = parse_file_filters(params=params)
        files = self._scan(query=query, telegram_id=telegram_id)
        files.sort(key=lambda row: (-row['modifiedNs'], row['telegramId'], row['basename']))
        total = len(files)
        page = min(page, max(1, (total + page_size - 1) // page_size))
        offset = (page - 1) * page_size
        rows = files[offset:offset + page_size]

        for row in rows:
            del row['modifiedNs']

        return {'files': rows, 'total': total, 'page': page, 'pageSize': page_size}

    def open_download(self, params: Mapping[str, str]) -> FileDownload:
        """
        Opens a regular file through anchored, non-symlink directory descriptors.

        :param params: Mapping[str, str]: Exact Telegram ID and stored basename
        :raises BridgeError: Identifiers are invalid or the retained file is absent/unsafe
        :return: FileDownload: The opened descriptor, observed length and stored basename
        """
        if set(params) != {'telegramId', 'basename'}:
            raise BridgeError(status=400, message='Specify Telegram ID and stored basename')

        telegram_id = validate_telegram_id(value=params['telegramId'])
        basename = validate_basename(value=params['basename'])

        with self._directory(path=self.root) as root_fd:
            try:
                with self._directory(path=telegram_id, parent=root_fd) as user_fd:
                    descriptor = os.open(
                        basename,
                        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        dir_fd=user_fd,
                    )
            except OSError as error:
                if error.errno in MISSING_ENTRY_ERRORS:
                    raise BridgeError(status=404, message='Stored file not found') from error

                raise

        with ExitStack() as cleanup:
            cleanup.callback(os.close, descriptor)
            metadata = os.fstat(descriptor)

            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise BridgeError(status=404, message='Stored file not found')

            stream = os.fdopen(descriptor, 'rb')
            cleanup.pop_all()

            return FileDownload(stream=stream, size=metadata.st_size, basename=basename)

    @staticmethod
    @contextmanager
    def _directory(path: Path | str, parent: int | None = None) -> Iterator[int]:
        """Anchors a directory without following its final component if it is a symlink."""
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)

        try:
            yield descriptor
        finally:
            os.close(descriptor)

    @staticmethod
    def _entries(descriptor: int, budget: ScanBudget) -> Iterator[os.DirEntry]:
        """Bounds work across all scanned directories without materializing directory names."""
        with os.scandir(descriptor) as entries:
            for entry in entries:
                if next(budget[0], None) is None:
                    raise BridgeError(status=413, message='Too many entries; filter by Telegram ID')

                if time.monotonic() > budget[1]:
                    raise BridgeError(status=503, message='File inventory temporarily unavailable')

                yield entry

    def _scan(self, query: str, telegram_id: str) -> list[dict[str, Any]]:
        """Scans a selected user's directory or canonical user directories under the root."""
        budget = (iter(range(MAX_SCAN_ENTRIES)), time.monotonic() + MAX_SCAN_SECONDS)
        rows: list[dict[str, Any]] = []

        try:
            with self._directory(path=self.root) as root_fd:
                names = iter((telegram_id,)) if telegram_id else (
                    entry.name for entry in self._entries(descriptor=root_fd, budget=budget)
                )

                for name in names:
                    try:
                        if validate_telegram_id(value=name) != name:
                            continue
                    except BridgeError:
                        continue

                    rows.extend(self._scan_user(
                        parent=root_fd,
                        telegram_id=name,
                        query=query,
                        budget=budget,
                    ))
        except FileNotFoundError:
            # A fresh bot data volume has no downloads directory until its first upload.
            return []

        return rows

    def _scan_user(
        self,
        parent: int,
        telegram_id: str,
        query: str,
        budget: ScanBudget,
    ) -> list[dict[str, Any]]:
        """Skips concurrently removed entries and unsafe file types, preserving genuine errors."""
        rows: list[dict[str, Any]] = []

        try:
            with self._directory(path=telegram_id, parent=parent) as user_fd:
                for entry in self._entries(descriptor=user_fd, budget=budget):
                    try:
                        basename = validate_basename(value=entry.name)
                        metadata = entry.stat(follow_symlinks=False)
                    except (BridgeError, FileNotFoundError):
                        continue

                    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                        continue

                    if query not in f'{basename} {telegram_id}'.casefold():
                        continue

                    rows.append({
                        'basename': basename,
                        'telegramId': telegram_id,
                        'bytes': metadata.st_size,
                        'modifiedAt': datetime.fromtimestamp(
                            metadata.st_mtime, tz=timezone.utc,
                        ).isoformat(),
                        'modifiedNs': metadata.st_mtime_ns,
                    })
        except OSError as error:
            if error.errno not in MISSING_ENTRY_ERRORS:
                raise

        return rows
