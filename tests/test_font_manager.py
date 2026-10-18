import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import font_manager


class FontManagerTests(unittest.TestCase):
    def test_font_preference_is_saved_locally_and_other_settings_are_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "config" / "ui_settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"ui_color": "#78d5ed"}), encoding="utf-8")
            with patch.object(font_manager, "SETTINGS_FILE", settings):
                font_manager.save_font_settings("Example Display")
            saved = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(saved["font_family"], "Example Display")
            self.assertEqual(saved["ui_color"], "#78d5ed")

    def test_only_common_desktop_font_file_types_are_accepted(self):
        self.assertEqual(
            font_manager.SUPPORTED_FONT_EXTENSIONS,
            {".ttf", ".otf", ".ttc"},
        )

    def test_import_rejects_executables_without_registering_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "fake.exe"
            executable.write_bytes(b"not a font")
            with self.assertRaisesRegex(ValueError, "Select a .ttf"):
                font_manager.import_custom_font(executable)


if __name__ == "__main__":
    unittest.main()
