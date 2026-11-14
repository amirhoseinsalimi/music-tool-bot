from pyi18n import PyI18n
from utils.extensions import SUPPORTED_LANGUAGES

i18n = PyI18n(SUPPORTED_LANGUAGES, load_path="i18n/")

DEFAULT_LOCALE = "en"
