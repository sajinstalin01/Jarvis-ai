import unittest
from pc_operator import PCOperator
class Perms:
 def __init__(self): self.enabled=set()
 def has(self,p): return p in self.enabled
class Tests(unittest.TestCase):
 def setUp(self):
  self.p=Perms();self.calls=[];self.op=PCOperator(self.p,lambda a,b:self.calls.append((a,b)) or False)
 def test_metrics_and_help(self):
  self.assertIn("pc mouse",self.op.dispatch("pc control help"))
  self.assertIn("Logical CPUs",self.op.dispatch("pc metrics"));self.assertFalse(self.calls)
 def test_permission_required(self):
  self.assertIn("Permission disabled",self.op.dispatch("pc mouse click 20 20"));self.assertFalse(self.calls)
 def test_hotkey_allowlist(self):
  self.p.enabled.add("desktop_input")
  self.assertIn("Cancelled",self.op.dispatch("pc keyboard hotkey ctrl+c"))
  self.assertIn("Hotkey blocked",self.op.dispatch("pc keyboard hotkey win+r"))
 def test_power_permission_required(self):
  self.assertIn("Permission disabled",self.op.dispatch("pc power shutdown"))
 def test_unknown_command(self):self.assertIsNone(self.op.dispatch("turn on the computer"))
if __name__=="__main__":unittest.main()
