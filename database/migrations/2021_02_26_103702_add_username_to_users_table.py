# pylint: disable=invalid-name

from masoniteorm.migrations import Migration


TABLE_NAME = 'users'
COLUMN_NAME = 'username'


class AddUsernameToUsersTable(Migration):
    def up(self):
        with self.schema.table(TABLE_NAME) as table:
            table.string(COLUMN_NAME).after('user_id').default(None).nullable()

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.drop_column(COLUMN_NAME)
