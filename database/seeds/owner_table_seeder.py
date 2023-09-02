import os
import sys

from masoniteorm.seeds import Seeder

from config.envs import OWNER_USER_ID_INT
from database.models import Admin

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_owner_if_does_not_exist(owner_id: int) -> None:
    """
    Checks if an owner with a specified ``owner_id`` exists in the database. If it's not, it creates it using
    :func:`create_owner`.

    :param owner_id: int: The ``id`` of the owner to be checked and saved
    """
    if Admin.where('admin_user_id', owner_id).first():
        return

    create_owner(owner_id=owner_id)


def create_owner(owner_id: int) -> None:
    """
    Creates an owner with a specified ``owner_id`` and stores in the database.

    :param owner_id: int: The `id` of the owner to be saved
    """
    Admin.create({
        'admin_user_id': owner_id,
        'is_owner': True,
    })


class OwnerTableSeeder(Seeder):
    @staticmethod
    def run():
        create_owner_if_does_not_exist(owner_id=OWNER_USER_ID_INT)
