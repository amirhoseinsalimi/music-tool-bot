"""Sessionless updates should get a localized start prompt instead of indexing missing state."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import modules.core.handlers  # Match bot.py's import order.
from modules.bitrate_changer.handlers import change_bitrate, show_bitrate_changer_keyboard
from modules.core.handlers import handle_responses
from modules.cutter.handlers import handle_cutter, show_cutter_help
from modules.tag_editor.handlers import (
    ask_for_tag,
    ask_which_tag_to_edit,
    display_preview,
    finish_editing_tags,
    handle_photo_message,
    handle_tag_editor,
)
from modules.voice_converter.handlers import send_file_as_voice
from telegram import ReplyKeyboardRemove
from utils import t
from utils.misc import is_user_data_empty


def inner(handler):
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


class SessionlessHandlerTests(unittest.TestCase):
    def test_incomplete_state_is_sessionless_but_complete_legacy_state_is_valid(self):
        self.assertTrue(is_user_data_empty({'user': object(), '_new_user_on_this_update': True}))
        self.assertTrue(is_user_data_empty({'session_started': True, 'music_path': 'stale.mp3'}))
        legacy = {
            'music_path': 'song.mp3', 'current_module': '', 'music_duration': 30,
            'tag_editor': {}, 'music_message_id': 1,
        }
        self.assertFalse(is_user_data_empty(legacy))

    def test_registered_session_dependent_handlers_reply_in_all_languages(self):
        handlers = (
            handle_responses,
            change_bitrate,
            show_bitrate_changer_keyboard,
            handle_tag_editor,
            handle_photo_message,
            ask_which_tag_to_edit,
            display_preview,
            finish_editing_tags,
            ask_for_tag,
            send_file_as_voice,
            handle_cutter,
            show_cutter_help,
        )
        for language in ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id'):
            for handler in handlers:
                with self.subTest(language=language, handler=handler.__name__):
                    reply = AsyncMock()
                    message = SimpleNamespace(
                        text='not a session value', photo=[], message_id=1,
                        reply_text=reply,
                    )
                    user = SimpleNamespace(user_id=42, username='tester')
                    context = SimpleNamespace(user_data={
                        'user': user,
                        '_new_user_on_this_update': True,
                        'language': language,
                    })
                    update = SimpleNamespace(
                        message=message, effective_message=message,
                        effective_user=SimpleNamespace(id=42), update_id=1,
                    )

                    asyncio.run(inner(handler)(update, context))

                    reply.assert_awaited_once()
                    self.assertEqual(reply.call_args.kwargs.get('text'), t(language, 'defaultMessage'))
                    if handler is handle_photo_message:
                        markup = reply.call_args.kwargs.get('reply_markup')
                        self.assertIsInstance(markup, ReplyKeyboardRemove)
                        self.assertTrue(markup.remove_keyboard)

    def test_initialized_no_audio_photo_still_removes_the_keyboard(self):
        reply = AsyncMock()
        message = SimpleNamespace(text=None, photo=[], message_id=1, reply_text=reply)
        context = SimpleNamespace(user_data={
            'user': SimpleNamespace(user_id=42, username='tester'),
            'session_started': True,
            'music_path': '',
            'current_module': '',
            'music_duration': 0,
            'tag_editor': {},
            'music_message_id': 0,
            'language': 'en',
        })
        update = SimpleNamespace(message=message, effective_message=message)

        asyncio.run(inner(handle_photo_message)(update, context))

        markup = reply.call_args.kwargs.get('reply_markup')
        self.assertIsInstance(markup, ReplyKeyboardRemove)
        self.assertTrue(markup.remove_keyboard)


if __name__ == '__main__':
    unittest.main()
