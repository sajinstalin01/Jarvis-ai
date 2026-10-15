import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from jarvis_services import JarvisStore, parse_reminder_command, system_metrics


class JarvisStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = JarvisStore(Path(self.temp.name) / "test.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_memory_and_history_persist(self):
        memory_id = self.store.remember("Prefer concise answers")
        self.assertGreater(memory_id, 0)
        self.assertEqual(self.store.list_memories()[0]["content"], "Prefer concise answers")
        self.store.save_message("BOSS", "hello JARVIS")
        self.assertIn("hello", self.store.search_history("hello")[0]["content"])
        self.assertTrue(self.store.forget_memory(memory_id))
        self.assertEqual(self.store.list_memories(), [])

    def test_reminder_once_fires_and_disables(self):
        due = datetime.now().astimezone() - timedelta(minutes=1)
        reminder_id = self.store.add_reminder("test reminder", due)
        due_rows = self.store.due_reminders()
        self.assertEqual([row["id"] for row in due_rows], [reminder_id])
        self.assertEqual(self.store.list_reminders(), [])

    def test_recurring_reminder_moves_forward(self):
        due = datetime.now().astimezone() - timedelta(days=2)
        reminder_id = self.store.add_reminder("daily task", due, "daily")
        self.assertEqual(len(self.store.due_reminders()), 1)
        reminder = next(row for row in self.store.list_reminders() if row["id"] == reminder_id)
        self.assertGreater(datetime.fromisoformat(reminder["due_at"]), datetime.now().astimezone())

    def test_workflow_allowlist(self):
        self.store.save_workflow("morning", ["launch chrome", "open github"])
        self.assertEqual(len(self.store.get_workflow("morning")["steps"]), 2)
        with self.assertRaises(ValueError):
            self.store.save_workflow("unsafe", ["delete all files"])
        with self.assertRaises(ValueError):
            self.store.save_workflow("url", ["open https://example.com"])

    def test_reminder_parser(self):
        parsed = parse_reminder_command("remind me in 10 minutes to stretch")
        self.assertEqual(parsed[0], "stretch")
        self.assertEqual(parsed[2], "once")
        daily = parse_reminder_command("remind me daily to review tasks")
        self.assertEqual(daily[2], "daily")
        self.assertIsNone(parse_reminder_command("remind me whenever"))

    def test_metrics_returns_basic_info(self):
        metrics = system_metrics()
        self.assertIn("host", metrics)
        self.assertIn("platform", metrics)


if __name__ == "__main__":
    unittest.main()
