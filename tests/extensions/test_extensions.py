"""Verify standalone startup and the generic optional extension contract."""

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[2] / "utils" / "extensions.py"
spec = importlib.util.spec_from_file_location("optional_extension", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExtensionTests(unittest.TestCase):
    def test_standalone_keyboard_has_no_extension_rows(self):
        with patch.dict(module._keyboard_providers, {}, clear=True):
            self.assertEqual(module.optional_keyboard_rows("en", 42), [])

    def test_keyboard_provider_receives_language_and_user_and_replaces_itself(self):
        with patch.dict(module._keyboard_providers, {}, clear=True):
            old = Mock(return_value=[["old"]])
            provider = Mock(return_value=[["extra"]])
            module.register_keyboard_provider("example", old)
            module.register_keyboard_provider("example", provider)
            self.assertEqual(module.optional_keyboard_rows("fa", 42), [["extra"]])
            provider.assert_called_once_with("fa", 42)
            old.assert_not_called()

    def test_disabled_does_not_import_private_package(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(module.importlib, "import_module") as imported:
            module.register_optional_extension(Mock())
            imported.assert_not_called()

    def test_configured_extension_receives_application(self):
        with patch.dict(os.environ, {"BOT_EXTENSION": "example_extension:register"}), patch.object(module.importlib, "import_module") as imported:
            application = Mock()
            module.register_optional_extension(application)
            imported.assert_called_once_with("example_extension")
            imported.return_value.register.assert_called_once_with(application)

    def test_invalid_extension_is_rejected_before_import(self):
        with patch.dict(os.environ, {"BOT_EXTENSION": "invalid target"}), patch.object(module.importlib, "import_module") as imported:
            with self.assertRaises(ValueError):
                module.register_optional_extension(Mock())
            imported.assert_not_called()
