from models.admin import Admin


def is_user_owner(user_id: int) -> bool:
    owner = Admin.where('admin_user_id', '=', user_id).where('is_owner', '=', True).first()

    return owner.is_owner if owner else False
