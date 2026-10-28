import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UIThreadBoundaryTests(unittest.TestCase):
    def test_worker_updates_are_queued_to_gui_thread(self):
        source = (ROOT / "ui.py").read_text(encoding="utf-8")
        signal_names = (
            "_audio_level_sig",
            "_glance_sig",
            "_visemes_sig",
            "_phone_connected_sig",
        )
        for name in signal_names:
            self.assertIn(name + " = pyqtSignal", source)
            self.assertIn(name + ".connect(", source)
        for connection in (
            "self._audio_level_sig.connect(self.hud.set_audio_level, Qt.ConnectionType.QueuedConnection)",
            "self._glance_sig.connect(self.hud.glance, Qt.ConnectionType.QueuedConnection)",
            "self._visemes_sig.connect(self.hud.push_visemes, Qt.ConnectionType.QueuedConnection)",
            "self._phone_connected_sig.connect(self._notify_phone_connected_on_ui, Qt.ConnectionType.QueuedConnection)",
        ):
            self.assertIn(connection, source)
        self.assertIn("self._win._audio_level_sig.emit(float(level))", source)
        self.assertIn("self._win._glance_sig.emit(float(dx), float(dy), float(hold))", source)
        self.assertIn("self._win._visemes_sig.emit(tuple(frames), float(hop), float(at))", source)
        self.assertIn("self._win._phone_connected_sig.emit()", source)
        self.assertNotIn("self._win.hud.set_audio_level(level)", source)
        self.assertNotIn("self._win.hud.push_visemes(frames, hop, at)", source)

    def test_confirmation_dialog_rejects_worker_thread_call(self):
        source = (ROOT / "app_control_manager.py").read_text(encoding="utf-8")
        self.assertIn("QThread.currentThread() != window.thread()", source)
        self.assertIn("return False", source)


if __name__ == "__main__":
    unittest.main()
