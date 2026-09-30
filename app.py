"""Run: python app.py. Local synthetic demo, not a production HTTP server."""
import argparse
import json
import secrets
import threading
import time
from datetime import date, timedelta
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from nextstep import store, engine, llm

ROOT = Path(__file__).resolve().parent
MAX_BODY = 4096

def make_server(db_path, host="127.0.0.1", port=8000):
    store.initialize(db_path)
    adapter = llm.OpenAIAdapter.from_environment() or engine.ScriptedAdapter()
    sessions = {}
    lock = threading.RLock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never persist bodies, query strings, customer IDs or private text.

        def send(self, status, body, content_type="application/json; charset=utf-8", cookie=None, private=False):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            policy = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'; "
            policy += "connect-src 'none'; frame-ancestors 'self'; sandbox allow-scripts" if private else "connect-src 'self'; frame-src 'self'; frame-ancestors 'none'"
            self.send_header("Content-Security-Policy", policy)
            if cookie:
                self.send_header("Set-Cookie", f"nextstep_session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=14400")
            self.end_headers()
            self.wfile.write(body)

        def host_valid(self):
            port_actual = self.server.server_port
            return self.headers.get("Host") in {f"127.0.0.1:{port_actual}", f"localhost:{port_actual}"}

        def session(self):
            jar = cookies.SimpleCookie()
            try:
                jar.load(self.headers.get("Cookie", ""))
                token = jar["nextstep_session"].value if "nextstep_session" in jar else None
                session = sessions.get(token)
                if session and time.monotonic() - session["created"] < 14400:
                    return session
            except cookies.CookieError:
                pass
            return None

        def do_GET(self):
            with lock:
                self.get_request()

        def get_request(self):
            if not self.host_valid():
                return self.send(403, {"error": "Host not allowed"})
            parsed = urlsplit(self.path)
            if parsed.query:
                return self.send(400, {"error": "Query fields are not supported. Identity comes from the session."})
            if parsed.path == "/api/state":
                session = self.session()
                if not session:
                    return self.send(401, {"error": "Open the demo to create a synthetic session."})
                with store.connect(db_path) as db:
                    state = engine.snapshot(db, session["customer_id"], session["today"], adapter)
                state["csrf"] = session["csrf"]
                state["demo_customers"] = [{"id": p[0], "name": p[1], "initials": p[2]} for p in store.PEOPLE]
                return self.send(200, state)
            files = {"/": ("index.html", "text/html"), "/styles.css": ("styles.css", "text/css"),
                     "/app.js": ("app.js", "text/javascript"), "/private.html": ("private.html", "text/html"),
                     "/private.js": ("private.js", "text/javascript"), "/private.css": ("private.css", "text/css"),
                     "/favicon.svg": ("favicon.svg", "image/svg+xml")}
            if parsed.path not in files:
                return self.send(404, {"error": "Unknown route"})
            new_cookie = None
            if parsed.path == "/" and not self.session():
                # Privileged demo selector, not real customer authentication.
                now = time.monotonic()
                for token in list(sessions):
                    if now - sessions[token]["created"] >= 14400:
                        del sessions[token]
                if len(sessions) >= 500:
                    return self.send(503, {"error": "Demo session limit reached. Restart the local server."})
                new_cookie = secrets.token_urlsafe(32)
                sessions[new_cookie] = {"customer_id": "sofia", "csrf": secrets.token_urlsafe(32), "today": store.TODAY, "created": now}
            filename, mime = files[parsed.path]
            return self.send(200, (ROOT / "static" / filename).read_bytes(), mime + "; charset=utf-8", new_cookie, parsed.path == "/private.html")

        def do_POST(self):
            with lock:
                self.post_request()

        def post_request(self):
            if not self.host_valid():
                return self.send(403, {"error": "Host not allowed"})
            session = self.session()
            origin = self.headers.get("Origin")
            expected = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not session or origin not in expected or not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), session["csrf"]):
                return self.send(403, {"error": "A valid same-origin session and CSRF token are required."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise engine.InvalidInput("A small JSON request is required.")
                data = json.loads(self.rfile.read(length))
                with store.connect(db_path) as db:
                    if self.path == "/api/demo/select":
                        engine.require_fields(data, ["customer_id"])
                        if data.get("customer_id") not in {p[0] for p in store.PEOPLE}:
                            raise engine.InvalidInput("Unknown synthetic customer")
                        session["customer_id"] = data["customer_id"]
                        session["today"] = store.TODAY
                    elif self.path == "/api/demo/reset":
                        engine.require_fields(data, [])
                        store.reset_customer(db, session["customer_id"])
                        session["today"] = store.TODAY
                    elif self.path == "/api/demo/advance":
                        engine.require_fields(data, [])
                        session["today"] = (date.fromisoformat(session["today"]) + timedelta(days=7)).isoformat()
                    elif self.path.startswith("/api/action/"):
                        engine.mutate(db, session["customer_id"], self.path.removeprefix("/api/action/"), data, session["today"])
                        if self.path in {"/api/action/permissions", "/api/action/dismiss", "/api/action/share"} and hasattr(adapter, "clear_cache"):
                            adapter.clear_cache()
                    elif self.path == "/api/ask":
                        engine.require_fields(data, ["question"])
                        question = data.get("question")
                        if not isinstance(question, str) or not 5 <= len(question.strip()) <= 300:
                            raise engine.InvalidInput("A short question is required.")
                        state = engine.snapshot(db, session["customer_id"], session["today"], adapter)
                        context = state["analysis"]["request"]
                        if context is None:
                            raise engine.InvalidInput("No permitted suggestion to ask about.")
                        answer = engine.answer_question(context, question.strip(), adapter)
                        return self.send(200, answer)
                    else:
                        return self.send(404, {"error": "Unknown route"})
                return self.send(200, {"ok": True})
            except (ValueError, TypeError, engine.InvalidInput):
                # Fixed error: untrusted text is never reflected into a bank-visible response.
                return self.send(400, {"error": "This action is not allowed in the current state, or its fields are invalid. Refresh and check the inputs."})

    return ThreadingHTTPServer((host, port), Handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Private NextStep local demo")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=str(ROOT / "data" / "nextstep.sqlite3"))
    args = parser.parse_args()
    server = make_server(args.db, port=args.port)
    print(f"Private NextStep is running at http://127.0.0.1:{server.server_port}", flush=True)
    print("Synthetic data only. " + ("OpenAI interpretation enabled." if llm.OpenAIAdapter.from_environment() else "OPENAI_API_KEY missing: scripted fallback.") + " Private AI unavailable. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
