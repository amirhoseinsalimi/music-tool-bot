import os
import sys
from orator.seeds import Seeder
from dotenv import load_dotenv
from orator import Model

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dbconfig import db
from models.admin import Admin

Model.set_connection_resolver(db)

load_dotenv(verbose=True)
OWNER_USER_ID = os.getenv("OWNER_USER_ID") if os.getenv("OWNER_USER_ID") else 0
OWNER_USER_ID = int(OWNER_USER_ID)

Model.set_connection_resolver(db)


class OwnerSeeder(Seeder):
    def run(self):
        admin = Admin.where('admin_user_id', '=', OWNER_USER_ID).first()

        if not admin:
            owner = Admin()
            owner.admin_user_id = OWNER_USER_ID
            owner.is_owner = True

            owner.save()
