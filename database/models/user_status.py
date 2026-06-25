from masoniteorm.models import Model


class UserStatus(Model):
    __fillable__ = ['slug', 'name']