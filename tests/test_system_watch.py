import tempfile
import unittest
from pathlib import Path
from features.system_watch import SystemWatch

class SystemWatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.watch=SystemWatch(Path(self.tmp.name))
    def tearDown(self): self.tmp.cleanup()
    def test_monitor_opt_in_and_toggle(self):
        self.assertFalse(self.watch.enabled())
        self.assertIn("enabled",self.watch.set_enabled(True))
        self.assertTrue(self.watch.enabled())
        self.assertIn("disabled",self.watch.set_enabled(False))
        self.assertFalse(self.watch.enabled())
    def test_history_empty(self):
        self.assertIn("No monitoring samples",self.watch.history())
