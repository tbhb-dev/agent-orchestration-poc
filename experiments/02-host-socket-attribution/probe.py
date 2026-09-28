"""Disposable macOS Unix-socket attribution probe."""

import argparse
import ctypes
import json
import os
import runpy
import socket
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

core = runpy.run_path(str(Path(__file__).with_name("attribution_core.py")))
Process = core["Process"]
Peer = core["Peer"]
membership = core["membership"]
peer_stable = core["peer_stable"]


class AuditToken(ctypes.Structure):
    _fields_ = [("val", ctypes.c_uint32 * 8)]


class BSDInfo(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("status", ctypes.c_uint32),
        ("xstatus", ctypes.c_uint32),
        ("pid", ctypes.c_uint32),
        ("ppid", ctypes.c_uint32),
        ("uid", ctypes.c_uint32),
        ("gid", ctypes.c_uint32),
        ("ruid", ctypes.c_uint32),
        ("rgid", ctypes.c_uint32),
        ("svuid", ctypes.c_uint32),
        ("svgid", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("comm", ctypes.c_char * 16),
        ("name", ctypes.c_char * 32),
        ("nfiles", ctypes.c_uint32),
        ("pgid", ctypes.c_uint32),
        ("pjobc", ctypes.c_uint32),
        ("tdev", ctypes.c_uint32),
        ("tpgid", ctypes.c_uint32),
        ("nice", ctypes.c_int32),
        ("start_sec", ctypes.c_uint64),
        ("start_usec", ctypes.c_uint64),
    ]


def process_info(pid: int) -> Process | None:
    """Read one live process through libproc, failing closed on exit or denial."""
    libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
    libproc.proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    libproc.proc_pidinfo.restype = ctypes.c_int
    info = BSDInfo()
    size = ctypes.sizeof(info)
    if libproc.proc_pidinfo(pid, 3, 0, ctypes.byref(info), size) != size:
        return None
    return Process(
        pid=info.pid,
        ppid=info.ppid,
        start_us=info.start_sec * 1_000_000 + info.start_usec,
    )


def peer_info(conn: socket.socket, accepted_us: int) -> Peer:
    """Read the connecting task's opaque audit token from the kernel."""
    raw = conn.getsockopt(0, 6, ctypes.sizeof(AuditToken))
    token = AuditToken.from_buffer_copy(raw)
    bsm = ctypes.CDLL("/usr/lib/libbsm.dylib")
    bsm.audit_token_to_pid.argtypes = [AuditToken]
    bsm.audit_token_to_pid.restype = ctypes.c_int
    bsm.audit_token_to_pidversion.argtypes = [AuditToken]
    bsm.audit_token_to_pidversion.restype = ctypes.c_int
    return Peer(
        bsm.audit_token_to_pid(token), bsm.audit_token_to_pidversion(token), accepted_us
    )


def ancestry(pid: int) -> dict[int, Process]:
    """Read a bounded parent chain from the current process table."""
    result: dict[int, Process] = {}
    while pid > 1 and pid not in result:
        process = process_info(pid)
        if process is None:
            break
        result[pid] = process
        pid = process.ppid
    return result


def serve(socket_path: Path, root_pid: int, count: int) -> None:
    """Serve a fixed number of disposable requests and emit redacted JSON."""
    root = process_info(root_pid)
    if root is None:
        raise RuntimeError("launch root is absent")
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(socket_path))
        listener.listen(count)
        for _ in range(count):
            conn, _ = listener.accept()
            accepted_us = time.time_ns() // 1_000
            with conn:
                initial = peer_info(conn, accepted_us)
                request = conn.recv(512).decode()
                peer = peer_info(conn, time.time_ns() // 1_000)
                observed = ancestry(peer.pid)
                decision = (
                    membership(peer, root, observed)
                    if peer_stable(initial, peer)
                    else "changed-peer"
                )
                conn.sendall(decision.encode())
                print(
                    json.dumps(
                        {
                            "initial": asdict(initial),
                            "peer": asdict(peer),
                            "root": asdict(root),
                            "observed": [asdict(p) for p in observed.values()],
                            "claim": request,
                            "decision": decision,
                        }
                    ),
                    flush=True,
                )
    socket_path.unlink()


def client(socket_path: Path, claim: str) -> None:
    """Send one untrusted claim to a disposable gateway."""
    with socket.socket(socket.AF_UNIX) as conn:
        conn.connect(str(socket_path))
        conn.sendall(claim.encode())
        print(conn.recv(512).decode(), flush=True)


def root_loop() -> None:
    """Act as one fixture launch root, with no operator control path."""
    print(os.getpid(), flush=True)
    for line in sys.stdin:
        path, claim, mode = json.loads(line)
        argv = [sys.executable, __file__, "client", path, claim]
        if mode == "nested":
            argv = [sys.executable, __file__, "relay", path, claim]
        if mode == "exit-parent":
            subprocess.Popen([*argv, "200"], stdout=subprocess.DEVNULL)
            return
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            start_new_session=mode == "detached",
        )
        print(
            json.dumps(
                {
                    "exit": result.returncode,
                    "reply": result.stdout.strip(),
                    "error": result.stderr.strip(),
                }
            ),
            flush=True,
        )


def relay(socket_path: Path, claim: str) -> None:
    """Make one extra process generation before the actual socket client."""
    subprocess.run(
        [sys.executable, __file__, "client", str(socket_path), claim], check=True
    )


def transfer(socket_path: Path) -> None:
    """Pass a connected descriptor to a successor and exit before it writes."""
    with socket.socket(socket.AF_UNIX) as conn:
        conn.connect(str(socket_path))
        child = subprocess.Popen(
            [sys.executable, __file__, "inherited", str(conn.fileno())],
            pass_fds=(conn.fileno(),),
            stdout=subprocess.DEVNULL,
        )
        print(child.pid, flush=True)


def inherited(fd: int) -> None:
    """Write on the original connection after the connecting process exits."""
    time.sleep(0.2)
    with socket.socket(fileno=fd) as conn:
        conn.sendall(b"held")
        time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=[
            "server",
            "client",
            "inspect",
            "root",
            "relay",
            "transfer",
            "inherited",
        ],
    )
    parser.add_argument("path", nargs="?", default="")
    parser.add_argument("value", nargs="?", default="")
    parser.add_argument("count", nargs="?", type=int, default=1)
    args = parser.parse_args()
    if args.mode == "server":
        serve(Path(args.path), int(args.value), args.count)
    elif args.mode == "client":
        time.sleep(args.count / 1_000 if args.count > 1 else 0)
        client(Path(args.path), args.value)
    elif args.mode == "root":
        root_loop()
    elif args.mode == "relay":
        relay(Path(args.path), args.value)
    elif args.mode == "transfer":
        transfer(Path(args.path))
    elif args.mode == "inherited":
        inherited(int(args.path))
    else:
        process = process_info(os.getpid())
        if process is None:
            raise RuntimeError("self process absent")
        print(json.dumps(asdict(process)))


if __name__ == "__main__":
    main()
