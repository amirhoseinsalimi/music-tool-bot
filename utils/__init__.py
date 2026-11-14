"""Backward-compatible utility exports, resolved lazily for optional API imports."""
from importlib import import_module

_EXPORTS = {'upsert_user': 'decorators', 'delete_all_user_files': 'fs', 'delete_file': 'fs', 'download_file': 'fs', 'get_audio_file_extension': 'fs', 'MISSING_PREFIX': 'i18n', 't': 'i18n', 'ffmpeg_logger': 'logging', 'get_logger': 'logging', 'logger': 'logging', 'get_chat_id': 'misc', 'get_effective_message_id': 'misc', 'get_effective_user_id': 'misc', 'get_effective_user_username': 'misc', 'get_file_name': 'misc', 'get_message': 'misc', 'get_message_text': 'misc', 'get_user_data': 'misc', 'get_user_language_or_fallback': 'misc', 'is_user_data_empty': 'misc', 'reply_default_message': 'misc', 'reset_user_data_context': 'misc', 'resize_image': 'misc', 'set_current_module': 'misc', 'unset_current_module': 'misc'}
__all__ = ['MISSING_PREFIX', 'delete_all_user_files', 'delete_file', 'download_file', 'ffmpeg_logger', 'get_audio_file_extension', 'get_chat_id', 'get_effective_message_id', 'get_effective_user_id', 'get_effective_user_username', 'get_file_name', 'get_logger', 'get_message', 'get_message_text', 'get_user_data', 'get_user_language_or_fallback', 'is_user_data_empty', 'logger', 'reply_default_message', 'reset_user_data_context', 'resize_image', 'set_current_module', 't', 'unset_current_module', 'upsert_user']


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module('.' + _EXPORTS[name], __name__), name)
    globals()[name] = value
    return value
