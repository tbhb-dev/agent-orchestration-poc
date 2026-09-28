"""Disposable loopback model endpoint with committed, fixed response frames."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast, override

from agent_orchestration_poc.core.host_socket_attribution import (
    ResponderRequest,
    logged_path,
    responder_reply,
)

FIXTURES = Path(__file__).parent / "fixtures" / "responder"


class Responder(HTTPServer):
    """Single-profile server with no outbound request path."""

    def __init__(self, port: int, profile: str, log_path: Path) -> None:
        super().__init__(("127.0.0.1", port), RequestHandler)
        self.profile = profile
        self.log_path = log_path
        self.completed = 0


class RequestHandler(BaseHTTPRequestHandler):
    """Serve at most one tool call and one final frame."""

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Suppress default request and header logging."""

    @override
    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        """Record rejected methods and malformed requests without request content."""
        server = cast("Responder", self.server)
        with server.log_path.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {"path": logged_path(getattr(self, "path", "")), "status": code}
                )
                + "\n"
            )
        super().send_error(code, message, explain)

    def handle_request(self) -> None:
        """Reject any request outside the fixed path, host, method, and sequence."""
        server = cast("Responder", self.server)
        port = server.server_address[1]
        status, fixture = responder_reply(
            ResponderRequest(
                self.command,
                self.path,
                self.headers.get("Host", ""),
                port,
                server.profile,
                server.completed,
                self.headers.get("Content-Length", ""),
                self.headers.get("Transfer-Encoding", ""),
            )
        )
        if fixture:
            remaining = int(self.headers["Content-Length"])
            while remaining:
                received = self.rfile.read(min(remaining, 65536))
                if not received:
                    status, fixture = 400, None
                    break
                remaining -= len(received)
        with server.log_path.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps({"path": logged_path(self.path), "status": status}) + "\n"
            )
        body = (FIXTURES / fixture).read_bytes() if fixture else b""
        self.send_response(status)
        self.send_header(
            "Content-Type", "text/event-stream" if fixture else "text/plain"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if body:
            self.wfile.write(body)
            server.completed += 1

    do_POST = handle_request  # noqa: N815 - HTTP handler dispatch requires this name.
    do_GET = handle_request  # noqa: N815 - HTTP handler dispatch requires this name.


def main() -> None:
    """Start a loopback listener and print only its address and process ID."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=["127.0.0.1"], required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--profile",
        choices=[
            "codex-interactive",
            "codex-headless",
            "claude-interactive",
            "claude-headless",
        ],
        required=True,
    )
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    with Responder(args.port, args.profile, args.log) as server:
        print(
            json.dumps(
                {
                    "host": "127.0.0.1",
                    "port": server.server_address[1],
                    "pid": os.getpid(),
                }
            ),
            flush=True,
        )
        server.serve_forever()


if __name__ == "__main__":
    main()
