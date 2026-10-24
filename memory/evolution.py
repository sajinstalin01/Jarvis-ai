"""Privacy-conscious automatic memory evolution for JARVIS.

Only high-confidence, explicit statements are learned. Data stays in the local
SQLite store. Secrets and sensitive personal topics are never auto-saved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = ROOT / "jarvis_data" / "memory_settings.json"

# Deliberately narrow: facts must be stated explicitly rather than inferred.
_PATTERNS = (
    ("preference", re.compile(r"^\s*i\s+(?:prefer|like|love|usually prefer)\s+(.+?)\s*$", re.I)),
    ("response_style", re.compile(r"^\s*(?:please\s+)?(?:keep|make)\s+(?:your|the)\s+(?:answers?|responses?)\s+(.+?)\s*$", re.I)),
    ("identity", re.compile(r"^\s*my name is\s+(.+?)\s*$", re.I)),
    ("identity", re.compile(r"^\s*call me\s+([A-Za-z][\w -]{1,60})\s*$", re.I)),
    ("project", re.compile(r"^\s*(?:i am working on|i'm working on|my current project is|my project is|i am building|i'm building)\s+(.+?)\s*$", re.I)),
    ("tooling", re.compile(r"^\s*i (?:use|work with|mostly use)\s+(.+?)\s*$", re.I)),
    ("role", re.compile(r"^\s*(?:i work as|my role is)\s+(.+?)\s*$", re.I)),
)
_SENSITIVE = re.compile(
    r"\b(password|passcode|api[\s_-]*key|secret|token|otp|one[- ]time code|"
    r"credit card|debit card|bank account|cvv|pin code|medical|diagnos(?:is|ed)|"
    r"prescription|religion|political party|political opinion|sexual orientation|"
    r"ethnic(?:ity)?|caste|ssn|social security)\b",
    re.I,
)
_CREDENTIAL_LIKE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b")


def is_enabled() -> bool:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return bool(data.get("auto_memory", True)) if isinstance(data, dict) else True
    except (OSError, ValueError, TypeError):
        return True


def set_enabled(enabled: bool) -> bool:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    try:
        loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data.update(loaded)
    except (OSError, ValueError, TypeError):
        pass
    data["auto_memory"] = bool(enabled)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(SETTINGS_FILE)
    return bool(enabled)


def extract_candidate(text: str) -> tuple[str, str] | None:
    value = str(text or "").strip()
    if not value or len(value) > 1000 or _SENSITIVE.search(value) or _CREDENTIAL_LIKE.search(value):
        return None
    # Don't duplicate explicit memory commands or store instructions, questions, or multi-line dumps.
    if "\n" in value or value.casefold().startswith(("remember ", "forget memory ", "memory auto ", "api ")):
        return None
    for category, pattern in _PATTERNS:
        match = pattern.match(value)
        if not match:
            continue
        fact = re.split(r"(?<=[.!?])\s+|[;\n]", match.group(1).strip(), maxsplit=1)[0].strip(" .!?")
        if len(fact) < 2 or len(fact) > 220 or _SENSITIVE.search(fact) or _CREDENTIAL_LIKE.search(fact):
            return None
        return category, fact
    return None


def learn_from_message(store, text: str) -> str | None:
    """Upsert one explicitly stated fact; return a user-safe status message."""
    if not is_enabled():
        return None
    candidate = extract_candidate(text)
    if not candidate:
        return None
    category, fact = candidate
    content = f"AUTO-MEMORY [{category}]: {fact}"
    entries = store.list_memories(limit=200)
    prefix = f"AUTO-MEMORY [{category}]:"
    matching = [row for row in entries if str(row.get("content", "")).startswith(prefix)]
    if matching and str(matching[0].get("content", "")).casefold() == content.casefold():
        return None  # avoid duplicate writes for a repeated fact
    # Evolve the current fact of this category instead of accumulating stale versions.
    for row in matching:
        store.forget_memory(int(row["id"]))
    store.remember(content)
    return f"Auto-memory updated ({category}). Manage it with 'memories' or disable with 'memory auto off'."


def status_text() -> str:
    return "Automatic memory is " + ("ON" if is_enabled() else "OFF") + ". Only explicit, non-sensitive preferences, identity labels, roles, projects, and tools are learned locally."
