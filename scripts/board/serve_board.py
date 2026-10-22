#!/usr/bin/env python3
"""Local server for the MWA image board on the laptop (standard library only).

Serves the board folder (default ~/mwa-board) at http://127.0.0.1:8793 and keeps the
viewer's verdicts and next-step requests in two files in that folder:
  judgements.json   {product: {product, status, note, updated}}
  requests.json     [{id, product, sun, ch, cal, action, from, to, dt, channels, calibrator,
                      note, state, created, reply?}]
API (used by index.html when it is served from here):
  GET  /api/state           -> {"judgements": {...}, "requests": [...]}
  POST /api/judgement       body: one judgement (product, status, note)
  POST /api/request         body: one request; the server adds id, state "open", created
Claude reads the two files and writes state/reply into requests.json when it acts.
Only listens on localhost.

    python3 scripts/board/serve_board.py [--dir ~/mwa-board] [--port 8793]
"""
import argparse
import json
import os
import time
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):   # quiet: only errors go to the log
        pass

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/state"):
            d = self.directory
            return self._json(200, {"judgements": load(f"{d}/judgements.json", {}),
                                    "requests": load(f"{d}/requests.json", [])})
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json(400, {"error": "not JSON"})
        d = self.directory
        if self.path == "/api/judgement":
            if not body.get("product"):
                return self._json(400, {"error": "product missing"})
            j = load(f"{d}/judgements.json", {})
            j[body["product"]] = dict(product=body["product"], status=body.get("status", ""),
                                      note=body.get("note", ""), updated=time.strftime("%Y-%m-%dT%H:%M:%S"))
            save(f"{d}/judgements.json", j)
            return self._json(200, j[body["product"]])
        if self.path == "/api/request":
            if not body.get("product") or not body.get("action"):
                return self._json(400, {"error": "product or action missing"})
            r = load(f"{d}/requests.json", [])
            body.update(id=uuid.uuid4().hex[:10], state="open", created=time.strftime("%Y-%m-%dT%H:%M:%S"))
            r.append(body)
            save(f"{d}/requests.json", r)
            return self._json(200, body)
        return self._json(404, {"error": "unknown endpoint"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.expanduser("~/mwa-board"))
    ap.add_argument("--port", type=int, default=8793)
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), partial(Handler, directory=a.dir))
    print(f"MWA image board on http://localhost:{a.port} ({a.dir})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
