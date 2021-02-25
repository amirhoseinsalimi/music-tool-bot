from models.user import User


def increment_usage_counter_for_user(user_id: int) -> int:
    try:
        user = User.where('user_id', '=', user_id).first()

        user.number_of_files_sent = user.number_of_files_sent + 1

        user.push()

        return user.number_of_files_sent
    except:
        return 0
