"""Live counter coverage at the shared rolling-window boundaries."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock

from admin_bridge.analytics_users import current_user_stats


class LiveUserStatsTest(unittest.TestCase):
    """Verify the counts-only contract for the Admin consumer."""

    def test_rolling_cutoffs_and_statuses(self):
        """Include the exact cutoffs and distinguish inactive from churned."""
        now = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
        stamp = now.replace(tzinfo=None)
        cursor = Mock()
        cursor.fetchall.return_value = [
            {"slug": "active", "iso": "en", "last_interaction_at": stamp - timedelta(hours=24)},
            {"slug": "active", "iso": "en", "last_interaction_at": stamp - timedelta(days=31)},
            {"slug": "blocked", "iso": "fa", "last_interaction_at": stamp - timedelta(days=91)},
            {"slug": None, "iso": None, "last_interaction_at": None},
        ]
        result = current_user_stats(cursor, {}, now)
        self.assertEqual(result["capturedAt"], now.isoformat())
        self.assertEqual(result["totalUsers"], 4)
        self.assertEqual(result["status"], {"active": 3, "blocked": 1, "deleted": 0})
        self.assertEqual(result["activity"], {"daily24h": 1, "weekly7d": 1, "monthly31d": 2,
                                              "active90d": 2, "inactive": 1, "churned90d": 1})
