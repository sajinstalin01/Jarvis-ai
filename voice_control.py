"""Reliable microphone input and serialized local speech output for JARVIS.

Audio capture is isolated in a worker. TTS is owned by one dedicated worker
thread so pyttsx3/COM engines are never initialized on the Qt thread and then
used from unrelated threads. Device selection is optional and name-based.
"""
from __future__ import annotations

import os
import queue
import threading
from typing import Callable

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


def list_microphones() -> list[str]:
    """Return installed microphone names without opening a recording stream."""
    if sr is None:
        return []
    try:
        return list(sr.Microphone.list_microphone_names())
    except Exception:
        return []


def resolve_microphone(device_setting: str | None, names: list[str]) -> int | None:
    """Resolve an explicit numeric index or case-insensitive name fragment."""
    value = str(device_setting or "").strip()
    if not value or value.casefold() in {"default", "system default", "auto"}:
        return None
    if value.isdigit():
        index = int(value)
        if 0 <= index < len(names):
            return index
        raise ValueError(f"Microphone index {index} is unavailable; found {len(names)} device(s).")
    matches = [i for i, name in enumerate(names) if value.casefold() in name.casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError("Microphone name is ambiguous: " + ", ".join(names[i] for i in matches))
    raise ValueError(f"Microphone '{value}' was not found. Available: " + (", ".join(names) or "none"))


class VoiceController:
    """Push-to-talk input and single-owner TTS output.

    JARVIS_MIC_DEVICE accepts a device index or unique name fragment.
    JARVIS_TTS_VOICE optionally selects an installed OS voice by name/id fragment.
    """

    _STOP = object()
    _INTERRUPT = object()

    def __init__(self, on_result: Callable[[str], None], on_status: Callable[[str], None] = lambda _s: None):
        self.on_result = on_result
        self.on_status = on_status
        self._listen_lock = threading.Lock()
        self._tts_queue: queue.Queue = queue.Queue()
        self._closed = threading.Event()
        self._tts_ready = threading.Event()
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True, name="JarvisTTSOwner")
        self._tts_thread.start()

    def _status(self, message: str) -> None:
        try:
            self.on_status(str(message))
        except Exception:
            pass

    def listen_once(self) -> None:
        if sr is None:
            self._status("Voice input requires SpeechRecognition and PyAudio. Install PyAudio for your Python version.")
            return
        if self._closed.is_set():
            self._status("Voice controller is closed.")
            return
        if not self._listen_lock.acquire(blocking=False):
            self._status("Microphone is already listening.")
            return

        def work():
            try:
                recognizer = sr.Recognizer()
                try:
                    from memory.config_manager import get_mic_sensitivity
                    sensitivity = get_mic_sensitivity()
                except Exception:
                    sensitivity = "normal"
                recognizer.energy_threshold = {"low": 350, "normal": 220, "high": 120}.get(sensitivity, 220)
                recognizer.dynamic_energy_threshold = True
                recognizer.pause_threshold = 0.7
                recognizer.non_speaking_duration = 0.4

                names = list_microphones()
                setting = os.getenv("JARVIS_MIC_DEVICE", "")
                device_index = resolve_microphone(setting, names)
                self._status("Listening on " + (names[device_index] if device_index is not None else "the system default microphone") + "…")
                sample_rate = os.getenv("JARVIS_MIC_SAMPLE_RATE", "").strip()
                kwargs = {"device_index": device_index, "chunk_size": 1024}
                if sample_rate.isdigit():
                    kwargs["sample_rate"] = int(sample_rate)
                with sr.Microphone(**kwargs) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.6)
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

                provider = os.getenv("JARVIS_STT_PROVIDER", "google").strip().lower()
                if provider in {"whisper", "offline"}:
                    self._status("Transcribing locally with Whisper…")
                    try:
                        import numpy as np
                        from core.stt import WhisperSTT
                        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                        if not hasattr(self, "_whisper_stt"):
                            self._whisper_stt = WhisperSTT(model_name=os.getenv("JARVIS_WHISPER_MODEL", "base"))
                        text = self._whisper_stt.transcribe(samples)
                    except ImportError as exc:
                        raise RuntimeError("Offline voice needs faster-whisper. Set JARVIS_STT_PROVIDER=whisper after installing it.") from exc
                else:
                    self._status("Recognizing speech…")
                    text = recognizer.recognize_google(audio)
                if text and text.strip():
                    self.on_result(text.strip())
                    self._status("Voice command recognized.")
                else:
                    self._status("No speech was recognized.")
            except Exception as exc:
                self._status(f"Microphone/voice error: {type(exc).__name__}: {exc}")
            finally:
                self._listen_lock.release()

        threading.Thread(target=work, daemon=True, name="JarvisVoiceInput").start()

    def speak(self, text: str) -> None:
        """Queue speech; never touch the TTS engine from the caller's thread."""
        message = str(text or "").strip()
        if message and not self._closed.is_set():
            try:
                self._tts_queue.put_nowait(message[:3000])
            except Exception as exc:
                self._status(f"Speech queue error: {exc}")

    def _tts_loop(self) -> None:
        engine = None
        loop_started = False
        try:
            if pyttsx3 is not None:
                # The SAPI/COM engine and its event loop are owned by this thread.
                engine = pyttsx3.init()
                engine.setProperty("rate", max(125, min(210, int(os.getenv("JARVIS_TTS_RATE", "172")))))
                engine.setProperty("volume", 1.0)
                voices = engine.getProperty("voices") or []
                requested = os.getenv("JARVIS_TTS_VOICE", "").strip().casefold()
                selected = None
                if requested:
                    selected = next((v for v in voices if requested in str(getattr(v, "name", "")).casefold() or requested in str(getattr(v, "id", "")).casefold()), None)
                else:
                    # Prefer a naturally available English UK voice, then a
                    # commonly installed lower-register English voice. This is
                    # a delivery profile, not an imitation of a specific actor.
                    def voice_score(v):
                        name = str(getattr(v, "name", "")).casefold()
                        ident = str(getattr(v, "id", "")).casefold()
                        langs = " ".join(str(x) for x in (getattr(v, "languages", []) or [])).casefold()
                        text = name + " " + ident + " " + langs
                        score = 0
                        if "en-gb" in text or "english (united kingdom)" in text or "english uk" in text: score += 8
                        elif "english" in text or "en-us" in text: score += 4
                        if any(word in text for word in ("male", "george", "daniel", "ryan", "david", "james", "guy")): score += 3
                        return score
                    selected = max(voices, key=voice_score) if voices else None
                if selected is not None:
                    engine.setProperty("voice", selected.id)
                engine.startLoop(False)
                loop_started = True
                self._status("JARVIS voice output ready.")
            else:
                self._status("Voice output unavailable: install pyttsx3.")
        except Exception as exc:
            self._status(f"Voice output initialization failed: {exc}")
            engine = None
        finally:
            self._tts_ready.set()

        running = True
        while running and not self._closed.is_set():
            try:
                item = self._tts_queue.get(timeout=0.01)
                if item is self._STOP:
                    running = False
                elif item is self._INTERRUPT:
                    if engine is not None:
                        engine.stop()
                elif engine is not None:
                    engine.say(item)
            except queue.Empty:
                pass
            except Exception as exc:
                self._status(f"Voice queue error: {exc}")
            if engine is not None and loop_started:
                try:
                    engine.iterate()
                except Exception as exc:
                    self._status(f"Voice playback error: {exc}")
                    try:
                        engine.stop()
                    except Exception:
                        pass
        if engine is not None:
            try:
                engine.stop()
                if loop_started:
                    engine.endLoop()
            except Exception:
                pass

    def stop(self) -> None:
        """Interrupt the current utterance and discard queued speech, keeping TTS ready."""
        try:
            while True:
                self._tts_queue.get_nowait()
        except queue.Empty:
            pass
        except Exception:
            pass
        if not self._closed.is_set():
            self._tts_queue.put_nowait(self._INTERRUPT)

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self._tts_queue.put_nowait(self._STOP)
        except Exception:
            pass
