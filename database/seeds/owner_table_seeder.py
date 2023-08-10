import os
import sys

from masoniteorm.seeds import Seeder
from database.models import Admin

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))





class OwnerTableSeeder(Seeder):
    def run(self):
        """Run the database seeds."""

        if Admin.where('admin_user_id', OWNER_USER_ID_INT).first():
            return

        Admin.create({
            'admin_user_id': OWNER_USER_ID_INT,
            'is_owner': True,
        })