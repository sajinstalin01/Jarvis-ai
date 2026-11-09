"""Safe Home Assistant device bridge, including Alexa-exposed entities.

JARVIS talks to Home Assistant's REST API. Alexa device control is provided by
Home Assistant's supported Alexa Smart Home integration (Cloud or manual skill).
No Alexa account credentials or long-lived tokens are stored in this module.
"""
from __future__ import annotations
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ALLOWED_SERVICES = {
    "light": {"turn_on", "turn_off", "toggle"},
    "switch": {"turn_on", "turn_off", "toggle"},
    "fan": {"turn_on", "turn_off", "toggle", "set_percentage"},
    "climate": {"set_temperature", "set_hvac_mode"},
    "cover": {"open_cover", "close_cover", "stop_cover"},
    "media_player": {"media_play", "media_pause", "media_stop", "volume_up", "volume_down", "volume_set", "turn_on", "turn_off"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
}
_ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$", re.I)

class DeviceIntegrationHub:
    def __init__(self, root, confirm=None, opener=None):
        self.root = Path(root)
        self.config_path = self.root / "config" / "device_integrations.json"
        self.confirm = confirm or (lambda *_: False)
        self.opener = opener or urllib.request.urlopen

    def _config(self):
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _connection(self):
        cfg = self._config()
        base = str(os.getenv("HOME_ASSISTANT_URL") or cfg.get("home_assistant_url") or "").strip().rstrip("/")
        token = str(os.getenv("HOME_ASSISTANT_TOKEN") or "").strip()
        if not base or not token:
            raise RuntimeError("Home Assistant is not configured. Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN environment variables; never paste the token into chat.")
        parsed = urllib.parse.urlparse(base)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError("Use HTTPS for a non-local Home Assistant server.")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("Invalid Home Assistant URL.")
        return base, token

    def _request(self, method, path, payload=None):
        base, token = self._connection()
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(base + path, data=data, method=method, headers={
            "Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json"
        })
        try:
            with self.opener(req, timeout=8) as response:
                raw = response.read(2_000_000)
            return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", "replace")
            raise RuntimeError(f"Home Assistant HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise RuntimeError(f"Home Assistant request failed: {exc}") from exc

    def status(self):
        try:
            data = self._request("GET", "/api/")
            return "Home Assistant connected: " + str(data.get("message", "API reachable"))
        except Exception as exc:
            return "Home Assistant unavailable: " + str(exc)

    def entities(self, query=""):
        try:
            rows = self._request("GET", "/api/states")
            needle = str(query or "").casefold()
            found = []
            for item in rows if isinstance(rows, list) else []:
                entity = str(item.get("entity_id", ""))
                attrs = item.get("attributes") or {}
                name = str(attrs.get("friendly_name") or entity)
                if not needle or needle in (entity + " " + name).casefold():
                    found.append(f"{entity} · {name} · {item.get('state','unknown')}")
            return "\n".join(found[:80]) or "No matching Home Assistant entities."
        except Exception as exc:
            return "Device discovery failed: " + str(exc)

    def alexa_status(self):
        return ("Alexa integration uses Home Assistant's Alexa Smart Home integration. "
                "Expose selected Home Assistant entities to Alexa, then discover devices in the Alexa app. "
                "Configure HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN for JARVIS device control. "
                "JARVIS does not collect Amazon passwords or Alexa account tokens.")

    def control(self, entity_id, service, data=None):
        entity = str(entity_id or "").strip().casefold()
        service = str(service or "").strip().casefold()
        if not _ENTITY.fullmatch(entity):
            return "Invalid entity ID. Use a Home Assistant entity such as light.desk."
        domain = entity.split(".", 1)[0]
        if service not in _ALLOWED_SERVICES.get(domain, set()):
            return "Blocked service. Only allow-listed Home Assistant services for supported device domains are accepted."
        payload = dict(data or {})
        if len(json.dumps(payload)) > 2000 or any(k in payload for k in ("entity_id", "service", "domain")):
            return "Invalid service data."
        if not self.confirm("Confirm smart-device action", f"Run {domain}.{service} for {entity}?"):
            return "Device action cancelled; nothing was changed."
        try:
            result = self._request("POST", f"/api/services/{domain}/{service}", {"entity_id": entity, **payload})
            return f"Home Assistant accepted {domain}.{service} for {entity}. Response: {str(result)[:500]}"
        except Exception as exc:
            return "Device action failed: " + str(exc)

    def dispatch(self, command):
        raw = str(command or "").strip()
        p = raw.casefold()
        if p in {"alexa", "alexa help", "alexa status", "alexa setup"}:
            return self.alexa_status()
        if p in {"devices", "devices status", "smart home status"}:
            return self.status()
        if p in {"devices list", "list devices", "show connected devices"}:
            return self.entities()
        m = re.fullmatch(r"(?:devices|device) (?:find|search) (.+)", raw, re.I)
        if m:
            return self.entities(m.group(1))
        m = re.fullmatch(r"(?:turn on|switch on) ([a-z_]+\.[a-z0-9_]+)", raw, re.I)
        if m:
            return self.control(m.group(1), "turn_on")
        m = re.fullmatch(r"(?:turn off|switch off) ([a-z_]+\.[a-z0-9_]+)", raw, re.I)
        if m:
            return self.control(m.group(1), "turn_off")
        return None
