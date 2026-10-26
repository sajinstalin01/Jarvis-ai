import tempfile, unittest
from pathlib import Path
from features.hub import FeatureHub
class FeatureTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.h=FeatureHub(self.root)
 def tearDown(self): self.temp.cleanup()
 def test_graph(self):
  self.assertIn("saved",self.h.dispatch("graph add JARVIS -> includes -> Vision").lower())
  self.assertIn("Vision",self.h.dispatch("graph search Vision"))
 def test_workflow_allowlist(self):
  self.assertIn("Saved workflow",self.h.dispatch("workflow studio add demo: time; calculate 2 + 2"))
  self.assertIn("Only",self.h.dispatch("workflow studio add bad: delete all files"))
 def test_index_search(self):
  p=self.root/"docs"; p.mkdir(); (p/"guide.md").write_text("JARVIS feature intelligence",encoding="utf-8")
  self.assertIn("Indexed 1",self.h.dispatch(f"files index {p}"))
  self.assertIn("guide.md",self.h.dispatch("files search intelligence"))
 def test_project_registry(self):
  p=self.root/"my-project"; p.mkdir()
  self.assertIn("registered",self.h.dispatch(f"project add demo: {p}").lower())
  self.assertIn("demo",self.h.dispatch("projects"))
 def test_unknown_command(self): self.assertIsNone(self.h.dispatch("unrelated user prompt"))
if __name__=="__main__": unittest.main()
