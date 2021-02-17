import unittest


class TestTest(unittest.TestCase):
    def test_first(self):
        self.assertEqual(sum([4, 3]), 7)

    def test_second(self):
        self.assertEqual(sum([4, 3]), 7)

    def test_third(self):
        self.assertEqual(sum([4, 3]), 8)

    def test_fourth(self):
        self.assertEqual(sum([4, 3]), 7)


if __name__ == '__main__':
    print('Hi')
    unittest.main()
