"""Small, explicit local PC-control actions for JARVIS; no arbitrary shell execution."""
from __future__ import annotations
import datetime
import os
import platform
from pathlib import Path


def lock_screen() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "Lock screen control is currently supported on Windows only."
    try:
        import ctypes
        if ctypes.windll.user32.LockWorkStation():
            return True, "Locking this Windows session."
        return False, "Windows could not lock the session."
    except Exception as exc:
        return False, f"Could not lock the session: {exc}"


def toggle_mute() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "System mute shortcut is currently supported on Windows only."
    try:
        import ctypes
        VK_VOLUME_MUTE = 0xAD
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)
        return True, "Toggled system mute."
    except Exception as exc:
        return False, f"Could not toggle system mute: {exc}"


def take_screenshot() -> tuple[bool, str]:
    try:
        from PIL import ImageGrab
        root = Path(__file__).resolve().parent / "jarvis_data" / "screenshots"
        root.mkdir(parents=True, exist_ok=True)
        filename = "jarvis_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        target = root / filename
        ImageGrab.grab().save(target)
        return True, f"Screenshot saved locally: {target}"
    except ImportError:
        return False, "Screenshot needs Pillow. Install it with: python -m pip install Pillow"
    except Exception as exc:
        return False, f"Screenshot failed: {exc}"
