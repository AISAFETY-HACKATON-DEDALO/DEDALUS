"""Loopback-only HTTP adapter. Credentials are never exposed by an HTTP endpoint."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json

from .core import Lab


def make_server(lab, port=0):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def handle_request(self):
            host = self.headers.get("Host", "")
            expected = f"127.0.0.1:{self.server.server_port}"
            if host != expected or self.headers.get("Origin") is not None:
                status, body = 403, {"error": "local_client_required"}
            else:
                auth = self.headers.get("Authorization", "")
                token = auth[7:] if auth.startswith("Bearer ") else ""
                status, body = lab.request(self.command, self.path, token)
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        do_GET = handle_request
        do_POST = handle_request
        do_DELETE = handle_request

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="DEDALO local synthetic laboratory")
    parser.add_argument("--mode", choices=Lab.MODES, default="maze")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    lab = Lab(args.mode)
    with make_server(lab, args.port) as server:
        print(f"Local laboratory: http://127.0.0.1:{server.server_port}")
        print("Temporary synthetic session credentials (do not publish):")
        print(json.dumps(lab.credentials, indent=2))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
