# pylint: disable=invalid-name

from orator.migrations import Migration


class CreateAdminsTable(Migration):

    def up(self):
        with self.schema.create('admins') as table:
            table.increments('id')
            table.integer('admin_user_id').unique()
            table.boolean('is_owner').default(False)

            table.timestamps()

    def down(self):
        self.schema.drop('admins')
