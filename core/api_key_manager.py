"""Local multi-key registry and live health checks for JARVIS API integrations.

Supported services are the providers used by this repository: Groq, Gemini, and
ElevenLabs. Any number of keys may be configured per service. Secret values are
never returned by status functions; only a masked suffix is shown.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
API_FILE = ROOT / "config" / "api_keys.json"

PROVIDERS = {
    "groq": {"title": "Groq", "env": "GROQ_API_KEY", "legacy": ("groq_api_key", "groq")},
    "gemini": {"title": "Gemini", "env": "GEMINI_API_KEY", "legacy": ("gemini_api_key", "gemini")},
    "elevenlabs": {
        "title": "ElevenLabs", "env": "ELEVENLABS_API_KEY",
        "legacy": ("elevenlabs_api_key", "elevenlabs"),
    },
}
ALIASES = {
    "google": "gemini", "google gemini": "gemini", "genai": "gemini",
    "eleven labs": "elevenlabs", "eleven_labs": "elevenlabs",
}


def _provider_name(provider: str) -> str:
    value = str(provider or "").strip().casefold().replace("-", "_")
    value = ALIASES.get(value, value).replace(" ", "")
    if value not in PROVIDERS:
        raise ValueError(f"Unsupported API provider: {provider}")
    return value


def _read_config() -> dict[str, Any]:
    try:
        value = json.loads(API_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _values(value: Any) -> list[str]:
    """Normalize a single key, a list, or a small {keys: [...]} config shape."""
    if isinstance(value, dict):
        value = value.get("keys", value.get("api_keys", value.get("key", [])))
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    value = parsed
            except ValueError:
                pass
        if isinstance(value, str):
            value = re.split(r"[;\r\n]+", value)
    if not isinstance(value, (list, tuple, set)):
        return []
    result = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def get_api_keys(provider: str, *, config: dict[str, Any] | None = None,
                 env: dict[str, str] | None = None) -> list[str]:
    """Return unique keys in priority order, without imposing a pool-size limit.

    Supported formats:
      - GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, ...
      - GROQ_API_KEYS='["key1", "key2"]' (JSON array)
      - config/api_keys.json: {"api_keys": {"groq": ["key1", "key2"]}}
      - legacy provider-specific fields such as "gemini_api_key".
    """
    name = _provider_name(provider)
    definition = PROVIDERS[name]
    environment = os.environ if env is None else env
    settings = _read_config() if config is None else config
    base = definition["env"]
    candidates: list[str] = []

    # Preserve the primary environment key first, then numbered variables.
    if environment.get(base):
        candidates.append(str(environment[base]).strip())
    numbered = []
    for env_name, value in environment.items():
        match = re.fullmatch(re.escape(base) + r"_(\d+)", str(env_name), re.I)
        if match and str(value).strip():
            numbered.append((int(match.group(1)), str(value).strip()))
    candidates.extend(value for _, value in sorted(numbered))
    candidates.extend(_values(environment.get(base + "S", "")))

    all_keys = settings.get("api_keys", {})
    if isinstance(all_keys, dict):
        for key_name in (name, base, base.casefold(), base.lower() + "s"):
            if key_name in all_keys:
                candidates.extend(_values(all_keys[key_name]))
    for legacy in definition["legacy"]:
        if legacy in settings:
            candidates.extend(_values(settings[legacy]))

    unique: list[str] = []
    seen: set[str] = set()
    for key in candidates:
        key = key.strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def mask_api_key(key: str) -> str:
    value = str(key or "")
    if not value:
        return "(empty)"
    return "••••" + value[-4:] if len(value) >= 4 else "••••"


def _error_status(exc: Exception) -> tuple[str, str]:
    """Classify provider errors without printing request headers or API keys."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    status = status or getattr(response, "status_code", None)
    message = str(exc).casefold()
    match = re.search(r"\b(401|403|404|408|429|500|502|503|504)\b", message)
    if not status and match:
        status = int(match.group(1))
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None

    if status == 401 or "invalid api key" in message or "unauthorized" in message:
        return "INVALID", "Provider rejected the key (authentication failed)."
    if status == 403 or "permission denied" in message or "forbidden" in message:
        return "FAILED", "Provider denied access; verify key permissions and account access."
    if status == 429 or "rate limit" in message or "quota" in message:
        return "RATE LIMITED", "Provider is reachable, but rate limit or quota was reported."
    if any(term in message for term in ("timeout", "timed out", "connection error", "connection refused",
                                        "name or service not known", "network is unreachable", "urlerror")):
        return "CONNECTION FAILED", "Could not reach the provider; check internet access and retry."
    # Don't echo provider exception bodies because some SDKs include request details.
    if status is not None:
        return "FAILED", f"Provider request failed (HTTP {status})."
    return "FAILED", f"Provider check failed ({type(exc).__name__})."


def probe_api_key(provider: str, key: str, *, timeout: float = 12.0,
                  clients: dict[str, Callable[[str], Any]] | None = None) -> dict[str, str]:
    """Test one credential with a lightweight authenticated API request."""
    name = _provider_name(provider)
    title = PROVIDERS[name]["title"]
    if not str(key or "").strip():
        return {"provider": title, "key": mask_api_key(key), "status": "NOT CONFIGURED",
                "detail": "No key was provided."}
    try:
        if clients and name in clients:
            clients[name](key)
        elif name == "groq":
            from groq import Groq
            client = Groq(api_key=key, timeout=timeout)
            try:
                client.models.list()
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        elif name == "gemini":
            from google import genai
            client = genai.Client(api_key=key)
            try:
                iterator = iter(client.models.list())
                next(iterator, None)
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        elif name == "elevenlabs":
            from elevenlabs_api import ElevenLabsClient
            ElevenLabsClient(api_key=key, timeout=timeout).get_user()
        return {"provider": title, "key": mask_api_key(key), "status": "VALID",
                "detail": "Authenticated API request succeeded."}
    except Exception as exc:  # SDK/network error types differ by provider version.
        status, detail = _error_status(exc)
        return {"provider": title, "key": mask_api_key(key), "status": status, "detail": detail}


def check_all_api_keys(*, providers: list[str] | None = None,
                       config: dict[str, Any] | None = None,
                       env: dict[str, str] | None = None,
                       clients: dict[str, Callable[[str], Any]] | None = None) -> list[dict[str, str]]:
    """Probe every configured key for each provider, plus unconfigured provider rows."""
    names = [_provider_name(p) for p in providers] if providers else list(PROVIDERS)
    results: list[dict[str, str]] = []
    for name in names:
        keys = get_api_keys(name, config=config, env=env)
        if not keys:
            results.append({
                "provider": PROVIDERS[name]["title"], "key": "(none)",
                "status": "NOT CONFIGURED", "detail": "Add a key in the local .env or config/api_keys.json.",
            })
            continue
        for index, key in enumerate(keys, 1):
            row = probe_api_key(name, key, clients=clients)
            row["slot"] = str(index)
            results.append(row)
    return results


def format_api_status(rows: list[dict[str, str]]) -> str:
    lines = ["API KEY HEALTH (key values are masked):"]
    for row in rows:
        slot = f" #{row['slot']}" if row.get("slot") else ""
        lines.append(
            f"{row.get('provider', 'API')}{slot} [{row.get('key', '(hidden)')}] — "
            f"{row.get('status', 'UNKNOWN')}: {row.get('detail', '')}"
        )
    return "\n".join(lines)
