# pylint: disable=invalid-name
from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder

TABLE_NAME = 'users'
DISPLAY_NAME_COLUMN = 'display_name'


class AddDisplayNameToUsers(Migration):
    """Align existing in-progress name handling with its PostgreSQL schema."""

    def _statement(self, query: str) -> None:
        QueryBuilder(
            connection=self.connection,
            connection_details=self.schema.connection_details,
            schema=self.schema_name,
        ).statement(query)

    def up(self):
        if not self.schema.has_column(TABLE_NAME, DISPLAY_NAME_COLUMN):
            with self.schema.table(TABLE_NAME) as table:
                table.string(DISPLAY_NAME_COLUMN, 511).nullable()

        # Keep the PostgreSQL expression for whitespace trimming and empty-name handling;
        # Masonite's query builder does not express this transformation portably.
        self._statement("""
            UPDATE users SET display_name = NULLIF(CONCAT_WS(' ',
                NULLIF(BTRIM(first_name), ''), NULLIF(BTRIM(last_name), '')), '')
            WHERE display_name IS NULL;
        """)

    def down(self):
        if self.schema.has_column(TABLE_NAME, DISPLAY_NAME_COLUMN):
            with self.schema.table(TABLE_NAME) as table:
                table.drop_column(DISPLAY_NAME_COLUMN)
