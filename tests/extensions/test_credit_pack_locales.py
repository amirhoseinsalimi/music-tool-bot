from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / 'i18n'


class CreditPackLocaleTests(unittest.TestCase):
    def test_every_catalog_uses_the_credit_pack_button_order(self):
        catalogs = sorted(LOCALES.glob('*.yaml'))
        self.assertTrue(catalogs)
        for catalog in catalogs:
            with self.subTest(locale=catalog.stem):
                content = catalog.read_text(encoding='utf-8')
                for key in ('starsCatalogNotice', 'starsPack', 'starsDiscountPack', 'starsTestPack'):
                    self.assertIsNotNone(
                        re.search(rf'^  {key}:', content, re.MULTILINE), key)

                button = re.search(r'^  starsDiscountPack: (.+)$', content, re.MULTILINE)
                self.assertIsNotNone(button, catalog.name)
                label = button.group(1)
                self.assertLess(label.index('{stars}'), label.index('{credits}'))
                self.assertLess(label.index('{credits}'), label.index('{discount}'))
                self.assertNotRegex(content, r'^  starsBonusCredits:', catalog.name)


if __name__ == '__main__':
    unittest.main()
