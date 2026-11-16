"""Authenticated, allow-listed JARVIS remote-control API.

The server binds to loopback by default. LAN binding must be explicitly enabled
from the desktop UI. It never executes shell input or accepts arbitrary URLs.
"""
from __future__ import annotations
import hmac
import json
import secrets
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class JarvisRemoteServer:
    def __init__(self, command_handler: Callable[[str], str], status_handler: Callable[[], dict]):
        self.command_handler = command_handler
        self.status_handler = status_handler
        self.server = None
        self.thread = None
        self.token = None
        self.token_expires_at = 0.0
        self.host = "127.0.0.1"
        self.port = 8765
        self.scheme = "http"
        self._lock = threading.Lock()
        self._expiry_timer = None

    @property
    def running(self) -> bool:
        return self.server is not None

    def start(self, allow_lan: bool = False, port: int = 8765, certfile: str | None = None, keyfile: str | None = None) -> str:
        with self._lock:
            if self.server is not None:
                return self.token
            self.host = "0.0.0.0" if allow_lan else "127.0.0.1"
            self.port = int(port)
            if not 1024 <= self.port <= 65535:
                raise ValueError("Remote-control port must be between 1024 and 65535.")
            if allow_lan and not (certfile and keyfile):
                raise ValueError("LAN access requires JARVIS_TLS_CERT and JARVIS_TLS_KEY. Configure a trusted TLS certificate first.")
            tls_context=None
            if allow_lan:
                tls_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                tls_context.minimum_version=ssl.TLSVersion.TLSv1_2
                tls_context.load_cert_chain(certfile=certfile,keyfile=keyfile)
            self.scheme = "https" if allow_lan else "http"
            self.token = secrets.token_urlsafe(32)
            self.token_expires_at=time.time()+600
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
                    ) and time.time() < owner.token_expires_at

                def do_GET(self):
                    if self.path in {"/","/index.html"}:
                        page=b'''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>JARVIS Companion</title><style>body{font:16px system-ui;max-width:620px;margin:2rem auto;padding:0 1rem;background:#07111e;color:#e6f4ff}button,input{font:inherit;padding:.8rem;margin:.25rem;border-radius:.5rem;border:1px solid #31526a;background:#102235;color:inherit}button{cursor:pointer}pre{white-space:pre-wrap;background:#102235;padding:1rem;border-radius:.5rem}#app{display:none}</style><h1>JARVIS Companion</h1><p>Temporary authenticated companion for this JARVIS session.</p><div id="login"><label>Session key <input id="token" type="password" autocomplete="off"></label><button onclick="connect()">Connect</button></div><div id="app"><button onclick="status()">Refresh status</button><button onclick="command('lock screen')">Lock PC</button><p><input id="application" placeholder="Allow-listed app name"><button onclick="launchApp()">Launch app</button></p></div><pre id="out">Enter the session key shown in JARVIS.</pre><script>const out=document.querySelector('#out');let token=localStorage.getItem('jarvis_session')||'';const q=new URLSearchParams(location.search).get('token');if(q){token=q;localStorage.setItem('jarvis_session',token);history.replaceState({},'',location.pathname)}if(token)connect();function connect(){token=document.querySelector('#token').value||token;if(!token){out.textContent='Enter the session key from JARVIS.';return}localStorage.setItem('jarvis_session',token);document.querySelector('#app').style.display='block';document.querySelector('#login').style.display='none';status()}async function request(path,body){try{const r=await fetch(path,{method:body?'POST':'GET',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});out.textContent=JSON.stringify(await r.json(),null,2);if(r.status===401){localStorage.removeItem('jarvis_session');document.querySelector('#login').style.display='block'}}catch(e){out.textContent='Connection failed: '+e}}function status(){request('/api/status')}function command(c){request('/api/command',{command:c})}function launchApp(){const a=document.querySelector('#application').value.trim();if(a)command('launch '+a)}</script>'''
                        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(page))); self.send_header("Cache-Control","no-store"); self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"); self.send_header("Referrer-Policy","no-referrer"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(page); return
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
            if allow_lan:
                try:
                    self.server.socket=tls_context.wrap_socket(self.server.socket,server_side=True)
                except Exception:
                    self.server.server_close(); self.server=None; self.token=None; self.token_expires_at=0.0
                    raise
            self.server.daemon_threads = True
            self.thread = threading.Thread(target=self.server.serve_forever, name="JarvisRemoteAPI", daemon=True)
            self.thread.start()
            self._expiry_timer=threading.Timer(600,self.stop)
            self._expiry_timer.daemon=True; self._expiry_timer.start()
            return self.token

    def stop(self):
        with self._lock:
            server, self.server = self.server, None
            self.token = None
            self.token_expires_at=0.0
            self.thread = None
            timer,self._expiry_timer=self._expiry_timer,None
            if timer: timer.cancel()
        if server is not None:
            server.shutdown()
            server.server_close()
