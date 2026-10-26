import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from utils.error_handler import on_error


class ErrorHandlerTests(unittest.TestCase):
    def test_polling_error_without_update_is_logged_without_crashing(self):
        from telegram.error import NetworkError

        context = SimpleNamespace(error=NetworkError('polling failed'), user_data=None,
                                   bot=SimpleNamespace(send_message=AsyncMock()))
        with patch('utils.error_handler.OWNER_USER_ID_INT', None), \
             patch('utils.error_handler._alerted', {}), \
             patch('utils.error_handler.logger') as logger:
            asyncio.run(on_error(None, context))
        logger.warning.assert_called_once()
        context.bot.send_message.assert_not_awaited()

    def test_unexpected_error_replies_resets_and_alerts(self):
        reply = AsyncMock()
        update = SimpleNamespace(update_id=17, effective_user=SimpleNamespace(id=42), effective_message=SimpleNamespace(reply_text=reply))
        context = SimpleNamespace(error=ValueError('private text'), user_data={'language': 'en'}, bot=SimpleNamespace(send_message=AsyncMock()))
        with patch('utils.error_handler.reset_user_data_context') as reset, patch('utils.error_handler.delete_all_user_files'), patch('utils.error_handler.OWNER_USER_ID_INT', 99), patch('utils.error_handler._alerted', {}):
            asyncio.run(on_error(update, context))
        reset.assert_called_once_with(42, context.user_data)
        reply.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()
        self.assertNotIn('private text', context.bot.send_message.call_args.kwargs['text'])

    def test_forbidden_marks_user_blocked_without_reply(self):
        from telegram.error import Forbidden
        update = SimpleNamespace(update_id=18, effective_user=SimpleNamespace(id=42), effective_message=SimpleNamespace(reply_text=AsyncMock()))
        context = SimpleNamespace(error=Forbidden('blocked'), user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))
        user = SimpleNamespace(user_status_id=1, save=Mock())
        status = SimpleNamespace(id=7)
        with patch('utils.error_handler.User.where') as users, patch('utils.error_handler.UserStatus.where') as statuses:
            users.return_value.first.return_value = user
            statuses.return_value.first.return_value = status
            asyncio.run(on_error(update, context))
        self.assertEqual(user.user_status_id, 7)
        user.save.assert_called_once()
        update.effective_message.reply_text.assert_not_awaited()

    def test_unrelated_bad_request_is_unexpected_and_does_not_log_exception_text(self):
        from telegram.error import BadRequest

        reply = AsyncMock()
        update = SimpleNamespace(update_id=19, effective_user=SimpleNamespace(id=42), effective_message=SimpleNamespace(reply_text=reply))
        context = SimpleNamespace(error=BadRequest('private detail'), user_data={'language': 'en'}, bot=SimpleNamespace(send_message=AsyncMock()))
        with patch('utils.error_handler.reset_user_data_context'), patch('utils.error_handler.delete_all_user_files'), patch('utils.error_handler.OWNER_USER_ID_INT', None), patch('utils.error_handler.logger') as logger:
            asyncio.run(on_error(update, context))
        reply.assert_awaited_once()
        logger.error.assert_called_once()
        self.assertNotIn('private detail', str(logger.error.call_args))


if __name__ == '__main__':
    unittest.main()
