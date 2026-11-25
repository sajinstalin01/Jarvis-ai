"""On-demand foreground-window context for JARVIS.

Only the active window title and owning process name are read. No screenshots,
keystrokes, clipboard contents, or background activity are collected.
"""
from __future__ import annotations

import os
import platform


def get_foreground_context() -> dict:
    """Return the current foreground window title/process where supported."""
    title = ""
    process = ""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return {"available": False, "title": "", "process": "", "reason": "No foreground window."}
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(max(1, length + 1))
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, len(buf))
            title = buf.value.strip()
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    import psutil
                    process = psutil.Process(pid.value).name()
                except Exception:
                    process = ""
        else:
            try:
                import pygetwindow
                active = pygetwindow.getActiveWindow()
                title = str(getattr(active, "title", "") or "").strip() if active else ""
            except Exception:
                pass
        return {"available": bool(title), "title": title[:500], "process": process[:160], "reason": ""}
    except Exception as exc:
        return {"available": False, "title": "", "process": "", "reason": f"{type(exc).__name__}: {exc}"}


def format_foreground_context() -> str:
    data = get_foreground_context()
    if not data["available"]:
        return "Foreground window information is unavailable." + (f" {data['reason']}" if data["reason"] else "")
    suffix = f" ({data['process']})" if data["process"] else ""
    return f"Active window: {data['title']}{suffix}"
