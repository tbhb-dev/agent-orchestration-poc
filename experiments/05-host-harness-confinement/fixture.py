"""Disposable Unix-socket targets, with no real harness or credentials."""

import argparse
import hashlib
import hmac
import json
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ENDPOINTS = ("peer", "enroll", "management", "queue", "cc-socks", "oversight")
REQUIRED = {
    "own-peer": "allowed",
    "workspace-edit": "allowed",
    "other-peer": "blocked",
    "other-socket": "blocked",
    "enroll": "blocked",
    "renew-other": "blocked",
    "management": "blocked",
    "canary-shell": "blocked",
    "canary-native": "blocked",
    "canary-replace": "blocked",
    "key-use": "blocked",
    "writable-parent": "blocked",
    "symlink": "blocked",
    "wrapper-replace": "blocked",
    "launch-input": "blocked",
    "project-settings": "blocked",
    "process-secrets": "blocked",
    "signal": "blocked",
    "debugger": "blocked",
    "settings-edit": "blocked",
    "helper-replace": "blocked",
    "mcp-management": "blocked",
    "plugin-management": "blocked",
    "other-queue-shell": "blocked",
    "other-queue-mcp": "blocked",
    "other-queue-hook": "blocked",
    "other-queue-project-server": "blocked",
    "other-cc-socks-shell": "blocked",
    "other-cc-socks-mcp": "blocked",
    "other-cc-socks-hook": "blocked",
    "other-cc-socks-project-server": "blocked",
    "operator-key": "blocked",
    "operator-socket": "blocked",
    "oversight": "blocked",
    "unsandboxed-path": "blocked",
    "sandbox-init-failure": "blocked",
}


def socket_path(root: Path, workload: str, endpoint: str) -> Path:
    """Return a target path without opening it or consulting host state."""
    if workload not in ("A", "B") or endpoint not in ENDPOINTS:
        raise ValueError("unknown disposable target")
    return root / workload / f"{endpoint}.sock"


def socket_result(response: dict[str, str], workload: str, endpoint: str) -> str:
    """Classify a response from a disposable target."""
    return (
        "allowed"
        if response == {"wrapper": workload, "endpoint": endpoint}
        else "inconclusive"
    )


def failure_result(error_name: str) -> str:
    """Retain the failure class without calling every failure a denial."""
    return f"inconclusive:{error_name}"


def profile_status(results: dict[str, str]) -> str:
    """Qualify only a complete matrix of observed allows and denials."""
    if not REQUIRED.keys() <= results.keys():
        return "incomplete"
    return (
        "qualified"
        if all(results[key] == value for key, value in REQUIRED.items())
        else "unsupported"
    )


def serve(root: Path, workload: str) -> None:
    """Bind only sockets inside one disposable wrapper directory."""
    listeners: list[socket.socket] = []
    for endpoint in ENDPOINTS:
        target = socket_path(root, workload, endpoint)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(target))
        server.listen(1)
        server.settimeout(0.2)
        listeners.append(server)
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    try:
        while running:
            for endpoint, server in zip(ENDPOINTS, listeners, strict=True):
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    continue
                with connection:
                    connection.sendall(
                        json.dumps({"wrapper": workload, "endpoint": endpoint}).encode()
                    )
    finally:
        for server in listeners:
            server.close()


def connect(target: Path) -> dict[str, str]:
    """Return the disposable endpoint identity reached by a client."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(1)
        client.connect(str(target))
        response = client.recv(256)
    result: dict[str, str] = json.loads(response)
    return result


def baseline() -> None:
    """Show target reachability from this worker's current execution path."""
    with tempfile.TemporaryDirectory(
        prefix="bv02-242-", dir="/private/tmp"
    ) as temporary:
        root = Path(temporary)
        for workload in ("A", "B"):
            (root / workload).mkdir(mode=0o700)
        canary = root / "B" / "canary.key"
        canary.write_bytes(secrets.token_bytes(32))
        canary.chmod(0o600)
        config = root / "B" / "wrapper.conf"
        config.write_text("disposable=true\n")
        config.chmod(0o600)
        children = [
            subprocess.Popen([sys.executable, __file__, "serve", str(root), workload])
            for workload in ("A", "B")
        ]
        try:
            for _ in range(50):
                if all(socket_path(root, name, "peer").exists() for name in ("A", "B")):
                    break
                time.sleep(0.02)
            for workload, endpoint in (
                ("A", "peer"),
                ("B", "peer"),
                ("B", "enroll"),
                ("B", "management"),
                ("B", "queue"),
                ("B", "cc-socks"),
                ("B", "oversight"),
            ):
                target = socket_path(root, workload, endpoint)
                try:
                    reached = connect(target)
                    status = socket_result(reached, workload, endpoint)
                except OSError as error:
                    status = failure_result(type(error).__name__)
                print(
                    json.dumps({"target": f"{workload}/{endpoint}", "result": status})
                )
            key = canary.read_bytes()
            digest = hmac.digest(key, b"probe", hashlib.sha256)
            print(
                json.dumps(
                    {
                        "target": "B/canary",
                        "read_bytes": len(key),
                        "digest_bytes": len(digest),
                    }
                )
            )
            config.write_text("replacement=disposable\n")
            print(json.dumps({"target": "B/wrapper.conf", "after": config.read_text()}))
        finally:
            for child in children:
                child.terminate()
            for child in children:
                child.wait(timeout=3)
    print(json.dumps({"cleanup": not root.exists()}))


def main() -> None:
    """Run the baseline or one wrapper process."""
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("baseline", "serve", "connect"))
    parser.add_argument("path", nargs="?")
    parser.add_argument("workload", nargs="?")
    args = parser.parse_args()
    if args.action == "baseline":
        baseline()
    elif args.action == "serve":
        if args.path is None or args.workload is None:
            parser.error("serve requires root and workload")
        serve(Path(args.path), args.workload)
    else:
        if args.path is None:
            parser.error("connect requires a socket path")
        print(json.dumps(connect(Path(args.path))))


if __name__ == "__main__":
    main()
