from database.models import User


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
