import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AppControlWiringTests(unittest.TestCase):
    def test_active_bridge_routes_app_control_commands(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn("from app_control_manager import AppControlManager", source)
        self.assertIn("self.app_control = AppControlManager(ui)", source)
        self.assertIn("app_control_response = self.app_control.handle_command(raw)", source)

    def test_privileged_app_launches_check_the_permission_gate(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn('self.app_control.permissions.has("app_launch")', source)

    def test_message_and_call_workflows_are_documented_as_manual_actions(self):
        manager = (ROOT / "app_control_manager.py").read_text(encoding="utf-8")
        self.assertIn("No message was sent", manager)
        self.assertIn("JARVIS did not place a call", manager)
        self.assertIn("will not press Enter, click Send", manager)

    def test_local_permission_state_is_git_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config/app_permissions.json", ignore)


if __name__ == "__main__":
    unittest.main()
