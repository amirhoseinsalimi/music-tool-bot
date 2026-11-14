# pylint: disable=invalid-name
from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class CreateBotStartEvents(Migration):
    """Record Telegram start keys and whether the start created the user."""

    def _statement(self, query):
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement('''
            CREATE TABLE bot_start_events (
                update_id BIGINT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                source_key VARCHAR(64),
                is_new_user BOOLEAN NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT bot_start_source_key_valid CHECK (
                    source_key IS NULL OR source_key ~ '^[A-Za-z0-9_-]{1,64}$'
                )
            );
        ''')
        self._statement('CREATE INDEX bot_start_events_by_time ON bot_start_events (started_at, source_key);')
        self._statement('CREATE INDEX bot_start_events_by_user ON bot_start_events (user_id, started_at DESC);')
        self._statement('CREATE UNIQUE INDEX bot_start_events_one_acquisition ON bot_start_events (user_id) WHERE is_new_user;')

    def down(self):
        self._statement('DROP TABLE bot_start_events;')
