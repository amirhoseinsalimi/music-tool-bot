# pylint: disable=invalid-name

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class AddTelegramNamesToUsers(Migration):
    """Store Telegram's current first and last names when users interact."""

    def _statement(self, query):
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement(
            'ALTER TABLE users '
            'ADD COLUMN first_name VARCHAR(255), '
            'ADD COLUMN last_name VARCHAR(255);'
        )

    def down(self):
        self._statement(
            'ALTER TABLE users '
            'DROP COLUMN first_name, '
            'DROP COLUMN last_name;'
        )
