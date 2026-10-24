import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import evolution


class MemoryEvolutionTests(unittest.TestCase):
    def test_extracts_explicit_preference_and_project(self):
        self.assertEqual(evolution.extract_candidate("I prefer dark mode"), ("preference", "dark mode"))
        self.assertEqual(evolution.extract_candidate("I'm building a Jarvis desktop assistant."),
                         ("project", "a Jarvis desktop assistant"))

    def test_skips_secrets_sensitive_topics_and_non_explicit_text(self):
        self.assertIsNone(evolution.extract_candidate("I prefer my API key to be private"))
        self.assertIsNone(evolution.extract_candidate("How do I fix Windows?"))
        self.assertIsNone(evolution.extract_candidate("My password is test123"))

    def test_memory_toggle_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory_settings.json"
            with patch.object(evolution, "SETTINGS_FILE", path):
                self.assertTrue(evolution.is_enabled())
                evolution.set_enabled(False)
                self.assertFalse(evolution.is_enabled())
                evolution.set_enabled(True)
                self.assertTrue(evolution.is_enabled())


if __name__ == "__main__":
    unittest.main()
