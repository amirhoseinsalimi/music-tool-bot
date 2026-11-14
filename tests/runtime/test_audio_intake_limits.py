"""Audio intake limits and accepted-file counting, using faked Telegram files."""
import asyncio
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import modules.core.handlers  # Match the application's import order.
from config.envs import MAX_DURATION_SECONDS, get_positive_int_env
from modules.core.handlers import MAX_DOWNLOAD_BYTES, handle_music_message
from modules.tag_editor.service import read_and_store_music_tags
from telegram.error import BadRequest
from utils import t


class AudioIntakeLimitTests(unittest.TestCase):
    def make_update(self, file_size=MAX_DOWNLOAD_BYTES, duration=60):
        message = SimpleNamespace(
            audio=SimpleNamespace(
                file_id='telegram-audio-id', file_name='audio.mp3', mime_type='audio/mpeg',
                file_size=file_size, duration=timedelta(seconds=duration),
                performer=None, title=None, thumbnail=None,
            ),
            message_id=17,
            chat_id=42,
            reply_text=AsyncMock(),
        )
        user = SimpleNamespace(user_id=42, username='tester')
        update = SimpleNamespace(
            message=message, effective_message=message,
            effective_user=SimpleNamespace(id=42), update_id=9,
        )
        context = SimpleNamespace(
            user_data={'user': user, 'language': 'en'},
            bot=SimpleNamespace(send_chat_action=AsyncMock(), get_file=AsyncMock()),
        )
        return update, context, message

    def test_exact_size_and_duration_boundaries_are_accepted_and_counted(self):
        for file_size in (MAX_DOWNLOAD_BYTES, None):
            with self.subTest(file_size=file_size):
                update, context, _message = self.make_update(file_size=file_size, duration=MAX_DURATION_SECONDS)
                with patch('modules.core.handlers.create_user_directory'), \
                     patch('modules.core.handlers.download_file', new=AsyncMock(return_value='/tmp/song.mp3')) as download, \
                     patch('modules.core.handlers.read_and_store_music_tags', new=AsyncMock(return_value=True)), \
                     patch('modules.core.handlers.increment_file_counter_for_user') as counter, \
                     patch('modules.core.handlers.show_module_selector', new=AsyncMock()) as show_selector:
                    asyncio.run(handle_music_message.__wrapped__(update, context))
                download.assert_awaited_once()
                counter.assert_called_once_with(user_id=42)
                show_selector.assert_awaited_once()

    def test_duration_limit_uses_positive_config_with_a_default(self):
        self.assertGreater(MAX_DURATION_SECONDS, 0)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_positive_int_env('TEST_MAX_DURATION', 3600), 3600)
        with patch.dict(os.environ, {'TEST_MAX_DURATION': '7200'}):
            self.assertEqual(get_positive_int_env('TEST_MAX_DURATION', 3600), 7200)
        for value in ('0', '-1', 'invalid'):
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_MAX_DURATION': value}):
                self.assertEqual(get_positive_int_env('TEST_MAX_DURATION', 3600), 3600)

    def test_limit_messages_exist_in_all_locales(self):
        for language in ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id'):
            with self.subTest(language=language):
                size_message = t(language, 'errTooLargeFile')
                duration_message = t(language, 'errAudioTooLong', maxDuration=MAX_DURATION_SECONDS)
                self.assertNotIn('missing translation', size_message)
                self.assertNotIn('missing translation', duration_message)
                self.assertIn(str(MAX_DURATION_SECONDS), duration_message)

    def test_one_byte_over_size_limit_is_rejected_before_download(self):
        update, context, message = self.make_update(file_size=MAX_DOWNLOAD_BYTES + 1)
        with patch('modules.core.handlers.increment_file_counter_for_user') as counter, \
             patch('modules.core.handlers.download_file', new=AsyncMock()) as download:
            asyncio.run(handle_music_message.__wrapped__(update, context))
        message.reply_text.assert_awaited_once()
        self.assertEqual(message.reply_text.call_args.kwargs['text'], t('en', 'errTooLargeFile'))
        self.assertIn('20', message.reply_text.call_args.kwargs['text'])
        self.assertIsNotNone(message.reply_text.call_args.kwargs['reply_markup'])
        counter.assert_not_called()
        download.assert_not_awaited()

    def test_unknown_size_is_tried_and_bad_request_from_get_file_or_download_is_localized(self):
        async def run():
            for failure_stage in ('get_file', 'download_to_drive'):
                with self.subTest(stage=failure_stage), tempfile.TemporaryDirectory() as directory:
                    update, context, message = self.make_update(file_size=None)
                    telegram_file = SimpleNamespace(file_id='resolved-file-id',
                                                    download_to_drive=AsyncMock(side_effect=BadRequest('File is too big')))
                    if failure_stage == 'get_file':
                        context.bot.get_file.side_effect = BadRequest('File is too big')
                    else:
                        context.bot.get_file.return_value = telegram_file
                    with patch('modules.core.handlers.create_user_directory'), \
                         patch('utils.fs.DOWNLOAD_DIR_PATH', Path(directory)), \
                         patch('modules.core.handlers.increment_file_counter_for_user') as counter:
                        await handle_music_message.__wrapped__(update, context)
                    message.reply_text.assert_awaited_once()
                    self.assertEqual(message.reply_text.call_args.kwargs['text'], t('en', 'errTooLargeFile'))
                    self.assertIsNotNone(message.reply_text.call_args.kwargs['reply_markup'])
                    counter.assert_not_called()
        asyncio.run(run())

    def test_duration_limit_is_separate_and_bad_files_do_not_count(self):
        update, context, message = self.make_update(file_size=100, duration=3601)
        with patch('modules.core.handlers.increment_file_counter_for_user') as counter, \
             patch('modules.core.handlers.download_file', new=AsyncMock()) as download:
            asyncio.run(handle_music_message.__wrapped__(update, context))
        self.assertEqual(message.reply_text.call_args.kwargs['text'],
                         t('en', 'errAudioTooLong', maxDuration=3600))
        self.assertIsNotNone(message.reply_text.call_args.kwargs['reply_markup'])
        counter.assert_not_called()
        download.assert_not_awaited()

    def test_real_tag_reader_failure_resets_without_counting_or_opening_module_menu(self):
        async def run():
            for failure in (OSError('broken tags'), NotImplementedError('unsupported tags')):
                with self.subTest(failure=type(failure).__name__):
                    update, context, message = self.make_update(file_size=100)
                    with patch('modules.core.handlers.create_user_directory'), \
                         patch('modules.core.handlers.download_file', new=AsyncMock(return_value='/tmp/broken.mp3')), \
                         patch('modules.tag_editor.service.music_tag.load_file', side_effect=failure), \
                         patch('modules.core.handlers.increment_file_counter_for_user') as counter, \
                         patch('modules.core.handlers.show_module_selector', new=AsyncMock()) as show_selector:
                        await handle_music_message.__wrapped__(update, context)
                    self.assertEqual(message.reply_text.await_count, 1)
                    self.assertEqual(message.reply_text.call_args.kwargs['text'], t('en', 'errOnReadingTags'))
                    counter.assert_not_called()
                    show_selector.assert_not_awaited()
                    self.assertEqual(context.user_data['music_path'], '')
        asyncio.run(run())

    def test_tag_reader_reports_handled_failure_as_false_and_success_as_true(self):
        async def run():
            update, context, message = self.make_update()
            context.user_data.update({'music_path': '/tmp/song.mp3', 'tag_editor': {}})
            with patch('modules.tag_editor.service.music_tag.load_file', side_effect=OSError('bad audio')):
                self.assertFalse(await read_and_store_music_tags(update, context.user_data))
            message.reply_text.assert_awaited_once()
            music = MagicMock()
            music.get.return_value = ''
            music.raw = {}
            music.__getitem__.side_effect = KeyError
            with patch('modules.tag_editor.service.music_tag.load_file', return_value=music):
                self.assertTrue(await read_and_store_music_tags(update, context.user_data))
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
