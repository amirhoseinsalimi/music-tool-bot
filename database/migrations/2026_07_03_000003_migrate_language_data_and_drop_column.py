# pylint: disable=invalid-name

from masoniteorm.migrations import Migration
from masoniteorm.query import QueryBuilder

TABLE_NAME = 'users'
LANGUAGES_TABLE = 'languages'

# Frozen copy of the language rows as they existed when this migration was written. It duplicates
# `LanguageTableSeeder` on purpose: a migration must not import a model or a seeder, because both
# describe the *current* schema, while a migration runs against the schema of its own point in
# history. Importing them is what made this migration drop `users.language` without backfilling.
LANGUAGES = (
    ('en', 'English', 'English', '🇬🇧', True),
    ('fa', 'Persian', 'فارسی', '🇮🇷', False),
    ('ru', 'Russian', 'Русский', '🇷🇺', False),
    ('es', 'Spanish', 'Español', '🇪🇸', False),
    ('fr', 'French', 'Français', '🇫🇷', False),
    ('ar', 'Arabic', 'العربية', '🇸🇦', False),
)


class MigrateLanguageDataAndDropColumn(Migration):

    def _table(self, name: str) -> QueryBuilder:
        """A builder bound to this migration's connection, and to a table rather than a model."""
        return QueryBuilder(table=name, connection=self.connection, schema=self.schema_name)

    def up(self):
        # `languages` must hold every iso present in `users.language` before the rows can be mapped
        # onto each other. Seeding here, rather than relying on `db-seed` (which runs after
        # migrations), keeps this migration self-contained. Check-before-insert to stay idempotent.
        for iso, name, native_name, flag, is_default in LANGUAGES:
            if self._table(LANGUAGES_TABLE).where('iso', iso).first():
                continue

            self._table(LANGUAGES_TABLE).create({
                'iso': iso,
                'name': name,
                'native_name': native_name,
                'flag': flag,
                'is_default': is_default,
            })

        # Read the isos back from the table rather than from LANGUAGES, so a language added by hand
        # (during a recovery, say) is picked up too.
        for language in self._table(LANGUAGES_TABLE).get():
            self._table(TABLE_NAME) \
                .where('language', language['iso']) \
                .update({'language_id': language['id']})

        self._assert_every_user_mapped()

        with self.schema.table(TABLE_NAME) as table:
            table.drop_column('language')

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.string('language').default('en')

        for language in self._table(LANGUAGES_TABLE).get():
            self._table(TABLE_NAME) \
                .where('language_id', language['id']) \
                .update({'language': language['iso']})

    def _assert_every_user_mapped(self):
        """Abort unless every user row came out of the backfill with a `language_id`.

        Statements autocommit, so nothing wraps this migration in a transaction and a failure
        raised after `drop_column` could not undo it. Verify first, destroy second. Raising here
        leaves the migration unrecorded and `language` intact, so the data can be corrected and the
        migration re-run.
        """
        unmapped = self._table(TABLE_NAME).where_null('language_id').count()

        if not unmapped:
            return

        orphans = self._table(TABLE_NAME) \
            .where_null('language_id') \
            .select('language') \
            .distinct() \
            .get()

        isos = ', '.join(sorted(repr(row['language']) for row in orphans))

        raise RuntimeError(
            f'Refusing to drop {TABLE_NAME}.language: {unmapped} rows still have a NULL '
            f'language_id. Unmapped values: {isos}. Add the missing rows to `{LANGUAGES_TABLE}`, '
            f'then re-run this migration.'
        )
