from database.models import Admin, User


def increment_file_counter_for_user(user_id: int) -> int:
    """Increment the `number_of_files_sent` column of user with the specified `user_id`.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     The new value for `user.number_of_files_sent`
    """
    user = User.where('user_id', '=', user_id).first()

    if user:
        user.update({
            "number_of_files_sent": user.number_of_files_sent + 1
        })

        return user.number_of_files_sent

    raise LookupError(f'User with id {user_id} not found.')


def is_admin_owner(user_id: int) -> bool:
    """Check if the user with `user_id` is owner or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False


def is_user_admin(user_id: int) -> bool:
    """Check if the user with `user_id` is admin or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)
