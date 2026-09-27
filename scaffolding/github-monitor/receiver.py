"""Temporary #167 ingress, replaced by permanent #189 and #190."""
# ruff: noqa: INP001, PLR0911

import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import override

from state import classify_delivery, signature_result
from store import Store

MAX_BODY = 25 * 1024 * 1024
MAX_HEADERS = 16 * 1024
GUID = re.compile(r"[0-9a-fA-F-]{36}\Z")


class Handler(BaseHTTPRequestHandler):
    """Accept one verified GitHub webhook route."""

    store: Store
    secret: bytes
    installation_id: int
    request_timeout = 5.0

    @override
    def setup(self) -> None:
        """Bound request-line and header reads before the parser starts."""
        self.request.settimeout(self.request_timeout)
        super().setup()

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Avoid logging untrusted paths, headers, and payloads."""
        del format, args

    def _reply(self, status: int) -> None:
        self.send_response(status)
        self.send_header("X-Local-Monitor-Schema", "1")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        """Reject reads while allowing the local CLI to identify this listener."""
        self._reply(405)

    def do_POST(self) -> None:
        """Verify bytes before parsing, then acknowledge only committed receipts."""
        if self.path != "/hooks/github":
            self._reply(404)
            return
        self._post_hook()

    def _post_hook(self) -> None:
        """Handle the one allowed route."""
        size = sum(len(key) + len(value) for key, value in self.headers.items())
        length_header = self.headers.get("Content-Length", "")
        if (
            size > MAX_HEADERS
            or len(length_header) > 8
            or not length_header.isdecimal()
        ):
            self._reply(400)
            return
        length = int(length_header)
        if length > MAX_BODY or self.headers.get("Transfer-Encoding"):
            self._reply(413)
            return
        try:
            body = self.rfile.read(length)
        except TimeoutError:
            self._reply(408)
            return
        if len(body) != length:
            self._reply(400)
            return
        result = signature_result(
            self.headers.get("X-Hub-Signature-256"), body, self.secret
        )
        if result != "valid":
            try:
                self.store.count(result)
            except sqlite3.Error, OSError:
                self._reply(503)
                return
            self._reply(401)
            return
        guid = self.headers.get("X-GitHub-Delivery", "")
        event = self.headers.get("X-GitHub-Event", "")
        if (
            not GUID.fullmatch(guid)
            or not event
            or self.headers.get_content_type() != "application/json"
        ):
            self._reply(400)
            return
        try:
            invalidations = classify_delivery(event, body, self.installation_id)
        except ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError:
            self._reply(422)
            return
        try:
            outcome = self.store.receive(guid, event, body, invalidations)
        except sqlite3.Error, OSError:
            self._reply(503)
            return
        self._reply(409 if outcome == "changed_guid" else 202)


def serve(store: Store, secret: bytes, installation_id: int) -> None:
    """Block in the foreground until SIGTERM or Ctrl-C."""
    handler = type(
        "ConfiguredHandler",
        (Handler,),
        {"store": store, "secret": secret, "installation_id": installation_id},
    )
    server = HTTPServer(("127.0.0.1", 8787), handler)
    store.restart()
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
