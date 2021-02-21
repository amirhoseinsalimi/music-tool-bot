from orator import Model


class User(Model):
    __fillable__ = ['user_id', 'number_of_files_sent']
