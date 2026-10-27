import unittest
from core.intent_router import normalize_natural_command
from pc_operator import PCOperator

class FakePermissions:
    def __init__(self, enabled=()):
        self.enabled=set(enabled)
    def has(self, key):
        return key in self.enabled

class PCOperatorTests(unittest.TestCase):
    def make_operator(self, enabled=(), confirm=True):
        return PCOperator(FakePermissions(enabled), lambda *args: confirm)

    def test_window_move_route_parses_coordinates(self):
        op=self.make_operator()
        op.window_move=lambda *args: "MOVE:"+repr(args)
        self.assertEqual(op.dispatch("pc window move Chrome -1920 0 1280 800"),
                         "MOVE:('Chrome', -1920, 0, 1280, 800)")

    def test_volume_and_brightness_range_validation(self):
        op=self.make_operator()
        self.assertIn("0 to 100",op.volume_set(101))
        self.assertIn("0 to 100",op.brightness_set(-1))

    def test_sensitive_control_requires_permission(self):
        op=self.make_operator()
        self.assertIn("Permission disabled",op.volume_set(50))
        self.assertIn("Permission disabled",op.power_plan("balanced"))

    def test_cancelled_confirmation_does_not_execute(self):
        op=self.make_operator(enabled=("system_settings",),confirm=False)
        self.assertIn("Cancelled",op.volume_set(50))
        self.assertIn("Cancelled",op.power_plan("balanced"))

    def test_natural_language_control_aliases(self):
        self.assertEqual(normalize_natural_command("Set volume to 45 percent"),"pc volume set 45")
        self.assertEqual(normalize_natural_command("Show open windows"),"pc windows")
        self.assertEqual(normalize_natural_command("Switch power plan to balanced"),"pc power plan balanced")

if __name__=="__main__":
    unittest.main()
