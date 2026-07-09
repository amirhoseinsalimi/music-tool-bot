from masoniteorm.seeds import Seeder

from database.models import Language


class LanguageTableSeeder(Seeder):
    @staticmethod
    def run():
        languages = [
            {'iso': 'en', 'name': 'English', 'native_name': 'English', 'flag': '🇬🇧', 'is_default': True},
            {'iso': 'fa', 'name': 'Persian', 'native_name': 'فارسی', 'flag': '🇮🇷', 'is_default': False},
            {'iso': 'ru', 'name': 'Russian', 'native_name': 'Русский', 'flag': '🇷🇺', 'is_default': False},
            {'iso': 'es', 'name': 'Spanish', 'native_name': 'Español', 'flag': '🇪🇸', 'is_default': False},
            {'iso': 'fr', 'name': 'French', 'native_name': 'Français', 'flag': '🇫🇷', 'is_default': False},
            {'iso': 'ar', 'name': 'Arabic', 'native_name': 'العربية', 'flag': '🇸🇦', 'is_default': False},
            {'iso': 'hi', 'name': 'Hindi', 'native_name': 'हिन्दी', 'flag': '🇮🇳', 'is_default': False},
            {'iso': 'id', 'name': 'Indonesian', 'native_name': 'Bahasa Indonesia', 'flag': '🇮🇩', 'is_default': False},
        ]

        for language in languages:
            existing = Language.where('iso', language['iso']).first()

            if not existing:
                Language.create(language)
