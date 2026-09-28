"""Exact resume frames and loopback responder integration."""

import http.client
import json
import threading
from pathlib import Path

import pytest

from .lifecycle_core import PROFILES  # pyrefly: ignore[missing-import]
from .resume_responder import FRAMES, load_responder  # pyrefly: ignore[missing-import]


@pytest.mark.parametrize("profile", PROFILES)
def test_resume_frames(profile: str) -> None:
    """Each profile's tool frame checks only its B private marker."""
    data = (FRAMES / f"{profile}-tool.sse").read_text()
    marker = "codex" if profile.startswith("codex-") else "claude"
    expected = f"test -r /private/tmp/bv01-228-{profile}/B/{marker}/private-marker"
    assert expected in data  # noqa: S101 - pytest assertion
    assert "probe.py client" not in data  # noqa: S101 - pytest assertion
    for line in data.splitlines():
        if line.startswith("data: "):
            json.loads(line.removeprefix("data: "))


@pytest.mark.parametrize("profile", PROFILES)
def test_resume_responder_loopback(profile: str, tmp_path: Path) -> None:
    """The reused server sends two frames then refuses a third request."""
    responder = load_responder()
    server = responder.Responder(0, profile, tmp_path / "model.jsonl")
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    path = "/v1/responses" if profile.startswith("codex-") else "/v1/messages"
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        for expected_status, suffix in ((200, "tool"), (200, "final"), (409, None)):
            connection.request("POST", path, body=b"{}")
            reply = connection.getresponse()
            body = reply.read()
            assert reply.status == expected_status  # noqa: S101 - pytest assertion
            if suffix:
                assert body == (FRAMES / f"{profile}-{suffix}.sse").read_bytes()  # noqa: S101 - pytest assertion
        connection.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
