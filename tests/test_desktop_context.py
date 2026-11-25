"""Tests for on-demand foreground context routing."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DesktopContextTests(unittest.TestCase):
    def test_context_module_limits_collection_to_window_metadata(self):
        source = (ROOT / "features/desktop_context.py").read_text(encoding="utf-8")
        self.assertIn("GetForegroundWindow", source)
        self.assertIn("GetWindowTextW", source)
        self.assertNotIn("ImageGrab", source)
        self.assertNotIn("pyautogui.screenshot", source)

    def test_context_is_only_requested_for_window_related_prompts(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn('("this window", "current window", "active window"', source)
        self.assertIn('if p in {"pc foreground", "active window", "foreground window"}:', source)


if __name__ == "__main__":
    unittest.main()
