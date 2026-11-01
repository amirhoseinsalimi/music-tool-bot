"""PostgreSQL checks for core schema migrations."""
import importlib
import unittest

import psycopg2
from masoniteorm.connections import PostgresConnection
from masoniteorm.schema import Schema

from pg_support import PostgresFixture


class DropUnusedTelegramNameColumnsTests(unittest.TestCase):
    """Exercise the programmatic, repeatable drop-column migration on PostgreSQL."""

    def setUp(self):
        self.fixture = PostgresFixture()
        self.addCleanup(self.fixture.close)
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute('''CREATE TABLE users (
                    id BIGINT PRIMARY KEY,
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    display_name VARCHAR(511)
                )''')
                cursor.execute(
                    'INSERT INTO users VALUES (%s, %s, %s, %s)',
                    (1, 'Ada', 'Lovelace', 'Ada Lovelace'),
                )

        options = psycopg2.extensions.parse_dsn(self.fixture.base)
        connection_details = {
            'test': {
                'driver': 'postgres',
                'host': options['host'],
                'port': options['port'],
                'database': options['dbname'],
                'user': options['user'],
                'password': options['password'],
            },
        }
        migration_module = importlib.import_module(
            'database.migrations.2026_11_01_000001_drop_unused_telegram_name_columns')
        self.migration = object.__new__(migration_module.DropUnusedTelegramNameColumns)
        self.migration.schema = Schema(
            connection='test',
            connection_details=connection_details,
            connection_class=PostgresConnection,
            schema=self.fixture.schema,
        )

    def test_up_drops_only_unused_columns_and_can_be_retried(self):
        """Preserve display_name and safely repeat the migration after its columns are gone."""
        self.migration.up()
        self.migration.up()

        self.assertFalse(self.migration.schema.has_column('users', 'first_name'))
        self.assertFalse(self.migration.schema.has_column('users', 'last_name'))
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute('SELECT display_name FROM users WHERE id=1')
                row = cursor.fetchone()
        self.assertEqual(row['display_name'], 'Ada Lovelace')

    def test_down_restores_nullable_columns_and_can_be_retried(self):
        """Keep rollback schema restoration repeatable without changing display_name."""
        self.migration.up()
        self.migration.down()
        self.migration.down()

        self.assertTrue(self.migration.schema.has_column('users', 'first_name'))
        self.assertTrue(self.migration.schema.has_column('users', 'last_name'))
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute(
                    'SELECT first_name, last_name, display_name FROM users WHERE id=1')
                row = cursor.fetchone()
        self.assertIsNone(row['first_name'])
        self.assertIsNone(row['last_name'])
        self.assertEqual(row['display_name'], 'Ada Lovelace')
