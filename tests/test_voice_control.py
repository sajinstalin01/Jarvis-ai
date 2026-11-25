"""Tests for voice device resolution and single-owner TTS architecture."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VoiceControlTests(unittest.TestCase):
    def test_microphone_resolution_default_numeric_and_name(self):
        from voice_control import resolve_microphone
        names = ["Realtek Microphone", "USB Headset Mic"]
        self.assertIsNone(resolve_microphone("", names))
        self.assertIsNone(resolve_microphone("system default", names))
        self.assertEqual(resolve_microphone("1", names), 1)
        self.assertEqual(resolve_microphone("usb headset", names), 1)

    def test_microphone_resolution_rejects_ambiguous_and_missing(self):
        from voice_control import resolve_microphone
        with self.assertRaises(ValueError):
            resolve_microphone("mic", ["USB Mic", "Webcam Mic"])
        with self.assertRaises(ValueError):
            resolve_microphone("9", ["Built-in Mic"])

    def test_tts_engine_is_created_inside_single_owner_worker(self):
        source = (ROOT / "voice_control.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        init = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "VoiceController")
        constructor = next(n for n in init.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "init" for n in ast.walk(constructor)))
        self.assertIn("pyttsx3.init()", source)
        self.assertIn("JarvisTTSOwner", source)

    def test_interrupt_uses_voice_stop(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn("self._voice.stop()", source)


if __name__ == "__main__":
    unittest.main()
