"""Load an operator-configured optional extension without a free-bot dependency."""

import importlib
import inspect
import os
import re
from pathlib import Path
from functools import wraps

# Public, versioned interface for optional extensions. Keep this module importable
# without Telegram/ORM initialization; implementation imports remain lazy.
API_VERSION = 1
SUPPORTED_LANGUAGES = ('en', 'fa', 'ru', 'es', 'fr', 'ar', 'hi', 'id')
_keyboard_providers = {}


def _lazy_upsert_user(function):
    """Keep the optional extension loader importable without bot dependencies."""
    @wraps(function)
    async def wrapped(update, context, *args, **kwargs):
        from utils.decorators import upsert_user as core_upsert_user
        return await core_upsert_user(function)(update, context, *args, **kwargs)
    wrapped.upserts_user = True
    return wrapped


def register_keyboard_provider(name, provider):
    """Let an installed extension contribute user-specific feature rows."""
    if not callable(provider):
        raise ValueError("Keyboard provider must be callable")
    _keyboard_providers[name] = provider


def optional_keyboard_rows(language, user_id=None, feature_settings=None):
    """The standalone bot has no extra rows unless an extension registers them."""
    rows = []
    for provider in _keyboard_providers.values():
        try:
            parameters = inspect.signature(provider).parameters
        except (TypeError, ValueError):
            parameters = {}
        if 'feature_settings' in parameters:
            provided_rows = provider(language, user_id, feature_settings=feature_settings)
        else:
            provided_rows = provider(language, user_id)
        rows.extend(provided_rows)
    return rows


def register_optional_extension(application):
    """Call ``module:function`` only when BOT_EXTENSION is explicitly configured.

    The extension must already be installed in the bot environment. Its code
    stays outside this public repository. Configuration is trusted operator input.
    """
    target = os.getenv("BOT_EXTENSION", "")

    if not target:
        return

    if not re.fullmatch(r"[a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*)*:[a-zA-Z_][\w]*", target):
        raise ValueError("BOT_EXTENSION must be module:function")

    module_name, function_name = target.split(":")
    register = getattr(importlib.import_module(module_name), function_name)

    if not callable(register):
        raise ValueError("BOT_EXTENSION must refer to a callable")

    parameters = inspect.signature(register).parameters.values()
    if any(parameter.name == "upsert_user" for parameter in parameters):
        register(application, upsert_user=_lazy_upsert_user)
    else:
        register(application)


# Contract v1 adapters. Their implementation may move without changing consumers.
upsert_user = _lazy_upsert_user


def text(context, key, **values):
    from config.pyi18n import i18n
    language = (getattr(context, 'user_data', None) or {}).get('language', 'en')
    if language not in SUPPORTED_LANGUAGES:
        language = 'en'
    return i18n.gettext(language, key, **values)


def language_or_fallback(user_data):
    from utils import get_user_language_or_fallback
    return get_user_language_or_fallback(user_data)


def user_storage_root(user_id):
    if type(user_id) is not int or not 0 < user_id < 2**63:
        raise ValueError('A valid Telegram user ID is required')
    from config.envs import DATA_DIR
    return (Path(DATA_DIR) / 'downloads' / str(user_id)).resolve()


async def show_module_selector(update, context):
    from modules.core.handlers import show_module_selector as implementation
    return await implementation(update, context)


async def start_over(update, context):
    from modules.core.handlers import start_over as implementation
    return await implementation(update, context)


async def read_tags(update, user_data):
    from modules.tag_editor.service import read_and_store_music_tags
    return await read_and_store_music_tags(update, user_data)


async def display_tag_preview(update, context):
    from modules.tag_editor.handlers import display_preview
    return await display_preview(update, context)


def feature_settings():
    from runtime_controls import bot_settings
    return bot_settings()


def disabled_message(language):
    from runtime_controls import disabled_message as implementation
    return implementation(language)
