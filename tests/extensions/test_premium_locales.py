"""Premium Telegram responses remain present in every core locale."""

from pathlib import Path
import unittest

import yaml


LOCALES = ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id')
PREMIUM_KEYS = (
    'starsPremiumTitle',
    'starsFeatureAvailable',
    'starsFeatureUnavailable',
    'starsPremiumHelpInstructions',
    'starsJobProcessing',
    'starsJobInProgress',
    'starsJobCancelled',
    'starsCancelTooLate',
)


class PremiumLocaleTests(unittest.TestCase):
    def test_premium_message_keys_exist_and_are_translated_in_all_catalogs(self):
        root = Path(__file__).resolve().parents[2] / 'i18n'
        catalogs = {}
        for locale in LOCALES:
            with self.subTest(locale=locale):
                catalog = yaml.safe_load((root / f'{locale}.yaml').read_text(encoding='utf-8'))
                messages = catalog[locale]
                catalogs[locale] = messages
                for key in PREMIUM_KEYS:
                    self.assertIn(key, messages)
                    self.assertTrue(messages[key].strip())
                    if locale != 'en':
                        self.assertNotEqual(messages[key], catalogs.get('en', messages).get(key))

        self.assertEqual(set(catalogs), set(LOCALES))
        for locale in LOCALES[1:]:
            self.assertEqual(
                {key for key in PREMIUM_KEYS if key in catalogs[locale]},
                set(PREMIUM_KEYS),
            )


if __name__ == '__main__':
    unittest.main()
