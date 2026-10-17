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
