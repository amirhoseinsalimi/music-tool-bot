"""Filesystem boundaries, authorization and retained download resource regressions."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from pg_support import PostgresFixture
from test_bridge import PostgreSQLConnection

from postgres_storage import Database
from admin_bridge.app import create_app
from admin_bridge.exceptions import BridgeError
from admin_bridge.files import CHUNK_SIZE, FileStore
from admin_bridge.service import CoreRepository


class FileTests(unittest.TestCase):
    """Use actual disposable files and database membership without a configured deployment."""

    def setUp(self) -> None:
        """Creates an isolated downloads tree and a single current admin."""
        directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.root = self.base / 'downloads'
        self.user = self.root / '42'
        self.user.mkdir(parents=True)
        self.payload = b'audio\x00' * 30000
        (self.user / 'safe.mp3').write_bytes(self.payload)
        os.utime(self.user / 'safe.mp3', (100, 100))
        (self.root / '7000000001').mkdir()
        (self.root / '7000000001' / 'newer.ogg').write_bytes(b'new')
        os.utime(self.root / '7000000001' / 'newer.ogg', (200, 200))
        fixture = PostgresFixture()
        self.addCleanup(fixture.close)
        self.database = fixture.dsn

        with Database(self.database) as connection:
            connection.execute('CREATE TABLE admins(admin_user_id BIGINT, is_owner BOOLEAN);'
                               'INSERT INTO admins VALUES(42, TRUE);')

        self.store = FileStore(root=self.root)
        self.app = create_app(
            token='s' * 32,
            repository=CoreRepository(connect=self._connect, files=self.store),
        )

    def _connect(self) -> PostgreSQLConnection:
        """Returns the existing read-only core test adapter."""
        return PostgreSQLConnection(path=str(self.database))

    def request(
        self,
        path: str = '/v1/files',
        params: dict[str, str] | None = None,
        actor: str = '42',
    ) -> tuple[int, dict[str, str], Any]:
        """Returns the actual WSGI iterable to allow streaming cancellation assertions."""
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, QUERY_STRING=urlencode(params or {}),
                       HTTP_AUTHORIZATION='Bearer ' + 's' * 32, HTTP_X_ADMIN_TELEGRAM_ID=actor)
        status: list[int] = []
        headers: dict[str, str] = {}

        def start_response(code: str, fields: list[tuple[str, str]]) -> None:
            status.append(int(code.split()[0]))
            headers.update(fields)

        body = self.app(environ, start_response)

        return status[0], headers, body

    def test_inventory_filters_pagination_and_observed_timestamps(self) -> None:
        """Counts files, skips empty directories and exposes real modification times."""
        (self.root / '99').mkdir()
        status, _headers, body = self.request(params={'pageSize': '1', 'page': '9'})
        data = json.loads(b''.join(body))
        self.assertEqual(status, 200)
        self.assertEqual((data['total'], data['page']), (2, 2))
        self.assertEqual(data['files'][0], {
            'basename': 'safe.mp3', 'telegramId': '42', 'bytes': len(self.payload),
            'modifiedAt': '1970-01-01T00:01:40+00:00',
        })
        self.assertEqual(self.store.list_files(params={'q': 'NEWER'})['total'], 1)
        self.assertEqual(self.store.list_files(params={'q': '7000000001'})['total'], 1)
        self.assertEqual(self.store.list_files(params={'telegramId': '42'})['total'], 1)
        (self.user / 'safe.mp3').unlink()
        self.assertEqual(self.store.list_files(params={'telegramId': '42'})['total'], 0)

    def test_missing_downloads_directory_is_an_empty_inventory(self) -> None:
        """A fresh data volume without downloads returns an empty list, not a server error."""
        self.root.rename(self.base / 'downloads-before-first-upload')

        status, _headers, body = self.request()

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(b''.join(body)), {
            'files': [], 'total': 0, 'page': 1, 'pageSize': 10,
        })

    def test_download_stream_headers_and_cleanup(self) -> None:
        """Streams the retained bytes, bounded chunks and a safe attachment response."""
        status, headers, body = self.request(
            path='/v1/files/download', params={'telegramId': '42', 'basename': 'safe.mp3'},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(headers['Content-Length'], str(len(self.payload)))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        chunks = list(body)
        self.assertEqual(b''.join(chunks), self.payload)
        self.assertTrue(all(len(chunk) <= CHUNK_SIZE for chunk in chunks))
        self.assertTrue(body.stream.closed)

    def test_cancellation_and_removed_file(self) -> None:
        """Closes unconsumed responses and reports concurrent cleanup as a missing file."""
        download = self.store.open_download(params={'telegramId': '42', 'basename': 'safe.mp3'})
        download.close()
        self.assertTrue(download.stream.closed)
        download = self.store.open_download(params={'telegramId': '42', 'basename': 'safe.mp3'})
        iterator = iter(download)
        next(iterator)
        iterator.close()
        self.assertTrue(download.stream.closed)
        (self.user / 'safe.mp3').unlink()
        self.assertEqual(self.request(
            path='/v1/files/download', params={'telegramId': '42', 'basename': 'safe.mp3'},
        )[0], 404)

    def test_unsafe_paths_links_and_special_files_are_never_served(self) -> None:
        """Rejects traversal, linked user directories, hard links, symlinks and FIFOs."""
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'secret.mp3').write_bytes(b'private')
        (self.user / 'linked.mp3').symlink_to(outside / 'secret.mp3')
        (self.root / '99').symlink_to(outside, target_is_directory=True)
        os.link(outside / 'secret.mp3', self.user / 'hard.mp3')
        os.mkfifo(self.user / 'pipe.mp3')
        (self.user / 'nested').mkdir()
        self.assertEqual(self.store.list_files(params={})['total'], 2)

        for basename in ('../outside/secret.mp3', '/etc/passwd', '..', 'a\\b', 'a\r\nb', '\x00'):
            with self.subTest(basename=basename):
                self.assertEqual(self.request(
                    path='/v1/files/download', params={'telegramId': '42', 'basename': basename},
                )[0], 400)

        for basename in ('linked.mp3', 'hard.mp3', 'pipe.mp3', 'nested'):
            with self.subTest(basename=basename):
                self.assertEqual(self.request(
                    path='/v1/files/download', params={'telegramId': '42', 'basename': basename},
                )[0], 404)

        self.assertEqual(self.request(
            path='/v1/files/download', params={'telegramId': '99', 'basename': 'secret.mp3'},
        )[0], 404)

    def test_directory_swap_cannot_redirect_an_opened_download(self) -> None:
        """A renamed user directory and replacement symlink cannot escape its anchored fd."""
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'safe.mp3').write_bytes(b'private')
        original_open = os.open

        def swap(path: Any, flags: int, **kwargs: Any) -> int:
            if path == 'safe.mp3':
                self.user.rename(self.root / 'old-user')
                self.user.symlink_to(outside, target_is_directory=True)

            return original_open(path, flags, **kwargs)

        with patch('admin_bridge.files.os.open', side_effect=swap):
            download = self.store.open_download(params={'telegramId': '42', 'basename': 'safe.mp3'})

        self.assertEqual(b''.join(download), self.payload)

    def test_membership_revocation_prevents_inventory_and_download_open(self) -> None:
        """Checks current core membership before filesystem listing or descriptor opening."""
        store = Mock()
        self.app = create_app(
            token='s' * 32, repository=CoreRepository(connect=self._connect, files=store),
        )

        with Database(self.database) as connection:
            connection.execute('DELETE FROM admins')

        for path in ('/v1/files', '/v1/files/download'):
            self.assertEqual(self.request(path=path)[0], 403)

        store.list_files.assert_not_called()
        store.open_download.assert_not_called()

    def test_invalid_filters_and_scan_limits_fail_explicitly(self) -> None:
        """Returns real failures for invalid parameters or exhausted scan budgets."""
        for params in ({'page': '0'}, {'pageSize': '101'}, {'telegramId': '../42'},
                       {'status': 'active'}, {'q': 'a' * 81}):
            with self.subTest(params=params):
                self.assertEqual(self.request(params=params)[0], 400)

        with patch('admin_bridge.files.MAX_SCAN_ENTRIES', 1):
            with self.assertRaises(BridgeError) as error:
                self.store.list_files(params={})

            self.assertEqual(error.exception.status, 413)
