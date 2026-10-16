"""Isolated regression tests for the administrative bridge's public v1 contract."""

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from wsgiref.util import setup_testing_defaults

from admin_bridge.app import create_app
from admin_bridge.service import CoreRepository
from admin_bridge.utils import (
    parse_user_filters,
    serialize_timestamp,
    validate_telegram_id,
)


class SQLiteCursor:
    """Adapts a test cursor to the repository's PostgreSQL cursor interface."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Creates a cursor for the isolated core fixture."""
        self.cursor = connection.cursor()

    def __enter__(self) -> 'SQLiteCursor':
        """Returns the cursor for a repository read."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Closes the cursor after a read, including failed reads."""
        self.cursor.close()

    def execute(self, query: str, values: tuple | list = ()) -> None:
        """Translates driver syntax for SQLite without changing the bound values."""
        if query.startswith('SET LOCAL'):
            return

        self.cursor.execute(query.replace('%s', '?').replace('ILIKE', 'LIKE'), values)

    def fetchone(self) -> dict[str, Any] | None:
        """Returns one dictionary row or ``None`` when the query found no record."""
        row = self.cursor.fetchone()

        return dict(row) if row is not None else None

    def fetchall(self) -> list[dict[str, Any]]:
        """Returns the remaining dictionary rows."""
        return [dict(row) for row in self.cursor.fetchall()]


class SQLiteConnection:
    """Uses a disposable database and enforces the repository's read-only contract."""

    def __init__(self, path: str) -> None:
        """Opens a connection to the isolated fixture."""
        self.connection = sqlite3.connect(database=path)
        self.connection.row_factory = sqlite3.Row
        self.closed = False

    def set_session(self, **kwargs: object) -> None:
        """Requires the production transaction settings and prevents test writes."""
        if kwargs != {'readonly': True, 'isolation_level': 'REPEATABLE READ'}:
            raise AssertionError('The bridge must use a read-only, repeatable-read transaction')

        self.connection.execute('PRAGMA query_only=ON')

    def cursor(self, **_kwargs: object) -> SQLiteCursor:
        """Returns the adapter used by the real repository implementation."""
        return SQLiteCursor(connection=self.connection)

    def close(self) -> None:
        """Closes the transaction and records closure for regression assertions."""
        self.connection.close()
        self.closed = True


