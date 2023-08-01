# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'admins'


class CreateAdminsTable(Migration):

    def up(self):
        with self.schema.create(TABLE_NAME) as table:
            table.increments('id')
            table.integer('admin_user_id').unique()
            table.boolean('is_owner').default(False)

            table.timestamps()

    def down(self):
        self.schema.drop(TABLE_NAME)
