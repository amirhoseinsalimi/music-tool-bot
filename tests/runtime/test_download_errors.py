import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import BadRequest

from utils.fs import download_file


class DownloadErrorTests(unittest.TestCase):
    def test_get_file_bad_request_is_preserved(self):
        context = SimpleNamespace(bot=SimpleNamespace(get_file=AsyncMock(side_effect=BadRequest('too big'))))
        media = SimpleNamespace(file_id='file-1')

        with self.assertRaises(BadRequest):
            asyncio.run(download_file(42, media, 'audio', context))

    def test_download_bad_request_is_preserved(self):
        telegram_file = SimpleNamespace(file_id='file-2', download_to_drive=AsyncMock(side_effect=BadRequest('too big')))
        context = SimpleNamespace(bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file)))
        media = SimpleNamespace(file_id='file-2', mime_type='audio/mpeg', file_name='track.mp3')

        with patch('utils.fs.Path.mkdir'):
            with self.assertRaises(BadRequest):
                asyncio.run(download_file(42, media, 'audio', context))


if __name__ == '__main__':
    unittest.main()
