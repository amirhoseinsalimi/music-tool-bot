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
            def register(app):
                pass
            imported.return_value.register = register
            module.register_optional_extension(application)
            imported.assert_called_once_with("example_extension")
            # Older standalone extensions keep their one argument contract.

    def test_configured_core_extension_receives_upsert_decorator(self):
        with patch.dict(os.environ, {"BOT_EXTENSION": "example_extension:register"}), patch.object(module.importlib, "import_module") as imported:
            application = Mock()
            received = {}
            def register(app, *, upsert_user=None):
                received.update(application=app, upsert_user=upsert_user)
            imported.return_value.register = register
            module.register_optional_extension(application)
            self.assertIs(received["application"], application)
            self.assertTrue(callable(received["upsert_user"]))
            self.assertEqual(received["upsert_user"].__name__, "_lazy_upsert_user")

    def test_invalid_extension_is_rejected_before_import(self):
        with patch.dict(os.environ, {"BOT_EXTENSION": "invalid target"}), patch.object(module.importlib, "import_module") as imported:
            with self.assertRaises(ValueError):
                module.register_optional_extension(Mock())
            imported.assert_not_called()


class PublicContractTests(unittest.IsolatedAsyncioTestCase):
    def test_version_and_catalog_languages_match(self):
        self.assertEqual(module.API_VERSION, 1)
        self.assertEqual(set(module.SUPPORTED_LANGUAGES), {p.stem for p in (path.parents[1]/'i18n').glob('*.yaml')})

    async def test_adapters_delegate_without_importing_private_code(self):
        import sys
        from types import ModuleType
        from unittest.mock import AsyncMock
        handlers=ModuleType('modules.core.handlers')
        handlers.show_module_selector=AsyncMock(return_value='selector')
        handlers.start_over=AsyncMock(return_value='reset')
        service=ModuleType('modules.tag_editor.service');service.read_and_store_music_tags=AsyncMock(return_value=True)
        preview=ModuleType('modules.tag_editor.handlers');preview.display_preview=AsyncMock(return_value='preview')
        with patch.dict(sys.modules,{'modules.core.handlers':handlers,'modules.tag_editor.service':service,'modules.tag_editor.handlers':preview}):
            self.assertEqual(await module.show_module_selector('update','context'),'selector')
            self.assertEqual(await module.start_over('update','context'),'reset')
            self.assertTrue(await module.read_tags('update',{}))
            self.assertEqual(await module.display_tag_preview('update','context'),'preview')
            service.read_and_store_music_tags.assert_awaited_once_with('update',{})

    async def test_public_upsert_wrapper_runs_core_decorator_once(self):
        import sys
        from types import ModuleType
        from unittest.mock import AsyncMock
        decorated=AsyncMock();decorator=Mock(return_value=decorated)
        source=ModuleType('utils.decorators');source.upsert_user=decorator
        callback=AsyncMock()
        with patch.dict(sys.modules,{'utils.decorators':source}):
            registered=module.upsert_user(callback)
            self.assertTrue(registered.upserts_user)
            await registered('update','context')
        decorator.assert_called_once_with(callback)
        decorated.assert_awaited_once_with('update','context')

    def test_storage_root_validates_identity_without_creating_files(self):
        import sys,tempfile
        from types import ModuleType
        with tempfile.TemporaryDirectory() as tmp:
            env=ModuleType('config.envs');env.DATA_DIR=tmp
            with patch.dict(sys.modules,{'config.envs':env}):
                self.assertEqual(module.user_storage_root(42),Path(tmp)/'downloads/42')
                for invalid in (None,'42',True,0,-1,2**63):
                    with self.assertRaises(ValueError):module.user_storage_root(invalid)
            self.assertFalse((Path(tmp)/'downloads').exists())


class PublicImportTests(unittest.TestCase):
    def test_actual_package_import_needs_only_standard_library(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,'-S','-c',
            "import sys; import utils.extensions as api; assert api.API_VERSION == 1; "
            "assert 'utils.decorators' not in sys.modules; assert 'config.pyi18n' not in sys.modules; "
            "assert 'telegram' not in sys.modules; assert 'masoniteorm' not in sys.modules"],
            cwd=path.parents[1],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
