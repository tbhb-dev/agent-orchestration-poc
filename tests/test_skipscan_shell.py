"""Loopback API integration for the pull request scanner."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar, override
from urllib.parse import parse_qs, urlsplit

import pytest

skipscan_shell = pytest.importorskip("agent_orchestration_poc.shell.skipscan")
run = skipscan_shell.run
run_event = skipscan_shell.run_event


class Handler(BaseHTTPRequestHandler):
    surface = "body"
    untracked = False
    created: ClassVar[dict[str, object]] = {}
    updated: ClassVar[dict[str, object]] = {}

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        text = "skipped" if Handler.untracked else "skipped #300"
        selected = text if Handler.surface == "commit" else "skipped #300"
        page = int(parse_qs(urlsplit(self.path).query).get("page", ["1"])[0])
        if path.endswith("/pulls"):
            data: object = [
                {"number": 1, "head": {"repo": {"full_name": "fork/r"}, "ref": "topic"}}
            ]
        elif path.endswith("/commits"):
            data = [{"sha": "a", "commit": {"message": selected}}]
        elif path.endswith("/reviews"):
            data = [
                {
                    "body": text if Handler.surface == "review" else "skipped #300",
                    "html_url": "review",
                }
            ]
        elif path.endswith("/comments"):
            kind = "discussion" if "/issues/" in path else "inline"
            data = [
                {
                    "body": text if Handler.surface == kind else "skipped #300",
                    "html_url": kind,
                }
            ]
        elif self.headers.get("Accept") == "application/vnd.github.v3.diff":
            line = text if Handler.surface == "diff" else "skipped #300"
            data = f"diff --git a/note.md b/note.md\n@@ -0,0 +1 @@\n+{line}\n"
        else:
            data = {
                "body": text if Handler.surface == "body" else "skipped #300",
                "head": {"sha": "current-head"},
                "commits": 101,
            }
        if isinstance(data, list) and not path.endswith("/pulls"):
            filler = [
                {
                    "body": "ordinary",
                    "html_url": "filler",
                    "sha": "filler",
                    "commit": {"message": "ordinary"},
                }
            ] * 100
            data = filler if page == 1 else data
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


@pytest.mark.socket
@pytest.mark.parametrize(
    "surface", ["body", "inline", "discussion", "review", "commit", "diff"]
)
def test_shell_reads_every_surface_on_loopback(
    surface: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    Handler.surface = surface
    Handler.untracked = False
    server = HTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        assert run(f"http://127.0.0.1:{server.server_port}", "dummy", "o/r", 1) == 0
        assert "0 untracked" in caplog.text
        Handler.untracked = True
        assert run(f"http://127.0.0.1:{server.server_port}", "dummy", "o/r", 1) == 1
        source = {
            "body": "PR #1 body",
            "inline": "inline",
            "discussion": "discussion",
            "review": "review",
            "commit": "commit a",
            "diff": "PR #1:note.md",
        }[surface]
        assert f"{source}:1: skipped" in caplog.text
        api = f"http://127.0.0.1:{server.server_port}"
        payload = {"issue": {"number": 1, "pull_request": {"url": "pr"}}}
        assert run_event(api, "dummy", "o/r", "issue_comment", payload) == 1
        assert Handler.created == {
            "name": "skipscan",
            "head_sha": "current-head",
            "status": "in_progress",
        }
        assert Handler.updated == {"status": "completed", "conclusion": "failure"}
        Handler.untracked = False
        assert run_event(api, "dummy", "o/r", "issue_comment", payload) == 0
        assert Handler.updated == {"status": "completed", "conclusion": "success"}
        workflow_payload: dict[str, Any] = {
            "workflow_run": {
                "head_repository": {"full_name": "fork/r"},
                "head_branch": "topic",
                "pull_requests": [],
            }
        }
        Handler.untracked = True
        assert run_event(api, "dummy", "o/r", "workflow_run", workflow_payload) == 1
        assert Handler.created["head_sha"] == "current-head"
        assert Handler.updated == {"status": "completed", "conclusion": "failure"}
        Handler.untracked = False
        assert run_event(api, "dummy", "o/r", "workflow_run", workflow_payload) == 0
        assert Handler.updated == {"status": "completed", "conclusion": "success"}
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


def test_commit_endpoint_ceiling_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    commits = [{"sha": str(i), "commit": {"message": "ordinary"}} for i in range(250)]
    commits.append({"sha": "250", "commit": {"message": "skipped"}})

    def get(url: str, token: str, accept: str = "") -> str:
        if "/commits?" in url:
            page = int(url.rsplit("page=", 1)[1])
            return json.dumps(commits[:250][(page - 1) * 100 : page * 100])
        if "?" in url:
            return "[]"
        if accept:
            return ""
        return json.dumps({"body": "", "commits": len(commits)})

    monkeypatch.setattr(skipscan_shell, "_get", get)
    with pytest.raises(ValueError, match="Incomplete commit scan"):
        run("https://api.github.com", "dummy", "o/r", 1)
