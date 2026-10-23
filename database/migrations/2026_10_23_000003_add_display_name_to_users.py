# pylint: disable=invalid-name
from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class AddDisplayNameToUsers(Migration):
    """Align existing in-progress name handling with its PostgreSQL schema."""

    def _statement(self, query):
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement('ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(511);')
        self._statement("""
            UPDATE users SET display_name = NULLIF(CONCAT_WS(' ',
                NULLIF(BTRIM(first_name), ''), NULLIF(BTRIM(last_name), '')), '')
            WHERE display_name IS NULL;
        """)

    def down(self):
        self._statement('ALTER TABLE users DROP COLUMN IF EXISTS display_name;')
