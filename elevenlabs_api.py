"""Lightweight ElevenLabs REST client using only the Python standard library.

Implements common audio endpoints without logging or persisting API keys:
text-to-speech, speech-to-text, voice discovery, model discovery, account/usage,
sound effects, music, multi-voice dialogue, voice conversion, and audio isolation.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

API_BASE = "https://api.elevenlabs.io"
ROOT = Path(__file__).resolve().parent
AUDIO_DIR = ROOT / "generated_audio"
MAX_UPLOAD_BYTES = 150 * 1024 * 1024
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
MAX_TTS_CHARACTERS = 10000
MAX_DIALOGUE_CHARACTERS = 2000


class ElevenLabsAPIError(RuntimeError):
    """Readable API error without exposing request headers or the secret key."""


def _format_error(status: int | None, body: bytes) -> str:
    detail = ""
    try:
        parsed = json.loads(body.decode("utf-8", errors="replace"))
        if isinstance(parsed, dict):
            raw = parsed.get("detail", parsed.get("message", parsed.get("error", "")))
            if isinstance(raw, dict):
                detail = str(raw.get("message") or raw.get("detail") or raw.get("status") or "")
            elif raw:
                detail = str(raw)
    except (ValueError, TypeError):
        pass
    detail = re.sub(r"(?i)(xi-api-key|api[_ -]?key|authorization)\s*[:=]\s*\S+", r"\1: [redacted]", detail)
    detail = " ".join(detail.split())[:500]
    if status == 401:
        return "ElevenLabs rejected the API key (401). Check the key and its permissions."
    if status == 403:
        return "ElevenLabs denied this operation (403). Check API-key permissions and plan access."
    if status == 429:
        return "ElevenLabs rate limit or quota reached (429). Check your plan and usage."
    if status and detail:
        return f"ElevenLabs API error {status}: {detail}"
    if status:
        return f"ElevenLabs API request failed with HTTP {status}."
    return "ElevenLabs API request failed. Check network access and try again."


class ElevenLabsClient:
    def __init__(self, api_key: str | None = None, timeout: float = 45.0):
        self.api_key = str(api_key if api_key is not None else os.getenv("ELEVENLABS_API_KEY", "")).strip()
        self.timeout = max(5.0, min(float(timeout), 180.0))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _require_key(self) -> None:
        if not self.api_key:
            raise ElevenLabsAPIError(
                "ElevenLabs API key is not configured. Use 'elevenlabs configure' or set ELEVENLABS_API_KEY in .env."
            )

    def _url(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        url = API_BASE + "/" + endpoint.lstrip("/")
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean, doseq=True)
        return url

    def _request(self, method: str, endpoint: str, *, params=None, json_body=None,
                 multipart_fields=None, file_field=None, expect_binary=False):
        self._require_key()
        headers = {"xi-api-key": self.api_key, "Accept": "application/json"}
        data = None
        if multipart_fields is not None or file_field is not None:
            boundary = "----JARVISElevenLabs" + uuid.uuid4().hex
            chunks: list[bytes] = []
            fields = list((multipart_fields or {}).items())
            for name, value in fields:
                chunks.extend([
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ])
            if file_field is not None:
                field_name, file_path = file_field
                path = Path(file_path)
                size = path.stat().st_size
                if size <= 0:
                    raise ElevenLabsAPIError("The selected file is empty.")
                if size > MAX_UPLOAD_BYTES:
                    raise ElevenLabsAPIError(
                        f"Audio file exceeds the local {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit."
                    )
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                chunks.extend([
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'.encode(),
                    f"Content-Type: {mime}\r\n\r\n".encode(),
                    path.read_bytes(),
                    b"\r\n",
                ])
            chunks.append(f"--{boundary}--\r\n".encode())
            data = b"".join(chunks)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self._url(endpoint, params), data=data, headers=headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
                if expect_binary:
                    if "json" in content_type.casefold():
                        raise ElevenLabsAPIError(_format_error(response.status, payload))
                    return payload, content_type, dict(response.headers.items())
                if not payload:
                    return {}
                try:
                    return json.loads(payload.decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ElevenLabsAPIError("ElevenLabs returned an unexpected non-JSON response.") from exc
        except urllib.error.HTTPError as exc:
            body = exc.read(16_384)
            raise ElevenLabsAPIError(_format_error(exc.code, body)) from None
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", "network error"))
            raise ElevenLabsAPIError(f"Could not reach ElevenLabs: {reason[:200]}") from None
        except TimeoutError:
            raise ElevenLabsAPIError("ElevenLabs request timed out. Try again.") from None
        except OSError as exc:
            raise ElevenLabsAPIError(f"Could not read the selected audio or save the request: {exc}") from None

    def _save_audio(self, payload: bytes, prefix: str) -> str:
        if not payload:
            raise ElevenLabsAPIError("ElevenLabs returned an empty audio file.")
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", prefix).strip("_")[:40] or "audio"
        filename = f"{safe_prefix}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
        destination = AUDIO_DIR / filename
        destination.write_bytes(payload)
        return str(destination)

    def get_user(self) -> dict[str, Any]:
        return self._request("GET", "/v1/user")

    def get_subscription(self) -> dict[str, Any]:
        return self._request("GET", "/v1/user/subscription")

    def list_voices(self, search: str = "", page_size: int = 30) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": max(1, min(int(page_size), 100))}
        if search.strip():
            params["search"] = search.strip()[:100]
        return self._request("GET", "/v2/voices", params=params)

    def list_models(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/v1/models")
        return data if isinstance(data, list) else data.get("models", [])

    def text_to_speech(self, text: str, voice_id: str, model_id: str = DEFAULT_MODEL_ID) -> str:
        text = str(text).strip()
        if not text:
            raise ElevenLabsAPIError("Text to speak cannot be empty.")
        if len(text) > MAX_TTS_CHARACTERS:
            raise ElevenLabsAPIError(f"Text exceeds the {MAX_TTS_CHARACTERS:,}-character limit used by this JARVIS command.")
        if not voice_id.strip():
            raise ElevenLabsAPIError("Set a voice ID first. Use 'elevenlabs voices' then 'elevenlabs set-voice <voice_id>'.")
        payload, _content_type, _headers = self._request(
            "POST", f"/v1/text-to-speech/{urllib.parse.quote(voice_id, safe='')}",
            params={"output_format": DEFAULT_OUTPUT_FORMAT},
            json_body={"text": text, "model_id": model_id},
            expect_binary=True,
        )
        return self._save_audio(payload, "speech")

    def transcribe(self, file_path: str | os.PathLike, language_code: str | None = None) -> dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise ElevenLabsAPIError(f"Audio/video file not found: {path}")
        fields: dict[str, Any] = {"model_id": "scribe_v2"}
        if language_code:
            fields["language_code"] = language_code
        data = self._request(
            "POST", "/v1/speech-to-text",
            params={"enable_logging": "true"},
            multipart_fields=fields, file_field=("file", path),
        )
        return data if isinstance(data, dict) else {"text": str(data)}

    def generate_sound_effect(self, prompt: str, duration_seconds: float = 5.0,
                              loop: bool = False, model_id: str = "eleven_text_to_sound_v2") -> str:
        prompt = prompt.strip()
        if not prompt:
            raise ElevenLabsAPIError("Describe the sound effect to generate.")
        duration = max(0.5, min(float(duration_seconds), 30.0))
        payload, _content_type, _headers = self._request(
            "POST", "/v1/sound-generation",
            params={"output_format": DEFAULT_OUTPUT_FORMAT},
            json_body={
                "text": prompt[:1000],
                "duration_seconds": duration,
                "loop": bool(loop),
                "model_id": model_id,
                "prompt_influence": 0.3,
            },
            expect_binary=True,
        )
        return self._save_audio(payload, "sound_effect")

    def compose_music(self, prompt: str, duration_seconds: float = 30.0,
                      instrumental: bool = False, model_id: str = "music_v2_5") -> str:
        prompt = prompt.strip()
        if not prompt:
            raise ElevenLabsAPIError("Describe the music you want to generate.")
        if len(prompt) > 4100:
            raise ElevenLabsAPIError("Music prompt must be 4,100 characters or fewer.")
        duration = max(3.0, min(float(duration_seconds), 600.0))
        payload, _content_type, _headers = self._request(
            "POST", "/v1/music",
            params={"output_format": "auto"},
            json_body={
                "prompt": prompt,
                "music_length_ms": int(duration * 1000),
                "model_id": model_id,
                "force_instrumental": bool(instrumental),
            },
            expect_binary=True,
        )
        return self._save_audio(payload, "music")

    def text_to_dialogue(self, inputs: list[dict[str, str]]) -> str:
        if not inputs or len(inputs) > 8:
            raise ElevenLabsAPIError("Provide between 1 and 8 dialogue turns.")
        total = sum(len(str(item.get("text", ""))) for item in inputs)
        if total > MAX_DIALOGUE_CHARACTERS:
            raise ElevenLabsAPIError(f"Dialogue is limited to {MAX_DIALOGUE_CHARACTERS:,} total characters per request.")
        for item in inputs:
            if not str(item.get("text", "")).strip() or not str(item.get("voice_id", "")).strip():
                raise ElevenLabsAPIError("Each dialogue turn needs both a voice ID and text.")
        payload, _content_type, _headers = self._request(
            "POST", "/v1/text-to-dialogue",
            params={"output_format": DEFAULT_OUTPUT_FORMAT},
            json_body={"inputs": inputs},
            expect_binary=True,
        )
        return self._save_audio(payload, "dialogue")

    def change_voice(self, file_path: str | os.PathLike, voice_id: str,
                     model_id: str = "eleven_multilingual_sts_v2",
                     remove_background_noise: bool = False) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise ElevenLabsAPIError(f"Audio file not found: {path}")
        if not voice_id.strip():
            raise ElevenLabsAPIError("Provide a target voice ID.")
        payload, _content_type, _headers = self._request(
            "POST", f"/v1/voice-changer/{urllib.parse.quote(voice_id, safe='')}",
            params={"output_format": DEFAULT_OUTPUT_FORMAT},
            multipart_fields={
                "model_id": model_id,
                "remove_background_noise": str(bool(remove_background_noise)).lower(),
                "file_format": "other",
            },
            file_field=("audio", path),
            expect_binary=True,
        )
        return self._save_audio(payload, "voice_changed")

    def isolate_audio(self, file_path: str | os.PathLike) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise ElevenLabsAPIError(f"Audio file not found: {path}")
        payload, _content_type, _headers = self._request(
            "POST", "/v1/audio-isolation",
            multipart_fields={"file_format": "other"},
            file_field=("audio", path),
            expect_binary=True,
        )
        return self._save_audio(payload, "audio_isolated")
