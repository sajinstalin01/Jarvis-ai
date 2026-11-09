"""Local resource/task monitor. No screen, keystroke, clipboard or private-app capture."""
from __future__ import annotations
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class SystemWatch:
    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root / "jarvis_data"
        self.data.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data / "system_watch.sqlite3"
        self.settings_path = self.data / "system_watch.json"
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY, at TEXT NOT NULL, cpu REAL, ram REAL, disk REAL, sent INTEGER, received INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, at TEXT NOT NULL, message TEXT NOT NULL)")
    def db(self):
        c = sqlite3.connect(self.db_path, timeout=5)
        c.row_factory = sqlite3.Row
        return c
    def _settings(self):
        try:
            d=json.loads(self.settings_path.read_text(encoding="utf-8"))
            return d if isinstance(d,dict) else {}
        except (OSError,ValueError): return {}
    def set_enabled(self, enabled):
        d=self._settings(); d["enabled"]=bool(enabled); d["updated_at"]=datetime.now().astimezone().isoformat()
        self.settings_path.write_text(json.dumps(d,indent=2),encoding="utf-8")
        return "System resource monitoring " + ("enabled" if enabled else "disabled") + "."
    def enabled(self):
        return bool(self._settings().get("enabled",False))
    def sample(self):
        try:
            import psutil
        except ImportError:
            return {"error":"Install psutil to enable system monitoring."}
        cpu=float(psutil.cpu_percent(interval=None))
        ram=float(psutil.virtual_memory().percent)
        usage=shutil.disk_usage(str(self.root.anchor or self.root))
        disk=usage.used*100.0/max(1,usage.total)
        net=psutil.net_io_counters()
        now=datetime.now().astimezone().isoformat(timespec="seconds")
        alerts=[]
        if cpu>=90: alerts.append(f"High CPU usage: {cpu:.0f}%")
        if ram>=90: alerts.append(f"High memory usage: {ram:.0f}%")
        if disk>=95: alerts.append(f"Low disk space: {100-disk:.0f}% free")
        with self.db() as c:
            c.execute("INSERT INTO samples(at,cpu,ram,disk,sent,received) VALUES(?,?,?,?,?,?)",(now,cpu,ram,disk,int(net.bytes_sent),int(net.bytes_recv)))
            for message in alerts: c.execute("INSERT INTO alerts(at,message) VALUES(?,?)",(now,message))
            c.execute("DELETE FROM samples WHERE id NOT IN (SELECT id FROM samples ORDER BY id DESC LIMIT 2000)")
            c.execute("DELETE FROM alerts WHERE id NOT IN (SELECT id FROM alerts ORDER BY id DESC LIMIT 200)")
        return {"at":now,"cpu":cpu,"ram":ram,"disk":disk,"sent":int(net.bytes_sent),"received":int(net.bytes_recv),"alerts":alerts}
    def report(self):
        result=self.sample()
        if "error" in result: return result["error"]
        out=[f"CPU {result['cpu']:.1f}% · RAM {result['ram']:.1f}% · disk used {result['disk']:.1f}%",f"Network totals: sent {result['sent']} bytes · received {result['received']} bytes"]
        out.extend("ALERT · "+x for x in result["alerts"])
        return "\n".join(out)
    def history(self, limit=10):
        with self.db() as c:
            rows=c.execute("SELECT at,cpu,ram,disk FROM samples ORDER BY id DESC LIMIT ?",(max(1,min(100,int(limit))),)).fetchall()
        return "\n".join(f"{r['at']} · CPU {r['cpu']:.1f}% · RAM {r['ram']:.1f}% · disk {r['disk']:.1f}%" for r in rows) or "No monitoring samples yet."
    def alerts(self):
        with self.db() as c:
            rows=c.execute("SELECT at,message FROM alerts ORDER BY id DESC LIMIT 20").fetchall()
        return "\n".join(f"{r['at']} · {r['message']}" for r in rows) or "No system alerts recorded."
