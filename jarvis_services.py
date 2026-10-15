"""Local services for JARVIS: SQLite history/memory, reminders, metrics and safe diagnostics."""
from __future__ import annotations

import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "jarvis_data"
DB_PATH = DATA_DIR / "jarvis.sqlite3"
SAFE_WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "wikipedia": "https://www.wikipedia.org",
}


class JarvisStore:
    """Small local SQLite store. No conversation data is sent to a remote service."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    message TEXT NOT NULL,
                    recurrence TEXT NOT NULL DEFAULT 'once',
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    steps_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    @staticmethod
    def _now():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def save_message(self, speaker: str, content: str):
        with self._connect() as db:
            db.execute("INSERT INTO messages(created_at,speaker,content) VALUES(?,?,?)",
                       (self._now(), speaker[:40], str(content)[:20000]))

    def search_history(self, query: str = "", limit: int = 50):
        q = f"%{query.strip()}%"
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,created_at,speaker,content FROM messages "
                "WHERE (?='' OR content LIKE ?) ORDER BY id DESC LIMIT ?",
                (query.strip(), q, max(1, min(int(limit), 200))),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_history(self):
        with self._connect() as db:
            db.execute("DELETE FROM messages")

    def remember(self, content: str):
        content = content.strip()
        if not content:
            raise ValueError("Memory text cannot be empty.")
        with self._connect() as db:
            cursor = db.execute("INSERT INTO memories(created_at,content) VALUES(?,?)",
                                (self._now(), content[:4000]))
            return int(cursor.lastrowid)

    def list_memories(self, query: str = "", limit: int = 100):
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,created_at,content FROM memories WHERE (?='' OR content LIKE ?) "
                "ORDER BY id DESC LIMIT ?",
                (query.strip(), f"%{query.strip()}%", max(1, min(int(limit), 200))),
            ).fetchall()
        return [dict(row) for row in rows]

    def forget_memory(self, memory_id: int):
        with self._connect() as db:
            cursor = db.execute("DELETE FROM memories WHERE id=?", (int(memory_id),))
            return cursor.rowcount > 0

    def add_reminder(self, message: str, due_at: datetime, recurrence: str = "once"):
        recurrence = recurrence.lower().strip()
        if recurrence not in {"once", "daily", "weekly"}:
            raise ValueError("Recurrence must be once, daily or weekly.")
        if due_at.tzinfo is None:
            due_at = due_at.astimezone()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO reminders(created_at,due_at,message,recurrence,enabled) VALUES(?,?,?,?,1)",
                (self._now(), due_at.isoformat(timespec="seconds"), message.strip()[:1000], recurrence),
            )
            return int(cursor.lastrowid)

    def list_reminders(self, include_disabled: bool = False):
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,due_at,message,recurrence,enabled FROM reminders "
                + ("" if include_disabled else "WHERE enabled=1 ") + "ORDER BY due_at LIMIT 100"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_reminder(self, reminder_id: int):
        with self._connect() as db:
            cursor = db.execute("DELETE FROM reminders WHERE id=?", (int(reminder_id),))
            return cursor.rowcount > 0

    def due_reminders(self, now: datetime | None = None):
        now = now or datetime.now().astimezone()
        due = []
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,due_at,message,recurrence FROM reminders WHERE enabled=1"
            ).fetchall()
            for row in rows:
                try:
                    due_at = datetime.fromisoformat(row["due_at"])
                    if due_at.tzinfo is None:
                        due_at = due_at.astimezone()
                    if due_at <= now:
                        due.append(dict(row))
                        if row["recurrence"] == "daily":
                            next_due = due_at + timedelta(days=max(1, (now - due_at).days + 1))
                            db.execute("UPDATE reminders SET due_at=? WHERE id=?",
                                       (next_due.isoformat(timespec="seconds"), row["id"]))
                        elif row["recurrence"] == "weekly":
                            days = max(1, (now - due_at).days // 7 + 1) * 7
                            next_due = due_at + timedelta(days=days)
                            db.execute("UPDATE reminders SET due_at=? WHERE id=?",
                                       (next_due.isoformat(timespec="seconds"), row["id"]))
                        else:
                            db.execute("UPDATE reminders SET enabled=0 WHERE id=?", (row["id"],))
                except (ValueError, TypeError):
                    db.execute("UPDATE reminders SET enabled=0 WHERE id=?", (row["id"],))
        return due

    def save_workflow(self, name: str, steps: list[str]):
        name = name.strip()
        if not name or not steps:
            raise ValueError("Workflow name and at least one step are required.")
        if len(steps) > 10:
            raise ValueError("A workflow can contain at most 10 steps.")
        for step in steps:
            normalized = step.strip().lower()
            if not (normalized.startswith("launch ") or normalized.startswith("open ") or normalized.startswith("search ")):
                raise ValueError("Only launch, open, and search steps are allowed.")
            if normalized.startswith("open ") and normalized[5:].strip().startswith(("http://", "https://", "file:", "javascript:")):
                raise ValueError("Workflows can open named websites, not arbitrary URLs.")
        with self._connect() as db:
            db.execute(
                "INSERT INTO workflows(name,steps_json,created_at) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET steps_json=excluded.steps_json,created_at=excluded.created_at",
                (name, json.dumps([step.strip() for step in steps]), self._now()),
            )

    def list_workflows(self):
        with self._connect() as db:
            rows = db.execute("SELECT id,name,steps_json FROM workflows ORDER BY name").fetchall()
        result = []
        for row in rows:
            try:
                steps = json.loads(row["steps_json"])
                if isinstance(steps, list):
                    result.append({"id": row["id"], "name": row["name"], "steps": steps})
            except (ValueError, TypeError):
                continue
        return result

    def get_workflow(self, name: str):
        for workflow in self.list_workflows():
            if workflow["name"].casefold() == name.strip().casefold():
                return workflow
        return None

    def delete_workflow(self, name: str):
        with self._connect() as db:
            cursor = db.execute("DELETE FROM workflows WHERE name=? COLLATE NOCASE", (name.strip(),))
            return cursor.rowcount > 0


def system_metrics():
    """Return available live metrics. psutil is optional and failures are non-fatal."""
    result: dict[str, Any] = {
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    try:
        import psutil
        result.update({
            "cpu_percent": psutil.cpu_percent(interval=0.15),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": psutil.virtual_memory().used / (1024 ** 3),
            "disk_percent": psutil.disk_usage(str(Path.home().anchor or "/")).percent,
            "network_sent_mb": psutil.net_io_counters().bytes_sent / (1024 ** 2),
            "network_recv_mb": psutil.net_io_counters().bytes_recv / (1024 ** 2),
        })
        try:
            battery = psutil.sensors_battery()
            result["battery_percent"] = battery.percent if battery else None
        except (AttributeError, OSError):
            result["battery_percent"] = None
        try:
            temps = psutil.sensors_temperatures()
            readings = []
            for entries in temps.values():
                for entry in entries:
                    if entry.current is not None:
                        readings.append(float(entry.current))
            result["temperatures_c"] = readings[:8]
        except (AttributeError, OSError):
            result["temperatures_c"] = []
    except ImportError:
        result["metrics_note"] = "Install psutil to enable CPU, RAM, disk and network metrics."
    except Exception as exc:
        result["metrics_note"] = f"Some metrics are unavailable: {exc}"
    return result


def developer_diagnostics():
    """Read-only project diagnostics. Never runs arbitrary shell input."""
    import ast
    report = [
        f"Project: {ROOT}",
        f"Python: {sys.version.split()[0]}",
        f"Platform: {platform.platform()}",
    ]
    source = ROOT / "jarvis.py"
    try:
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        report.append("jarvis.py syntax: OK")
    except (OSError, SyntaxError) as exc:
        report.append(f"jarvis.py syntax: ERROR — {exc}")
    git = shutil.which("git")
    if git and (ROOT / ".git").exists():
        for args, label in ((["status", "--short"], "Git status"), (["log", "-1", "--oneline"], "Latest commit")):
            try:
                result = subprocess.run([git, *args], cwd=ROOT, capture_output=True, text=True, timeout=8)
                report.append(f"{label}: {(result.stdout or result.stderr).strip() or 'clean'}")
            except (OSError, subprocess.SubprocessError) as exc:
                report.append(f"{label}: unavailable ({exc})")
    else:
        report.append("Git: unavailable or this folder is not a repository")
    return "\n".join(report)


def parse_reminder_command(text: str, now: datetime | None = None):
    """Parse explicit forms: 'remind me in 10 minutes to stretch' or 'remind me daily to review'."""
    import re
    now = now or datetime.now().astimezone()
    value = text.strip()
    match = re.fullmatch(r"remind me in (\d+) (minute|minutes|hour|hours|day|days) to (.+)", value, re.I)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if amount < 1 or amount > 365:
            raise ValueError("Reminder delay must be between 1 and 365 units.")
        delta = timedelta(minutes=amount) if unit.startswith("minute") else timedelta(hours=amount) if unit.startswith("hour") else timedelta(days=amount)
        return match.group(3).strip(), now + delta, "once"
    match = re.fullmatch(r"remind me (daily|weekly) to (.+)", value, re.I)
    if match:
        recurrence = match.group(1).lower()
        return match.group(2).strip(), now + timedelta(days=1 if recurrence == "daily" else 7), recurrence
    return None
