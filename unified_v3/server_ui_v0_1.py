import http.server, urllib.request, urllib.error, json, sys, os

SIDECAR = os.environ.get("SIDECAR_HOST", "http://127.0.0.1:8777")
PORT = int(os.environ.get("UI_PORT", "8778"))
UI_DIR = os.path.dirname(os.path.abspath(__file__))

class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ui": "unified-3", "sidecar": SIDECAR, "status": "ok"})
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy_post(self.path)
        else:
            self.send_error(404)

    def proxy_post(self, path):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            req = urllib.request.Request(
                SIDECAR + path, data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                self.send_response(resp.getcode())
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_json(502, {"error": str(e)})

    def send_json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write("[ui] " + (fmt % args) + "\n")

if __name__ == "__main__":
    # Verify sidecar is reachable
    try:
        req = urllib.request.Request(SIDECAR + "/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            r.read()
    except Exception as e:
        print(f"ERROR: Sidecar not reachable at {SIDECAR}: {e}", file=sys.stderr)
        sys.exit(1)

    with ReusableHTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Unified-3 UI serving on http://127.0.0.1:{PORT}", flush=True)
        httpd.serve_forever()
