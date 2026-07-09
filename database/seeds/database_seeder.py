from masoniteorm.seeds import Seeder

from database.seeds.language_table_seeder import LanguageTableSeeder
from database.seeds.owner_table_seeder import OwnerTableSeeder
from database.seeds.user_status_table_seeder import UserStatusTableSeeder


class DatabaseSeeder(Seeder):
    def run(self):
        self.call(LanguageTableSeeder, UserStatusTableSeeder, OwnerTableSeeder)
