import os
import tempfile
import time
import unittest
from pathlib import Path

from utils.retention import FILE_RETENTION_DAYS, purge_expired_downloads


class FileRetentionTests(unittest.TestCase):
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

            self.assertEqual(purge_expired_downloads(root, now), 1)
            self.assertFalse(old.exists())
            self.assertEqual(recent.read_bytes(), b'recent')
            self.assertEqual(outside.read_bytes(), b'outside')
            self.assertTrue((user / 'link.mp3').is_symlink())
