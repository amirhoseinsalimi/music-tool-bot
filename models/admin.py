from orator import Model


class Admin(Model):
    __fillable__ = ['admin_user_id', 'is_owner']
