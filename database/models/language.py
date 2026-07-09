from masoniteorm.models import Model


class Language(Model):
    __fillable__ = ['iso', 'name', 'native_name', 'flag', 'is_default']

    @classmethod
    def ordered(cls):
        """All languages in a stable order, so keyboards and handlers agree on it."""
        return cls.order_by('id').get()

    @property
    def label(self) -> str:
        """The reply keyboard button text for this language, e.g. ``🇬🇧 English``."""
        return f'{self.flag} {self.native_name}'
