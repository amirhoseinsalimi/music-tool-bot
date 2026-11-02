"""Reference seeders add missing rows and preserve existing records when repeated."""

import unittest
from unittest.mock import patch

from database.seeds import language_table_seeder, owner_table_seeder, user_status_table_seeder


def memory_model(key_column):
    """Create a tiny insert-if-missing model double for one reference table."""
    rows = {}

    class Query:
        def __init__(self, value):
            self.value = value

        def first(self):
            return rows.get(self.value)

    class Model:
        @classmethod
        def where(cls, column, value):
            if column != key_column:
                raise AssertionError(f'Unexpected lookup column: {column}')
            return Query(value)

        @classmethod
        def create(cls, attributes):
            key = attributes[key_column]
            if key in rows:
                raise AssertionError(f'Duplicate reference row: {key}')
            rows[key] = dict(attributes)
            return rows[key]

    return Model, rows


class SeedIdempotenceTests(unittest.TestCase):
    def test_languages_and_statuses_can_be_seeded_twice(self):
        for module, model_name, seeder, key_column in (
            (language_table_seeder, 'Language', language_table_seeder.LanguageTableSeeder, 'iso'),
            (user_status_table_seeder, 'UserStatus', user_status_table_seeder.UserStatusTableSeeder, 'slug'),
        ):
            with self.subTest(seeder=seeder.__name__):
                model, rows = memory_model(key_column)
                with patch.object(module, model_name, model):
                    seeder.run()
                    first_count = len(rows)
                    seeder.run()

                self.assertGreater(first_count, 0)
                self.assertEqual(len(rows), first_count)

    def test_owner_is_not_duplicated_when_seed_runs_again(self):
        model, rows = memory_model('admin_user_id')
        with patch.object(owner_table_seeder, 'Admin', model), \
                patch.object(owner_table_seeder, 'OWNER_USER_ID_INT', 123):
            owner_table_seeder.OwnerTableSeeder.run()
            owner_table_seeder.OwnerTableSeeder.run()

        self.assertEqual(rows, {123: {'admin_user_id': 123, 'is_owner': True}})


if __name__ == '__main__':
    unittest.main()
