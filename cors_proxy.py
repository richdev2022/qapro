#!/usr/bin/env python3
"""
cors_proxy.py — a tiny zero-dependency CORS proxy AND UI server for the
API Tester web app.

Run it once and open http://localhost:8787/ in a browser — the tester UI
(index.html) is served from the same process, so the browser's proxy requests
to /api/proxy (or /?url=) are same-origin (no CORS preflight at all). Any
request the browser sends with `?url=<target>` is forwarded to the real API
with its method, headers and body intact, and the response is returned with
`Access-Control-Allow-Origin: *`. This is what lets the visual tester show
live responses from APIs (like Prestmit) that do not send CORS headers
themselves.

This is the local-development counterpart of the deployed `api/proxy.mjs`
Vercel function; both expose the same `?url=<target>` contract so the UI works
identically locally and on Vercel.

Usage:
    python3 cors_proxy.py            # serves UI + proxy on http://localhost:8787
    python3 cors_proxy.py 9000       # custom port

The browser then calls:
    http://localhost:8787/?url=<URL-encoded target URL>

Security: binds to 127.0.0.1 only (your machine), prints every request it
forwards, and forwards your headers (including API keys) ONLY to the target URL
you specify. It never logs header values.
"""

import http.server
import socketserver
import urllib.parse
import urllib.request
import urllib.error
import sys
import os
import json

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787

# Headers we must not blindly copy from the client or from the upstream.
HOP_BY_HOP = {
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "upgrade",
}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Concise one-line log; never log header values.
        sys.stdout.write(f"[{self.address_string()}] {self.command} {self.path}\n")
        sys.stdout.flush()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def _serve_static(self, name, content_type):
        """Serve a file shipped alongside this script (e.g. api-tester.html).
        Looks next to cors_proxy.py first, then in the current working dir.
        Returns True if a response was sent, None if the file was not found."""
        here = os.path.dirname(os.path.abspath(__file__))
        for d in (here, os.getcwd()):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except OSError:
                    return None
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self._cors_headers()
                self.end_headers()
                if self.command != "HEAD":
                    try:
                        self.wfile.write(data)
                    except BrokenPipeError:
                        pass
                return True
        return None

    def do_OPTIONS(self):
        # Browser CORS preflight — answer immediately.
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _handle(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        target = qs.get("url", [None])[0]
        if not target:
            # Serve the API Tester UI at the root, so running this script is a
            # one-command launch: `python3 cors_proxy.py` then open
            # http://localhost:<PORT>/ in a browser. When the UI is served from
            # here, its proxy requests back to this same origin are same-origin
            # (no CORS preflight needed at all). The /api/proxy path the
            # deployed (Vercel) app uses also works here, since this handler
            # reads the ?url= query and ignores the path.
            if self._serve_static("index.html", "text/html; charset=utf-8") is not None:
                return
            # Fall back to a tiny landing page if the HTML file is missing.
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(LANDING.encode("utf-8"))
            return

        # Read request body (for POST/PUT/PATCH).
        body = None
        length = int(self.headers.get("Content-Length") or 0)
        if length > 0:
            body = self.rfile.read(length)

        # Copy client headers through to the target, dropping hop-by-hop ones
        # and the proxy-only "Origin" header.
        fwd_headers = {}
        for k, v in self.headers.items():
            if k.lower() in HOP_BY_HOP or k.lower() == "origin":
                continue
            fwd_headers[k] = v

        req = urllib.request.Request(target, data=body, method=self.command,
                                     headers=fwd_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status = resp.getcode()
                resp_body = resp.read()
                resp_headers = list(resp.getheaders())
        except urllib.error.HTTPError as e:
            status = e.code
            resp_body = e.read()
            resp_headers = list(e.headers.items()) if e.headers else []
        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(
                {"error": "upstream unreachable", "detail": str(e.reason)}
            ).encode("utf-8"))
            return
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(
                {"error": "proxy error", "detail": str(e)}
            ).encode("utf-8"))
            return

        # Relay upstream status + body back to the browser, with CORS headers
        # and the upstream response headers exposed.
        self.send_response(status)
        for k, v in resp_headers:
            if k.lower() in HOP_BY_HOP:
                continue
            self.send_header(k, v)
        self._cors_headers()
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(resp_body)
            except BrokenPipeError:
                pass

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle
    do_DELETE = _handle
    do_HEAD = _handle


LANDING = """<!doctype html><html><head><meta charset='utf-8'><title>CORS Proxy</title>
<style>body{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e9ef;padding:40px;line-height:1.6}
code{background:#1d2330;padding:2px 6px;border-radius:4px}</style></head>
<body><h1>✅ CORS proxy running</h1>
<p>Switch back to the <strong>API Tester</strong> tab, enable the <strong>CORS / Proxy</strong>
toggle, pick <strong>Local proxy</strong>, and hit <strong>Send</strong>.</p>
<p>Forwarding pattern: <code>http://localhost:%PORT%/?url=&lt;encoded target&gt;</code></p>
<p>Every request is logged in this terminal. Stop with <code>Ctrl+C</code>.</p>
</body></html>""".replace("%PORT%", str(PORT))


class ReuseTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ReuseTCPServer(("127.0.0.1", PORT), Handler)
    print(f"CORS proxy + API Tester UI listening on http://localhost:{PORT}/", flush=True)
    print("Open that URL in a browser; in the app enable the CORS/Proxy toggle", flush=True)
    print("(Local proxy is pre-selected) and hit Send.", flush=True)
    print("Press Ctrl+C to stop.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
