from database.models import Admin


def is_admin_owner(user_id: int) -> bool:
    """Check if the user with `user_id` is owner or not.

    **Keyword arguments:**
     - user_id (int) -- The user id of the user

    **Returns:**
     `bool`
    """
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False