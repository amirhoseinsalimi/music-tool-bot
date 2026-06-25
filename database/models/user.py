from masoniteorm.models import Model
from masoniteorm.relationships import belongs_to


class User(Model):
    __fillable__ = ['user_id', 'username', 'language', 'number_of_files_sent', 'user_status_id']

    @belongs_to('user_status_id', 'id')
    def user_status(self):
        from database.models.user_status import UserStatus

        return UserStatus
