"""Optional microphone input and local spoken replies for JARVIS."""
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
                with sr.Microphone() as source:
                    self.on_status("Listening… speak now")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
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
