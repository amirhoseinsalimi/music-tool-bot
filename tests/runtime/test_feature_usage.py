"""Completion telemetry runs only after a free-tool result was sent."""
import ast
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from feature_usage import send_file_and_record_completion


ROOT = Path(__file__).resolve().parents[2]
HANDLERS = (
    'modules/cutter/handlers.py',
    'modules/bitrate_changer/handlers.py',
    'modules/voice_converter/handlers.py',
    'modules/tag_editor/handlers.py',
)


class CompletionTelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_only_after_file_send_succeeds(self):
        steps = []

        async def send_file():
            steps.append('sent')
            return 'telegram-message'

        async def record(*_args):
            self.assertEqual(steps, ['sent'])
            steps.append('recorded')

        record_mock = AsyncMock(side_effect=record)
        with patch('feature_usage.record_completion', record_mock):
            result = await send_file_and_record_completion(
                send_file(), 'cutter', 123, 456
            )

        self.assertEqual(result, 'telegram-message')
        self.assertEqual(steps, ['sent', 'recorded'])
        record_mock.assert_awaited_once_with('cutter', 123, 456)

    async def test_failed_file_send_does_not_record(self):
        async def send_file():
            raise RuntimeError('send failed')

        record_mock = AsyncMock()
        with patch('feature_usage.record_completion', record_mock):
            with self.assertRaisesRegex(RuntimeError, 'send failed'):
                await send_file_and_record_completion(
                    send_file(), 'cutter', 123, 456
                )

        record_mock.assert_not_awaited()

    def test_every_free_tool_handler_uses_the_delivery_wrapper(self):
        for relative_path in HANDLERS:
            with self.subTest(handler=relative_path):
                tree = ast.parse((ROOT / relative_path).read_text())
                calls = [node for node in ast.walk(tree)
                         if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Name)
                         and node.func.id == 'send_file_and_record_completion']
                self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
