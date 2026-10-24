"""Optional microphone input and spoken replies for JARVIS.

Google Speech Recognition remains the default STT provider. ElevenLabs Scribe
can be selected explicitly with JARVIS_STT_PROVIDER=elevenlabs; this uploads
the captured microphone audio to ElevenLabs, so enable it only when intended.
"""
import os
import tempfile
import threading
from pathlib import Path

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
            audio_path = None
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    self.on_status("Listening… speak now")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
                provider = os.getenv("JARVIS_STT_PROVIDER", "google").strip().casefold()
                self.on_status(f"Recognizing speech with {provider}…")
                if provider == "elevenlabs":
                    from elevenlabs_api import ElevenLabsAPIError, ElevenLabsClient

                    with tempfile.NamedTemporaryFile(prefix="jarvis_stt_", suffix=".wav", delete=False) as temp:
                        temp.write(audio.get_wav_data())
                        audio_path = Path(temp.name)
                    try:
                        transcript = ElevenLabsClient().transcribe(audio_path)
                    except ElevenLabsAPIError as exc:
                        self.on_status(f"ElevenLabs speech recognition: {exc}")
                        return
                    text = str(transcript.get("text", "")).strip()
                else:
                    text = recognizer.recognize_google(audio)
                if text:
                    self.on_result(text)
                    self.on_status("Voice command recognized")
                else:
                    self.on_status("No speech was recognized.")
            except Exception as exc:
                self.on_status(f"Voice input: {exc}")
            finally:
                if audio_path is not None:
                    try:
                        audio_path.unlink(missing_ok=True)
                    except OSError:
                        pass

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
