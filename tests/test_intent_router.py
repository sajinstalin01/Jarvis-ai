import unittest
from core.intent_router import normalize_natural_command


class NaturalIntentRouterTests(unittest.TestCase):
    def test_prefix_and_polite_open(self):
        self.assertEqual(normalize_natural_command("Jarvis, could you open Chrome for me?"), "open Chrome")

    def test_system_commands(self):
        self.assertEqual(normalize_natural_command("Please check my PC"), "pc status")
        self.assertEqual(normalize_natural_command("take a screenshot"), "pc screenshot")
        self.assertEqual(normalize_natural_command("lock my computer"), "pc lock")

    def test_tasks(self):
        self.assertEqual(normalize_natural_command("Jarvis, show my tasks"), "tasks list")
        self.assertEqual(normalize_natural_command("mark task 12 as complete"), "tasks done 12")
        self.assertEqual(normalize_natural_command("delete task 5"), "tasks delete 5")
        self.assertEqual(normalize_natural_command("add a new task: prepare the demo"), "tasks add prepare the demo")

    def test_search_and_calculation(self):
        self.assertEqual(normalize_natural_command("look up Python tutorials"), "search Python tutorials")
        self.assertEqual(normalize_natural_command("calculate 12 * (8 + 2)"), "calculate 12 * (8 + 2)")

    def test_ambiguous_or_arbitrary_shell_is_not_routed(self):
        self.assertIsNone(normalize_natural_command("run this powershell command: Remove-Item C:\\"))
        self.assertIsNone(normalize_natural_command("clean up my downloads"))
        self.assertIsNone(normalize_natural_command("do something clever"))


if __name__ == "__main__":
    unittest.main()
