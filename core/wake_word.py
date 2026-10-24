"""Compatibility facade for the optional local wake-word engine.

The active HUD imports this stable module path. The implementation lives in
mark_lvi_wake_word.py so importing the HUD does not load the optional ONNX
runtime at startup.
"""
from __future__ import annotations

from typing import Callable


def _backend():
    # Keep the substantial optional wake-word implementation lazy.
    from core import mark_lvi_wake_word
    return mark_lvi_wake_word


def is_ready() -> bool:
    """Return whether the optional local wake-word package and models are ready."""
    try:
        return bool(_backend().is_ready())
    except Exception:
        return False


def install_and_download(
    progress: Callable[[str], None] | None = None,
    *,
    logger: Callable[[str], None] | None = None,
    notify: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Install the optional engine and models through the existing UI callback.

    logger is used by the active HUD. progress remains accepted for
    compatibility with older callers that passed a callback positionally.
    """
    log = logger if callable(logger) else progress if callable(progress) else print
    try:
        return _backend().install_and_download(logger=log, notify=notify)
    except Exception as exc:
        message = f"Wake-word setup error: {type(exc).__name__}: {exc}"
        try:
            log(message)
        except Exception:
            pass
        return False, message
