from masoniteorm.seeds import Seeder

from database.seeds.user_status_table_seeder import UserStatusTableSeeder
from database.seeds.owner_table_seeder import OwnerTableSeeder


class DatabaseSeeder(Seeder):
    def run(self):
        self.call(UserStatusTableSeeder, OwnerTableSeeder)
