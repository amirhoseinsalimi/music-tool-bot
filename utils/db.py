from database.models import Admin, User


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


def increment_file_counter_for_user(user_id: int) -> None:
    """
    Increments the ``number_of_files_sent`` field for a given user.

    :param user_id: int: The ``user_id`` of the user whose file count we want to increment
    :raises LookupError: No Such a user in the database
    """
    user = User.where('user_id', '=', user_id).first()

    if not user:
        raise LookupError(f'User with id {user_id} not found.')

    user.update({
        "number_of_files_sent": user.number_of_files_sent + 1
    })


def update_user_username_if_updated(user_id: int, username: str) -> None:
    """
    Updates the ``username`` of a specified user if it has been updated.

    :param user_id: int: The ``user_id`` of the user we want to update their username
    :param username: str: The new `username` to set for the user
    """
    user = User.where('user_id', '=', user_id).first()

    if user.username == username:
        return

    user.update({
        'username': username,
    })
