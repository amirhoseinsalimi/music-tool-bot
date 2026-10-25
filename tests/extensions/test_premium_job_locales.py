import unittest
from pathlib import Path
import yaml


LOCALES = Path(__file__).resolve().parents[2] / "i18n"


class PremiumJobLocaleTests(unittest.TestCase):
    def test_claim_expiry_and_daily_limit_messages_exist_in_every_catalog(self):
        catalogs = sorted(LOCALES.glob("*.yaml"))
        self.assertEqual(len(catalogs), 8)
        for catalog in catalogs:
            with self.subTest(locale=catalog.stem):
                messages = yaml.safe_load(catalog.read_text(encoding="utf-8"))[catalog.stem]
                self.assertTrue(messages["starsJobExpired"].strip())
                self.assertIn("{job_id}", messages["starsJobExpired"])
                self.assertTrue(messages["starsJobClaimLimit"].strip())
