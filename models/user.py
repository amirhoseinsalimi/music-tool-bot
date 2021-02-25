from orator import Model


class User(Model):
    __fillable__ = ['user_id', 'language', 'number_of_files_sent']
