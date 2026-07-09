# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'


class AddLanguageIdToUsers(Migration):

    def up(self):
        with self.schema.table(TABLE_NAME) as table:
            table.integer('language_id').nullable()
            table.foreign('language_id').references('id').on('languages').on_delete('set null')

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.drop_column('language_id')
