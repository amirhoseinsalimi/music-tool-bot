from masoniteorm.seeds import Seeder

from database.models import UserStatus


class UserStatusTableSeeder(Seeder):
    @staticmethod
    def run():
        statuses = [
            {'slug': 'active', 'name': 'Active'},
            {'slug': 'blocked', 'name': 'Blocked'},
            {'slug': 'deleted', 'name': 'Deleted'},
        ]

        for status in statuses:
            existing = UserStatus.where('slug', status['slug']).first()

            if not existing:
                UserStatus.create(status)
