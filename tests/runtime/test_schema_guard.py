"""Startup schema guard checks the release migration set without writing to PostgreSQL."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import psycopg2

import bot

from utils.schema_guard import SchemaGuardError, assert_database_schema_current


class SchemaGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.temp_dir / '2026_01_01_000001_first.py').touch()
        (self.temp_dir / '2026_01_02_000001_second.py').touch()

    def test_all_release_migrations_applied_allows_startup_and_closes_connection(self):
        connection, cursor = self._connection([
            ('2026_01_01_000001_first',),
            ('2026_01_02_000001_second',),
        ])
        factory = MagicMock(return_value=connection)

        assert_database_schema_current(factory, self.temp_dir)

        factory.assert_called_once()
        cursor.execute.assert_called_once_with('SELECT migration FROM migrations')
        connection.close.assert_called_once()

    def test_missing_migration_refuses_startup_with_upgrade_instruction(self):
        connection, _ = self._connection([('2026_01_01_000001_first',)])

        with self.assertRaisesRegex(SchemaGuardError, '2026_01_02_000001_second') as raised:
            assert_database_schema_current(lambda **_: connection, self.temp_dir)

        self.assertIn('make db-upgrade', str(raised.exception))
        connection.close.assert_called_once()

    def test_unavailable_migration_history_refuses_startup_clearly(self):
        def fail_to_connect(**_):
            raise psycopg2.OperationalError('connection refused')

        with self.assertRaisesRegex(SchemaGuardError, 'Could not verify the database migration history'):
            assert_database_schema_current(fail_to_connect, self.temp_dir)

    def test_empty_migration_directory_refuses_to_pass(self):
        empty = self.temp_dir / 'empty'
        empty.mkdir()

        with self.assertRaisesRegex(SchemaGuardError, 'No database migrations were found'):
            assert_database_schema_current(lambda **_: None, empty)

    def test_bot_exits_before_registering_handlers_when_one_migration_is_pending(self):
        message = (
            'Database schema is behind this release; pending migrations: '
            '2026_01_02_000001_second. Run `make db-upgrade` before starting the bot.'
        )
        with (
            unittest.mock.patch.object(bot, 'configure_logging'),
            unittest.mock.patch.object(bot, 'assert_database_schema_current',
                                       side_effect=SchemaGuardError(message)),
            unittest.mock.patch.object(bot.logger, 'critical') as critical,
            unittest.mock.patch.object(bot, 'register_admin') as register_admin,
            unittest.mock.patch.object(bot, 'register_core') as register_core,
        ):
            with self.assertRaises(SystemExit) as raised:
                bot.main()

        self.assertEqual(raised.exception.code, 1)
        critical.assert_called_once()
        self.assertEqual(str(critical.call_args.args[1]), message)
        register_admin.assert_not_called()
        register_core.assert_not_called()

    @staticmethod
    def _connection(applied):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = applied
        connection.cursor.return_value = cursor
        return connection, cursor


if __name__ == '__main__':
    unittest.main()
