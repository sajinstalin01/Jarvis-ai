import tempfile
import unittest
from pathlib import Path
from unittest import mock

import elevenlabs_api
from elevenlabs_api import (
    DEFAULT_MODEL_ID,
    ElevenLabsAPIError,
    ElevenLabsClient,
    _format_error,
)


class ElevenLabsClientTests(unittest.TestCase):
    def test_missing_api_key_fails_before_network_call(self):
        client = ElevenLabsClient(api_key="")
        with self.assertRaisesRegex(ElevenLabsAPIError, "API key is not configured"):
            client.get_user()

    def test_tts_saves_binary_audio_and_uses_expected_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = ElevenLabsClient(api_key="local-test-key")
            with mock.patch.object(elevenlabs_api, "AUDIO_DIR", Path(tmp)), mock.patch.object(
                client, "_request", return_value=(b"fake-mp3-bytes", "audio/mpeg", {})
            ) as request:
                path = Path(client.text_to_speech("Hello, JARVIS", "voice123"))
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), b"fake-mp3-bytes")
            args, kwargs = request.call_args
            self.assertEqual(args[:2], ("POST", "/v1/text-to-speech/voice123"))
            self.assertEqual(kwargs["json_body"]["text"], "Hello, JARVIS")
            self.assertEqual(kwargs["json_body"]["model_id"], DEFAULT_MODEL_ID)
            self.assertEqual(kwargs["params"]["output_format"], "mp3_44100_128")

    def test_tts_rejects_empty_and_overlong_text_before_request(self):
        client = ElevenLabsClient(api_key="test")
        with mock.patch.object(client, "_request") as request:
            with self.assertRaisesRegex(ElevenLabsAPIError, "cannot be empty"):
                client.text_to_speech("  ", "voice123")
            with self.assertRaisesRegex(ElevenLabsAPIError, "character limit"):
                client.text_to_speech("x" * (elevenlabs_api.MAX_TTS_CHARACTERS + 1), "voice123")
        request.assert_not_called()

    def test_voice_list_search_is_escaped_as_query_parameters(self):
        client = ElevenLabsClient(api_key="test")
        with mock.patch.object(client, "_request", return_value={"voices": []}) as request:
            client.list_voices("English voice", page_size=999)
        request.assert_called_once_with(
            "GET", "/v2/voices", params={"page_size": 100, "search": "English voice"}
        )

    def test_sound_effect_duration_is_clamped_and_loop_setting_is_preserved(self):
        client = ElevenLabsClient(api_key="test")
        with mock.patch.object(client, "_request", return_value=(b"sound", "audio/mpeg", {})) as request, \
             mock.patch.object(elevenlabs_api, "AUDIO_DIR", Path(tempfile.gettempdir())):
            path = client.generate_sound_effect("rain", duration_seconds=400, loop=True)
        payload = request.call_args.kwargs["json_body"]
        self.assertEqual(payload["duration_seconds"], 30.0)
        self.assertTrue(payload["loop"])
        self.assertTrue(Path(path).is_file())
        Path(path).unlink(missing_ok=True)

    def test_dialogue_total_characters_are_limited_before_api_call(self):
        client = ElevenLabsClient(api_key="test")
        with mock.patch.object(client, "_request") as request:
            with self.assertRaisesRegex(ElevenLabsAPIError, "limited to"):
                client.text_to_dialogue([{"voice_id": "voice123", "text": "x" * 2001}])
        request.assert_not_called()

    def test_transcription_upload_requires_an_existing_file_and_uses_scribe(self):
        client = ElevenLabsClient(api_key="test")
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "sample.wav"
            audio.write_bytes(b"wav bytes")
            with mock.patch.object(client, "_request", return_value={"text": "hello"}) as request:
                self.assertEqual(client.transcribe(audio)["text"], "hello")
            self.assertEqual(request.call_args.args[:2], ("POST", "/v1/speech-to-text"))
            self.assertEqual(request.call_args.kwargs["multipart_fields"]["model_id"], "scribe_v2")
            self.assertEqual(request.call_args.kwargs["file_field"], ("file", audio.resolve()))

    def test_error_messages_never_echo_api_key(self):
        key = "xi-secret-example-value"
        message = _format_error(401, f"Invalid xi-api-key: {key}".encode())
        self.assertIn("rejected the API key", message)
        self.assertNotIn(key, message)
        self.assertIn("quota", _format_error(429, b"").casefold())


if __name__ == "__main__":
    unittest.main()
