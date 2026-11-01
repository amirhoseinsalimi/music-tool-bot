# pylint: disable=invalid-name
"""Remove legacy name columns after their values have been folded into display_name."""

from masoniteorm.migrations import Migration


TABLE_NAME = 'users'
UNUSED_COLUMNS = ('first_name', 'last_name')


class DropUnusedTelegramNameColumns(Migration):
    """Drop redundant columns created before the bot stored display_name directly."""

    def up(self):
        """Drop legacy columns when present."""
        columns = [
            column for column in UNUSED_COLUMNS
            if self.schema.has_column(TABLE_NAME, column)
        ]
        if not columns:
            return

        with self.schema.table(TABLE_NAME) as table:
            for column in columns:
                table.drop_column(column)

    def down(self):
        """Restore nullable legacy columns when absent."""
        columns = [
            column for column in UNUSED_COLUMNS
            if not self.schema.has_column(TABLE_NAME, column)
        ]
        if not columns:
            return

        with self.schema.table(TABLE_NAME) as table:
            for column in columns:
                table.string(column).nullable()
