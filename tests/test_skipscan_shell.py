"""Loopback API integration for the pull request scanner."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar, override

import pytest

skipscan_shell = pytest.importorskip("agent_orchestration_poc.shell.skipscan")
run = skipscan_shell.run
run_event = skipscan_shell.run_event


def test_shell_reads_every_surface_on_loopback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Handler(BaseHTTPRequestHandler):
        body_text = "skipped #300"
        created: ClassVar[dict[str, object]] = {}
        updated: ClassVar[dict[str, object]] = {}

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path.endswith("/commits"):
                data: object = [{"sha": "a", "commit": {"message": "Deferred #300"}}]
            elif path.endswith("/reviews"):
                data = [{"body": "Untested #300", "html_url": "review"}]
            elif path.endswith("/comments"):
                data = [{"body": "Skipped #300", "html_url": "comment"}]
            elif self.headers.get("Accept") == "application/vnd.github.v3.diff":
                data = "diff --git a/note.md b/note.md\n@@ -0,0 +1 @@\n+skipped #300\n"
            else:
                data = {"body": self.body_text, "head": {"sha": "current-head"}}
            body = (data if isinstance(data, str) else json.dumps(data)).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            Handler.created = json.loads(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b'{"id":99}')

        def do_PATCH(self) -> None:
            Handler.updated = json.loads(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        assert run(f"http://127.0.0.1:{server.server_port}", "dummy", "o/r", 1) == 0
        assert "0 untracked" in caplog.text
        Handler.body_text = "skipped"
        assert run(f"http://127.0.0.1:{server.server_port}", "dummy", "o/r", 1) == 1
        assert "PR #1 body:1: skipped" in caplog.text
        api = f"http://127.0.0.1:{server.server_port}"
        payload = {"issue": {"number": 1, "pull_request": {"url": "pr"}}}
        assert run_event(api, "dummy", "o/r", "issue_comment", payload) == 1
        assert Handler.created == {
            "name": "skipscan",
            "head_sha": "current-head",
            "status": "in_progress",
        }
        assert Handler.updated == {"status": "completed", "conclusion": "failure"}
        Handler.body_text = "skipped #300"
        assert run_event(api, "dummy", "o/r", "issue_comment", payload) == 0
        assert Handler.updated == {"status": "completed", "conclusion": "success"}
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
