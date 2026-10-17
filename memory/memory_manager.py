"""Simple persistent key/value memory used by the uploaded HUD's memory panel."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from threading import RLock
ROOT = Path(__file__).resolve().parents[1]
FILE = Path(__file__).resolve().parent / "long_term.json"
_LOCK = RLock()
def _read():
    try:
        value = json.loads(FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception: return []
def _write(rows):
    FILE.parent.mkdir(parents=True, exist_ok=True); FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
def all_entries_for_ui():
    with _LOCK: return list(reversed(_read()))
def remember(key, value, category="general"):
    with _LOCK:
        rows=_read(); now=datetime.now().astimezone().isoformat(timespec="seconds")
        rows=[r for r in rows if not (r.get("key")==key and r.get("category")==category)]
        rows.append({"key":str(key)[:200],"value":str(value)[:4000],"category":str(category)[:40],"updated":now})
        _write(rows)
def forget(key, category="general"):
    with _LOCK:
        rows=_read(); kept=[r for r in rows if not (r.get("key")==key and r.get("category")==category)]; _write(kept); return len(kept)!=len(rows)
