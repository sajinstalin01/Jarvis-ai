"""J.A.R.V.I.S. Qt HUD entry point.

The active UI is the uploaded PyQt6 holographic interface in ui.py. Existing
AI, local SQLite history/memory, app-launch helpers, reminders and safe PC
controls remain wired through this bridge.
"""
from __future__ import annotations
import ast
import datetime as dt
import json
import os
import platform
import re
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
load_env()

CONFIG_DIR = ROOT / "config"
API_FILE = CONFIG_DIR / "api_keys.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
if not API_FILE.exists():
    API_FILE.write_text(json.dumps({
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "os_system": {"Windows": "windows", "Darwin": "mac"}.get(platform.system(), "linux"),
        "assistant_name": "JARVIS",
    }, indent=2), encoding="utf-8")

try:
    _cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
    if _cfg.get("gemini_api_key"):
        os.environ.setdefault("GEMINI_API_KEY", str(_cfg["gemini_api_key"]))
except Exception:
    pass

try:
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:
    raise SystemExit("PyQt6 is required for the new JARVIS HUD. Run: python -m pip install -r requirements.txt") from exc

import ui as _ui_module
from ui import JarvisUI, apply_realistic_theme, polish_window
from font_manager import (get_font_settings, install_font_menu, load_custom_fonts)
from open_command import parse_open_payload, safe_website_url
from app_control_manager import AppControlManager
from jarvis_ai import generate_response
from jarvis_control import lock_screen, take_screenshot, toggle_mute
from jarvis_remote import JarvisRemoteServer
from jarvis_services import JarvisStore, SAFE_WEBSITES, developer_diagnostics, parse_reminder_command, system_metrics
from voice_control import VoiceController
try:
    # Reuse the existing safe app allow-list and arithmetic parser.
    from jarvis_legacy import launch_app, safe_calculate, web_search
except Exception as exc:
    launch_app = None
    def safe_calculate(expr):
        try:
            tree = ast.parse(expr, mode="eval")
            allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                       ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                       ast.Mod, ast.Pow, ast.USub, ast.UAdd)
            if any(not isinstance(n, allowed) for n in ast.walk(tree)):
                raise ValueError("Only basic arithmetic is allowed.")
            return str(eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, {}))
        except Exception as err:
            return f"Calculation failed: {err}"
    def web_search(query):
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
        return "Opened a browser search."
    print(f"[JARVIS] Legacy launcher unavailable; using limited fallback: {exc}")


