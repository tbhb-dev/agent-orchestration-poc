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


def upgrade_response(request: bytes) -> bytes:
    """Validate an upgrade request and construct its HTTP response."""
    lines = request.decode("ascii").split("\r\n")
    fields = {
        name.lower(): value
        for line in lines[1:]
        if ": " in line
        for name, value in [line.split(": ", 1)]
    }
    if (
        lines[0] != "GET / HTTP/1.1"
        or fields.get("upgrade", "").lower() != "websocket"
        or fields.get("sec-websocket-version") != "13"
        or fields.get("connection", "").lower() != "upgrade"
    ):
        raise ValueError("invalid WebSocket upgrade")
    accept = websocket_accept(fields["sec-websocket-key"])
    return (
        "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
        + accept
        + "\r\n\r\n"
    ).encode()


def upgrade_request(nonce: str) -> bytes:
    """Construct the client request from a caller-supplied random nonce."""
    return (
        "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: "
        + nonce
        + "\r\nSec-WebSocket-Version: 13\r\n\r\n"
    ).encode()


def valid_upgrade_response(response: bytes, nonce: str) -> bool:
    """Check the target's upgrade and nonce binding."""
    return response.startswith(b"HTTP/1.1 101 ") and (
        f"Sec-WebSocket-Accept: {websocket_accept(nonce)}\r\n".encode() in response
    )


def frame_extension_size(first_two: bytes, masked: bool) -> int:
    """Return the number of extension bytes required by a text frame."""
    first, second = first_two
    if first != 0x81 or bool(second & 0x80) != masked:
        raise ValueError("unexpected WebSocket frame")
    return 2 if second & 0x7F == 126 else 8 if second & 0x7F == 127 else 0


def frame_length(header: bytes, masked: bool) -> int:
    """Decode a minimal RFC 6455 length with the fixture's 4096-byte bound."""
    extension = frame_extension_size(header[:2], masked)
    if len(header) != 2 + extension:
        raise ValueError("invalid WebSocket frame header")
    length = int.from_bytes(header[2:]) if extension else header[1] & 0x7F
    if (
        length > 4096
        or (extension == 2 and length < 126)
        or (extension == 8 and length < 65536)
    ):
        raise ValueError("oversize or nonminimal WebSocket frame")
    return length


def decode_frame(payload: bytes, key: bytes, masked: bool) -> bytes:
    """Unmask a frame payload using a caller-read key."""
    if masked and len(key) != 4 or not masked and key:
        raise ValueError("invalid WebSocket mask")
    return (
        bytes(value ^ key[index % 4] for index, value in enumerate(payload))
        if masked
        else payload
    )


def encode_frame(payload: bytes, key: bytes) -> bytes:
    """Serialize one final text frame using a caller-supplied mask or none."""
    size = len(payload)
    if size > 4096 or len(key) not in (0, 4):
        raise ValueError("oversize WebSocket frame or invalid mask")
    second = 0x80 if key else 0
    prefix = (
        bytes([0x81, second | size])
        if size <= 125
        else bytes([0x81, second | 126]) + size.to_bytes(2)
    )
    return prefix + key + decode_frame(payload, key, bool(key))


def queue_reply(payload: bytes) -> tuple[bytes, str]:
    """Parse a request and serialize the accepted or invalid result."""
    try:
        request = json.loads(payload)
    except UnicodeDecodeError, ValueError:
        request = None
    reply = queue_response(request)
    return json.dumps(
        reply, separators=(",", ":")
    ).encode(), "accepted" if "result" in reply else "invalid"


def queue_client_result(payload: bytes) -> str:
    """Classify a target reply from its plain JSON bytes."""
    try:
        response = json.loads(payload)
    except UnicodeDecodeError, ValueError:
        return "invalid"
    return "accepted" if response == queue_response(queue_request()) else "invalid"


def queue_request_bytes() -> bytes:
    """Serialize the fixed request for a masked client frame."""
    return json.dumps(queue_request(), separators=(",", ":")).encode()


def cc_line() -> bytes:
    """Serialize the fixed Claude peer message as NDJSON."""
    return json.dumps(cc_frame(), separators=(",", ":")).encode() + b"\n"


def mcp_probe_response(call_id: object, outcome: str) -> dict[str, Any]:
    """Construct one MCP tool result from a completed probe outcome."""
    return {
        "jsonrpc": "2.0",
        "id": call_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"outcome": outcome, "classification": classify(outcome)}
                    ),
                }
            ],
            "isError": outcome not in ("accepted", "sent"),
        },
    }


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
