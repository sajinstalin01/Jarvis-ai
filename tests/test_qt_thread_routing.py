"""Regression tests for Qt thread ownership in scheduled workflows."""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "jarvis.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def find_method(class_name, method_name):
    for node in TREE.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                    return child
    raise AssertionError(f"{class_name}.{method_name} not found")


class QtThreadRoutingTests(unittest.TestCase):
    def test_reminder_worker_queues_workflow_tick(self):
        method = find_method("JarvisBridge", "_reminder_loop")
        calls = [
            node for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run_due_workflows"
        ]
        self.assertEqual(calls, [], "Scheduled workflow code must not run on reminder worker thread.")
        self.assertIn("workflow_tick_requested.emit()", ast.get_source_segment(SOURCE, method))

    def test_workflow_tick_is_queued_to_gui_thread(self):
        self.assertIn("workflow_tick_requested = pyqtSignal()", SOURCE)
        self.assertIn("self._run_due_workflows_on_ui, Qt.ConnectionType.QueuedConnection", SOURCE)
        method = find_method("JarvisBridge", "_run_due_workflows_on_ui")
        self.assertTrue(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run_due_workflows"
            for node in ast.walk(method)
        ))


if __name__ == "__main__":
    unittest.main()
