import logging
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.retention import (FILE_RETENTION_DAYS, get_file_retention_days,
                             purge_expired_downloads, purge_expired_log_files)


class FileRetentionTests(unittest.TestCase):
    def test_retention_setting_defaults_and_clamps(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(get_file_retention_days(), 14)
        with patch.dict('os.environ', {'FILE_RETENTION_DAYS': '60'}):
            self.assertEqual(get_file_retention_days(), 60)
        with patch.dict('os.environ', {'FILE_RETENTION_DAYS': '61'}):
            self.assertEqual(get_file_retention_days(), 60)
        with patch.dict('os.environ', {'FILE_RETENTION_DAYS': '0'}):
            self.assertEqual(get_file_retention_days(), 1)
        with patch.dict('os.environ', {'FILE_RETENTION_DAYS': 'invalid'}):
            self.assertEqual(get_file_retention_days(), 14)

    def test_only_aged_user_media_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'downloads'
            user = root / '123'
            user.mkdir(parents=True)
            old = user / 'old.mp3'
            old.write_bytes(b'old')
            recent = user / 'recent.mp3'
            recent.write_bytes(b'recent')
            outside = Path(directory) / 'outside.mp3'
            outside.write_bytes(b'outside')
            (user / 'link.mp3').symlink_to(outside)
            now = time.time()
            aged = now - (FILE_RETENTION_DAYS + 1) * 86400
            os.utime(old, (aged, aged))

            self.assertEqual(purge_expired_downloads(root, now, root / 'logs'), 1)
            self.assertFalse(old.exists())
            self.assertEqual(recent.read_bytes(), b'recent')
            self.assertEqual(outside.read_bytes(), b'outside')
            self.assertTrue((user / 'link.mp3').is_symlink())

    def test_only_aged_inactive_log_files_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'old.log'
            old.write_text('old', encoding='utf-8')
            recent = root / 'recent.log'
            recent.write_text('recent', encoding='utf-8')
            active = root / 'active.log'
            active.write_text('active', encoding='utf-8')
            now = time.time()
            aged = now - (FILE_RETENTION_DAYS + 1) * 86400
            os.utime(old, (aged, aged))
            os.utime(active, (aged, aged))
            handler = logging.FileHandler(active)
            logging_logger = logging.getLogger('music_tool_bot')
            logging_logger.addHandler(handler)
            try:
                self.assertEqual(purge_expired_log_files(root, now), 1)
            finally:
                logging_logger.removeHandler(handler)
                handler.close()
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(active.exists())
