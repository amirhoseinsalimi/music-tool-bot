"""PostgreSQL checks for core schema migrations."""
import importlib
import unittest

import psycopg2
from masoniteorm.connections import PostgresConnection
from masoniteorm.schema import Schema

from pg_support import PostgresFixture


class AddTelegramNameColumnsTests(unittest.TestCase):
    """Exercise the programmatic, repeatable Telegram-name schema migrations."""

    def setUp(self):
        self.fixture = PostgresFixture()
        self.addCleanup(self.fixture.close)
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute('CREATE TABLE users (id BIGINT PRIMARY KEY)')

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
        self.schema = Schema(
            connection='test',
            connection_details=connection_details,
            connection_class=PostgresConnection,
            schema=self.fixture.schema,
        )

    def _migration(self, module_name, class_name):
        migration_class = getattr(importlib.import_module(module_name), class_name)
        migration = object.__new__(migration_class)
        migration.schema = self.schema
        migration.connection = 'test'
        migration.schema_name = self.fixture.schema
        return migration

    def test_name_columns_are_added_and_display_name_is_backfilled(self):
        """Create legacy columns with schema APIs and preserve PostgreSQL name normalization."""
        names = self._migration(
            'database.migrations.2026_10_23_000001_add_telegram_names_to_users',
            'AddTelegramNamesToUsers',
        )
        display_name = self._migration(
            'database.migrations.2026_10_23_000003_add_display_name_to_users',
            'AddDisplayNameToUsers',
        )

        names.up()
        names.up()
        self.assertTrue(self.schema.has_column('users', 'first_name'))
        self.assertTrue(self.schema.has_column('users', 'last_name'))
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO users (id, first_name, last_name) VALUES (%s, %s, %s)',
                    (1, '  Ada ', ' Lovelace  '),
                )

        display_name.up()
        display_name.up()
        self.assertTrue(self.schema.has_column('users', 'display_name'))
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute('SELECT display_name FROM users WHERE id=1')
                self.assertEqual(cursor.fetchone()['display_name'], 'Ada Lovelace')

        display_name.down()
        display_name.down()
        self.assertFalse(self.schema.has_column('users', 'display_name'))


class CreateOutboxMessagesMigrationTests(unittest.TestCase):
    """Verify the programmatic outbox migration and rollback on PostgreSQL."""

    def setUp(self):
        self.fixture = PostgresFixture()
        self.addCleanup(self.fixture.close)
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
        module = importlib.import_module(
            'database.migrations.2026_11_01_000002_create_outbox_messages')
        self.migration = object.__new__(module.CreateOutboxMessages)
        self.migration.schema = Schema(
            connection='test', connection_details=connection_details,
            connection_class=PostgresConnection, schema=self.fixture.schema,
        )

    def test_create_and_drop_outbox_schema(self):
        """Exercise outbox table creation and rollback against PostgreSQL."""
        self.migration.up()
        self.assertTrue(self.migration.schema.has_table('outbox_messages'))
        with self.fixture.connect() as db:
            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO outbox_messages (id, target_user_id, message_text)
                    VALUES (%s, %s, %s)
                    RETURNING status, attempts, message_text
                """, ('71b9bd57-0a19-4f17-9389-88440f386a00', 42, 'hello'))
                self.assertEqual(cursor.fetchone(), {
                    'status': 'queued', 'attempts': 0, 'message_text': 'hello',
                })
        self.migration.down()
        self.assertFalse(self.migration.schema.has_table('outbox_messages'))


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
