# pylint: disable=invalid-name

from masoniteorm.migrations import Migration


TABLE_NAME = 'users'
COLUMN_NAME = 'premium_expires_at'

class AddPremiumExpiresAtToUsers(Migration):
    def up(self):
        with self.schema.table("users") as table:
            table.timestamp(COLUMN_NAME).default(None).nullable()

    def down(self):
        with self.schema.table("users") as table:
            table.drop_column(COLUMN_NAME)
