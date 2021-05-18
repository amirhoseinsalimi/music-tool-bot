# pylint: disable=invalid-name

from orator.migrations import Migration


class CreateUsersTable(Migration):

    def up(self):
        with self.schema.create('users') as table:
            table.increments('id')
            table.integer('user_id').unique()
            table.string('language').default('en')
            table.integer('number_of_files_sent').default(0)

            table.timestamps()

    def down(self):
        self.schema.drop('users')
