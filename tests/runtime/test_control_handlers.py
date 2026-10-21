"""Exercise actual Telegram-registered handlers without network or database writes."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

# Use the same import order as bot.py to satisfy the existing module imports.
import modules.core.handlers
from modules.tag_editor.registerer import registry as tags
from modules.bitrate_changer.registerer import registry as bitrate
from modules.cutter.registerer import registry as cutter
from modules.voice_converter.registerer import registry as voice
from modules.tag_editor.handlers import handle_tag_editor
from modules.cutter.handlers import handle_cutter

class RegisteredControlTests(unittest.TestCase):
    def test_every_registered_action_upserts_before_disabled_reply(self):
        for feature,registry in [('tag_editor',tags),('bitrate_changer',bitrate),('cutter',cutter),('voice_converter',voice)]:
            actions=[handler.callback for handler in registry()]
            if feature=='tag_editor':actions.append(handle_tag_editor)
            if feature=='cutter':actions.append(handle_cutter)
            for action in actions:
                with self.subTest(feature=feature,action=action.__name__):
                    self.assertEqual(action.runtime_control_feature,feature)
                    reply=AsyncMock()
                    update=SimpleNamespace(effective_user=SimpleNamespace(id=42,username='tester'),
                                           effective_message=SimpleNamespace(reply_text=reply))
                    context=SimpleNamespace(user_data={})
                    user=SimpleNamespace(user_id=42,username='tester',user_status_id=1,save=Mock())
                    with patch('runtime_controls.bot_settings',return_value={feature:False}),patch('utils.decorators.User.where') as users:
                        users.return_value.first.return_value=user
                        asyncio.run(action(update,context))
                    users.assert_called_once_with('user_id', '=', 42)
                    user.save.assert_called_once()
                    reply.assert_awaited_once()
                    self.assertIn('temporarily unavailable',reply.call_args.args[0])

    def test_disabled_message_uses_each_selected_language_and_english_fallback(self):
        from runtime_controls import disabled_message
        for language in ['en','fa','ru','es','fr','ar','hi','id']:
            with self.subTest(language=language):
                expected=disabled_message(language)
                self.assertTrue(expected)
                self.assertNotIn('missing translation',expected)
                if language!='en':self.assertNotEqual(expected,disabled_message('en'))
                for feature,registry in [('tag_editor',tags),('bitrate_changer',bitrate),('cutter',cutter),('voice_converter',voice)]:
                    reply=AsyncMock()
                    update=SimpleNamespace(effective_user=SimpleNamespace(id=42,username='tester'),
                                           effective_message=SimpleNamespace(reply_text=reply))
                    context=SimpleNamespace(user_data={'language':language})
                    user=SimpleNamespace(user_id=42,username='tester',user_status_id=1,save=Mock())
                    with patch('runtime_controls.bot_settings',return_value={feature:False}),patch('utils.decorators.User.where') as users:
                        users.return_value.first.return_value=user
                        asyncio.run(registry()[0].callback(update,context))
                    reply.assert_awaited_once_with(expected,parse_mode=None)
        self.assertEqual(disabled_message('unknown'),disabled_message('en'))

if __name__=='__main__':unittest.main()
