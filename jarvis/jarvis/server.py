"""Local web HUD: http://127.0.0.1:8765

A tiny standard-library HTTP server with Server-Sent Events for live tokens,
sub-agent activity, confirmations and reminders.
"""
from __future__ import annotations

import json
import queue
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import platform_utils as pu
from .orchestrator import Jarvis

WEB_DIR = Path(__file__).parent / "web"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


class EventBus:
    def __init__(self):
        self.clients: list[queue.Queue] = []
        self.lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=2000)
        with self.lock:
            self.clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def publish(self, kind: str, data: dict) -> None:
        payload = json.dumps({"type": kind, **data}, default=str)
        with self.lock:
            for q in self.clients:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    pass


class WebConfirm:
    """Turns a sub-agent's confirmation request into a dialog in the browser."""

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.pending: dict[str, tuple[threading.Event, list[bool]]] = {}

    def __call__(self, prompt: str) -> bool:
        cid = uuid.uuid4().hex[:8]
        event, answer = threading.Event(), [False]
        self.pending[cid] = (event, answer)
        self.bus.publish("confirm", {"id": cid, "prompt": prompt})
        event.wait(timeout=120)
        self.pending.pop(cid, None)
        return answer[0]

    def resolve(self, cid: str, approved: bool) -> bool:
        item = self.pending.get(cid)
        if not item:
            return False
        item[1][0] = approved
        item[0].set()
        return True


class App:
    def __init__(self, config=None):
        self.bus = EventBus()
        self.confirm = WebConfirm(self.bus)
        self.jarvis = Jarvis(config, confirm=self.confirm)
        self.jarvis.on_event(self.bus.publish)
        self.busy = threading.Lock()
        self._listener = None

    def chat(self, message: str) -> None:
        def worker():
            with self.busy:
                self.bus.publish("thinking", {"message": message})
                try:
                    reply = self.jarvis.ask(message, on_token=lambda t: self.bus.publish("token", {"text": t}))
                    self.bus.publish("done", {"reply": reply})
                except Exception as exc:  # pragma: no cover - surfaced in the UI
                    self.bus.publish("error", {"message": f"{type(exc).__name__}: {exc}"})
        threading.Thread(target=worker, daemon=True).start()

    def transcribe(self, audio: bytes, suffix: str) -> str:
        from .voice import shared_listener
        cfg = self.jarvis.config
        listener = shared_listener(cfg.get("voice.stt_model"), cfg.get("voice.stt_device"))
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
            fh.write(audio)
            path = fh.name
        try:
            return listener.transcribe(path)
        finally:
            Path(path).unlink(missing_ok=True)

    def status(self) -> dict:
        cfg = self.jarvis.config
        ok, detail = self.jarvis.llm.health()
        stats = {}
        if pu.psutil:
            stats = {"cpu": pu.psutil.cpu_percent(interval=None),
                     "mem": pu.psutil.virtual_memory().percent}
        return {
            "name": cfg.get("assistant.name"), "user": cfg.get("assistant.user_name"),
            "model": cfg.get("llm.model"), "provider": cfg.get("llm.provider"),
            "online": ok, "detail": detail, "os": pu.OS_NAME, "stats": stats,
            "agents": [{"name": a.name, "title": a.title, "description": a.description}
                       for a in self.jarvis.agents.values()],
        }


def make_handler(app: App, check_host: bool):
    class Handler(BaseHTTPRequestHandler):
        server_version = "JARVIS/1.0"

        def log_message(self, *args):  # keep the console quiet
            pass

        def _host_ok(self) -> bool:
            if not check_host:
                return True
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in LOCAL_HOSTS

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data) -> None:
            self._send(code, json.dumps(data).encode())

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden host"})
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._send(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/status":
                return self._json(200, app.status())
            if path == "/api/events":
                return self._stream()
            self._json(404, {"error": "not found"})

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = app.bus.subscribe()
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        payload = q.get(timeout=15)
                        self.wfile.write(f"data: {payload}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                app.bus.unsubscribe(q)

        def do_POST(self):
            # Browsers cannot add custom headers cross-origin without a CORS
            # preflight we never approve, so this blocks other websites.
            if not self._host_ok() or self.headers.get("X-Jarvis") != "1":
                return self._json(403, {"error": "forbidden"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > 25_000_000:
                return self._json(413, {"error": "too large"})
            body = self.rfile.read(length) if length else b""
            path = self.path.split("?")[0]
            if path == "/api/transcribe":
                ctype = self.headers.get("Content-Type", "")
                suffix = ".ogg" if "ogg" in ctype else ".mp4" if "mp4" in ctype else ".wav" if "wav" in ctype else ".webm"
                try:
                    return self._json(200, {"text": app.transcribe(body, suffix)})
                except RuntimeError as exc:
                    return self._json(501, {"error": str(exc)})
                except Exception as exc:
                    return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            try:
                data = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid json"})
            if path == "/api/chat":
                message = str(data.get("message", "")).strip()
                if not message:
                    return self._json(400, {"error": "empty message"})
                if app.busy.locked():
                    return self._json(409, {"error": "busy"})
                app.chat(message)
                return self._json(202, {"ok": True})
            if path == "/api/confirm":
                ok = app.confirm.resolve(str(data.get("id")), bool(data.get("approved")))
                return self._json(200 if ok else 404, {"ok": ok})
            if path == "/api/reset":
                app.jarvis.reset()
                return self._json(200, {"ok": True})
            self._json(404, {"error": "not found"})

    return Handler


def serve(config=None, open_browser: bool = True) -> None:
    app = App(config)
    host = app.jarvis.config.get("server.host", "127.0.0.1")
    port = int(app.jarvis.config.get("server.port", 8765))
    check_host = host in ("127.0.0.1", "localhost", "::1")
    httpd = ThreadingHTTPServer((host, port), make_handler(app, check_host))
    httpd.daemon_threads = True
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}"
    print(f"JARVIS HUD online at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
        app.jarvis.shutdown()
