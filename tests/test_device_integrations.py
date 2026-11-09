import tempfile
import unittest
from pathlib import Path
from features.device_integrations import DeviceIntegrationHub

class DeviceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.hub=DeviceIntegrationHub(Path(self.tmp.name),confirm=lambda *_: True)
    def tearDown(self): self.tmp.cleanup()
    def test_alexa_guidance_does_not_claim_connection(self):
        text=self.hub.dispatch("alexa setup")
        self.assertIn("Home Assistant",text)
        self.assertIn("does not collect",text)
    def test_entity_filter_and_allowlist(self):
        self.assertIsNone(self.hub.dispatch("unrelated"))
        self.assertEqual(self.hub.control("shell.command","run"),"Invalid entity ID. Use a Home Assistant entity such as light.desk.")
        self.assertIn("Blocked service",self.hub.control("light.desk","delete"))
    def test_mutating_action_requires_confirmation(self):
        hub=DeviceIntegrationHub(Path(self.tmp.name),confirm=lambda *_: False)
        self.assertIn("cancelled",hub.control("light.desk","turn_on").lower())
