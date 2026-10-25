import unittest

from utils.misc import is_user_data_empty, reset_user_data_context


class SessionStateTests(unittest.TestCase):
    def test_decorator_only_user_data_is_sessionless(self):
        self.assertTrue(is_user_data_empty({'user': object(), '_new_user_on_this_update': True}))

    def test_started_marker_takes_precedence_over_dictionary_shape(self):
        data = {'user': object(), 'session_started': False, 'music_path': 'stale.mp3'}

        self.assertTrue(is_user_data_empty(data))

    def test_reset_marks_session_started(self):
        data = {'user': object()}

        reset_user_data_context(1, data)

        self.assertFalse(is_user_data_empty(data))


if __name__ == '__main__':
    unittest.main()
