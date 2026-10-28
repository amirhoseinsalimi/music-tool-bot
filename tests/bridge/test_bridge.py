"""Isolated regression tests for the administrative bridge's public v1 contract."""

import json
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch
from wsgiref.util import setup_testing_defaults

import psycopg2
from pg_support import PostgresFixture
from psycopg2.extensions import make_dsn

from postgres_storage import Database
from admin_bridge.app import create_app
from admin_bridge.exceptions import BridgeError
from admin_bridge.files import FileStore
from admin_bridge.service import CoreRepository
from admin_bridge.utils import (
    parse_user_filters,
    serialize_timestamp,
    validate_telegram_id,
)
from source_tracking import _record, source_key


class PostgreSQLConnection:
    """Use the real PostgreSQL driver and retain cleanup assertions."""

    def __init__(self, path):
        self.connection = psycopg2.connect(path)
        self.closed = False

    def set_session(self, **kwargs):
        """Require the production repeatable-read and read-only transaction."""
        if kwargs != {'readonly': True, 'isolation_level': 'REPEATABLE READ'}:
            raise AssertionError('Expected read-only repeatable-read PostgreSQL')
        self.connection.set_session(**kwargs)

    def cursor(self, **kwargs):
        """Return the real PostgreSQL cursor requested by the repository."""
        return self.connection.cursor(**kwargs)

    def close(self):
        """Close the connection and retain cleanup evidence."""
        self.connection.close()
        self.closed = True


