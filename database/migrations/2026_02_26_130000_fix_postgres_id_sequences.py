# pylint: disable=invalid-name

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class FixPostgresIdSequences(Migration):
    def _statement(self, query: str) -> None:
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement(
            "CREATE SEQUENCE IF NOT EXISTS migrations_migration_id_seq;"
        )
        self._statement(
            "ALTER TABLE migrations ALTER COLUMN migration_id SET DEFAULT nextval('migrations_migration_id_seq');"
        )
        self._statement(
            "ALTER SEQUENCE migrations_migration_id_seq OWNED BY migrations.migration_id;"
        )
        self._statement(
            "SELECT setval('migrations_migration_id_seq', COALESCE((SELECT MAX(migration_id) FROM migrations), 0) + 1, false);"
        )

        self._statement(
            "CREATE SEQUENCE IF NOT EXISTS users_id_seq;"
        )
        self._statement(
            "ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');"
        )
        self._statement(
            "ALTER SEQUENCE users_id_seq OWNED BY users.id;"
        )
        self._statement(
            "SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false);"
        )

        self._statement(
            "CREATE SEQUENCE IF NOT EXISTS admins_id_seq;"
        )
        self._statement(
            "ALTER TABLE admins ALTER COLUMN id SET DEFAULT nextval('admins_id_seq');"
        )
        self._statement(
            "ALTER SEQUENCE admins_id_seq OWNED BY admins.id;"
        )
        self._statement(
            "SELECT setval('admins_id_seq', COALESCE((SELECT MAX(id) FROM admins), 0) + 1, false);"
        )

    def down(self):
        self._statement(
            "ALTER TABLE migrations ALTER COLUMN migration_id DROP DEFAULT;"
        )
        self._statement(
            "ALTER TABLE users ALTER COLUMN id DROP DEFAULT;"
        )
        self._statement(
            "ALTER TABLE admins ALTER COLUMN id DROP DEFAULT;"
        )
        self._statement(
            "DROP SEQUENCE IF EXISTS migrations_migration_id_seq;"
        )
        self._statement(
            "DROP SEQUENCE IF EXISTS users_id_seq;"
        )
        self._statement(
            "DROP SEQUENCE IF EXISTS admins_id_seq;"
        )
