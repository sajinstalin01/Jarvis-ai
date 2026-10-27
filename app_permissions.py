"""Permission-gated, foreground-only app interaction helpers for JARVIS.

Windows does not have a universal "grant every permission" switch for desktop
apps. This module stores JARVIS-level opt-ins only; each typing, message-draft,
or call-preparation action is still confirmed in the GUI.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import struct
from ctypes import wintypes
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_PERMISSION_FILE = ROOT / "config" / "app_permissions.json"

PERMISSION_INFO = {
    "app_list": {
        "label": "Read installed app names",
        "description": "List/search registered Windows app display names only; not private app content.",
        "default": True,
    },
    "app_launch": {
        "label": "Launch installed apps",
        "description": "Open apps by name using JARVIS's safe launcher.",
        "default": True,
    },
    "type_text": {
        "label": "Type literal text in the foreground app",
        "description": "After a separate confirmation and 5-second switch window, type plain text only; never presses Enter or clicks.",
        "default": False,
    },
    "draft_message": {
        "label": "Prepare WhatsApp/Telegram message drafts",
        "description": "Open a share/draft link; you choose the recipient and press Send yourself.",
        "default": False,
    },
    "prepare_call": {
        "label": "Open calling app",
        "description": "Open WhatsApp or Telegram after confirmation; you choose the contact and start the call yourself.",
        "default": False,
    },
    "desktop_input": {
        "label": "Mouse and keyboard automation",
        "description": "Allow explicitly confirmed foreground mouse/keyboard actions with a restricted hotkey allow-list.",
        "default": True,
    },
    "window_control": {
        "label": "Manage application windows",
        "description": "Allow confirmed focus, minimize, maximize, restore and close requests.",
        "default": True,
    },
    "system_settings": {
        "label": "Open system settings and adjust volume",
        "description": "Allow confirmed Windows Settings navigation and media volume keys.",
        "default": True,
    },
    "system_power": {
        "label": "Power and session actions",
        "description": "Allow confirmed Windows shutdown, restart, sleep and logout requests.",
        "default": True,
    },
}

PERMISSION_ALIASES = {
    "read": "app_list",
    "read apps": "app_list",
    "read_apps": "app_list",
    "apps": "app_list",
    "search apps": "app_list",
    "launch": "app_launch",
    "open apps": "app_launch",
    "type": "type_text",
    "typing": "type_text",
    "write": "type_text",
    "write text": "type_text",
    "message": "draft_message",
    "messages": "draft_message",
    "send message": "draft_message",
    "send_message": "draft_message",
    "draft messages": "draft_message",
    "call": "prepare_call",
    "calls": "prepare_call",
    "make call": "prepare_call",
    "mouse": "desktop_input", "keyboard": "desktop_input",
    "mouse keyboard": "desktop_input", "desktop input": "desktop_input",
    "window": "window_control", "windows": "window_control", "window control": "window_control",
    "system settings": "system_settings", "volume": "system_settings",
    "power": "system_power", "system power": "system_power",
}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().replace("-", " ").split())


def resolve_permission(value: str) -> str | None:
    """Resolve a user-facing capability name; returns None for unknown names."""
    raw = _normalize(value)
    key = PERMISSION_ALIASES.get(raw, raw.replace(" ", "_"))
    return key if key in PERMISSION_INFO else None


class PermissionStore:
    """Local capability store; PC-control defaults are enabled with per-action confirmation."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path is not None else DEFAULT_PERMISSION_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._permissions = {key: bool(info["default"]) for key, info in PERMISSION_INFO.items()}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            saved = data.get("permissions", {}) if isinstance(data, dict) else {}
            try:
                version = int(data.get("version", 1)) if isinstance(data, dict) else 1
            except (TypeError, ValueError):
                version = 1
            if isinstance(saved, dict):
                for key in PERMISSION_INFO:
                    if isinstance(saved.get(key), bool):
                        self._permissions[key] = saved[key]
            if version < 2:
                for key in ("desktop_input", "window_control", "system_settings", "system_power"):
                    self._permissions[key] = True
                self._save()
        except (OSError, ValueError, TypeError):
            # If settings are missing/corrupt, use safe defaults.
            return

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"version": 2, "permissions": self._permissions}, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def has(self, permission: str) -> bool:
        key = resolve_permission(permission)
        return bool(key and self._permissions.get(key, False))

    def set(self, permission: str, enabled: bool) -> bool:
        key = resolve_permission(permission)
        if not key:
            return False
        self._permissions[key] = bool(enabled)
        self._save()
        return True

    def set_all(self, enabled: bool) -> None:
        for key in PERMISSION_INFO:
            self._permissions[key] = bool(enabled)
        self._save()

    def summary(self) -> str:
        rows = []
        for key, info in PERMISSION_INFO.items():
            state = "ON" if self._permissions[key] else "OFF"
            rows.append(f"{state:3} · {key} — {info['label']}\n      {info['description']}")
        rows.append(
            "\nDesktop input, window control, system settings and system power are enabled by default. "
            "Each action still asks for confirmation; this is not a Windows administrator/UAC grant. "
            "Typing, message drafts and calls remain opt-in. Private app contents, arbitrary file access, "
            "unattended calls and automatic message sending are not enabled."
        )
        return "\n".join(rows)