class BridgeTests(unittest.TestCase):
    """Verifies authorization, validation and the unchanged JSON response contract."""

    def setUp(self) -> None:
        """Creates a temporary core fixture without touching configured bot databases."""
        # addCleanup keeps the fixture alive across setUp and the test, including failures.
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        fixture = PostgresFixture()
        self.fixture = fixture
        self.addCleanup(fixture.close)
        self.path = fixture.dsn
        self.connections: list[PostgreSQLConnection] = []
        self.addCleanup(self.directory.cleanup)

        with Database(self.path) as database:
            database.execute("""
                CREATE TABLE admins(admin_user_id BIGINT, is_owner BOOLEAN);
                CREATE TABLE languages(id BIGINT, iso TEXT, name TEXT);
                CREATE TABLE user_statuses(id BIGINT, slug TEXT);
                CREATE TABLE users(
                    id BIGINT, user_id BIGINT, username TEXT, display_name TEXT,
                    number_of_files_sent BIGINT,
                    language_id BIGINT, user_status_id BIGINT, created_at TIMESTAMP,
                    updated_at TIMESTAMP, last_interaction_at TIMESTAMP
                );
                CREATE TABLE feature_usage_events(
                    feature TEXT NOT NULL, update_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
                    completed_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(feature,update_id)
                );
                CREATE TABLE bot_start_events(
                    update_id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL, source_key VARCHAR(64),
                    is_new_user BOOLEAN NOT NULL, started_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                INSERT INTO admins VALUES(42, TRUE);
                INSERT INTO languages VALUES(1, 'en', 'English'), (2, 'fa', 'Persian');
                INSERT INTO user_statuses VALUES(1, 'active'), (2, 'blocked');
                INSERT INTO users VALUES(
                    1, 7000000001, 'listener', 'Listener Example', 4, 1, 1,
                    '2026-10-10 12:00:00', '2026-10-10 12:00:00', NULL
                );
                INSERT INTO users VALUES(
                    2, 7000000002, NULL, 'Mina', 0, 2, 2,
                    '2026-10-11 12:00:00', '2026-10-11 12:00:00', '2026-10-11 12:00:00'
                );
            """)

        self.app = create_app(
            token='s' * 32,
            repository=CoreRepository(connect=self._connect),
        )

    def _connect(self) -> PostgreSQLConnection:
        """Creates and records a connection so cleanup can be asserted."""
        connection = PostgreSQLConnection(path=self.path)
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

        with Database(self.path) as database:
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

        with Database(self.path) as database:
            database.execute('UPDATE users SET user_status_id=999 WHERE id=1')

        self.assertIsNone(self.request(path='/v1/users/7000000001')[1]['status'])

    def test_feature_usage_is_dated_and_authorized(self) -> None:
        """Counts completions in Tehran dates and rejects unauthorised reads."""
        with Database(self.path) as database:
            database.execute(
                "INSERT INTO feature_usage_events VALUES "
                "('cutter',1,7000000001,'2026-10-21 20:29:59+00'),"
                "('cutter',2,7000000001,'2026-10-21 20:30:00+00'),"
                "('cutter',3,7000000002,'2026-10-21 20:40:00+00'),"
                "('tag_editor',4,7000000002,'2026-10-21 20:50:00+00')"
            )
        path = '/v1/analytics/features'
        query = 'from=2026-10-22&until=2026-10-22&group=day'
        code, data = self.request(path=path, query=query)
        self.assertEqual(code, 200)
        self.assertEqual(data['timezone'], 'Asia/Tehran')
        self.assertEqual(data['features'], [
            {'feature': 'cutter', 'completed': 2, 'users': 2},
            {'feature': 'tag_editor', 'completed': 1, 'users': 1},
        ])
        self.assertEqual(data['periods'][0]['period'], '2026-10-22')
        self.assertEqual(self.request(path=path, query=query, actor='999')[0], 403)
        self.assertEqual(self.request(path=path, query='from=2026-10-22&until=2026-10-21')[0], 400)

    def test_restricted_role_can_run_every_bridge_read_path(self) -> None:
        """Exercises every bridge query with only the production read grants."""
        role = 'bridge_test_' + self.fixture.schema[-12:]
        password = 'p' * 32
        with psycopg2.connect(self.path) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE ROLE {role} LOGIN PASSWORD %s', (password,))
                cursor.execute(f'GRANT USAGE ON SCHEMA {self.fixture.schema} TO {role}')
                cursor.execute(
                    f'GRANT SELECT ON users, admins, languages, user_statuses, '
                    f'feature_usage_events, bot_start_events TO {role}'
                )

        def drop_role() -> None:
            with psycopg2.connect(self.path) as connection:
                connection.autocommit = True
                with connection.cursor() as cursor:
                    cursor.execute(f'DROP OWNED BY {role}')
                    cursor.execute(f'DROP ROLE IF EXISTS {role}')

        self.addCleanup(drop_role)
        with Database(self.path) as database:
            database.execute(
                "INSERT INTO feature_usage_events VALUES "
                "('cutter',11,7000000001,'2026-10-22 00:00:00+00')"
            )
            database.execute(
                "INSERT INTO bot_start_events(update_id,user_id,source_key,is_new_user) "
                "VALUES (11,7000000001,'website',TRUE)"
            )
        root = Path(self.directory.name) / 'downloads'
        (root / '7000000001').mkdir(parents=True)
        (root / '7000000001' / 'track.mp3').write_bytes(b'audio')
        restricted_dsn = make_dsn(
            self.path, user=role, password=password,
            options=f'-csearch_path={self.fixture.schema}',
        )

        def restricted_connect() -> PostgreSQLConnection:
            return PostgreSQLConnection(path=restricted_dsn)

        self.app = create_app(
            token='s' * 32,
            repository=CoreRepository(
                connect=restricted_connect,
                files=FileStore(root=root),
            ),
        )
        requests = [
            ('/v1/overview', ''),
            ('/v1/users', ''),
            ('/v1/users/7000000001', ''),
            ('/v1/analytics/features', 'from=2026-10-22&until=2026-10-22'),
            ('/v1/analytics/sources', ''),
            ('/v1/files', 'telegramId=7000000001'),
        ]
        for path, query in requests:
            with self.subTest(path=path):
                status, _data = self.request(path=path, query=query)
                self.assertEqual(status, 200)

    def test_source_keys_count_first_visits_and_repeated_starts(self) -> None:
        """First visit, unique user and repeat Start totals use one Tehran date range."""
        with Database(self.path) as database:
            database.execute(
                "INSERT INTO bot_start_events VALUES "
                "(1,7000000001,'blackfriday',TRUE,'2026-10-10 12:00:00+00'),"
                "(2,7000000001,'blackfriday',FALSE,'2026-10-22 09:00:00+00'),"
                "(3,7000000002,'blackfriday',FALSE,'2026-10-22 10:00:00+00'),"
                "(4,7000000001,'digikala_campain',FALSE,'2026-10-22 11:00:00+00')"
            )
        path = '/v1/analytics/sources'
        code, report = self.request(path=path)
        self.assertEqual(code, 200)
        blackfriday = next(row for row in report['rows'] if row['key'] == 'blackfriday')
        self.assertEqual(blackfriday, {'key': 'blackfriday', 'newUsers': 1,
                                       'uniqueUsers': 2, 'botStarts': 3})
        self.assertEqual(report['totalNewUsers'], 2)
        self.assertEqual(report['unknownNewUsers'], 1)
        _, dated = self.request(path=path, query='from=2026-10-22&until=2026-10-22')
        self.assertEqual(next(row for row in dated['rows']
                         if row['key'] == 'blackfriday')['botStarts'], 2)
        profile = self.request(path='/v1/users/7000000001')[1]
        self.assertEqual(profile['acquisitionSource'], 'blackfriday')
        self.assertEqual(profile['latestTaggedSource'], 'digikala_campain')
        self.assertEqual(self.request(path=path, actor='999')[0], 403)
        self.assertEqual(self.request(path=path, query='from=2026-10-23&until=2026-10-22')[0], 400)

    def test_start_recording_validates_keys_and_is_idempotent(self) -> None:
        """Source parsing rejects invalid keys and repeated Telegram updates are idempotent."""
        self.assertEqual(source_key(['digikala_campain']), 'digikala_campain')
        self.assertIsNone(source_key(['bad key']))
        self.assertIsNone(source_key(['a', 'b']))
        connect = psycopg2.connect
        with patch('source_tracking.psycopg2.connect', side_effect=lambda **_: connect(self.path)):
            _record(91, 7000000001, 'blackfriday', True)
            _record(91, 7000000001, 'blackfriday', True)
        with Database(self.path) as database:
            self.assertEqual(database.execute(
                'SELECT COUNT(*) FROM bot_start_events').fetchone()[0], 1)

    def test_feature_usage_month_groups_are_31_days_from_selected_start(self) -> None:
        """Keeps the 31st day in bucket one and starts bucket two on day 32."""
        with Database(self.path) as database:
            database.execute(
                "INSERT INTO feature_usage_events VALUES "
                "('cutter',11,7000000001,'2026-10-30 21:00:00+00'),"
                "('cutter',12,7000000001,'2026-10-31 21:00:00+00')"
            )
        code, data = self.request(path='/v1/analytics/features',
                                  query='from=2026-10-01&until=2026-11-03&group=month')
        self.assertEqual(code, 200)
        self.assertEqual([row['period'] for row in data['periods']],
                         ['2026-10-01', '2026-11-01'])

    def test_id_and_search_validation(self) -> None:
        """Normalizes string IDs, escapes LIKE wildcards and serializes explicit UTC."""
        self.assertEqual(validate_telegram_id(value='007000000001'), '7000000001')
        _, values, *_ = parse_user_filters(params={'q': '_%\\'})

        self.assertEqual(parse_user_filters(params={'sort': 'telegramId', 'direction': 'asc'})[4:],
                         ('telegramId', 'asc'))
        for invalid in ({'sort': 'user_id', 'direction': 'asc'},
                        {'sort': 'username', 'direction': 'sideways'},
                        {'direction': 'desc'}):
            with self.subTest(invalid=invalid), self.assertRaises(BridgeError):
                parse_user_filters(params=invalid)

        self.assertEqual(values, ['%\\_\\%\\\\%'] * 3)
        self.assertEqual(
            serialize_timestamp(value=datetime(2026, 10, 10)),
            '2026-10-10T00:00:00+00:00',
        )

    def test_complete_profile_response_contract(self) -> None:
        """Protects the exact v1 profile keys and values consumed by the private admin API."""
        self.assertEqual(self.request(path='/v1/users/7000000001')[1], {
            'id': 1,
            'telegramId': '7000000001',
            'displayName': 'Listener Example',
            'username': 'listener',
            'language': 'English',
            'languageIso': 'en',
            'status': 'active',
            'audioSubmissions': 4,
            'createdAt': '2026-10-10T12:00:00+00:00',
            'updatedAt': '2026-10-10T12:00:00+00:00',
            'lastInteractionAt': None,
            'acquisitionSource': None,
            'acquisitionRecordedAt': None,
            'latestTaggedSource': None,
            'latestTaggedAt': None,
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
    """Exercise driver-specific aggregate values absent from previous fixtures."""

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
