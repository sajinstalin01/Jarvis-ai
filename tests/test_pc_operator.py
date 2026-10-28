import unittest
from pc_operator import PCOperator

class PermissionStub:
    def has(self, name):
        return name in {"desktop_input", "window_control", "system_settings", "system_power"}

class PCOperatorNaturalLanguageTests(unittest.TestCase):
    def setUp(self):
        self.operator = PCOperator(PermissionStub(), lambda *args: True)
    def test_metrics_alias(self):
        self.operator.metrics = lambda: "metrics-ok"
        self.assertEqual(self.operator.dispatch("show PC resources"), "metrics-ok")
    def test_mouse_coordinate_aliases(self):
        seen = []
        self.operator.mouse = lambda action, x, y: seen.append((action, x, y)) or "mouse-ok"
        self.assertEqual(self.operator.dispatch("click at 400,200"), "mouse-ok")
        self.assertEqual(seen[-1], ("click", 400, 200))
        self.operator.dispatch("right click at 100 250")
        self.assertEqual(seen[-1], ("right click", 100, 250))
        self.operator.dispatch("move mouse to 800,600")
        self.assertEqual(seen[-1], ("move", 800, 600))
    def test_scroll_alias(self):
        seen = []
        self.operator.scroll = lambda amount: seen.append(amount) or "scroll-ok"
        self.operator.dispatch("scroll down 4")
        self.assertEqual(seen, [-4])
    def test_volume_and_brightness_aliases(self):
        seen = []
        self.operator.volume_set = lambda value: seen.append(("volume", value)) or "ok"
        self.operator.brightness_set = lambda value: seen.append(("brightness", value)) or "ok"
        self.operator.dispatch("set volume to 50%")
        self.operator.dispatch("set brightness to 70")
        self.assertEqual(seen, [("volume", 50), ("brightness", 70)])
    def test_window_alias(self):
        seen = []
        self.operator.window_action = lambda action, title: seen.append((action, title)) or "window-ok"
        self.operator.dispatch("minimize window Notepad")
        self.operator.dispatch("switch to window Calculator")
        self.assertEqual(seen, [("minimize", "Notepad"), ("focus", "Calculator")])
    def test_power_alias_still_routes_through_power_handler(self):
        seen = []
        self.operator.power = lambda action: seen.append(action) or "power-handler"
        self.assertEqual(self.operator.dispatch("shut down computer"), "power-handler")
        self.assertEqual(seen, ["shutdown"])

    def test_low_risk_actions_skip_confirmation_but_risky_actions_keep_it(self):
        prompts = []
        self.operator.confirm = lambda *args: prompts.append(args) or False
        ok, _ = self.operator.approve("desktop_input", "Scroll", "scroll", confirmation_required=False)
        self.assertTrue(ok)
        self.assertEqual(prompts, [])
        ok, message = self.operator.approve("desktop_input", "Type", "type text", confirmation_required=True)
        self.assertFalse(ok)
        self.assertIn("Cancelled", message)
        self.assertEqual(len(prompts), 1)

if __name__ == "__main__":
    unittest.main()
