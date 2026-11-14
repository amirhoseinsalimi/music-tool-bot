import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

# Match the application import order to resolve feature package imports.
import modules.core.handlers
from modules.admin import handlers
from modules.admin.registerer import registry
from telegram.error import Forbidden, RetryAfter
from telegram.ext import ConversationHandler
from utils import t


def inner(handler):
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


def make_update(user_id=42, text='/broadcast'):
    message = SimpleNamespace(
        text=text, message_id=7, chat_id=user_id,
        reply_text=AsyncMock(),
    )
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_message=message,
        message=message,
    )


class AdminBroadcastTests(unittest.TestCase):
    def setUp(self):
        handlers.broadcast_state.update({
            'active': False, 'admin_id': None, 'thread': None,
            'cancel_requested': False, 'sent': 0, 'failed': 0,
        })

    def test_conversation_has_one_minute_timeout_and_confirmation_command(self):
        conversation = registry()[0]
        self.assertEqual(conversation.conversation_timeout, 60)
        self.assertIn(handlers.CONFIRMING_BROADCAST, conversation.states)
        commands = [handler.commands for handler in conversation.states[handlers.CONFIRMING_BROADCAST]]
        self.assertIn(frozenset({'send_broadcast'}), commands)
        self.assertEqual(conversation.fallbacks[0].commands, frozenset({'cancel_broadcast'}))

    def test_submitted_message_is_previewed_without_starting_a_broadcast(self):
        update = make_update(text='Message with <markup> & symbols')
        context = SimpleNamespace(user_data={'language': 'en'})
        with patch.object(handlers, 'is_user_admin', return_value=True):
            state = asyncio.run(inner(handlers.handle_admin_message)(update, context))
        self.assertEqual(state, handlers.CONFIRMING_BROADCAST)
        self.assertEqual(context.user_data['broadcast_pending_message_id'], 7)
        self.assertFalse(handlers.broadcast_state['active'])
        update.message.reply_text.assert_awaited_once_with(t('en', 'broadcastConfirm'))

    def test_a_second_admin_cannot_cancel_another_admins_broadcast(self):
        handlers.broadcast_state.update({'active': True, 'admin_id': 41})
        update = make_update(user_id=42, text='/cancel_broadcast')
        context = SimpleNamespace(user_data={'language': 'en'})
        with patch.object(handlers, 'is_user_admin', return_value=True):
            asyncio.run(inner(handlers.cancel_broadcast)(update, context))
        self.assertTrue(handlers.broadcast_state['active'])
        self.assertEqual(handlers.broadcast_state['admin_id'], 41)
        update.message.reply_text.assert_awaited_once_with(t('en', 'broadcastNotOwner'))

    def test_running_broadcast_rejects_a_concurrent_start(self):
        handlers.broadcast_state.update({'active': True, 'admin_id': 41})
        update = make_update(text='/broadcast')
        context = SimpleNamespace(user_data={'language': 'en'}, args=[])
        with patch.object(handlers, 'is_user_admin', return_value=True):
            result = asyncio.run(inner(handlers.broadcast_command)(update, context))
        self.assertEqual(result, ConversationHandler.END)
        update.message.reply_text.assert_awaited_once_with(t('en', 'broadcastAlreadyRunning'))

    def test_language_filter_is_shown_and_saved_for_confirmation(self):
        update = make_update(text='/broadcast fa')
        context = SimpleNamespace(user_data={'language': 'en'}, args=['fa'])
        with patch.object(handlers, 'is_user_admin', return_value=True):
            state = asyncio.run(inner(handlers.broadcast_command)(update, context))
        self.assertEqual(state, handlers.AWAITING_MESSAGE)
        self.assertEqual(context.user_data['broadcast_language'], 'fa')
        update.message.reply_text.assert_awaited_once_with(t('en', 'broadcastPromptLanguage', language_code='fa'))

    def test_blocked_users_are_included_and_status_updates_follow_results(self):
        async def run():
            active = SimpleNamespace(id=1, slug='active')
            blocked = SimpleNamespace(id=2, slug='blocked')
            deleted = SimpleNamespace(id=3, slug='deleted')
            blocked_user = Mock(user_id=101, user_status_id=blocked.id)
            active_user = Mock(user_id=102, user_status_id=active.id)
            deleted_user = Mock(user_id=103, user_status_id=deleted.id)
            users = [blocked_user, active_user]
            users_query = Mock()
            users_query.where.return_value = users_query
            users_query.get.return_value = users
            users_query_factory = Mock(return_value=users_query)

            async def copy_message(**kwargs):
                if kwargs['chat_id'] == active_user.user_id:
                    raise Forbidden('bot was blocked by the user')
            update = make_update(text='/send_broadcast')
            context = SimpleNamespace(
                user_data={
                    'language': 'en', 'broadcast_pending_message_id': 7,
                    'broadcast_pending_chat_id': 42,
                },
                bot=SimpleNamespace(copy_message=AsyncMock(side_effect=copy_message), send_message=AsyncMock()),
            )
            with patch.object(handlers, 'is_user_admin', return_value=True), \
                 patch.object(handlers.User, 'where', new=users_query_factory), \
                 patch.object(handlers.UserStatus, 'where', side_effect=lambda field, slug: SimpleNamespace(first=lambda: {
                     'active': active, 'blocked': blocked, 'deleted': deleted,
                 }[slug])):
                await inner(handlers.send_broadcast)(update, context)
                worker = handlers.broadcast_state['thread']
                for _ in range(300):
                    if not worker.is_alive():
                        break
                    await asyncio.sleep(0.01)
                self.assertFalse(worker.is_alive())

            self.assertEqual([call.kwargs['chat_id'] for call in context.bot.copy_message.await_args_list], [101, 102])
            self.assertEqual(blocked_user.user_status_id, active.id)
            blocked_user.save.assert_called_once_with()
            self.assertEqual(active_user.user_status_id, blocked.id)
            active_user.save.assert_called_once_with()
            deleted_user.save.assert_not_called()
            users_query_factory.assert_called_once_with('user_status_id', '!=', deleted.id)
            self.assertFalse(handlers.broadcast_state['active'])

        asyncio.run(run())

    def test_retry_after_retries_copy_and_plain_copy_avoids_html_parse_mode(self):
        async def run():
            active = SimpleNamespace(id=1, slug='active')
            blocked = SimpleNamespace(id=2, slug='blocked')
            deleted = SimpleNamespace(id=3, slug='deleted')
            calls = 0

            async def copy_message(**kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RetryAfter(0)
                return None

            user = Mock(user_id=201, user_status_id=active.id)
            users_query = Mock()
            users_query.where.return_value = users_query
            users_query.get.return_value = [user]
            users_query_factory = Mock(return_value=users_query)
            update = make_update(text='/send_broadcast')
            context = SimpleNamespace(
                user_data={'language': 'en', 'broadcast_pending_message_id': 8, 'broadcast_pending_chat_id': 42},
                bot=SimpleNamespace(copy_message=AsyncMock(side_effect=copy_message), send_message=AsyncMock()),
            )
            with patch.object(handlers, 'is_user_admin', return_value=True), \
                 patch.object(handlers.User, 'where', new=users_query_factory), \
                 patch.object(handlers.UserStatus, 'where', side_effect=lambda field, slug: SimpleNamespace(first=lambda: {
                     'active': active, 'blocked': blocked, 'deleted': deleted,
                 }[slug])):
                await inner(handlers.send_broadcast)(update, context)
                worker = handlers.broadcast_state['thread']
                for _ in range(300):
                    if not worker.is_alive():
                        break
                    await asyncio.sleep(0.01)
                self.assertFalse(worker.is_alive())
            self.assertEqual(calls, 2, (users_query_factory.call_count, context.bot.copy_message.await_count, handlers.broadcast_state))
            self.assertNotIn('parse_mode', context.bot.copy_message.await_args.kwargs)

        asyncio.run(run())

    def test_cancel_during_retry_keeps_broadcast_reserved_until_worker_stops(self):
        async def run():
            active = SimpleNamespace(id=1, slug='active')
            blocked = SimpleNamespace(id=2, slug='blocked')
            deleted = SimpleNamespace(id=3, slug='deleted')
            user = Mock(user_id=301, user_status_id=active.id)
            users_query = Mock()
            users_query.where.return_value = users_query
            users_query.get.return_value = [user]
            users_query_factory = Mock(return_value=users_query)
            retry_wait_started = threading.Event()
            release_retry_wait = threading.Event()
            calls = 0

            async def copy_message(**kwargs):
                nonlocal calls
                calls += 1
                raise RetryAfter(5)

            context = SimpleNamespace(
                user_data={
                    'language': 'en', 'broadcast_pending_message_id': 9,
                    'broadcast_pending_chat_id': 42,
                },
                bot=SimpleNamespace(copy_message=AsyncMock(side_effect=copy_message), send_message=AsyncMock()),
            )
            statuses = {'active': active, 'blocked': blocked, 'deleted': deleted}
            with patch.object(handlers, 'is_user_admin', return_value=True), \
                 patch.object(handlers.User, 'where', new=users_query_factory), \
                 patch.object(handlers.UserStatus, 'where', side_effect=lambda field, slug: SimpleNamespace(
                     first=lambda: statuses[slug]
                 )), \
                 patch.object(handlers.time, 'sleep', side_effect=lambda _: (
                     retry_wait_started.set(), release_retry_wait.wait(2)
                 )):
                await inner(handlers.send_broadcast)(make_update(text='/send_broadcast'), context)
                worker = handlers.broadcast_state['thread']
                self.assertTrue(await asyncio.to_thread(retry_wait_started.wait, 1))

                cancel_update = make_update(text='/cancel_broadcast')
                await inner(handlers.cancel_broadcast)(cancel_update, SimpleNamespace(user_data={'language': 'en'}))
                self.assertTrue(handlers.broadcast_state['active'])
                release_retry_wait.set()
                for _ in range(300):
                    if not worker.is_alive():
                        break
                    await asyncio.sleep(0.01)
                self.assertFalse(worker.is_alive())

            self.assertEqual(calls, 1)
            self.assertFalse(handlers.broadcast_state['active'])

        asyncio.run(run())

    def test_broadcast_messages_exist_in_all_locales(self):
        for language in ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id'):
            for key in ('broadcastPrompt', 'broadcastPromptLanguage', 'broadcastConfirm', 'broadcastNoPending', 'broadcastStarted',
                        'broadcastComplete', 'broadcastStatusActive', 'broadcastStatusIdle',
                        'broadcastAlreadyRunning', 'broadcastNotOwner', 'broadcastCancelled'):
                with self.subTest(language=language, key=key):
                    message = t(language, key, count=2, sent=1, failed=1, blocked=1, active=1, admin_id=42,
                                language_code='fa')
                    self.assertTrue(message)
                    self.assertNotIn('missing translation', message)


if __name__ == '__main__':
    unittest.main()
