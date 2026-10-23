import sys
import asyncio
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import modules.core.handlers
from config import envs
from modules.donation.handlers import show_donation_methods
from modules.donation.utils import ADDRESS_NAMES, donation_destinations, generate_donation_keyboard


def without_environment_addresses():
    return patch.multiple(envs, **{name: '' for name in ADDRESS_NAMES})


class DonationKeyboardTests(unittest.TestCase):
    def test_no_configured_methods_does_not_build_an_empty_keyboard(self):
        with without_environment_addresses(), patch.dict(sys.modules, {'premium.donation_defaults': None}):
            self.assertIsNone(generate_donation_keyboard())


    def test_private_receiving_defaults_build_the_keyboard_and_environment_can_override(self):
        package = ModuleType('premium')
        package.__path__ = []
        defaults = ModuleType('premium.donation_defaults')
        defaults.DONATION_ADDRESSES = {'BTC_WALLET_ADDRESS': 'private-btc',
                                      'ZARIN_LINK_ADDRESS': 'https://example.com/donate'}
        with without_environment_addresses(), patch.dict(sys.modules, {
            'premium': package, 'premium.donation_defaults': defaults,
        }):
            keyboard = generate_donation_keyboard()
            self.assertEqual([[button.text for button in row] for row in keyboard.keyboard],
                             [['Bitcoin', 'ZarinPal']])
            self.assertIs(keyboard.is_persistent, True)
            with patch.object(envs, 'BTC_WALLET_ADDRESS', 'environment-btc'):
                self.assertEqual(donation_destinations()['BTC_WALLET_ADDRESS'], 'environment-btc')

    def test_registered_donate_command_sends_configured_buttons(self):
        package = ModuleType('premium')
        package.__path__ = []
        defaults = ModuleType('premium.donation_defaults')
        defaults.DONATION_ADDRESSES = {'BTC_WALLET_ADDRESS': 'private-btc'}
        reply = AsyncMock()
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42, username='tester'),
                                 message=SimpleNamespace(reply_text=reply))
        context = SimpleNamespace(user_data={'language': 'en'})
        user = SimpleNamespace(user_id=42, username='tester', user_status_id=1, save=Mock())
        with without_environment_addresses(), patch.dict(sys.modules, {
            'premium': package, 'premium.donation_defaults': defaults,
        }), patch('utils.decorators.User.where') as users:
            users.return_value.first.return_value = user
            asyncio.run(show_donation_methods(update, context))
        markup = reply.call_args.kwargs['reply_markup']
        self.assertEqual(markup.keyboard[0][0].text, 'Bitcoin')