def filter_installed_apps(records: Iterable[tuple[str, str]], query: str = "", limit: int = 30) -> list[str]:
    """Return sorted display names only; never expose AppIDs in chat output."""
    needle = _normalize(query).replace(" ", "")
    names = []
    seen = set()
    for row in records or ():
        if not isinstance(row, (tuple, list)) or len(row) < 1:
            continue
        name = str(row[0] or "").strip()
        normalized = "".join(ch for ch in name.casefold() if ch.isalnum())
        if not name or normalized in seen:
            continue
        if needle and needle not in normalized:
            continue
        seen.add(normalized)
        names.append(name)
    return sorted(names, key=str.casefold)[:max(1, int(limit))]


def validate_typing_text(value: str) -> tuple[bool, str]:
    text = str(value or "")
    if not text.strip():
        return False, "Type command is empty."
    if len(text) > 1000:
        return False, "For safety, one type command is limited to 1,000 characters."
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        return False, "Only one line of plain text is supported; control characters are blocked."
    return True, text


def type_text_into_foreground_window(value: str) -> tuple[bool, str]:
    """Type literal Unicode text into the current Windows foreground window.

    This does not send Enter, click controls, read the window, or run commands.
    The caller is responsible for the GUI confirmation and countdown.
    """
    if platform.system() != "Windows":
        return False, "Foreground typing is supported only on Windows."
    valid, message = validate_typing_text(value)
    if not valid:
        return False, message

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)),
        ]

    ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG), ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False, "No foreground window was detected; nothing was typed."
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return False, "The active window has no readable title; typing was cancelled for safety."
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value.strip()
        normalized_title = "".join(ch for ch in title.casefold() if ch.isalnum())
        if not title or normalized_title.startswith("jarvismarklvi") or normalized_title in {"jarvis", "jarvisassistant"}:
            return False, "JARVIS is still active or the target window could not be verified; nothing was typed."

        payload = value.encode("utf-16-le")
        units = struct.unpack("<" + "H" * (len(payload) // 2), payload)
        inputs = (INPUT * (len(units) * 2))()
        index = 0
        for unit in units:
            inputs[index].type = 1  # INPUT_KEYBOARD
            inputs[index].ki = KEYBDINPUT(0, unit, 0x0004, 0, 0)  # KEYEVENTF_UNICODE
            index += 1
            inputs[index].type = 1
            inputs[index].ki = KEYBDINPUT(0, unit, 0x0004 | 0x0002, 0, 0)  # key up
            index += 1

        user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        user32.SendInput.restype = wintypes.UINT
        sent = user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            return False, f"Windows accepted {sent} of {len(inputs)} keyboard events. Some or all text may be missing."
        return True, f"Typed {len(value)} characters into the foreground window '{title}'. No Enter key was pressed."
    except (AttributeError, OSError, ValueError, ctypes.ArgumentError) as exc:
        return False, f"Could not type text: {exc}"
