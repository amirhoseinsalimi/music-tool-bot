import re
from pathlib import Path

from database.models import Admin


def pretty_print_size(number_of_bytes: float) -> str:
    """
    Pretty print file sizes

    :param number_of_bytes: float: Number of bytes to convert
    :return: str: Human-readable file size
    """
    units = [
        (1 << 50, ' PB'),
        (1 << 40, ' TB'),
        (1 << 30, ' GB'),
        (1 << 20, ' MB'),
        (1 << 10, ' KB'),
        (1, (' byte', ' bytes')),
    ]

    for factor, suffix in units:
        if number_of_bytes >= factor:
            break

    amount = int(number_of_bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix

        if amount == 1:
            suffix = singular
        else:
            suffix = multiple

    return str(amount) + suffix


def get_dir_size_in_bytes(dir_path: str) -> float:
    """
    Get the size of a directory and its subdirectories in bytes.

    :param dir_path: str: The path of the directory to get its size
    :return: float: The size of a directory and its subdirectories in bytes
    """
    root_directory = Path(dir_path)

    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())


def get_list_limit(message: str) -> int | None:
    number_pattern = r'\d+'

    limit = re.findall(number_pattern, message)

    if len(limit):
        limit = int(limit[0])
    else:
        limit = None

    return limit


def is_admin_owner(user_id: int) -> bool:
    """
    Checks if the user is the bot owner.

    :param user_id: int: The ``user_id`` of the user whom we want to check their ownership
    :return: bool: Whether the user is the owner
    """
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False


def is_user_admin(user_id: int) -> bool:
    """
    Check if the user is the bot owner.

    :param user_id: int: The ``user_id`` of the user whom we want to check
    :return: bool: Whether the user is an admin
    """
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)


def extract_user_id(message: str) -> str:
    """
    Extracts and returns the user ``id`` of `/{add/del}admin` commands.

    The `message` is expected to look like ``/addadmin <user_id>``.

    :param message: str: The ``/{add/del}admin`` command containing a user ``id``
    :return: int: The normalized user's ``id``
    """
    return message.partition(' ')[2]