class JarvisBridge:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.store = JarvisStore()
        self.app_control = AppControlManager(ui)
        self._voice = VoiceController(self._voice_result, self._voice_status)
        self._voice_lock = threading.Lock()
        self.remote = JarvisRemoteServer(self._remote_command, self._remote_status)
        self._reminder_stop = threading.Event()
        self.ui.on_text_command = self.handle_command
        self.ui.on_interrupt = self.interrupt
        self.ui.on_push_to_talk = self._ptt_enable
        self.ui.ptt_hold = self._ptt_hold
        self.ui.on_wake_toggle = self._wake_toggle
        self.ui.on_wake_manual = self._wake_manual
        self.ui.wake_get_state = lambda: {"ready": False, "enabled": False, "awake": True}
        self.ui.get_plugins = lambda: []
        self.ui.get_plugin_settings = lambda: []
        self.ui.on_remote_clicked = self._remote_overlay_request
        self._reminder_thread = threading.Thread(target=self._reminder_loop, daemon=True, name="JarvisReminders")
        self._reminder_thread.start()
        self.ui.write_log("SYS: PyQt6 HUD connected to Groq/Gemini, local memory, app launcher and PC controls.")
        if not (os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")):
            self.ui.write_log("SYS: Add GROQ_API_KEY or GEMINI_API_KEY to .env, or enter a Gemini key in setup.")

    def _voice_status(self, message):
        self.ui.write_log("VOICE: " + str(message))

    def _voice_result(self, text):
        if text:
            self.handle_command(str(text))

    def _ptt_enable(self, enabled):
        return "window" if enabled else ""

    def _ptt_hold(self, held):
        if held:
            self._voice.listen_once()

    def _wake_toggle(self, enabled):
        return "Wake-word listening is not bundled in this build. Use the microphone / push-to-talk control."

    def _wake_manual(self):
        self.ui.write_log("VOICE: Wake-word engine is not configured; use push-to-talk.")

    def interrupt(self):
        # pyttsx3 is optional and speech is run in its own worker thread.
        self.ui.write_log("SYS: Interrupt requested. Stop the current spoken response from your audio device if needed.")

    def _refresh_api_keys(self):
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8"))
            key = str(cfg.get("gemini_api_key", "")).strip()
            if key:
                os.environ["GEMINI_API_KEY"] = key
        except Exception:
            pass

    def _remote_status(self):
        return system_metrics()

    def _remote_command(self, command):
        normalized = command.strip().lower()
        if normalized in ("status", "pc status"):
            return json.dumps(self._remote_status(), ensure_ascii=False)
        if normalized in ("lock", "lock screen", "pc lock"):
            return lock_screen()[1]
        if normalized.startswith("launch ") and launch_app:
            if not self.app_control.permissions.has("app_launch"):
                return "App-launch permission is disabled."
            ok, msg = launch_app(normalized[7:].strip())
            return msg
        return "Remote command rejected."

    def _remote_overlay_request(self):
        # Do not silently expose the machine to a LAN. The separate authenticated
        # API can be started explicitly with the chat command 'remote server start'.
        self.ui.write_log("REMOTE: Use 'remote server start' to start the authenticated local API.")
        return None

    def _context(self):
        rows = list(reversed(self.store.search_history("", limit=20)))
        context = []
        for row in rows:
            speaker = str(row.get("speaker", "")).upper()
            role = "user" if speaker in {"BOSS", "USER", "YOU"} else "assistant"
            content = str(row.get("content", "")).strip()
            if content:
                context.append({"role": role, "content": content[:3000]})
        # Current prompt is stored before routing; generate_response appends it separately.
        if context and context[-1].get("role") == "user":
            context.pop()
        memories = self.store.list_memories(limit=8)
        saved = "\n".join(f"- {m['content']}" for m in memories if m.get("content"))
        return context[-16:], saved

    def _remember_history(self, speaker, text):
        try:
            self.store.save_message(speaker, str(text)[:12000])
        except Exception:
            pass

    def _log_answer(self, answer, provider=""):
        self.ui.write_log(f"JARVIS: {answer}")
        if provider:
            self.ui.write_log(f"SYS: Response provider: {provider}")
        try:
            if not self.ui.muted:
                self._voice.speak(answer)
        except Exception:
            pass

    def _local_command(self, text):
        raw = text.strip()
        p = raw.casefold()
        app_control_response = self.app_control.handle_command(raw)
        if app_control_response is not None:
            return app_control_response
        if p in {"help", "commands", "what can you do"}:
            return ("Available commands:\n"
                    "• launch <app> [search <query>]; apps; apps search <name>; refresh apps\n"
                    "• permissions; grant/revoke permission <read apps|launch apps|type text|send message|call|all>\n"
                    "• type text <plain text> (permission + per-action confirmation)\n"
                    "• draft message on <whatsapp|telegram>: <text> (draft only)\n"
                    "• prepare call on <whatsapp|telegram> (opens app; you place call)\n"
                    "• open <google|youtube|github|gmail|wikipedia>\n"
                    "• search <query>; calculate <expression>\n"
                    "• pc status, pc lock, pc mute, pc screenshot\n"
                    "• remember <fact>, memories [search], forget memory <id>, history [search]\n"
                    "• remind me in 10 minutes to <task>; remind me daily/weekly to <task>; list reminders\n"
                    "• save workflow <name>: launch <app>; open <site>; search <query>\n"
                    "• run workflow <name>; workflows; developer diagnostics\n"
                    "• remote server start / remote server stop")
        if p in {"time", "what time is it"}:
            return "Local time: " + dt.datetime.now().astimezone().strftime("%I:%M:%S %p")
        if p in {"date", "what is the date", "what's the date"}:
            return "Today is " + dt.datetime.now().astimezone().strftime("%A, %d %B %Y")
        if p in {"system info", "pc status", "computer status", "system status"}:
            return "\n".join(f"{k.replace('_',' ').title()}: {v}" for k, v in system_metrics().items())
        if p in {"pc lock", "lock pc", "lock screen", "lock computer"}:
            return lock_screen()[1]
        if p in {"pc mute", "toggle mute", "mute volume"}:
            return toggle_mute()[1]
        if p in {"pc screenshot", "take screenshot", "screenshot"}:
            return take_screenshot()[1]
        if p in {"remote server stop", "stop remote server"}:
            self.remote.stop()
            return "Authenticated remote API stopped; access token discarded."
        if p in {"remote server start", "start remote server"}:
            token = self.remote.start(allow_lan=False)
            return (f"Authenticated remote API started on this PC only: http://127.0.0.1:{self.remote.port}\n"
                    f"Bearer token (keep private): {token}\n"
                    "Allowed actions: status, lock screen, launch <app>. Use 'remote server stop' when finished.")
        if p.startswith("remember "):
            fact = raw[9:].strip()
            if not fact: return "Tell me what to remember after 'remember'."
            mid = self.store.remember(fact)
            return f"Saved memory #{mid} locally."
        if p == "memories" or p.startswith("memories "):
            query = raw[8:].strip() if len(raw) > 8 else ""
            rows = self.store.list_memories(query, limit=30)
            return "\n".join(f"#{m['id']} · {m['content']}" for m in rows) or "No saved memories found."
        match = re.fullmatch(r"forget memory (\d+)", p)
        if match:
            return "Memory deleted." if self.store.forget_memory(int(match.group(1))) else "Memory ID not found."
        if p == "history" or p.startswith("history "):
            query = raw[7:].strip() if len(raw) > 7 else ""
            rows = self.store.search_history(query, limit=25)
            return "\n".join(f"{r['speaker']}: {r['content'][:260]}" for r in reversed(rows)) or "No matching history."
        if p == "list reminders" or p == "reminders":
            rows = self.store.list_reminders()
            return "\n".join(f"#{r['id']} · {r['due_at']} · {r['message']} ({r['recurrence']})" for r in rows) or "No active reminders."
        if p.startswith("cancel reminder "):
            try: rid = int(p.rsplit(" ", 1)[1])
            except ValueError: return "Use: cancel reminder <id>"
            return "Reminder deleted." if self.store.delete_reminder(rid) else "Reminder ID not found."
        if p.startswith("remind me "):
            parsed = parse_reminder_command(raw)
            if not parsed:
                return "Use: remind me in 10 minutes to stretch, or remind me daily to review."
            message, due_at, recurrence = parsed
            rid = self.store.add_reminder(message, due_at, recurrence)
            return f"Reminder #{rid} saved for {due_at.astimezone().strftime('%Y-%m-%d %I:%M %p')} ({recurrence})."
        if p == "developer diagnostics":
            return developer_diagnostics()
        if p == "workflows":
            rows = self.store.list_workflows()
            return "\n".join(f"{w['name']}: {'; '.join(w['steps'])}" for w in rows) or "No saved workflows."
        match = re.fullmatch(r"save workflow ([^:]+):\s*(.+)", raw, flags=re.I | re.S)
        if match:
            name, steps_text = match.groups()
            steps = [s.strip() for s in steps_text.split(";") if s.strip()]
            self.store.save_workflow(name, steps)
            return f"Workflow '{name.strip()}' saved with {len(steps)} steps."
        match = re.fullmatch(r"run workflow (.+)", raw, flags=re.I)
        if match:
            workflow = self.store.get_workflow(match.group(1))
            if not workflow: return "Workflow not found."
            output = []
            for step in workflow["steps"]:
                output.append(self._local_command(step) or "Done.")
            return "\n".join(output)
        if p.startswith("launch "):
            if not self.app_control.permissions.has("app_launch"):
                return "App-launch permission is disabled. Use 'grant permission launch apps' to enable it."
            if not launch_app: return "App launching helper is unavailable."
            tail = raw[7:].strip()
            m = re.fullmatch(r"(.+?)\s+search\s+(.+)", tail, flags=re.I)
            app, query = (m.group(1), m.group(2)) if m else (tail, None)
            ok, message = launch_app(app, search_query=query)
            return message
        if p.startswith("open "):
            target, query = parse_open_payload(raw[5:].strip())
            if not target:
                return "Use 'open <app or website>' or 'open <browser> search <query>'."

            site_url = safe_website_url(target, query)
            if site_url:
                webbrowser.open(site_url)
                return f"Opening {target}" + (f" and searching for '{query}'." if query else ".")

            if not self.app_control.permissions.has("app_launch"):
                return "App-launch permission is disabled. Use 'grant permission launch apps' to enable it."
            if target.casefold() in {"settings", "system settings", "windows settings"}:
                if launch_app:
                    ok, message = launch_app("settings")
                    return message

            if not launch_app:
                return "The app launcher is unavailable. You can still use 'search <query>'."
            ok, message = launch_app(target, search_query=query)
            if ok:
                return message
            if query and "search syntax is for browsers" in message.casefold():
                return (f"Couldn't search from '{target}'. {message} "
                        "Use a browser name such as chrome, edge, firefox, or brave.")
            return (f"Couldn't open '{target}'. {message}\n"
                    f"Try 'launch {target}' or use 'search <query>' for a web search.")
        if p.startswith("search "):
            return web_search(raw[7:].strip()) if web_search else "Search helper unavailable."
        if p.startswith("calculate "):
            return safe_calculate(raw[10:].strip())
        return None

    def handle_command(self, text):
        prompt = str(text or "").strip()
        if not prompt:
            return
        self._remember_history("BOSS", prompt)
        self.ui.set_state("THINKING")
        try:
            local = self._local_command(prompt)
            if local is not None:
                self._remember_history("JARVIS", local)
                self._log_answer(local)
                return
            self._refresh_api_keys()
            context, memories = self._context()
            answer, provider = generate_response(prompt, context=context, saved_memories=memories)
            self._remember_history("JARVIS", answer)
            self._log_answer(answer, provider)
        except Exception as exc:
            self.ui.write_log("ERR: " + str(exc))
        finally:
            self.ui.set_state("LISTENING")

    def _reminder_loop(self):
        while not self._reminder_stop.wait(5):
            try:
                due = self.store.due_reminders()
                for reminder in due:
                    self.ui.write_log(f"REMINDER: {reminder['message']}")
                    try:
                        if not self.ui.muted: self._voice.speak("Reminder: " + reminder["message"])
                    except Exception:
                        pass
            except Exception:
                pass


def main():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("J.A.R.V.I.S.")
    # Load user-owned fonts before any widgets are built. Missing fonts safely
    # fall back to the system font without blocking startup.
    load_custom_fonts()
    font_family = get_font_settings()["font_family"]
    apply_realistic_theme(_ui_module, app, font_family=font_family)
    ui = JarvisUI(str(ROOT / "assets" / "face.png"))
    polish_window(ui._win, font_family=font_family)
    try:
        install_font_menu(ui._win, app)
    except Exception as exc:
        print(f"[Fonts] Font menu unavailable: {exc}")
    bridge = JarvisBridge(ui)
    # Keep references alive for Qt's lifetime and clean up the local API.
    ui._bridge = bridge
    ui._win.destroyed.connect(lambda *_: bridge.remote.stop())
    ui.root.mainloop()

if __name__ == "__main__":
    main()
