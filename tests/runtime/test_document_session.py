"""Document intake keeps existing work and routes supported files correctly."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import modules.core.handlers  # Match bot.py's import order.
from config.modules import Module
from modules.core.handlers import handle_music_message, ignore_file
from modules.core.registerer import AudioDocumentFilter, registry as core_registry
from modules.tag_editor.handlers import handle_photo_message
from modules.tag_editor.registerer import registry as tag_registry
from utils import t


def inner(handler):
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


def filtered_update(message):
    return SimpleNamespace(
        message=message, effective_message=message,
        channel_post=None, edited_channel_post=None, edited_message=None,
        business_message=None, edited_business_message=None,
    )


class DocumentSessionTests(unittest.TestCase):
    def test_image_document_is_registered_and_sets_art_without_losing_session(self):
        image_handler = next(handler for handler in tag_registry() if handler.callback is handle_photo_message)
        for filename, mime_type in (('cover.jpg', 'image/jpeg'), ('cover.png', 'image/png')):
            with self.subTest(filename=filename):
                document = SimpleNamespace(file_id='cover-file', file_name=filename, mime_type=mime_type)
                message = SimpleNamespace(document=document, photo=[], chat_id=42, reply_text=AsyncMock())
                user_data = {
                    'user': SimpleNamespace(user_id=42, username='tester'), 'language': 'en',
                    'music_path': '/data/song.mp3', 'music_message_id': 11, 'music_duration': 20,
                    'current_module': Module.TAG_EDITOR.value,
                    'tag_editor': {'current_tag': 'album_art', 'title': 'Keep this title'},
                }
                context = SimpleNamespace(user_data=user_data)
                update = SimpleNamespace(message=message, effective_message=message)
                self.assertTrue(image_handler.filters.filter(filtered_update(message)))
                with patch('modules.tag_editor.handlers.download_file', new=AsyncMock(return_value='/data/cover.jpg')) as download:
                    asyncio.run(inner(handle_photo_message)(update, context))
                download.assert_awaited_once_with(user_id=42, file_to_download=document, file_type='photo', context=context)
                self.assertEqual(user_data['music_path'], '/data/song.mp3')
                self.assertEqual(user_data['tag_editor']['title'], 'Keep this title')
                self.assertEqual(user_data['tag_editor']['new_art_path'], '/data/cover.jpg')

    def test_unsupported_document_reports_without_clearing_session(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        user_data = {
            'user': SimpleNamespace(user_id=42, username='tester'), 'language': 'en',
            'music_path': '/data/song.mp3', 'music_message_id': 11, 'music_duration': 20,
            'current_module': Module.TAG_EDITOR.value,
            'tag_editor': {'current_tag': 'title', 'title': 'Keep this title'},
        }
        original = dict(user_data)
        update = SimpleNamespace(message=message, effective_message=message)

        asyncio.run(inner(ignore_file)(update, SimpleNamespace(user_data=user_data)))

        message.reply_text.assert_awaited_once_with(text=t('en', 'unsupportedFileMessage'))
        self.assertEqual(user_data, original)
        for language in ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id'):
            with self.subTest(language=language):
                self.assertNotIn('missing translation', t(language, 'unsupportedFileMessage'))

    def test_image_document_outside_album_art_step_is_not_consumed_or_reset(self):
        document = SimpleNamespace(file_id='cover-file', file_name='cover.png', mime_type='image/png')
        message = SimpleNamespace(document=document, photo=[], chat_id=42, reply_text=AsyncMock())
        user_data = {
            'user': SimpleNamespace(user_id=42, username='tester'), 'language': 'en',
            'music_path': '/data/song.mp3', 'music_message_id': 11, 'music_duration': 20,
            'current_module': Module.TAG_EDITOR.value,
            'tag_editor': {'current_tag': 'title', 'title': 'Keep this title'},
        }
        update = SimpleNamespace(message=message, effective_message=message)

        with patch('modules.tag_editor.handlers.download_file', new=AsyncMock()) as download:
            asyncio.run(inner(handle_photo_message)(update, SimpleNamespace(user_data=user_data)))

        download.assert_not_awaited()
        message.reply_text.assert_awaited_once_with(text=t('en', 'unsupportedFileMessage'))
        self.assertEqual(user_data['music_path'], '/data/song.mp3')
        self.assertEqual(user_data['tag_editor']['title'], 'Keep this title')

    def test_audio_document_is_routed_to_audio_intake_by_mime_or_extension(self):
        for document in (
            SimpleNamespace(mime_type='audio/flac', file_name='track.bin'),
            SimpleNamespace(mime_type='application/octet-stream', file_name='track.flac'),
        ):
            with self.subTest(document=document):
                self.assertTrue(AudioDocumentFilter().filter(SimpleNamespace(document=document)))
        self.assertFalse(AudioDocumentFilter().filter(SimpleNamespace(
            document=SimpleNamespace(mime_type='application/octet-stream', file_name='notes.pdf'))))

        document = SimpleNamespace(
            file_id='audio-file', file_name='track.flac', mime_type='application/octet-stream', file_size=100,
        )
        message = SimpleNamespace(
            audio=None, document=document, video=None, contact=None,
            message_id=11, chat_id=42, reply_text=AsyncMock(),
        )
        user_data = {'user': SimpleNamespace(user_id=42, username='tester'), 'language': 'en'}
        context = SimpleNamespace(user_data=user_data, bot=SimpleNamespace(send_chat_action=AsyncMock()))
        update = SimpleNamespace(
            message=message, effective_message=message,
            effective_user=SimpleNamespace(id=42), update_id=1,
        )
        with patch('modules.core.registerer.Language.ordered', return_value=[]):
            handlers = core_registry()
        audio_handler = next(handler for handler in handlers if handler.callback is handle_music_message)
        unsupported_handler = next(handler for handler in handlers if handler.callback is ignore_file)
        self.assertTrue(audio_handler.filters.filter(filtered_update(message)))
        self.assertFalse(unsupported_handler.filters.filter(filtered_update(message)))
        unsupported_document = SimpleNamespace(
            mime_type='application/pdf', file_name='notes.pdf',
        )
        self.assertTrue(unsupported_handler.filters.filter(filtered_update(SimpleNamespace(
            audio=None, document=unsupported_document, video=None, contact=None))))
        self.assertTrue(unsupported_handler.filters.filter(filtered_update(SimpleNamespace(
            audio=None, document=None, video=None, contact=object()))))

        with patch('modules.core.handlers.create_user_directory'), \
             patch('modules.core.handlers.download_file', new=AsyncMock(return_value='/data/track.flac')) as download, \
             patch('modules.core.handlers.read_and_store_music_tags', new=AsyncMock()), \
             patch('modules.core.handlers.increment_file_counter_for_user'), \
             patch('modules.core.handlers.show_module_selector', new=AsyncMock()):
            asyncio.run(inner(handle_music_message)(update, context))

        download.assert_awaited_once_with(user_id=42, file_to_download=document, file_type='audio', context=context)
        self.assertEqual(user_data['music_path'], '/data/track.flac')


if __name__ == '__main__':
    unittest.main()
