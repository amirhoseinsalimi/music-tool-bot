"""Bounded audio work, localized timeout reporting, and nonblocking updates."""

import ast
import asyncio
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from modules.core.media import probe_audio_format
from utils.logging import (
    MEDIA_PROCESS_TIMEOUT_SECONDS,
    MediaProcessingTimeoutError,
    run_ffmpeg,
)
from utils.update_processor import UserUpdateProcessor


ROOT = Path(__file__).resolve().parents[2]
LOCALES = ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id')
BLOCKING_CALLS = {
    'convert_bitrate', 'convert_m4a_to_mp3', 'convert_to_voice', 'cut',
    'load_file', 'probe_audio_format', 'resize_image', 'run_ffmpeg', 'save_tags_to_file',
}
HANDLER_FILES = (
    'modules/core/handlers.py',
    'modules/cutter/handlers.py',
    'modules/bitrate_changer/handlers.py',
    'modules/voice_converter/handlers.py',
    'modules/tag_editor/handlers.py',
    'modules/tag_editor/service.py',
)


class AudioProcessingTests(unittest.TestCase):
    """Verify timeout enforcement and the update processor's safety boundary."""

    def test_hard_timeout_kills_a_slow_ffmpeg_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ffmpeg = root / 'ffmpeg'
            pid_file = root / 'pid'
            ffmpeg.write_text(
                '#!/usr/bin/env python3\n'
                'import os, time\n'
                f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
                'time.sleep(30)\n',
                encoding='utf-8',
            )
            ffmpeg.chmod(0o755)
            real_run = subprocess.run

            def short_test_timeout(command, **kwargs):
                self.assertEqual(kwargs['timeout'], 60)
                kwargs['timeout'] = 0.1
                return real_run(command, **kwargs)

            with patch.dict(os.environ, {'PATH': f"{directory}{os.pathsep}{os.environ['PATH']}"}):
                with patch('utils.logging.subprocess.run', side_effect=short_test_timeout):
                    with self.assertRaises(MediaProcessingTimeoutError):
                        run_ffmpeg(['ffmpeg'], 'slow test input')

            process_id = int(pid_file.read_text(encoding='utf-8'))
            with self.assertRaises(ProcessLookupError):
                os.kill(process_id, 0)

    def test_ffprobe_uses_the_same_hard_timeout(self):
        with patch('modules.core.media.subprocess.run', side_effect=subprocess.TimeoutExpired('ffprobe', 60)) as run:
            with self.assertRaises(MediaProcessingTimeoutError):
                probe_audio_format('audio.mp3')
        self.assertEqual(run.call_args.kwargs['timeout'], MEDIA_PROCESS_TIMEOUT_SECONDS)

    def test_same_user_waiters_do_not_block_other_users_or_share_locks(self):
        async def scenario(fake_ffmpeg: Path) -> None:
            processor = UserUpdateProcessor(max_concurrent_updates=4)
            started = fake_ffmpeg.with_suffix('.started')
            finished = fake_ffmpeg.with_suffix('.finished')
            slow_command = [str(fake_ffmpeg), str(started), str(finished)]
            same_user_finished = asyncio.Event()
            other_user_finished = asyncio.Event()

            async def process_slow_media() -> None:
                await asyncio.to_thread(run_ffmpeg, slow_command, 'slow test input')

            async def mark_same_user() -> None:
                same_user_finished.set()

            async def mark_other_user() -> None:
                other_user_finished.set()

            def update(user_id: int):
                return SimpleNamespace(
                    effective_user=SimpleNamespace(id=user_id),
                    effective_chat=SimpleNamespace(id=user_id),
                )

            slow_task = asyncio.create_task(processor.process_update(update(1), process_slow_media()))
            for _ in range(200):
                if started.exists():
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(started.exists(), 'fake ffmpeg did not start')

            same_user_tasks = [
                asyncio.create_task(processor.process_update(update(1), mark_same_user()))
                for _ in range(3)
            ]
            # IDs 1 and 65 collided in the previous 64-lock stripe scheme.
            other_user_task = asyncio.create_task(processor.process_update(update(65), mark_other_user()))
            for _ in range(200):
                if processor._user_locks.get(('user', 1), (None, 0))[1] == 4:
                    break
                await asyncio.sleep(0.001)
            self.assertEqual(processor._user_locks[('user', 1)][1], 4)
            await asyncio.wait_for(other_user_finished.wait(), timeout=0.2)
            self.assertFalse(finished.exists(), 'fake ffmpeg finished before the concurrency assertion')
            self.assertFalse(same_user_finished.is_set(), 'same-user update overlapped media processing')

            await asyncio.gather(slow_task, *same_user_tasks, other_user_task)
            self.assertTrue(finished.exists())
            self.assertFalse(processor._user_locks, 'idle user locks should be discarded')

        with tempfile.TemporaryDirectory() as directory:
            ffmpeg = Path(directory) / 'ffmpeg'
            ffmpeg.write_text(
                '#!/usr/bin/env python3\n'
                'import sys, time\n'
                'from pathlib import Path\n'
                'Path(sys.argv[1]).touch()\n'
                'time.sleep(0.6)\n'
                'Path(sys.argv[2]).touch()\n',
                encoding='utf-8',
            )
            ffmpeg.chmod(0o755)
            asyncio.run(scenario(ffmpeg))

    def test_blocking_media_calls_inside_async_functions_are_threaded(self):
        for relative_path in HANDLER_FILES:
            tree = ast.parse((ROOT / relative_path).read_text(encoding='utf-8'))
            parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
            for function in (node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)):
                for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                    name = call.func.attr if isinstance(call.func, ast.Attribute) else (
                        call.func.id if isinstance(call.func, ast.Name) else None
                    )
                    if name not in BLOCKING_CALLS:
                        continue
                    ancestor = call
                    threaded = False
                    while ancestor in parents:
                        ancestor = parents[ancestor]
                        if (isinstance(ancestor, ast.Call)
                                and isinstance(ancestor.func, ast.Attribute)
                                and isinstance(ancestor.func.value, ast.Name)
                                and ancestor.func.value.id == 'asyncio'
                                and ancestor.func.attr == 'to_thread'):
                            threaded = True
                            break
                    self.assertTrue(
                        threaded,
                        f'{relative_path}:{call.lineno} {name} must run through asyncio.to_thread',
                    )

    def test_timeout_message_is_translated_in_all_eight_catalogs(self):
        english = None
        messages = {}
        for locale in LOCALES:
            catalog = yaml.safe_load((ROOT / 'i18n' / f'{locale}.yaml').read_text(encoding='utf-8'))
            message = catalog[locale].get('errAudioProcessingTimeout')
            self.assertTrue(message, f'missing timeout message in {locale}')
            messages[locale] = message
            if locale == 'en':
                english = message
        self.assertEqual(len(set(messages.values())), len(LOCALES))
        self.assertTrue(english)


if __name__ == '__main__':
    unittest.main()
