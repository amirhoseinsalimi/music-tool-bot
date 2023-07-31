# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'


class CreateUsersTable(Migration):

    def up(self):
        with self.schema.create(TABLE_NAME) as table:
            table.increments('id')
            table.integer('user_id').unique()
            table.string('language').default('en')
            table.integer('number_of_files_sent').default(0)

            table.timestamps()

    def down(self):
        self.schema.drop(TABLE_NAME)
