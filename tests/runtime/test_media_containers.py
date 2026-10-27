import asyncio
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Match the application import order, which resolves the feature package cycle.
import modules.core.handlers
from modules.cutter.service import cut
from modules.core.media import probe_audio_format
from modules.tag_editor.handlers import finish_editing_tags
from modules.tag_editor.service import remove_album_art


TOOLS_AVAILABLE = shutil.which('ffmpeg') and shutil.which('ffprobe')


def inner(handler):
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


@unittest.skipUnless(TOOLS_AVAILABLE, 'ffmpeg and ffprobe are required')
class MediaContainerTests(unittest.TestCase):
    FORMATS = {
        'mp3': ('.mp3', ['-c:a', 'libmp3lame']),
        'm4a': ('.m4a', ['-c:a', 'aac']),
        'ogg': ('.ogg', ['-c:a', 'libvorbis']),
        'flac': ('.flac', ['-c:a', 'flac']),
        'wav': ('.wav', ['-c:a', 'pcm_s16le']),
        'aac': ('.aac', ['-c:a', 'aac', '-f', 'adts']),
    }
    CODECS = {'mp3': 'mp3', 'm4a': 'aac', 'ogg': 'vorbis', 'flac': 'flac', 'wav': 'pcm_s16le', 'aac': 'aac'}

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.inputs = {}
        for name, (extension, codec_args) in self.FORMATS.items():
            path = self.root / f'input_{name}{extension}'
            subprocess.run(
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                 '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
                 *codec_args, str(path)],
                check=True,
                capture_output=True,
            )
            self.inputs[name] = path

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def probe(path):
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=format_name:stream=codec_name,codec_type', '-of', 'json', str(path)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)

    def test_cut_outputs_mp3_for_every_supported_input(self):
        for name, input_path in self.inputs.items():
            with self.subTest(format=name):
                output = self.root / f'cut_{name}.mp3'
                cut(str(input_path), 0, 1, str(output))
                details = self.probe(output)
                self.assertEqual(output.suffix, '.mp3')
                self.assertEqual(details['streams'][0]['codec_name'], 'mp3')

    def test_remove_album_art_preserves_each_container_and_extension(self):
        class Message:
            reply_text = AsyncMock()

        class Update:
            message = Message()

        for name, source in self.inputs.items():
            with self.subTest(format=name):
                input_path = self.root / f'art_{name}{source.suffix}'
                shutil.copyfile(source, input_path)
                user_data = {
                    'music_path': str(input_path),
                    'tag_editor': {},
                }
                with patch('modules.tag_editor.service.t', return_value='ok'):
                    asyncio.run(remove_album_art(Update(), user_data, 'en'))
                self.assertTrue(input_path.exists())
                details = self.probe(input_path)
                self.assertEqual(details['streams'][0]['codec_type'], 'audio')
                self.assertEqual(input_path.suffix, self.FORMATS[name][0])
                self.assertEqual(details['streams'][0]['codec_name'], self.CODECS[name])
                self.assertEqual(probe_audio_format(str(input_path))[0], self.FORMATS[name][0])

    def test_tag_editor_delivery_uses_audio_or_document_with_real_extension(self):
        for name, source in self.inputs.items():
            with self.subTest(format=name):
                message = type('Message', (), {'message_id': 8, 'chat_id': 42})()
                message.reply_text = AsyncMock(return_value=type('Uploading', (), {'delete': AsyncMock()})())
                update = type('Update', (), {
                    'message': message,
                    'effective_message': message,
                    'effective_user': type('User', (), {'id': 42})(),
                    'update_id': 9,
                })()
                user_data = {
                    'language': 'en', 'music_path': str(source), 'music_message_id': 3,
                    'music_duration': 2, 'current_module': 'tag_editor',
                    'tag_editor': {'artist': 'Artist', 'title': 'Title'},
                    'user': type('User', (), {'user_id': 42})(),
                }
                bot = type('Bot', (), {
                    'send_chat_action': AsyncMock(),
                    'send_audio': AsyncMock(),
                    'send_document': AsyncMock(),
                })()
                context = type('Context', (), {'user_data': user_data, 'bot': bot})()
                with patch('modules.tag_editor.handlers.save_tags_to_file'), \
                     patch('modules.tag_editor.handlers.record_completion', new=AsyncMock()):
                    asyncio.run(inner(finish_editing_tags)(update, context))
                expected_method = 'send_audio' if source.suffix in {'.mp3', '.m4a'} else 'send_document'
                self.assertTrue(getattr(bot, expected_method).await_count == 1)
                self.assertEqual(getattr(bot, expected_method).call_args.kwargs['filename'], f'Artist - Title{source.suffix}')
                unexpected_method = 'send_document' if expected_method == 'send_audio' else 'send_audio'
                self.assertEqual(getattr(bot, unexpected_method).await_count, 0)


if __name__ == '__main__':
    unittest.main()
