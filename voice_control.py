"""Optional microphone input and local spoken replies for JARVIS."""
import os
import threading

try:
    import speech_recognition as sr
except ImportError:
    sr = None
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class VoiceController:
    def __init__(self, on_result, on_status=lambda s: None):
        self.on_result = on_result
        self.on_status = on_status
        self._stop = threading.Event()
        self.engine = None
        if pyttsx3:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 180)
            except Exception:
                self.engine = None

    def listen_once(self):
        if not sr:
            self.on_status("Voice input needs SpeechRecognition + PyAudio.")
            return

        def work():
            try:
                recognizer = sr.Recognizer()
                from memory.config_manager import get_mic_sensitivity
                recognizer.energy_threshold={"low":350,"normal":220,"high":120}.get(get_mic_sensitivity(),220)
                recognizer.dynamic_energy_threshold=True
                with sr.Microphone() as source:
                    self.on_status("Listening… speak now")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
                provider=os.getenv("JARVIS_STT_PROVIDER","google").strip().lower()
                if provider in {"whisper","offline"}:
                    self.on_status("Transcribing locally with Whisper…")
                    try:
                        import numpy as np
                        from core.stt import WhisperSTT
                        raw=audio.get_raw_data(convert_rate=16000,convert_width=2)
                        samples=np.frombuffer(raw,dtype=np.int16).astype(np.float32)/32768.0
                        if not hasattr(self,"_whisper_stt"): self._whisper_stt=WhisperSTT(model_name=os.getenv("JARVIS_WHISPER_MODEL","base"))
                        text=self._whisper_stt.transcribe(samples)
                    except ImportError as exc:
                        raise RuntimeError("Offline voice needs faster-whisper and numpy. Set JARVIS_STT_PROVIDER=whisper to enable it.") from exc
                else:
                    self.on_status("Recognizing speech with Google…")
                    text = recognizer.recognize_google(audio)
                if text:
                    self.on_result(text)
                    self.on_status("Voice command recognized")
                else:
                    self.on_status("No speech was recognized.")
            except Exception as exc:
                self.on_status(f"Voice input: {exc}")

        threading.Thread(target=work, daemon=True, name="JarvisVoiceInput").start()

    def speak(self, text):
        if not self.engine:
            return

        def work():
            try:
                self.engine.say(str(text)[:1500])
                self.engine.runAndWait()
            except Exception:
                pass

        threading.Thread(target=work, daemon=True, name="JarvisLocalTTS").start()
