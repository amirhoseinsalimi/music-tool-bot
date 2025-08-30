from typing import Any, Dict

from config.pyi18n import i18n, DEFAULT_LOCALE

MISSING_PREFIX = "missing translation for:"


def _normalize_locale(locale: str) -> str:
    """
    Normalize a locale string into a canonical short form.

    This function lowercases and trims the given ``locale`` code. If the code
    contains a hyphen (e.g., 'en-US'), it keeps only the base language part
    (e.g., 'en'). If the input is empty or None, it falls back to the default
    locale.

    :param locale: str: The locale string to normalize
    :return: str: The normalized locale or the default locale if invalid
    """
    loc = (locale or "").strip().lower()

    if "-" in loc:
        loc = loc.split("-", 1)[0]

    return loc or DEFAULT_LOCALE


def _safe_gettext(locale: str, key: str, **kwargs: Any) -> str:
    """
    Safely fetch a translation from i18n without raising exceptions.

    This function wraps ``i18n.gettext`` and returns its result if successful.
    If the requested locale does not exist or an error is raised, it returns
    a placeholder string in the format 'missing translation for: locale.key',
    which can then be handled consistently by fallback logic.

    :param locale: str: The locale code (e.g., 'en', 'fa')
    :param key: str: The translation key to retrieve
    :param kwargs: Any: Optional keyword arguments for interpolation
    :return: str: The translated string or a 'missing translation' placeholder
    """
    try:
        return i18n.gettext(locale, key, **kwargs)
    except Exception:
        return f"{MISSING_PREFIX} {locale}.{key}"


def _is_missing(s: str | None) -> bool:
    """
    Check whether a translation result indicates a missing entry.

    This function inspects a translation string and determines if it represents
    a missing translation. It considers values None, empty strings, or strings
    starting with 'missing translation for:' as missing.

    :param s: str | None: The translation string to check
    :return: bool: True if the translation is missing, False otherwise
    """
    return (s is None) or (s == "") or s.strip().lower().startswith(MISSING_PREFIX)


def _humanize(key: str) -> str:
    """
    Convert a translation key into a human-readable fallback string.

    This function takes the last segment of a translation key, replaces
    underscores and hyphens with spaces, trims whitespace, and capitalizes
    the first letter to produce a human-friendly string.

    :param key: str: The translation key (e.g., 'choose_language')
    :return: str: A humanized fallback string (e.g., 'Choose language')
    """

    last = key.split(".")[-1]
    pretty = last.replace("_", " ").replace("-", " ").strip()

    return pretty[:1].upper() + pretty[1:] if pretty else key


def t(locale: str, key: str, **kwargs: Any) -> str:
    """
    Translation helper with safe fallbacks.

    This function attempts to translate a given ``key`` for the specified
    ``locale`` using the application's i18n system. If the requested locale
    does not exist or if the translation key is missing, it gracefully falls
    back to the default locale (English). If the translation is missing in
    both the requested locale and the default locale, it returns a humanized
    version of the key instead of raising an error.

    :param locale: str: The requested locale code (e.g., 'en', 'fa', 'ru')
    :param key: str: The translation key to look up
    :param kwargs: Any: Optional keyword arguments to interpolate into the
                   translation string
    :return: str: The translated string, a fallback English string, or a
                  humanized key if no translation is found
    """
    loc = _normalize_locale(locale)

    template = _lookup(loc, key)

    escape_all = kwargs.pop("escape_all", True)
    raw_keys = kwargs.pop("raw_keys", ())
    raw_set = set(raw_keys)

    esc_kwargs: Dict[str, Any] = {}

    for k, v in kwargs.items():
        s = "" if v is None else str(v)
        esc_kwargs[k] = s if k in raw_set else escape_markdown_safe(s, version=2)

    filled = _format_safe(template, esc_kwargs)

    if escape_all:
        return escape_markdown_safe(filled, version=2)

    return filled


def _lookup(locale: str, key: str) -> str:
    """
    Retrieve a raw translation template without formatting values.

    This function mirrors the fallback behavior of ``t`` but returns the
    unformatted template so that callers can control escaping and formatting
    explicitly.

    :param locale: str: The requested locale code
    :param key: str: The translation key to look up
    :return: str: The raw template string or a humanized key if no translation is found
    """
    loc = _normalize_locale(locale)

    res = _safe_gettext(loc, key)

    if not _is_missing(res):
        return res

    if loc != DEFAULT_LOCALE:
        res_en = _safe_gettext(DEFAULT_LOCALE, key)

        if not _is_missing(res_en):
            return res_en

    return _humanize(key)


class _SafeDict(dict):
    """
    A mapping that preserves unknown placeholders during format operations.

    This dictionary subclass returns a '{name}' literal when a placeholder key
    is missing, allowing best-effort formatting without raising KeyError.
    """

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _format_safe(template: str, values: Dict[str, Any]) -> str:
    """
    Format a template with best-effort semantics.

    This function applies ``str.format_map`` using a dictionary that preserves
    unknown placeholders. Missing keys remain intact as '{name}' instead of
    raising an exception.

    :param template: str: The template string containing placeholders
    :param values: Dict[str, Any]: The values to substitute into the template
    :return: str: The formatted string with unknown placeholders preserved
    """
    return template.format_map(_SafeDict(values))


def escape_markdown_safe(text: str, version: int = 2) -> str:
    """
    Escape a text string for Telegram MarkdownV2.

    This function escapes characters reserved by MarkdownV2 to prevent parsing
    errors. If python-telegram-bot's helper is available, it will be used.
    Otherwise, a local implementation is applied.

    :param text: str: The input text to escape
    :param version: int: The Markdown version (only 2 is supported here)
    :return: str: The escaped text safe for MarkdownV2
    """
    if version != 2:
        return text

    try:
        from telegram.helpers import escape_markdown as _tg_escape_markdown  # type: ignore

        return _tg_escape_markdown(text, version=2)
    except Exception:
        specials = set(r"_*[]()~`>#+-=|{}.!\\")
        out = []

        for ch in text:
            out.append("\\" + ch if ch in specials else ch)

        return "".join(out)
