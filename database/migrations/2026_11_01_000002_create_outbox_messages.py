# pylint: disable=invalid-name
"""Queue owner initiated messages for delivery by the core bot."""

from masoniteorm.migrations import Migration


TABLE_NAME = 'outbox_messages'


class CreateOutboxMessages(Migration):
    """Create a bounded operational queue; this is not an admin access audit table."""

    def up(self):
        with self.schema.create(TABLE_NAME) as table:
            table.uuid('id').primary()
            table.big_integer('target_user_id')
            table.text('message_text').nullable()
            table.string('status', 32).default('queued')
            table.integer('attempts').default(0)
            table.string('last_error', 64).nullable()
            table.timestamp('created_at', now=True)
            table.timestamp('available_at', now=True)
            table.timestamp('sent_at').nullable()

            table.index(['status', 'available_at'], name='outbox_messages_pending_index')
            table.index(['created_at'], name='outbox_messages_retention_index')

    def down(self):
        self.schema.drop(TABLE_NAME)