class BridgeTests(unittest.TestCase):
    """Verifies authorization, validation and the unchanged JSON response contract."""

    def setUp(self) -> None:
        """Creates a temporary core fixture without touching configured bot databases."""
        # addCleanup keeps the fixture alive across setUp and the test, including failures.
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.path = str(Path(self.directory.name) / 'core.sqlite')
        self.connections: list[SQLiteConnection] = []
        self.addCleanup(self.directory.cleanup)

        with sqlite3.connect(database=self.path) as database:
            database.executescript("""
                CREATE TABLE admins(admin_user_id INTEGER, is_owner BOOLEAN);
                CREATE TABLE languages(id INTEGER, iso TEXT, name TEXT);
                CREATE TABLE user_statuses(id INTEGER, slug TEXT);
                CREATE TABLE users(
                    id INTEGER, user_id INTEGER, username TEXT, number_of_files_sent INTEGER,
                    language_id INTEGER, user_status_id INTEGER, created_at TEXT,
                    updated_at TEXT, last_interaction_at TEXT
                );
                INSERT INTO admins VALUES(42, 1);
                INSERT INTO languages VALUES(1, 'en', 'English'), (2, 'fa', 'Persian');
                INSERT INTO user_statuses VALUES(1, 'active'), (2, 'blocked');
                INSERT INTO users VALUES(
                    1, 7000000001, 'listener', 4, 1, 1,
                    '2026-10-10 12:00:00', '2026-10-10 12:00:00', NULL
                );
                INSERT INTO users VALUES(
                    2, 7000000002, NULL, 0, 2, 2,
                    '2026-10-11 12:00:00', '2026-10-11 12:00:00', '2026-10-11 12:00:00'
                );
            """)

        self.app = create_app(
            token='s' * 32,
            repository=CoreRepository(connect=self._connect),
        )

    def _connect(self) -> SQLiteConnection:
        """Creates and records a connection so cleanup can be asserted."""
        connection = SQLiteConnection(path=self.path)
        self.connections.append(connection)

        return connection

    def request(  # pylint: disable=too-many-arguments
        self,
        *,
        path: str = '/v1/users',
        query: str = '',
        actor: str = '42',
        token: str = 's' * 32,
        method: str = 'GET',
    ) -> tuple[int, dict[str, Any]]:
        """Calls the real WSGI app directly, without binding a network socket."""
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(
            PATH_INFO=path,
            QUERY_STRING=query,
            REQUEST_METHOD=method,
            HTTP_AUTHORIZATION='Bearer ' + token,
            HTTP_X_ADMIN_TELEGRAM_ID=actor,
        )
        status: list[int] = []
        body = b''.join(self.app(
            environ,
            lambda code, _headers: status.append(int(code.split()[0])),
        ))

        return status[0], json.loads(body)

    def test_authentication_membership_and_revocation(self) -> None:
        """Requires a bridge secret and denies every read after admin revocation."""
        self.assertEqual(self.request(token='wrong')[0], 401)
        self.assertEqual(self.request(actor='999')[0], 403)
        self.assertEqual(
            self.request(path='/v1/session')[1],
            {'telegramId': '42', 'isOwner': True},
        )

        with sqlite3.connect(database=self.path) as database:
            database.execute('DELETE FROM admins')

        for path in [
            '/v1/session', '/v1/users', '/v1/users/7000000001',
            '/v1/overview', '/v1/users/export',
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path=path)[0], 403)

    def test_filters_pagination_and_nullable_profile(self) -> None:
        """Keeps pagination bounds, literal bound searches and nullable fields intact."""
        code, data = self.request(query='pageSize=1&page=9')

        self.assertEqual(code, 200)
        self.assertEqual((data['page'], data['total']), (2, 2))
        self.assertEqual(data['users'][0]['telegramId'], '7000000001')
        self.assertIsNone(data['users'][0]['lastInteractionAt'])
        self.assertTrue(data['users'][0]['createdAt'].endswith('+00:00'))
        self.assertEqual(
            self.request(query='q=%40listener&status=active&language=en')[1]['total'],
            1,
        )
        self.assertEqual(self.request(query='q=%27%20OR%201%3D1--')[1]['total'], 0)
        self.assertEqual(
            self.request(path='/v1/users/7000000002')[1]['language'],
            'Persian',
        )
        self.assertEqual(self.request(path='/v1/users/999')[0], 404)

    def test_invalid_inputs_and_methods(self) -> None:
        """Rejects invalid filters, duplicate values, malformed IDs and all write methods."""
        for query in ['pageSize=101', 'page=0', 'status=reachable', 'q=a&q=b', 'unknown=1']:
            with self.subTest(query=query):
                self.assertEqual(self.request(query=query)[0], 400)

        self.assertEqual(self.request(actor='-42')[0], 400)
        self.assertEqual(self.request(method='POST')[0], 405)
        self.assertEqual(self.request(path='/v1/users/..%2F')[0], 400)

    def test_overview_export_and_unknown_relations(self) -> None:
        """Preserves current totals, filtered export and missing core relations."""
        data = self.request(path='/v1/overview')[1]

        self.assertEqual(
            (data['totalUsers'], data['activeStatus'], data['audioSubmissions']),
            (2, 1, 4),
        )
        self.assertEqual(
            self.request(path='/v1/users/export', query='status=blocked')[1]['total'],
            1,
        )

        with sqlite3.connect(database=self.path) as database:
            database.execute('UPDATE users SET user_status_id=999 WHERE id=1')

        self.assertIsNone(self.request(path='/v1/users/7000000001')[1]['status'])

    def test_id_and_search_validation(self) -> None:
        """Normalizes string IDs, escapes LIKE wildcards and serializes explicit UTC."""
        self.assertEqual(validate_telegram_id(value='007000000001'), '7000000001')
        _, values, _, _ = parse_user_filters(params={'q': '_%\\'})

        self.assertEqual(values, ['%\\_\\%\\\\%'] * 2)
        self.assertEqual(
            serialize_timestamp(value=datetime(2026, 10, 10)),
            '2026-10-10T00:00:00+00:00',
        )

    def test_complete_profile_response_contract(self) -> None:
        """Protects the exact v1 profile keys and values consumed by the private admin API."""
        self.assertEqual(self.request(path='/v1/users/7000000001')[1], {
            'id': 1,
            'telegramId': '7000000001',
            'username': 'listener',
            'language': 'English',
            'languageIso': 'en',
            'status': 'active',
            'audioSubmissions': 4,
            'createdAt': '2026-10-10T12:00:00+00:00',
            'updatedAt': '2026-10-10T12:00:00+00:00',
            'lastInteractionAt': None,
        })

    def test_read_transactions_close_on_success_and_denial(self) -> None:
        """Closes each connection even when current admin membership denies the read."""
        self.assertEqual(self.request(path='/v1/users')[0], 200)
        self.assertEqual(self.request(actor='999')[0], 403)
        self.assertEqual(len(self.connections), 2)
        self.assertTrue(all(connection.closed for connection in self.connections))

    def test_bad_request_never_opens_a_database_connection(self) -> None:
        """Rejects malformed callers before reaching the database service."""
        self.assertEqual(self.request(token='wrong')[0], 401)
        self.assertEqual(self.request(query='q=' + 'x' * 1024)[0], 400)
        self.assertEqual(self.request(query='&'.join(f'q{i}=x' for i in range(11)))[0], 400)
        self.assertEqual(self.connections, [])

    def test_unavailable_database_is_a_safe_error_response(self) -> None:
        """Returns a 503 without exposing credentials or treating an outage as no users."""
        repository = Mock()
        repository.dispatch.side_effect = RuntimeError('database credentials must stay private')
        self.app = create_app(token='s' * 32, repository=repository)

        with self.assertLogs('music_tool_bot.admin_bridge', level='ERROR') as logs:
            status, response = self.request()

        self.assertEqual(status, 503)
        self.assertEqual(response, {'error': 'Core data unavailable'})
        self.assertNotIn('credentials', ''.join(logs.output))


class PostgreSQLCounterTests(unittest.TestCase):
    """Exercise driver-specific aggregate values absent from SQLite fixtures."""

    def test_numeric_submission_sum_is_json_serializable(self) -> None:
        """PostgreSQL SUM(bigint) returns Decimal even for small submission counts."""
        cursor = Mock()
        cursor.fetchone.side_effect = [
            {'total': 1, 'audio': Decimal('3')},
            {'total': 1},
        ]
        cursor.fetchall.return_value = [{'name': 'English', 'count': 1}]
        overview = CoreRepository._get_overview(cursor=cursor)  # pylint: disable=protected-access

        self.assertEqual(json.loads(json.dumps(overview))['audioSubmissions'], 3)
        self.assertIsInstance(overview['audioSubmissions'], int)
