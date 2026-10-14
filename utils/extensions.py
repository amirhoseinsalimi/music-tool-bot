"""Load an operator-configured optional extension without a free-bot dependency."""

import importlib
import os
import re

_keyboard_providers = {}


def register_keyboard_provider(name, provider):
    """Let an installed extension contribute user-specific feature rows."""
    if not callable(provider):
        raise ValueError("Keyboard provider must be callable")
    _keyboard_providers[name] = provider


def optional_keyboard_rows(language, user_id=None):
    """The standalone bot has no extra rows unless an extension registers them."""
    return [row for provider in _keyboard_providers.values()
            for row in provider(language, user_id)]


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

    register(application)
