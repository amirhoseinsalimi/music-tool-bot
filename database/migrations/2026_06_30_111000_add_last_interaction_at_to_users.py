# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'


class AddLastInteractionAtToUsers(Migration):

    def up(self):
        with self.schema.table(TABLE_NAME) as table:
            table.datetime('last_interaction_at').nullable()

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.drop_column('last_interaction_at')