"""Realistic, restrained desktop skin for the J.A.R.V.I.S. PyQt HUD.

This module only changes presentation. It does not replace widgets or touch
assistant state, saved configuration, API keys, chat history, or user data.
"""
from __future__ import annotations

from typing import Any


REALISTIC_PALETTE = {
    "BG": "#080e16",
    "PANEL": "#0d1722",
    "PANEL2": "#111e2c",
    "BORDER": "#263b4e",
    "BORDER_B": "#3d718b",
    "BORDER_A": "#304b60",
    "PRI": "#78d5ed",
    "PRI_DIM": "#347d96",
    "PRI_GHO": "#102b39",
    "ACC": "#e9a36c",
    "ACC2": "#e9cc83",
    "GREEN": "#75d6a6",
    "GREEN_D": "#3d9a73",
    "RED": "#e87886",
    "MUTED_C": "#ba7b8c",
    "TEXT": "#c7e3eb",
    "TEXT_DIM": "#718d9a",
    "TEXT_MED": "#93b2bd",
    "WHITE": "#e8f1f5",
    "DARK": "#0b1520",
    "BAR_BG": "#1a2b39",
}


def apply_realistic_theme(ui_module: Any, app: Any, font_family: str = "Segoe UI") -> None:
    """Apply a muted titanium/blue palette before UI widgets are constructed."""
    palette_class = getattr(ui_module, "C", None)
    if palette_class is not None:
        for name, value in REALISTIC_PALETTE.items():
            setattr(palette_class, name, value)
        linked = getattr(ui_module, "_HUE_LINKED", ())
        defaults = getattr(ui_module, "_PALETTE_DEFAULTS", None)
        if isinstance(defaults, dict):
            for name in linked:
                if name in REALISTIC_PALETTE:
                    defaults[name] = REALISTIC_PALETTE[name]
        if hasattr(ui_module, "DEFAULT_UI_COLOR"):
            ui_module.DEFAULT_UI_COLOR = REALISTIC_PALETTE["PRI"]

    try:
        from PyQt6.QtGui import QFont
        app.setApplicationName("J.A.R.V.I.S.")
        app.setStyle("Fusion")
        app.setFont(QFont(font_family or "Segoe UI", 9))
        app.setStyleSheet("""
            QToolTip {
                color: #e8f1f5;
                background: #152433;
                border: 1px solid #3d718b;
                padding: 5px 8px;
            }
            QMenu {
                color: #c7e3eb;
                background: #0d1722;
                border: 1px solid #304b60;
                padding: 5px;
            }
            QMenu::item { padding: 7px 24px; border-radius: 4px; }
            QMenu::item:selected { color: #e8f1f5; background: #1a3547; }
            QComboBox QAbstractItemView {
                color: #c7e3eb;
                background: #0d1722;
                selection-color: #e8f1f5;
                selection-background-color: #1a3547;
                border: 1px solid #304b60;
                outline: 0;
            }
            QScrollBar:vertical {
                background: #0a131d; width: 9px; margin: 2px;
                border: none; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #304b60; min-height: 28px; border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #3d718b; }
            QScrollBar:horizontal {
                background: #0a131d; height: 9px; margin: 2px;
                border: none; border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #304b60; min-width: 28px; border-radius: 4px;
            }
            QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
            QProgressBar {
                color: #c7e3eb; background: #1a2b39;
                border: 1px solid #304b60; border-radius: 4px;
                text-align: center; min-height: 8px;
            }
            QProgressBar::chunk { background: #78d5ed; border-radius: 3px; }
        """)
    except Exception:
        # Presentation is deliberately non-fatal: JARVIS must still launch if
        # a future Qt version changes a styling API.
        pass


def polish_window(window: Any, font_family: str = "Segoe UI") -> None:
    """Apply the selected family to normal controls; keep technical panels monospaced."""
    try:
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QWidget

        family = str(font_family or "Segoe UI").strip() or "Segoe UI"
        for widget in window.findChildren(QWidget):
            try:
                name = type(widget).__name__
                if name in {"HudCanvas", "MetricBar", "LogWidget"} or isinstance(widget, QTextEdit):
                    continue
                current = widget.font()
                point_size = current.pointSizeF()
                size = max(8, min(32, int(round(point_size if point_size > 0 else 9))))
                replacement = QFont(family, size)
                replacement.setWeight(current.weight())
                replacement.setItalic(current.italic())
                replacement.setUnderline(current.underline())
                widget.setFont(replacement)
                if isinstance(widget, QLineEdit):
                    widget.setMinimumHeight(max(widget.minimumHeight(), 30))
            except Exception:
                continue
    except Exception:
        # Font customization is optional and must never prevent JARVIS startup.
        pass
