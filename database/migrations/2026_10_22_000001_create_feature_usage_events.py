# pylint: disable=invalid-name

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class CreateFeatureUsageEvents(Migration):
    """Forward-only completion history for the four free audio tools."""

    def _statement(self, query):
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement("""
            CREATE TABLE feature_usage_events (
                feature TEXT NOT NULL CHECK (feature IN
                    ('cutter', 'bitrate_changer', 'voice_converter', 'tag_editor')),
                update_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (feature, update_id)
            );
        """)
        self._statement(
            'CREATE INDEX feature_usage_events_by_time '
            'ON feature_usage_events (completed_at, feature);'
        )

    def down(self):
        self._statement('DROP TABLE feature_usage_events;')
