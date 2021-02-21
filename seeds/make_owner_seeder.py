import os
from orator.seeds import Seeder
from dotenv import load_dotenv

load_dotenv(verbose=True)
OWNER_USER_ID = os.getenv("OWNER_USER_ID") if os.getenv("OWNER_USER_ID") else 0
OWNER_USER_ID = int(OWNER_USER_ID)
print(OWNER_USER_ID)


class MakeOwnerSeeder(Seeder):
    def run(self):
        self.db.table('admins').insert({
            'admin_user_id': OWNER_USER_ID,
            'is_owner': True,
        })
