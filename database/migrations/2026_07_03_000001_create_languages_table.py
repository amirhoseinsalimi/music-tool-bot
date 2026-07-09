# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'languages'


class CreateLanguagesTable(Migration):

    def up(self):
        with self.schema.create(TABLE_NAME) as table:
            table.increments('id')
            table.string('iso', 2).unique()
            table.string('name', 50).unique()
            table.string('native_name', 50).unique()
            table.string('flag', 10)
            table.boolean('is_default').default(False)

            table.timestamps()

    def down(self):
        self.schema.drop(TABLE_NAME)
