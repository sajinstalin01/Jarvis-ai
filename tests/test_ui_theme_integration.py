"""Static regression tests for the active Qt theme wiring (no Qt install needed)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ThemeIntegrationTests(unittest.TestCase):
    def test_realistic_theme_lives_in_the_active_ui_module(self):
        ui_source = (ROOT / "ui.py").read_text(encoding="utf-8")
        self.assertIn("REALISTIC_PALETTE = {", ui_source)
        self.assertIn("def apply_realistic_theme(", ui_source)
        self.assertIn("def polish_window(", ui_source)

    def test_application_imports_theme_from_ui_not_legacy_module(self):
        app_source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn(
            "from ui import JarvisUI, apply_realistic_theme, polish_window",
            app_source,
        )
        self.assertNotIn(
            "from ui_theme import apply_realistic_theme, polish_window",
            app_source,
        )


if __name__ == "__main__":
    unittest.main()
