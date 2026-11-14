"""The admin /stats month uses the owner's 31-day lookback."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from modules.admin import service


class StatsMonthTests(unittest.TestCase):
    def test_monthly_active_includes_interaction_from_30_and_half_days_ago(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        users = [
            SimpleNamespace(language_id=None, user_status_id=1,
                            last_interaction_at=now - timedelta(days=30, hours=12)),
            SimpleNamespace(language_id=None, user_status_id=1,
                            last_interaction_at=now - timedelta(days=31, hours=12)),
        ]
        update = SimpleNamespace(message=SimpleNamespace(reply_text=AsyncMock()))
        statuses = {'active': 1, 'blocked': 2, 'deleted': 3}
        with patch.object(service.User, 'all', return_value=users), \
                patch.object(service.Language, 'all', return_value=[]), \
                patch.object(service.UserStatus, 'where', side_effect=lambda _key, slug: SimpleNamespace(first=lambda: SimpleNamespace(id=statuses[slug]))), \
                patch.object(service, 'get_dir_size_in_bytes', return_value=0), \
                patch.object(service, 'pretty_print_size', return_value='0 B'), \
                patch.object(service.os, 'listdir', return_value=[]), \
                patch.object(service.psutil, 'disk_usage', return_value=(0, 0, 0)):
            asyncio.run(service.show_stats(update))
        message = update.message.reply_text.call_args.kwargs['text']
        self.assertIn('Monthly Active (31d): 1', message)
