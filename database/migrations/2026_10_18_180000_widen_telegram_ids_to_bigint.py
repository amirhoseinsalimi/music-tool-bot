# pylint: disable=invalid-name

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class WidenTelegramIdsToBigint(Migration):
    """Store Telegram user identifiers without 32-bit integer limits."""

    def _statement(self, query: str) -> None:
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement("ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT;")
        self._statement("ALTER TABLE admins ALTER COLUMN admin_user_id TYPE BIGINT;")

    def down(self):
        self._statement(
            "ALTER TABLE users ALTER COLUMN user_id TYPE INTEGER "
            "USING user_id::INTEGER;"
        )
        self._statement(
            "ALTER TABLE admins ALTER COLUMN admin_user_id TYPE INTEGER "
            "USING admin_user_id::INTEGER;"
        )
