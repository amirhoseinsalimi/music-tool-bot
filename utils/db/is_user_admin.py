from models.admin import Admin


def is_user_admin(user_id: int) -> bool:
    """Check if the user with `user_id` is admin or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)