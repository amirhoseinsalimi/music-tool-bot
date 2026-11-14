"""Bot delivery outcomes never retry ambiguous Telegram sends."""

import asyncio
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from admin_bridge.outbox import deliver_outbox_message


class OutboxDeliveryTests(unittest.TestCase):
    """Verify the bot sends queued text and records safe terminal/retry states."""

    def setUp(self):
        self.message = {
            'id': '71b9bd57-0a19-4f17-9389-88440f386a00',
            'target_user_id': 7000000001,
            'message_text': 'hello',
            'attempts': 1,
        }
        self.send_message = AsyncMock()
        self.context = SimpleNamespace(bot=SimpleNamespace(send_message=self.send_message))

    def run_delivery(self):
        """Run the async worker once and return its persisted-state mock."""
        with patch('admin_bridge.outbox.claim_message', return_value=self.message), \
                patch('admin_bridge.outbox.finish_message') as finish:
            asyncio.run(deliver_outbox_message(self.context))
        return finish

    def test_success_records_sent_and_sends_to_the_queued_recipient(self):
        """A successful Telegram response marks the item sent."""
        finish = self.run_delivery()
        self.send_message.assert_awaited_once_with(chat_id=7000000001, text='hello')
        finish.assert_called_once_with(self.message['id'], 'sent')

    def test_forbidden_recipient_is_failed_and_marked_blocked(self):
        """A blocked recipient is terminal and updates the user's bot status."""
        self.send_message.side_effect = Forbidden('blocked')
        finish = self.run_delivery()
        finish.assert_called_once_with(
            self.message['id'], 'failed', 'recipient_blocked', None, 7000000001,
        )

    def test_bad_request_fails_without_retrying(self):
        """Invalid Telegram message content is terminal."""
        self.send_message.side_effect = BadRequest('rejected')
        finish = self.run_delivery()
        finish.assert_called_once_with(self.message['id'], 'failed', 'telegram_rejected')

    def test_rate_limit_is_requeued_but_ambiguous_telegram_error_is_not(self):
        """Known rate limits retry later; ambiguous results never do."""
        self.send_message.side_effect = RetryAfter(5)
        finish = self.run_delivery()
        finish.assert_called_once_with(self.message['id'], 'queued', 'rate_limited', 5)

        self.send_message.reset_mock()
        self.send_message.side_effect = RetryAfter(timedelta(seconds=5.2))
        finish = self.run_delivery()
        finish.assert_called_once_with(self.message['id'], 'queued', 'rate_limited', 6)

        self.send_message.reset_mock()
        self.send_message.side_effect = TelegramError('network failure')
        finish = self.run_delivery()
        finish.assert_called_once_with(
            self.message['id'], 'delivery_unknown', 'delivery_unknown',
        )


if __name__ == '__main__':
    unittest.main()
