import unittest
from unittest.mock import Mock

from core.api_key_manager import (
    check_all_api_keys, format_api_status, get_api_keys, mask_api_key, probe_api_key,
)


class ApiKeyManagerTests(unittest.TestCase):
    def test_unlimited_style_key_sources_are_deduplicated_without_limit(self):
        env = {
            "GROQ_API_KEY": "primary-key",
            "GROQ_API_KEY_2": "second-key",
            "GROQ_API_KEY_9": "ninth-key",
            "GROQ_API_KEYS": '["list-key", "second-key"]',
        }
        config = {"api_keys": {"groq": ["config-key", "primary-key"]},
                  "groq_api_key": "legacy-key"}
        self.assertEqual(
            get_api_keys("groq", config=config, env=env),
            ["primary-key", "second-key", "ninth-key", "list-key", "config-key", "legacy-key"],
        )

    def test_legacy_single_key_fields_remain_supported(self):
        self.assertEqual(get_api_keys("gemini", config={"gemini_api_key": "gemini-test"},
                                      env={}), ["gemini-test"])

    def test_keys_are_only_masked_in_display(self):
        self.assertEqual(mask_api_key("private-secret-1234"), "••••1234")
        self.assertNotIn("private-secret", mask_api_key("private-secret-1234"))

    def test_live_probe_reports_valid_without_exposing_key(self):
        rows = check_all_api_keys(
            providers=["groq"],
            config={"api_keys": {"groq": ["private-key-1234"]}},
            env={},
            clients={"groq": lambda key: None},
        )
        self.assertEqual(rows[0]["status"], "VALID")
        self.assertEqual(rows[0]["key"], "••••1234")
        self.assertNotIn("private-key", format_api_status(rows))

    def test_invalid_key_classification(self):
        row = probe_api_key("gemini", "invalid-test-key",
                            clients={"gemini": lambda key: (_ for _ in ()).throw(RuntimeError("HTTP 401 unauthorized"))})
        self.assertEqual(row["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
