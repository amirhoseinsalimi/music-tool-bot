# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'
NAME_COLUMNS = ('first_name', 'last_name')


class AddTelegramNamesToUsers(Migration):
    """Store Telegram's current first and last names when users interact."""

    def up(self):
        columns = [column for column in NAME_COLUMNS
                   if not self.schema.has_column(TABLE_NAME, column)]
        if not columns:
            return

        with self.schema.table(TABLE_NAME) as table:
            for column in columns:
                table.string(column).nullable()

    def down(self):
        columns = [column for column in NAME_COLUMNS
                   if self.schema.has_column(TABLE_NAME, column)]
        if not columns:
            return

        with self.schema.table(TABLE_NAME) as table:
            for column in columns:
                table.drop_column(column)
