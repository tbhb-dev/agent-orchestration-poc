"""Disposable loopback model endpoint with committed, fixed response frames."""

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import cast, override

from agent_orchestration_poc.core.host_socket_attribution import (
    ResponderRequest,
    responder_log,
    responder_reply,
)

FIXTURES = Path(__file__).parent / "fixtures" / "responder"


class Responder(HTTPServer):
    """Single-profile server with no outbound request path."""

    def __init__(self, port: int, profile: str, log_path: Path) -> None:
        super().__init__(("127.0.0.1", port), RequestHandler)
        self.profile = profile
        self.log_path = log_path
        self.tool_served = False
        self.final_served = False


class RequestHandler(BaseHTTPRequestHandler):
    """Serve fixed tool and final frames on the approved model path."""

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
                    responder_log(
                        getattr(self, "command", ""), getattr(self, "path", ""), code
                    )
                )
                + "\n"
            )
        super().send_error(code, message, explain)

    def handle_request(self) -> None:
        """Read bounded input and serve a frame selected by conversation content."""
        server = cast("Responder", self.server)
        port = server.server_address[1]
        request = ResponderRequest(
            self.command,
            self.path,
            self.headers.get("Host", ""),
            port,
            server.profile,
            content_length=self.headers.get("Content-Length", ""),
            transfer_encoding=self.headers.get("Transfer-Encoding", ""),
        )
        status, fixture, classification = responder_reply(request)
        if fixture and self.command == "POST":
            remaining = int(request.content_length)
            chunks: list[bytes] = []
            while remaining:
                received = self.rfile.read(min(remaining, 65536))
                if not received:
                    status, fixture, classification = 400, None, "invalid"
                    break
                chunks.append(received)
                remaining -= len(received)
            if status == 200:
                try:
                    body = json.loads(b"".join(chunks))
                except ValueError, UnicodeDecodeError:
                    status, fixture, classification = 400, None, "invalid"
                else:
                    status, fixture, classification = responder_reply(
                        ResponderRequest(
                            request.method,
                            request.path,
                            request.host,
                            request.port,
                            request.profile,
                            body,
                            server.tool_served,
                            server.final_served,
                            request.content_length,
                            request.transfer_encoding,
                        )
                    )
        with server.log_path.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    responder_log(
                        self.command, self.path, status, fixture, classification
                    )
                )
                + "\n"
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
            if classification == "tool":
                server.tool_served = True
            elif classification == "final":
                server.final_served = True

    do_POST = handle_request  # noqa: N815 - HTTP handler dispatch requires this name.
    do_GET = handle_request  # noqa: N815 - HTTP handler dispatch requires this name.

    def do_HEAD(self) -> None:
        """Answer only the approved Messages probe."""
        self.handle_request()


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
