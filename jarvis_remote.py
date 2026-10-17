"""Authenticated, allow-listed JARVIS remote-control API.

The server binds to loopback by default. LAN binding must be explicitly enabled
from the desktop UI. It never executes shell input or accepts arbitrary URLs.
"""
from __future__ import annotations
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class JarvisRemoteServer:
    def __init__(self, command_handler: Callable[[str], str], status_handler: Callable[[], dict]):
        self.command_handler = command_handler
        self.status_handler = status_handler
        self.server = None
        self.thread = None
        self.token = None
        self.host = "127.0.0.1"
        self.port = 8765
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self.server is not None

    def start(self, allow_lan: bool = False, port: int = 8765) -> str:
        with self._lock:
            if self.server is not None:
                return self.token
            self.host = "0.0.0.0" if allow_lan else "127.0.0.1"
            self.port = int(port)
            if not 1024 <= self.port <= 65535:
                raise ValueError("Remote-control port must be between 1024 and 65535.")
            self.token = secrets.token_urlsafe(32)
            owner = self

            class Handler(BaseHTTPRequestHandler):
                server_version = "JarvisRemote/1.0"
                sys_version = ""

                def log_message(self, fmt, *args):
                    # Do not log authorization headers, request bodies, or tokens.
                    return

                def _send(self, status, payload):
                    body = json.dumps(payload).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)

                def _authorized(self):
                    supplied = self.headers.get("Authorization", "")
                    prefix = "Bearer "
                    return supplied.startswith(prefix) and hmac.compare_digest(
                        supplied[len(prefix):], owner.token or ""
                    )

                def do_GET(self):
                    if self.path != "/api/status":
                        self._send(404, {"ok": False, "error": "Not found"})
                        return
                    if not self._authorized():
                        self._send(401, {"ok": False, "error": "Unauthorized"})
                        return
                    self._send(200, {"ok": True, "status": owner.status_handler()})

                def do_POST(self):
                    if self.path != "/api/command":
                        self._send(404, {"ok": False, "error": "Not found"})
                        return
                    if not self._authorized():
                        self._send(401, {"ok": False, "error": "Unauthorized"})
                        return
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if length < 1 or length > 2048:
                            raise ValueError("Request body must be between 1 and 2048 bytes.")
                        payload = json.loads(self.rfile.read(length).decode("utf-8"))
                        command = payload.get("command", "") if isinstance(payload, dict) else ""
                        if not isinstance(command, str) or len(command) > 160:
                            raise ValueError("Invalid command.")
                        normalized = command.strip().lower()
                        # Remote access deliberately supports only a tiny command set.
                        if normalized in ("status", "pc status"):
                            result = json.dumps(owner.status_handler(), ensure_ascii=False)
                        elif normalized in ("lock", "lock screen", "pc lock"):
                            result = owner.command_handler("pc lock")
                        elif normalized.startswith("launch ") or normalized.startswith("open app "):
                            app = normalized.split(" ", 1)[1].strip()
                            if app.startswith("app "):
                                app = app[4:].strip()
                            if not app or any(ch in app for ch in "\r\n;|&<>"):
                                raise ValueError("Invalid app name.")
                            result = owner.command_handler("launch " + app)
                        else:
                            raise ValueError("Remote command not allowed. Use status, lock screen, or launch <app>.")
                        self._send(200, {"ok": True, "result": result})
                    except (ValueError, TypeError, json.JSONDecodeError) as exc:
                        self._send(400, {"ok": False, "error": str(exc)})
                    except Exception:
                        self._send(500, {"ok": False, "error": "Command failed."})

                def do_PUT(self):
                    self._send(405, {"ok": False, "error": "Method not allowed"})

                def do_DELETE(self):
                    self._send(405, {"ok": False, "error": "Method not allowed"})

            self.server = ThreadingHTTPServer((self.host, self.port), Handler)
            self.server.daemon_threads = True
            self.thread = threading.Thread(target=self.server.serve_forever, name="JarvisRemoteAPI", daemon=True)
            self.thread.start()
            return self.token

    def stop(self):
        with self._lock:
            server, self.server = self.server, None
            self.token = None
            self.thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
