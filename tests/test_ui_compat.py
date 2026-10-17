import tempfile
import unittest
from pathlib import Path

from memory import config_manager, memory_manager


class UICompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.old_config_file = config_manager.FILE
        self.old_memory_file = memory_manager.FILE
        config_manager.FILE = root / "ui_settings.json"
        memory_manager.FILE = root / "long_term.json"

    def tearDown(self):
        config_manager.FILE = self.old_config_file
        memory_manager.FILE = self.old_memory_file
        self.temp.cleanup()

    def test_hud_settings_persist(self):
        config_manager.save_hud_style("core")
        self.assertEqual(config_manager.get_hud_style(), "core")
        config_manager.save_brief_enabled(True)
        self.assertTrue(config_manager.get_brief_enabled())

    def test_memory_panel_add_and_forget(self):
        memory_manager.remember("favorite_editor", "VS Code", "preferences")
        rows = memory_manager.all_entries_for_ui()
        self.assertEqual(rows[0]["key"], "favorite_editor")
        self.assertTrue(memory_manager.forget("favorite_editor", "preferences"))
        self.assertEqual(memory_manager.all_entries_for_ui(), [])


if __name__ == "__main__":
    unittest.main()
