import json
import tempfile
import unittest
from pathlib import Path

from app_permissions import (
    PERMISSION_INFO,
    PermissionStore,
    filter_installed_apps,
    resolve_permission,
    validate_typing_text,
)


class PermissionStoreTests(unittest.TestCase):
    def test_sensitive_actions_are_opt_in_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PermissionStore(Path(tmp) / "permissions.json")
            self.assertTrue(store.has("read"))
            self.assertTrue(store.has("launch"))
            self.assertFalse(store.has("type"))
            self.assertFalse(store.has("message"))
            self.assertFalse(store.has("call"))

    def test_permission_change_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions.json"
            store = PermissionStore(path)
            self.assertTrue(store.set("type", True))
            self.assertTrue(PermissionStore(path).has("type"))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(data["permissions"]["type_text"], True)

    def test_unknown_permission_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PermissionStore(Path(tmp) / "permissions.json")
            self.assertFalse(store.set("everything_including_files", True))
            self.assertFalse(store.has("everything_including_files"))
            self.assertEqual(resolve_permission("send_message"), "draft_message")

    def test_grant_all_covers_only_documented_capabilities(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PermissionStore(Path(tmp) / "permissions.json")
            store.set_all(True)
            self.assertTrue(all(store.has(key) for key in PERMISSION_INFO))
            self.assertNotIn("read_all_files", PERMISSION_INFO)
            self.assertNotIn("auto_send_message", PERMISSION_INFO)
            self.assertNotIn("auto_place_call", PERMISSION_INFO)

    def test_bad_settings_restore_safe_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions.json"
            path.write_text("{not valid", encoding="utf-8")
            store = PermissionStore(path)
            self.assertFalse(store.has("type_text"))
            self.assertFalse(store.has("draft_message"))
            self.assertFalse(store.has("prepare_call"))


class AppDiscoveryTests(unittest.TestCase):
    def test_filter_searches_names_without_exposing_app_ids(self):
        rows = [
            ("WhatsApp", "package.whatsapp!App"),
            ("Telegram Desktop", "package.telegram!App"),
            ("WhatsApp", "duplicate.id"),
            ("Paint", "mspaint.exe"),
        ]
        self.assertEqual(
            filter_installed_apps(rows, "whats"),
            ["WhatsApp"],
        )
        self.assertEqual(
            filter_installed_apps(rows),
            ["Paint", "Telegram Desktop", "WhatsApp"],
        )

    def test_typing_rejects_empty_control_characters_and_overlong_text(self):
        self.assertFalse(validate_typing_text("   ")[0])
        self.assertFalse(validate_typing_text("hello\nworld")[0])
        self.assertFalse(validate_typing_text("x" * 1001)[0])
        self.assertTrue(validate_typing_text("hello, world!")[0])


if __name__ == "__main__":
    unittest.main()
