"""Load an operator-configured optional extension without a free-bot dependency."""

import importlib
import os
import re


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
