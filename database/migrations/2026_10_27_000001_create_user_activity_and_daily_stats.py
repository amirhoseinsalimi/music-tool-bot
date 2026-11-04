# pylint: disable=invalid-name
"""Daily user activity and aggregate /stats snapshots."""

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder


class CreateUserActivityAndDailyStats(Migration):
    """Store only per-user activity dates and per-day aggregate counters."""

    def _statement(self, query):
        QueryBuilder(connection=self.connection, schema=self.schema_name).statement(query)

    def up(self):
        self._statement('''
            CREATE TABLE user_activity_days (
                user_id BIGINT NOT NULL,
                day DATE NOT NULL,
                PRIMARY KEY (user_id, day)
            );
        ''')
        self._statement('''
            CREATE TABLE daily_stats_snapshot (
                day DATE PRIMARY KEY,
                total_users BIGINT NOT NULL,
                active_users BIGINT NOT NULL,
                blocked_users BIGINT NOT NULL,
                deleted_users BIGINT NOT NULL,
                daily_active_users BIGINT NOT NULL,
                weekly_active_users BIGINT NOT NULL,
                monthly_active_users BIGINT NOT NULL,
                active_90d_users BIGINT NOT NULL,
                inactive_users BIGINT NOT NULL,
                language_status_counts JSONB NOT NULL,
                file_count BIGINT NOT NULL,
                file_bytes BIGINT NOT NULL,
                disk_used_bytes BIGINT NOT NULL,
                disk_total_bytes BIGINT NOT NULL,
                captured_at TIMESTAMPTZ NOT NULL
            );
        ''')
        self._statement('CREATE INDEX user_activity_days_by_day ON user_activity_days (day);')

    def down(self):
        self._statement('DROP TABLE daily_stats_snapshot;')
        self._statement('DROP TABLE user_activity_days;')
