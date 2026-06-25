# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'user_statuses'


class CreateUserStatusesTable(Migration):

    def up(self):
        with self.schema.create(TABLE_NAME) as table:
            table.increments('id')
            table.string('slug', 50).unique()
            table.string('name', 100)

            table.timestamps()

    def down(self):
        self.schema.drop(TABLE_NAME)