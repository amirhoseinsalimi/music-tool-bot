"""Every registered user update must refresh the core user before handling it."""

import unittest
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.ext import ConversationHandler

# Match bot.py's import order to avoid the existing core/feature import cycle.
import modules.core.handlers
from modules.admin.registerer import registry as admin_registry
from modules.bitrate_changer.registerer import registry as bitrate_registry
from modules.core.registerer import registry as core_registry
from modules.cutter.registerer import registry as cutter_registry
from modules.donation.registerer import registry as donation_registry
from modules.tag_editor.registerer import registry as tag_registry
from modules.voice_converter.registerer import registry as voice_registry
from utils.decorators import upsert_user


def callbacks(handlers):
    for handler in handlers:
        if isinstance(handler, ConversationHandler):
            yield from callbacks(handler.entry_points)
            for state_handlers in handler.states.values():
                yield from callbacks(state_handlers)
            yield from callbacks(handler.fallbacks)
        else:
            yield handler.callback


class UpsertHandlerTests(unittest.TestCase):
    def test_first_command_records_its_interaction_time(self):
        callback = AsyncMock()
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42, username='tester'))
        context = SimpleNamespace(user_data={})
        created_user = SimpleNamespace(user_id=42, username='tester')
        with patch('utils.decorators.User.where') as users, patch('utils.decorators.User.create', return_value=created_user) as create, patch('utils.decorators._get_default_language_id', return_value=1):
            users.return_value.first.return_value = None
            asyncio.run(upsert_user(callback)(update, context))
        recorded = create.call_args.args[0]['last_interaction_at']
        self.assertIsInstance(recorded, datetime)
        self.assertEqual(recorded.tzinfo, timezone.utc)
        self.assertTrue(context._new_user_on_this_update)
        self.assertNotIn('_new_user_on_this_update', context.user_data)
        callback.assert_awaited_once_with(update, context)

    def test_registered_user_handlers_use_upsert_user(self):
        with patch('modules.core.registerer.Language.ordered', return_value=[]):
            for registry in (admin_registry, bitrate_registry, core_registry,
                             cutter_registry, donation_registry, tag_registry, voice_registry):
                for callback in callbacks(registry()):
                    with self.subTest(registry=registry.__module__, callback=callback.__name__):
                        self.assertTrue(getattr(callback, 'upserts_user', False))
                        self.assertEqual(callback.__code__.co_filename, upsert_user.__code__.co_filename)
