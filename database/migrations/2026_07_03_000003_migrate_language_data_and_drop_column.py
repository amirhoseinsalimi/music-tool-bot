# pylint: disable=invalid-name

from masoniteorm.migrations import Migration

TABLE_NAME = 'users'


class MigrateLanguageDataAndDropColumn(Migration):

    def up(self):
        from database.models import Language, User
        from database.seeds.language_table_seeder import LanguageTableSeeder

        LanguageTableSeeder.run()

        language_id_by_iso = {language.iso: language.id for language in Language.all()}

        for user in User.all():
            language_id = language_id_by_iso.get(user.language)

            if language_id is not None:
                user.language_id = language_id
                user.save()

        with self.schema.table(TABLE_NAME) as table:
            table.drop_column('language')

    def down(self):
        with self.schema.table(TABLE_NAME) as table:
            table.string('language').default('en')

        from database.models import Language, User

        iso_by_language_id = {language.id: language.iso for language in Language.all()}

        for user in User.all():
            iso = iso_by_language_id.get(user.language_id)

            if iso is not None:
                user.language = iso
                user.save()
