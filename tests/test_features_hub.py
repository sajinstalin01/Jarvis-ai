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

 def test_search_ranks_filename_and_returns_snippet(self):
  docs=self.root/"docs"; docs.mkdir()
  (docs/"jarvis-memory.md").write_text("Memory search relevance\nJARVIS local memory indexing",encoding="utf-8")
  (docs/"misc.txt").write_text("A short unrelated note about cooking",encoding="utf-8")
  self.h.dispatch(f"files index {docs}")
  result=self.h.dispatch("files search jarvis memory")
  self.assertIn("jarvis-memory.md",result)
  self.assertIn("local memory indexing",result)
  self.assertLess(result.index("jarvis-memory.md"),result.index("misc.txt") if "misc.txt" in result else len(result))
 def test_search_empty_index_and_stopwords(self):
  self.assertIn("No indexed files",self.h.dispatch("files search jarvis"))
  self.assertIn("Use files search",self.h.dispatch("files search the and is"))
 def test_project_index_command(self):
  p=self.root/"project"; p.mkdir()
  (p/"README.md").write_text("active project indexing token",encoding="utf-8")
  self.h.dispatch(f"project add sample: {p}")
  result=self.h.dispatch("project index active")
  self.assertIn("Indexed 1",result)
  self.assertIn("active project indexing token",self.h.dispatch("files search indexing"))
 def test_unknown_command(self): self.assertIsNone(self.h.dispatch("unrelated user prompt"))
 def test_tasks_persist_and_complete(self):
  added=self.h.dispatch("tasks add Review JARVIS tests | due=2099-01-02 10:30")
  self.assertIn("Task #1 saved locally",added)
  self.assertIn("Review JARVIS tests",self.h.dispatch("tasks list"))
  self.assertIn("2099-01-02T10:30",self.h.dispatch("tasks list"))
  self.assertIn("marked done",self.h.dispatch("tasks done 1"))
  self.assertIn("[DONE]",self.h.dispatch("tasks list"))

 def test_tasks_validate_due_and_delete(self):
  self.assertIn("Invalid due date",self.h.dispatch("tasks add Bad date | due=tomorrow"))
  self.h.dispatch("tasks add Temporary task")
  self.assertIn("deleted",self.h.dispatch("tasks delete 1"))
  self.assertIn("No tasks saved",self.h.dispatch("tasks list"))

 def test_tasks_due_filter(self):
  self.h.dispatch("tasks add Future task | due=2099-01-02 10:30")
  self.assertIn("No overdue tasks",self.h.dispatch("tasks due"))
if __name__=="__main__": unittest.main()
