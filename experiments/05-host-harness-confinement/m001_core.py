"""Pure M-001 request and response rules for disposable protocol targets."""

import base64
import hashlib
import json
from typing import Any

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
THREAD = "00000000-0000-4000-8000-000000000242"
MESSAGE = "00000000-0000-4000-8000-000000000243"
QUEUE = "00000000-0000-4000-8000-000000000244"


def websocket_accept(key: str) -> str:
    """Compute the RFC 6455 server accept field from a validated nonce."""
    decoded = base64.b64decode(key, validate=True)
    if len(decoded) != 16:
        raise ValueError("invalid WebSocket key")
    return base64.b64encode(hashlib.sha1(key.encode() + GUID).digest()).decode()  # noqa: S324 - RFC 6455 requires SHA-1 for its handshake, not for security.


def queue_request() -> dict[str, Any]:
    """Build a reproducible JSON-RPC queue add for B's disposable thread."""
    return {
        "id": 2,
        "method": "thread/queue/add",
        "params": {
            "threadId": THREAD,
            "input": [
                {"type": "text", "text": "M-001 disposable probe", "text_elements": []}
            ],
            "clientUserMessageId": MESSAGE,
        },
    }


def queue_response(request: object) -> dict[str, Any]:
    """Accept only the exact probe, so reachability alone cannot pass M-001."""
    if request != queue_request():
        return {
            "id": 2,
            "error": {"code": -32600, "message": "invalid fixture request"},
        }
    return {
        "id": 2,
        "result": {
            "queuedSubmission": {
                "id": QUEUE,
                "input": queue_request()["params"]["input"],
                "clientUserMessageId": MESSAGE,
            }
        },
    }


def cc_frame() -> dict[str, Any]:
    """Build the minimal Claude peer message for B's dummy inbox."""
    return {
        "type": "user",
        "message": {"role": "user", "content": "M-001 disposable probe"},
        "msg_id": MESSAGE,
    }


def cc_result(line: bytes) -> str:
    """Classify a complete NDJSON peer frame without treating connect as a write."""
    try:
        frame = json.loads(line)
    except UnicodeDecodeError, ValueError:
        return "invalid"
    return "accepted" if frame == cc_frame() else "invalid"


def classify(outcome: str) -> str:
    """Keep protocol acceptance, sandbox denial, and missing evidence distinct."""
    if outcome == "accepted":
        return "allowed"
    if outcome in {"PermissionError", "EACCES", "EPERM"}:
        return "blocked"
    return "inconclusive"


def mcp_action(request: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Select a minimal MCP response or one protocol probe without side effects."""
    if "id" not in request:
        return None, None
    call_id = request["id"]
    method = request.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": call_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bv02-m001", "version": "1"},
            },
        }, None
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": call_id,
            "result": {
                "tools": [
                    {
                        "name": name,
                        "description": "Attempt one disposable foreign protocol write",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                    for name in ("probe_queue", "probe_cc_socks")
                ]
            },
        }, None
    if method == "tools/call":
        name = request.get("params", {}).get("name")
        kind = {"probe_queue": "queue", "probe_cc_socks": "cc-socks"}.get(name)
        if kind:
            return None, kind
    return {
        "jsonrpc": "2.0",
        "id": call_id,
        "error": {"code": -32601, "message": "unknown method or tool"},
    }, None
