"""Pure process-membership decisions for the disposable fixture."""

from dataclasses import dataclass


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
