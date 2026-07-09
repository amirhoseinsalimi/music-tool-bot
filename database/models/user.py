from masoniteorm.models import Model
from masoniteorm.relationships import belongs_to


class User(Model):
    __fillable__ = [
        'user_id',
        'username',
        'language_id',
        'number_of_files_sent',
        'user_status_id',
        'last_interaction_at'
    ]

    @belongs_to('user_status_id', 'id')
    def user_status(self):
        from database.models.user_status import UserStatus

        return UserStatus

    @belongs_to('language_id', 'id')
    def language(self):
        from database.models.language import Language

        return Language
