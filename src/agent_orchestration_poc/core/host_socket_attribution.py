"""Pure process-membership decisions for the disposable fixture."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Process:
    """Snapshot of one process and its parent."""

    pid: int
    ppid: int
    start_us: int


@dataclass(frozen=True)
class Peer:
    """Kernel peer identity observed at a request boundary."""

    pid: int
    pidversion: int
    accepted_us: int


@dataclass(frozen=True)
class ResponderRequest:
    """Values needed to select a fixed local model response."""

    method: str
    path: str
    host: str
    port: int
    profile: str
    completed: int
    content_length: str = "0"
    transfer_encoding: str = ""


def membership(peer: Peer, root: Process, observed: dict[int, Process]) -> str:
    """Decide ancestry from value snapshots, rejecting missing or stale links."""
    seen: set[int] = set()
    pid = peer.pid
    while pid not in seen:
        seen.add(pid)
        process = observed.get(pid)
        if process is None or process.start_us > peer.accepted_us:
            return "unknown"
        if pid == root.pid:
            return "allowed" if process.start_us == root.start_us else "stale"
        pid = process.ppid
    return "unknown"


def peer_stable(initial: Peer, after_read: Peer) -> bool:
    """Require the kernel's process instance to agree across a request read."""
    return (initial.pid, initial.pidversion) == (after_read.pid, after_read.pidversion)


def request_record(
    connection_id: str,
    case_tag: str,
    peers: tuple[Peer, Peer],
    root: Process,
    observed: dict[int, Process],
) -> dict[str, object]:
    """Turn kernel snapshots into one diagnostic request record."""
    before, after = peers
    decision = (
        membership(after, root, observed)
        if peer_stable(before, after)
        else "changed-peer"
    )
    return {
        "connection_id": connection_id,
        "case_tag": case_tag,
        "initial": asdict(before),
        "peer": asdict(after),
        "root": asdict(root),
        "observed": [asdict(process) for process in observed.values()],
        "decision": decision,
    }


def responder_reply(request: ResponderRequest) -> tuple[int, str | None]:
    """Select only the next fixed fixture for an exact loopback request."""
    if request.profile not in {
        "codex-interactive",
        "codex-headless",
        "claude-interactive",
        "claude-headless",
    }:
        return 400, None
    if request.profile.startswith("claude-") and request.method == "HEAD":
        return (
            (200, None)
            if request.path == "/v1/messages"
            and request.host == f"127.0.0.1:{request.port}"
            else (403, None)
        )
    expected_paths = (
        ("/v1/responses",)
        if request.profile.startswith("codex-")
        else ("/v1/messages", "/v1/messages?beta=true")
    )
    if (
        request.method != "POST"
        or request.path not in expected_paths
        or request.host != f"127.0.0.1:{request.port}"
    ):
        return 403, None
    if (
        request.transfer_encoding
        or not request.content_length.isascii()
        or not request.content_length.isdecimal()
        or len(request.content_length) > 7
        or int(request.content_length) > 2_000_000
    ):
        return 403, None
    if request.completed not in (0, 1):
        return 409, None
    return 200, f"{request.profile}-{'tool' if request.completed == 0 else 'final'}.sse"


def responder_log(method: str, path: str, status: int) -> dict[str, str | int]:
    """Record the request line and result without headers or body values."""
    return {"method": method, "path": path, "status": status}
