import os
import sys
from masoniteorm.seeds import Seeder
from dotenv import load_dotenv
from database.models.admin import Admin

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Model.set_connection_resolver(db)

load_dotenv(verbose=True)
OWNER_USER_ID = os.getenv("OWNER_USER_ID") if os.getenv("OWNER_USER_ID") else 0
OWNER_USER_ID_INT = int(OWNER_USER_ID)

# Model.set_connection_resolver(db)

class OwnerTableSeeder(Seeder):
    def run(self):
        """Run the database seeds."""

        if Admin.where('admin_user_id', OWNER_USER_ID_INT).first():
            return

        Admin.create({
            'admin_user_id': OWNER_USER_ID_INT,
            'is_owner': True,
        })