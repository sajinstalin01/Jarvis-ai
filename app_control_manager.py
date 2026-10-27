"""Permission-gated Windows app discovery and user-confirmed interactions for JARVIS."""
from __future__ import annotations

import platform
import re
import urllib.parse
import webbrowser

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from app_permissions import (
    PERMISSION_INFO,
    PermissionStore,
    filter_installed_apps,
    resolve_permission,
    type_text_into_foreground_window,
    validate_typing_text,
)

try:
    from jarvis_legacy import _start_apps_index, launch_app
except Exception:
    _start_apps_index = lambda: []
    launch_app = None


class AppControlManager:
    """Implements JARVIS-level app permissions with explicit action confirmations.

    It does not override Windows privacy controls, inspect private app contents,
    click Send, press Enter, select a recipient, or place calls automatically.
    """

    def __init__(self, ui):
        self.ui = ui
        self.permissions = PermissionStore()

    def _confirm(self, title: str, detail: str) -> bool:
        window = getattr(self.ui, "_win", None)
        if window is None:
            return False
        answer = QMessageBox.question(
            window,
            str(title),
            str(detail),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _finish_typed_text(self, text: str) -> None:
        ok, message = type_text_into_foreground_window(text)
        self.ui.write_log(("TYPE: " if ok else "TYPE BLOCKED: ") + message)
        try:
            window = getattr(self.ui, "_win", None)
            if window is not None:
                window.showNormal()
                window.raise_()
                window.activateWindow()
        except Exception:
            pass

    def _permission_command(self, raw: str):
        p = str(raw or "").strip().casefold()
        if p in {"permissions", "app permissions", "permission status", "show permissions"}:
            return self.permissions.summary()

        match = re.fullmatch(r"(?:grant|allow|enable)\s+permission\s+(.+)", raw, flags=re.I)
        if match:
            requested = match.group(1).strip()
            if requested.casefold() in {"all", "everything"}:
                detail = (
                    "Enable all JARVIS-supported app capabilities?\n\n"
                    "This enables app discovery/launch, literal typing, message drafts, call preparation, confirmed mouse/keyboard actions, window management, settings navigation and power requests. Every desktop input, window, settings and power action still requires its own confirmation. JARVIS will not silently send messages or override Windows permissions."
                )
                if not self._confirm("Grant supported app permissions", detail):
                    return "Permission grant cancelled; existing settings are unchanged."
                self.permissions.set_all(True)
                return "All supported JARVIS app capabilities are enabled. Sensitive actions still require per-action confirmation.\n\n" + self.permissions.summary()

            key = resolve_permission(requested)
            if not key:
                return "Unknown permission. Use read apps, launch apps, type text, send message, call, desktop input, window control, system settings, system power, or all."
            info = PERMISSION_INFO[key]
            if not self._confirm(
                "Grant permission: " + info["label"],
                info["description"] + "\n\nEnable this JARVIS capability? This does not override Windows or app permissions.",
            ):
                return "Permission grant cancelled; existing settings are unchanged."
            self.permissions.set(key, True)
            return f"Permission enabled: {key}.\n{info['description']}"

        match = re.fullmatch(r"(?:revoke|deny|disable)\s+permission\s+(.+)", raw, flags=re.I)
        if match:
            requested = match.group(1).strip()
            if requested.casefold() in {"all", "everything"}:
                if not self._confirm(
                    "Revoke all JARVIS app permissions",
                    "Disable all JARVIS capabilities, including mouse/keyboard, window management, settings and system power actions?",
                ):
                    return "Permission change cancelled."
                self.permissions.set_all(False)
                return "All JARVIS app capabilities are now disabled."
            key = resolve_permission(requested)
            if not key:
                return "Unknown permission. Use read apps, launch apps, type text, send message, call, desktop input, window control, system settings or system power."
            self.permissions.set(key, False)
            return f"Permission revoked: {key}."
        return None

    def _app_search(self, query: str = "", refresh: bool = False) -> str:
        if not self.permissions.has("app_list"):
            return "App discovery permission is disabled. Use 'grant permission read apps' to enable it."
        try:
            if refresh and hasattr(_start_apps_index, "cache_clear"):
                _start_apps_index.cache_clear()
            records = _start_apps_index()
        except Exception as exc:
            return f"Could not query Windows' registered app list: {exc}"
        names = filter_installed_apps(records, query=query, limit=50)
        if not names:
            if platform.system() != "Windows":
                return "Installed-app discovery currently uses Windows 10/11 Get-StartApps."
            return f"No registered apps matched {query!r}." if query else "Windows did not return any registered apps."
        heading = f"Apps matching '{query}':" if query else "Installed apps (first 50):"
        return heading + "\n" + "\n".join(f"• {name}" for name in names) + "\n\nTo open one, use: open <exact app name>"

    def handle_command(self, raw: str):
        """Return a response for app-control commands, or None when unrelated."""
        raw = str(raw or "").strip()
        if not raw:
            return None

        permission_response = self._permission_command(raw)
        if permission_response is not None:
            return permission_response

        p = raw.casefold()
        if p in {"apps", "list apps", "show apps", "installed apps", "search apps"}:
            return self._app_search()
        match = re.fullmatch(r"(?:apps|search apps|search app|find app|list apps)\s+search\s+(.+)", raw, flags=re.I)
        if match:
            return self._app_search(match.group(1).strip())
        match = re.fullmatch(r"(?:search app|find app|apps search|search apps)\s+(.+)", raw, flags=re.I)
        if match:
            return self._app_search(match.group(1).strip())
        if p == "refresh apps":
            return self._app_search(refresh=True)

        draft_match = re.fullmatch(
            r"(?:draft|send)\s+message\s+(?:on|via|in|to)\s+(whatsapp|telegram)\s*:\s*(.+)",
            raw, flags=re.I | re.S,
        ) or re.fullmatch(
            r"(?:draft|send)\s+(whatsapp|telegram)\s+message\s*:\s*(.+)",
            raw, flags=re.I | re.S,
        )
        if draft_match:
            groups = draft_match.groups()
            app = next(group for group in groups if group and group.casefold() in {"whatsapp", "telegram"})
            message_text = groups[-1].strip()
            if not self.permissions.has("draft_message"):
                return "Message-draft permission is disabled. Use 'grant permission send message' first."
            if not message_text:
                return "Message text is empty."
            if len(message_text) > 2000:
                return "Message drafts are limited to 2,000 characters."
            detail = (
                f"Open a {app.title()} share/draft link with this message?\n\n"
                f"{message_text[:1200]}\n\n"
                "The message text is included in the share URL and may appear in browser history. JARVIS will not select a recipient or press Send. Review the recipient and message in the app, then send manually."
            )
            if not self._confirm("Prepare message draft", detail):
                return "Message draft cancelled."
            encoded = urllib.parse.quote(message_text, safe="")
            url = f"https://wa.me/?text={encoded}" if app.casefold() == "whatsapp" else f"https://t.me/share/url?url=&text={encoded}"
            try:
                opened = webbrowser.open(url, new=2)
            except Exception as exc:
                return f"Could not open the {app.title()} draft link: {exc}"
            if not opened:
                return f"The default browser did not confirm opening the {app.title()} draft link. No message was sent."
            return f"Opened a {app.title()} message draft/share link. No message was sent; choose the recipient and send manually."

        call_match = re.fullmatch(r"(?:prepare\s+)?call\s+(?:on|in|via|with|using)\s+(whatsapp|telegram)", raw, flags=re.I)
        if call_match:
            app = call_match.group(1).casefold()
            if not self.permissions.has("prepare_call"):
                return "Call-preparation permission is disabled. Use 'grant permission call' first."
            if not self.permissions.has("app_launch"):
                return "App-launch permission is disabled. Use 'grant permission launch apps' first."
            if not launch_app:
                return "App launching helper is unavailable."
            if not self._confirm(
                "Open calling app",
                f"Open {app.title()} now? JARVIS will not choose a contact or start a call. You must verify the contact and place the call yourself.",
            ):
                return "Call preparation cancelled."
            ok, message = launch_app(app)
            if not ok:
                return message
            return f"Opened {app.title()}. Select the contact and start the call manually; JARVIS did not place a call."

        if p.startswith("type text "):
            if not self.permissions.has("type_text"):
                return "Foreground typing permission is disabled. Use 'grant permission type text' first."
            typed = raw[len("type text "):]
            valid, validation_message = validate_typing_text(typed)
            if not valid:
                return validation_message
            detail = (
                "Type this literal text into whichever application is foreground after a 5-second countdown?\n\n"
                f"{typed[:1000]}\n\n"
                "After confirming, switch to the intended app and click its text field. JARVIS will not press Enter, click Send, or execute shortcuts."
            )
            if not self._confirm("Type plain text", detail):
                return "Typing cancelled."
            window = getattr(self.ui, "_win", None)
            if window is None:
                return "Typing cancelled because the desktop window is unavailable."
            window.showMinimized()
            QTimer.singleShot(5000, lambda text_to_type=typed: self._finish_typed_text(text_to_type))
            return "JARVIS minimized. You have 5 seconds to switch to the intended app and click the exact text field. Only plain text will be typed; no send/Enter action will occur."

        return None
