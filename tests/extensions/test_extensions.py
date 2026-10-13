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
