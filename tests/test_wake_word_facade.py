"""Regression tests for the HUD's lazy wake-word compatibility facade."""
import unittest
from unittest.mock import patch

from core import wake_word


class WakeWordFacadeTests(unittest.TestCase):
    @patch("core.mark_lvi_wake_word.is_ready", return_value=True)
    def test_readiness_delegates_to_optional_engine(self, is_ready):
        self.assertTrue(wake_word.is_ready())
        is_ready.assert_called_once_with()

    @patch("core.mark_lvi_wake_word.install_and_download", return_value=(True, "ready"))
    def test_hud_logger_keyword_is_forwarded(self, install):
        messages = []
        ok, message = wake_word.install_and_download(logger=messages.append)
        self.assertTrue(ok)
        self.assertEqual(message, "ready")
        install.assert_called_once_with(logger=messages.append, notify=None)

    @patch("core.mark_lvi_wake_word.install_and_download", return_value=(True, "ready"))
    def test_legacy_positional_progress_callback_remains_supported(self, install):
        progress = []
        wake_word.install_and_download(progress.append)
        install.assert_called_once_with(logger=progress.append, notify=None)


if __name__ == "__main__":
    unittest.main()
