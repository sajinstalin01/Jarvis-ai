"""Central JARVIS settings and feature hub.

All widget creation and callbacks happen on the Qt GUI thread. Commands are
sent through the host's queued Qt signal instead of touching widgets from
background workers.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


class SettingsHubOverlay(QWidget):
    """Scrollable, categorized settings hub for the existing JARVIS features."""

    def __init__(self, parent, callbacks=None, command_callback=None):
        super().__init__(parent)
        self._callbacks = callbacks or {}
        self._command_callback = command_callback
        self.setObjectName("JarvisSettingsHub")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#JarvisSettingsHub { background: #080e16; border: 1px solid #3d718b; border-radius: 9px; }
            QLabel { color: #c7e3eb; background: transparent; }
            QLabel#HubTitle { color: #78d5ed; font-size: 16px; font-weight: 700; }
            QLabel#HubSection { color: #78d5ed; font-size: 10px; font-weight: 700; padding: 5px 2px 2px; border-bottom: 1px solid #263b4e; }
            QLabel#HubHint { color: #93b2bd; font-size: 10px; }
            QPushButton { color: #c7e3eb; background: #0d1722; border: 1px solid #263b4e; border-radius: 5px; padding: 7px 9px; text-align: left; }
            QPushButton:hover { color: #e8f1f5; background: #102b39; border-color: #78d5ed; }
            QPushButton#HubClose { text-align: center; padding: 4px 10px; }
            QScrollArea { border: none; background: transparent; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("⚙  J.A.R.V.I.S. SETTINGS HUB")
        title.setObjectName("HubTitle")
        head.addWidget(title)
        head.addStretch()
        close = QPushButton("✕")
        close.setObjectName("HubClose")
        close.setFixedWidth(34)
        close.clicked.connect(self.close)
        head.addWidget(close)
        outer.addLayout(head)

        hint = QLabel(
            "One place for assistant setup, PC operation, memory, automation, "
            "integrations, privacy and diagnostics."
        )
        hint.setObjectName("HubHint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        safety = QLabel(
            "PC-control permissions are enabled by default. Individual mouse, keyboard, "
            "window and power actions still show confirmation; Windows/UAC permissions "
            "cannot be granted by an application."
        )
        safety.setWordWrap(True)
        safety.setStyleSheet("color: #e9cc83; background: #111e2c; border: 1px solid #304b60; border-radius: 5px; padding: 8px;")
        outer.addWidget(safety)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(7)
        scroll.setWidget(body)

        self._add_section(layout, "01  ASSISTANT & APPEARANCE", [
            ("Customise assistant", "customise"),
            ("Engine & AI providers", "providers"),
            ("Audio devices", "audio"),
            ("Font collection", "fonts"),
        ])
        self._add_section(layout, "02  PC CONTROL & HARDWARE", [
            ("PC control command guide", "cmd:pc control help"),
            ("Live PC metrics · CPU / RAM / disk / network / GPU", "cmd:pc metrics"),
            ("Open windows", "cmd:pc windows"),
            ("Multi-monitor layout", "cmd:pc monitors"),
            ("Windows settings shortcuts", "cmd:pc settings display"),
            ("Permission status", "cmd:permissions"),
        ])
        self._add_section(layout, "03  MEMORY, CONTEXT & KNOWLEDGE", [
            ("Memory manager", "memory"),
            ("Knowledge graph", "cmd:graph"),
            ("Local file search & indexing help", "cmd:features"),
            ("Active project list", "cmd:projects"),
        ])
        self._add_section(layout, "04  AUTOMATION & TASKS", [
            ("Task list", "cmd:tasks list"),
            ("Saved workflows", "cmd:workflows"),
            ("Proactive assistant status", "cmd:proactive status"),
            ("Wake-word and voice commands help", "cmd:help"),
        ])
        self._add_section(layout, "05  PLUGINS, MODELS & INTEGRATIONS", [
            ("Plugin manager", "plugins"),
            ("Plugin settings", "plugin_settings"),
            ("Local AI models / Ollama status", "cmd:models status"),
            ("Remote-control setup", "remote"),
        ])
        self._add_section(layout, "06  PRIVACY, BACKUP & DIAGNOSTICS", [
            ("Security audit", "cmd:security audit"),
            ("Backup status", "cmd:backup status"),
            ("Create safe source backup", "cmd:backup create"),
            ("Network diagnostics", "cmd:network diagnose"),
            ("Performance report", "cmd:profile report"),
        ])
        layout.addStretch(1)

    def _add_section(self, parent_layout, heading, actions):
        label = QLabel(heading)
        label.setObjectName("HubSection")
        parent_layout.addWidget(label)
        for text, action in actions:
            button = QPushButton("›  " + text)
            button.setMinimumHeight(32)
            button.setToolTip(text)
            button.clicked.connect(lambda checked=False, key=action: self._run(key))
            parent_layout.addWidget(button)

    def _run(self, action):
        # Close this overlay first so the next overlay can own the foreground.
        self.hide()
        if action.startswith("cmd:"):
            if self._command_callback:
                self._command_callback(action[4:])
            return
        callback = self._callbacks.get(action)
        if callback:
            callback()
        else:
            self.show()
