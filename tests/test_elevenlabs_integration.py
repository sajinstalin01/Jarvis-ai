import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ElevenLabsIntegrationTests(unittest.TestCase):
    def test_active_bridge_instantiates_manager_and_routes_commands(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn("from elevenlabs_manager import ElevenLabsManager", source)
        self.assertIn("self.elevenlabs = ElevenLabsManager(", source)
        self.assertIn("elevenlabs_response = self.elevenlabs.handle_command(raw)", source)

    def test_generated_audio_and_secret_settings_are_ignored_by_git(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config/api_keys.json", ignore)
        self.assertIn("generated_audio/", ignore)

    def test_optional_normal_response_tts_is_opt_in(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("JARVIS_TTS_PROVIDER", "pyttsx3")', source)
        self.assertIn("self.elevenlabs.speak_response(answer)", source)

    def test_elevenlabs_scribe_is_opt_in_for_microphone_recognition(self):
        source = (ROOT / "voice_control.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("JARVIS_STT_PROVIDER", "google")', source)
        self.assertIn("ElevenLabsClient().transcribe(audio_path)", source)


    def test_bridge_has_health_status_and_auto_memory_commands(self):
        source = (ROOT / "jarvis.py").read_text(encoding="utf-8")
        self.assertIn('"api status"', source)
        self.assertIn('"api check"', source)
        self.assertIn('"memory auto off"', source)
        self.assertIn("learn_from_message(self.store, prompt)", source)

    def test_readme_lists_major_api_features_and_upload_privacy(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for item in (
            "text-to-speech", "speech-to-text", "sound effects", "music generation",
            "multi-voice dialogue", "voice conversion", "background-noise isolation",
            "uploads captured microphone audio",
        ):
            self.assertIn(item.casefold(), readme.casefold())


if __name__ == "__main__":
    unittest.main()
