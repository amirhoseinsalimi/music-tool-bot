# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'


class AddUserStatusIdToUsers(Migration):

    def up(self):
        with self.schema.table(TABLE_NAME) as table:
            table.integer('user_status_id').unsigned().default(1).nullable()

            table.foreign('user_status_id', 'users_user_status_id_foreign').references('id').on('user_statuses')

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.drop_foreign('users_user_status_id_foreign')
            table.drop_column('user_status_id')