"""Optional audio-device helpers for the Qt settings panel."""
DEFAULT_LABEL = "System default"
def list_devices(kind="input"):
    try:
        import sounddevice as sd
        rows = sd.query_devices()
        key = "max_input_channels" if kind == "input" else "max_output_channels"
        return [str(row.get("name", "")) for row in rows if int(row.get(key, 0)) > 0]
    except Exception:
        return []
def get_output_volume(device=""): return None
def set_output_volume(value, device=""): return False
def measure_input(device="", on_level=None):
    try:
        import sounddevice as sd
        import numpy as np
        chosen = device or None
        chunks = []
        def callback(indata, frames, timing, status):
            if status: pass
            level = float(np.sqrt(np.mean(indata.astype("float64") ** 2)))
            chunks.append(level)
            if on_level: on_level(min(1.0, level * 4.0))
        with sd.InputStream(device=chosen, channels=1, samplerate=16000, callback=callback):
            import time; time.sleep(3)
        peak = max(chunks, default=0.0)
        return {"ok": peak > 0.002, "peak": round(peak, 4), "verdict": "input detected" if peak > 0.002 else "no clear input detected"}
    except Exception as exc:
        return {"ok": False, "peak": 0, "verdict": str(exc)}
def play_tone(device=""):
    try:
        import sounddevice as sd
        import numpy as np
        rate = 22050
        t = np.arange(int(rate * 0.35)) / rate
        tone = 0.15 * np.sin(2 * np.pi * 660 * t)
        sd.play(tone, rate, device=device or None, blocking=True)
        return {"ok": True, "verdict": "tone played"}
    except Exception as exc:
        return {"ok": False, "verdict": str(exc)}
