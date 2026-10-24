"""Chat-command interface for ElevenLabs API features, with safe background jobs."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import webbrowser
from pathlib import Path
from typing import Callable

from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from elevenlabs_api import (
    DEFAULT_MODEL_ID,
    DEFAULT_VOICE_ID,
    ElevenLabsAPIError,
    ElevenLabsClient,
    MAX_TTS_CHARACTERS,
)

ROOT = Path(__file__).resolve().parent
API_FILE = ROOT / "config" / "api_keys.json"


def _unquote(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


class ElevenLabsManager:
    """Integrates ElevenLabs capabilities into JARVIS chat commands.

    Secret values are only collected in a masked GUI dialog and stored in the
    ignored local config file. Network generation/upload jobs run in background
    threads, then report through callbacks that should be Qt-signal-backed.
    """

    def __init__(self, ui, on_result: Callable[[str], None], on_play: Callable[[str], None]):
        self.ui = ui
        self._on_result = on_result
        self._on_play = on_play
        self._lock = threading.Lock()
        self._active_jobs = 0

    def _settings(self) -> dict:
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_settings(self, changes: dict) -> None:
        API_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = self._settings()
        data.update(changes)
        tmp = API_FILE.with_suffix(API_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(API_FILE)

    def _write_env_value(self, name: str, value: str) -> None:
        """Persist a setting in the ignored local .env without duplicating its key."""
        path = ROOT / ".env"
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        prefix = name + "="
        replacement = prefix + value
        found = False
        updated = []
        for line in lines:
            if line.strip().startswith(prefix):
                if not found:
                    updated.append(replacement)
                    found = True
                # Drop duplicate entries so load order is deterministic.
            else:
                updated.append(line)
        if not found:
            updated.append(replacement)
        path.write_text("\\n".join(updated).rstrip() + "\\n", encoding="utf-8")

    def _api_key(self) -> str:
        settings = self._settings()
        return (os.getenv("ELEVENLABS_API_KEY", "").strip()
                or str(settings.get("elevenlabs_api_key", "")).strip())

    def _client(self) -> ElevenLabsClient:
        return ElevenLabsClient(api_key=self._api_key())

    def _voice_id(self) -> str:
        settings = self._settings()
        return (os.getenv("ELEVENLABS_VOICE_ID", "").strip()
                or str(settings.get("elevenlabs_voice_id", "")).strip()
                or DEFAULT_VOICE_ID)

    def _model_id(self) -> str:
        settings = self._settings()
        return (os.getenv("ELEVENLABS_MODEL_ID", "").strip()
                or str(settings.get("elevenlabs_model_id", "")).strip()
                or DEFAULT_MODEL_ID)

    def _confirm(self, title: str, detail: str) -> bool:
        parent = getattr(self.ui, "_win", None)
        if parent is None:
            return False
        answer = QMessageBox.question(
            parent, title, detail,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _configure(self) -> str:
        parent = getattr(self.ui, "_win", None)
        if parent is None:
            return "ElevenLabs setup requires the desktop window."
        value, accepted = QInputDialog.getText(
            parent,
            "Configure ElevenLabs API",
            "Paste your ElevenLabs API key. It will be masked and stored only in local ignored config.",
            QLineEdit.EchoMode.Password,
        )
        key = value.strip()
        if not accepted or not key:
            return "ElevenLabs configuration cancelled."
        try:
            account = ElevenLabsClient(api_key=key, timeout=12).get_user()
        except ElevenLabsAPIError as exc:
            return f"ElevenLabs key validation failed: {exc}"
        # Never include the entered key in the response or logs.
        self._save_settings({"elevenlabs_api_key": key})
        os.environ["ELEVENLABS_API_KEY"] = key
        self._write_env_value("ELEVENLABS_API_KEY", key)
        name = str(account.get("first_name") or "account")
        return f"ElevenLabs API key validated and stored locally for {name}. The key is not written to chat history or Git."

    def _account_summary(self) -> str:
        data = self._client().get_user()
        subscription = data.get("subscription") if isinstance(data.get("subscription"), dict) else {}
        name = " ".join(filter(None, [
            str(data.get("first_name") or "").strip(),
            str(data.get("last_name") or "").strip(),
        ])) or "ElevenLabs user"
        fields = [f"Account: {name}"]
        if data.get("user_id"):
            fields.append(f"User ID: {data['user_id']}")
        if subscription.get("tier"):
            fields.append(f"Plan: {subscription['tier']}")
        if subscription.get("status"):
            fields.append(f"Subscription status: {subscription['status']}")
        fields.extend([
            f"Default voice ID: {self._voice_id()}",
            f"Default TTS model: {self._model_id()}",
            "API key: configured (value hidden)",
        ])
        return "\n".join(fields)

    def _usage_summary(self) -> str:
        data = self._client().get_subscription()
        count = data.get("character_count")
        limit = data.get("character_limit")
        lines = [
            f"Plan: {data.get('tier', 'unknown')}",
            f"Subscription status: {data.get('status', 'unknown')}",
        ]
        if count is not None and limit is not None:
            lines.append(f"Characters used: {count:,} / {limit:,}")
            if isinstance(limit, (int, float)) and limit:
                lines.append(f"Usage: {max(0, min(100, int(count * 100 / limit)))}% of the character limit")
        if data.get("voice_slots_used") is not None and data.get("voice_limit") is not None:
            lines.append(f"Voice slots: {data['voice_slots_used']} / {data['voice_limit']}")
        if data.get("can_use_instant_voice_cloning") is not None:
            lines.append(f"Instant voice cloning enabled by plan: {bool(data['can_use_instant_voice_cloning'])}")
        next_reset = data.get("next_character_count_reset_unix")
        if next_reset:
            try:
                when = dt.datetime.fromtimestamp(int(next_reset)).astimezone()
                lines.append("Next usage reset: " + when.strftime("%Y-%m-%d %I:%M %p %Z"))
            except (ValueError, OSError, OverflowError):
                pass
        lines.append("This is account usage data returned by ElevenLabs; availability varies by plan and API-key permissions.")
        return "\n".join(lines)

    def _voices_summary(self, query: str) -> str:
        data = self._client().list_voices(search=query, page_size=50)
        voices = data.get("voices", []) if isinstance(data, dict) else []
        if not voices:
            return f"No voices returned for search {query!r}."
        lines = []
        for voice in voices[:25]:
            name = str(voice.get("name") or "Unnamed voice")
            voice_id = str(voice.get("voice_id") or voice.get("id") or "")
            category = str(voice.get("category") or "")
            labels = voice.get("labels") or {}
            language = labels.get("language") if isinstance(labels, dict) else None
            suffix = " · ".join(str(x) for x in (category, language) if x)
            lines.append(f"• {name} — {voice_id}" + (f" ({suffix})" if suffix else ""))
        if data.get("has_more"):
            lines.append("More voices exist; narrow your search term.")
        lines.append("Set the default with: elevenlabs set-voice <voice_id>")
        return "\n".join(lines)

    def _models_summary(self) -> str:
        models = self._client().list_models()
        supported = [m for m in models if m.get("can_do_text_to_speech")]
        if not supported:
            return "No text-to-speech models were returned for this API key."
        lines = []
        for model in supported[:30]:
            lines.append(f"• {model.get('name') or model.get('model_id')} — {model.get('model_id')}")
        lines.append("Set a default with: elevenlabs set-model <model_id>")
        return "\n".join(lines)

    def _ask_upload_confirmation(self, action: str, path: Path) -> bool:
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
        except OSError:
            size_mb = 0
        return self._confirm(
            f"Send audio to ElevenLabs: {action}",
            f"Selected file: {path}\nSize: {size_mb:.1f} MB\n\n"
            "This uploads the audio to the ElevenLabs API for processing. Audio may contain personal or sensitive information. Continue?",
        )

    def speak_response(self, text: str) -> bool:
        """Opt-in TTS for normal JARVIS replies when ELEVENLABS is the configured provider."""
        text = str(text or "").strip()
        if not text or not self._api_key():
            self._on_result("ElevenLabs TTS is selected but no API key is configured.")
            return False
        # Normal assistant responses are capped to prevent accidental huge API charges.
        clipped = text[:MAX_TTS_CHARACTERS]
        if len(text) > len(clipped):
            clipped = clipped[:MAX_TTS_CHARACTERS - 32].rstrip() + " [response shortened]"
        self._start_job(
            "JARVIS voice response",
            lambda: ("Audio saved to " + (path := self._client().text_to_speech(clipped, self._voice_id(), self._model_id())), path),
            autoplay=True,
        )
        return True

    def _start_job(self, label: str, task: Callable[[], tuple[str, str | None]], autoplay: bool = False) -> str:
        with self._lock:
            self._active_jobs += 1

        def work():
            try:
                result, audio_path = task()
                self._on_result(f"{label}: {result}")
                if audio_path and autoplay:
                    self._on_play(audio_path)
            except ElevenLabsAPIError as exc:
                self._on_result(f"{label} failed: {exc}")
            except Exception as exc:
                self._on_result(f"{label} failed unexpectedly: {type(exc).__name__}: {str(exc)[:300]}")
            finally:
                with self._lock:
                    self._active_jobs = max(0, self._active_jobs - 1)

        threading.Thread(target=work, daemon=True, name="ElevenLabs-" + re.sub(r"\W+", "", label)[:25]).start()
        return f"{label} started in the background. JARVIS will log the result when it finishes."

    def _generation_confirm(self, title: str, description: str) -> bool:
        return self._confirm(
            f"Confirm ElevenLabs {title}",
            description + "\n\nThis request uses your ElevenLabs API and may consume plan credits. Continue?",
        )

    def handle_command(self, raw: str):
        raw = str(raw or "").strip()
        match = re.match(r"^elevenlabs(?:\s+|$)(.*)$", raw, flags=re.I | re.S)
        if not match:
            return None
        args = match.group(1).strip()
        if not args or args.casefold() in {"help", "commands"}:
            return (
                "ElevenLabs API commands:\n"
                "• elevenlabs configure — masked API-key entry and validation\n"
                "• elevenlabs status / usage — account and quota\n"
                "• elevenlabs voices [search term] / models\n"
                "• elevenlabs set-voice <voice_id> / set-model <model_id>\n"
                "• elevenlabs speak <text> — generate and play speech\n"
                "• elevenlabs sfx <prompt> — generate a sound effect\n"
                "• elevenlabs music <prompt> — generate a 30-second music track\n"
                "• elevenlabs dialogue <voice_id>: <text> || <voice_id>: <text>\n"
                "• elevenlabs transcribe <audio/video path> — batch transcription\n"
                "• elevenlabs isolate <audio path> — remove background noise\n"
                "• elevenlabs voice-change <voice_id> :: <audio path>\n"
                "Generated audio is saved under generated_audio/. The API key stays local and is never shown."
            )
        if args.casefold() == "configure":
            return self._configure()
        if args.casefold() in {"status", "test", "account"}:
            return self._start_job("Account check", lambda: (self._account_summary(), None))
        if args.casefold() in {"usage", "subscription"}:
            return self._start_job("Usage check", lambda: (self._usage_summary(), None))
        if args.casefold() == "models":
            return self._start_job("Model discovery", lambda: (self._models_summary(), None))
        if args.casefold() == "voices":
            return self._start_job("Voice discovery", lambda: (self._voices_summary(""), None))
        if args.casefold().startswith("voices "):
            term = _unquote(args[7:].strip())
            return self._start_job("Voice search", lambda: (self._voices_summary(term), None))

        set_voice = re.fullmatch(r"set-voice\s+([A-Za-z0-9_-]{3,128})", args, flags=re.I)
        if set_voice:
            voice_id = set_voice.group(1)
            self._save_settings({"elevenlabs_voice_id": voice_id})
            os.environ["ELEVENLABS_VOICE_ID"] = voice_id
            return f"Default ElevenLabs voice ID saved: {voice_id}"
        set_model = re.fullmatch(r"set-model\s+([A-Za-z0-9_.-]{3,100})", args, flags=re.I)
        if set_model:
            model_id = set_model.group(1)
            self._save_settings({"elevenlabs_model_id": model_id})
            os.environ["ELEVENLABS_MODEL_ID"] = model_id
            return f"Default ElevenLabs model ID saved: {model_id}. Use 'elevenlabs models' to see supported TTS models."

        tts = re.fullmatch(r"(?:speak|tts)\s+(.+)", args, flags=re.I | re.S)
        if tts:
            text = _unquote(tts.group(1))
            if len(text) > MAX_TTS_CHARACTERS:
                return f"Text is too long for this command (maximum {MAX_TTS_CHARACTERS:,} characters)."
            if not self._generation_confirm("text-to-speech", f"Voice ID: {self._voice_id()}\nModel: {self._model_id()}\nCharacters: {len(text)}\n\nText:\n{text[:900]}"):
                return "Speech generation cancelled."
            return self._start_job(
                "Text-to-speech",
                lambda: ("Audio saved to " + (path := self._client().text_to_speech(text, self._voice_id(), self._model_id())), path),
                autoplay=True,
            )

        sfx = re.fullmatch(r"sfx\s+(.+)", args, flags=re.I | re.S)
        if sfx:
            prompt = _unquote(sfx.group(1))
            if not self._generation_confirm("sound-effect generation", f"Prompt: {prompt[:1200]}\nDuration: 5 seconds"):
                return "Sound generation cancelled."
            return self._start_job(
                "Sound-effect generation",
                lambda: ("Audio saved to " + (path := self._client().generate_sound_effect(prompt, duration_seconds=5)), path),
                autoplay=True,
            )

        music = re.fullmatch(r"music\s+(.+)", args, flags=re.I | re.S)
        if music:
            prompt = _unquote(music.group(1))
            if not self._generation_confirm("music generation", f"Prompt: {prompt[:1200]}\nDuration: 30 seconds\nModel: music_v2_5"):
                return "Music generation cancelled."
            return self._start_job(
                "Music generation",
                lambda: ("Audio saved to " + (path := self._client().compose_music(prompt, duration_seconds=30)), path),
                autoplay=True,
            )

        dialogue = re.fullmatch(r"dialogue\s+(.+)", args, flags=re.I | re.S)
        if dialogue:
            turns = []
            for chunk in dialogue.group(1).split("||"):
                item = re.fullmatch(r"\s*([A-Za-z0-9_-]{3,128})\s*:\s*(.+?)\s*", chunk, flags=re.S)
                if not item:
                    return "Use: elevenlabs dialogue <voice_id>: Hello || <voice_id>: Hi"
                turns.append({"voice_id": item.group(1), "text": item.group(2).strip()})
            combined = "\n".join(f"{item['voice_id']}: {item['text']}" for item in turns)
            if not self._generation_confirm("dialogue generation", f"Turns: {len(turns)}\n\n{combined[:1200]}"):
                return "Dialogue generation cancelled."
            return self._start_job(
                "Dialogue generation",
                lambda: ("Audio saved to " + (path := self._client().text_to_dialogue(turns)), path),
                autoplay=True,
            )

        transcribe = re.fullmatch(r"transcribe\s+(.+)", args, flags=re.I | re.S)
        if transcribe:
            path = Path(_unquote(transcribe.group(1))).expanduser().resolve()
            if not path.is_file():
                return f"Audio/video file not found: {path}"
            if not self._ask_upload_confirmation("speech-to-text transcription", path):
                return "Transcription cancelled."
            def do_transcribe():
                data = self._client().transcribe(path)
                words = str(data.get("text", "")).strip()
                if not words:
                    words = json.dumps(data, ensure_ascii=False)[:3000]
                return ("Transcription:\n" + words[:10000], None)
            return self._start_job("Transcription", do_transcribe)

        isolate = re.fullmatch(r"isolate\s+(.+)", args, flags=re.I | re.S)
        if isolate:
            path = Path(_unquote(isolate.group(1))).expanduser().resolve()
            if not path.is_file():
                return f"Audio file not found: {path}"
            if not self._ask_upload_confirmation("audio isolation", path):
                return "Audio isolation cancelled."
            return self._start_job(
                "Audio isolation",
                lambda: ("Cleaned audio saved to " + (out := self._client().isolate_audio(path)), out),
                autoplay=True,
            )

        voice_change = re.fullmatch(r"voice-change\s+([A-Za-z0-9_-]{3,128})\s*::\s*(.+)", args, flags=re.I | re.S)
        if voice_change:
            voice_id = voice_change.group(1)
            path = Path(_unquote(voice_change.group(2))).expanduser().resolve()
            if not path.is_file():
                return f"Audio file not found: {path}"
            if not self._ask_upload_confirmation("voice conversion", path):
                return "Voice conversion cancelled."
            if not self._generation_confirm("voice conversion", f"Target voice ID: {voice_id}\nFile: {path.name}"):
                return "Voice conversion cancelled."
            return self._start_job(
                "Voice conversion",
                lambda: ("Converted audio saved to " + (out := self._client().change_voice(path, voice_id)), out),
                autoplay=True,
            )

        return "Unknown ElevenLabs command. Use 'elevenlabs help' for supported commands."
