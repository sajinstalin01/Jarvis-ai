"""Small local configuration store used by the uploaded Qt HUD.

Provider secrets remain in .env; this module stores UI preferences only.
"""
from __future__ import annotations
import json
from pathlib import Path
from threading import RLock

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
FILE = CONFIG_DIR / "ui_settings.json"
_LOCK = RLock()
DEFAULT_VOICE = "Kore"
AVAILABLE_VOICES = ["Kore", "Aoede", "Charon", "Fenrir", "Leda", "Orus", "Puck", "Zephyr"]
_DEFAULT = {
    "hud_style": "core", "brief_enabled": False, "voice": DEFAULT_VOICE,
    "input_device": "", "output_device": "", "wake_word_enabled": False,
    "push_to_talk_enabled": False, "plugins": {}, "plugin_config": {},
    "providers": {}, "pipeline": {"stt": "", "llm": "", "tts": ""},
    "provider_mode": "auto", "sidecar_first": False, "sidecar_provider": "",
}

def _read():
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        return {**_DEFAULT, **data}
    except Exception:
        return dict(_DEFAULT)

def save_all(data=None, **kwargs):
    with _LOCK:
        current = _read()
        if isinstance(data, dict): current.update(data)
        current.update(kwargs)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current

def get_state(): return _read()
def get_cfg(namespace=None):
    data = _read()
    if namespace is None: return data
    return data.get("plugin_config", {}).get(str(namespace), {})
def get_hud_style(): return _read().get("hud_style", "core")
def save_hud_style(value): save_all(hud_style="face" if value == "face" else "core")
def get_brief_enabled(): return bool(_read().get("brief_enabled", False))
def save_brief_enabled(value): save_all(brief_enabled=bool(value))
def get_voice(): return _read().get("voice", DEFAULT_VOICE)
def save_voice(value):
    if value in AVAILABLE_VOICES: save_all(voice=value)
def get_input_device(): return _read().get("input_device", "")
def get_output_device(): return _read().get("output_device", "")
def save_input_device(value): save_all(input_device=str(value or ""))
def save_output_device(value): save_all(output_device=str(value or ""))
def get_wake_word_enabled(): return bool(_read().get("wake_word_enabled", False))
def save_wake_word_enabled(value): save_all(wake_word_enabled=bool(value))
def get_push_to_talk_enabled(): return bool(_read().get("push_to_talk_enabled", False))
def save_push_to_talk_enabled(value): save_all(push_to_talk_enabled=bool(value))
def get_plugin_enabled(name): return bool(_read().get("plugins", {}).get(str(name), True))
def save_plugin_enabled(name, value):
    data = _read(); data.setdefault("plugins", {})[str(name)] = bool(value); save_all(data)
def save_plugin_config(namespace, values):
    data = _read(); data.setdefault("plugin_config", {})[str(namespace)] = dict(values); save_all(data)
def get_plugin_settings(): return []
def get_plugins(): return []
def get_pipeline(): return dict(_read().get("pipeline", {}))
def get_provider_config(provider_id): return dict(_read().get("providers", {}).get(str(provider_id), {}))
def get_provider_mode(): return _read().get("provider_mode", "auto")
def get_sidecar_first(): return bool(_read().get("sidecar_first", False))
def get_sidecar_provider(): return _read().get("sidecar_provider", "")
def save_providers(mode="auto", pipeline=None, sidecar_first=False, sidecar_provider="", providers=None, **kwargs):
    data = _read(); data.update(provider_mode=mode, pipeline=dict(pipeline or {}), sidecar_first=bool(sidecar_first), sidecar_provider=sidecar_provider, providers=dict(providers or {})); data.update(kwargs); save_all(data)
def save_provider_config(provider_id, values):
    data = _read(); data.setdefault("providers", {})[str(provider_id)] = dict(values); save_all(data)
def save_ns(namespace, values): save_plugin_config(namespace, values)
def get_desktop_dir(): return str(Path.home() / "Desktop")
def get_gpu(): return -1
def get_temp(): return -1
def get_declaration(provider_id): return None
