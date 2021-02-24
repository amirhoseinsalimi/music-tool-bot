from models.admin import Admin


def is_user_admin(user_id: int) -> bool:
    admin = Admin.where('admin_user_id', '=', user_id).first()

    return bool(admin)
