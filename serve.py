#!/usr/bin/env python3
"""Local preview server for the Bouncy Comet site.

    python serve.py          -> http://localhost:8000
    python serve.py 3000     -> http://localhost:3000

Serves 404.html for missing paths so the real 404 page can be tested.
"""
import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".webp": "image/webp",
    }

    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists("404.html"):
            body = open("404.html", "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


class Server(http.server.ThreadingHTTPServer):
    # Threaded: a browser keep-alive connection must not block other requests.
    daemon_threads = True
    allow_reuse_address = True


with Server(("", PORT), Handler) as httpd:
    print(f"\n  Bouncy Comet -> http://localhost:{PORT}\n  Ctrl+C to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
