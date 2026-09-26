#!/usr/bin/env python3
"""TCP peer-attribution test C2 for agent-work.

Run this OUTSIDE any sandbox, in a plain terminal:

    python3 c2.py [--port 47322]

It listens on 127.0.0.1 only. For each connection it asks the kernel which
process owns the client end of the socket, checks that the owner runs as the
same UID, walks the owner's process ancestry with ps, and reports:

- whether the socket owner is peer.py itself or something else (a proxy)
- which harness processes (claude, codex, agy) appear in the chain
- whether more than one harness appears (a nested harness, which the
  main-session-only rule would reject)
- how long the owner lookup took

Owner lookup:
- Linux: /proc/net/tcp for the socket inode, then a /proc/*/fd scan.
- macOS: lsof. Slow, but fine for a test; a real C2 would use libproc.
"""
import argparse
import datetime
import os
import socket
import subprocess
import sys
import threading
import time

HARNESS_HINTS = ("claude", "codex", "agy", "antigravity")
LAUNCHERS = ("node", "bun", "deno", "python", "python3")
DEFAULT_PORT = int(os.environ.get("AGENTWORK_PORT", "47322"))


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# --- socket owner lookup ----------------------------------------------------

def owners_linux(cport, sport):
    inode, uid = None, None
    with open("/proc/net/tcp") as f:
        next(f)
        for line in f:
            fields = line.split()
            lport = int(fields[1].split(":")[1], 16)
            rport = int(fields[2].split(":")[1], 16)
            if lport == cport and rport == sport:
                uid, inode = int(fields[7]), fields[9]
                break
    if not inode or inode == "0":
        return [], uid
    target = f"socket:[{inode}]"
    owners = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"{fd_dir}/{fd}") == target:
                    owners.append(int(pid))
                    break
            except OSError:
                continue
    return owners, uid


def owners_lsof(cport, sport):
    # -iTCP@host:port matches either end, so the C2's own socket shows up
    # too. Keep only sockets whose LOCAL end is the client's port.
    result = subprocess.run(
        ["lsof", "-w", "-nP", f"-iTCP@127.0.0.1:{cport}", "-F", "pun"],
        capture_output=True,
        text=True,
    )
    want = f"127.0.0.1:{cport}->127.0.0.1:{sport}"
    owners, uid = [], None
    cur_pid, cur_uid = None, None
    for line in result.stdout.splitlines():
        if not line:
            continue
        tag, val = line[0], line[1:]
        if tag == "p":
            cur_pid, cur_uid = int(val), None
        elif tag == "u":
            cur_uid = int(val)
        elif tag == "n" and val == want and cur_pid not in owners:
            owners.append(cur_pid)
            uid = cur_uid
    return owners, uid


def socket_owners(cport, sport):
    if sys.platform.startswith("linux"):
        return owners_linux(cport, sport)
    if sys.platform == "darwin":
        return owners_lsof(cport, sport)
    raise RuntimeError(f"unsupported platform: {sys.platform}")


# --- ancestry ---------------------------------------------------------------

def proc_info(pid):
    result = subprocess.run(
        ["ps", "-ww", "-o", "ppid=", "-o", "args=", "-p", str(pid)],
        capture_output=True,
        text=True,
    )
    out = result.stdout.strip()
    if not out:
        return None, None
    parts = out.split(None, 1)
    return int(parts[0]), (parts[1] if len(parts) > 1 else "")


def ancestry(pid):
    chain, seen = [], set()
    while pid and pid > 1 and pid not in seen:
        seen.add(pid)
        ppid, args = proc_info(pid)
        if ppid is None:
            chain.append((pid, "<exited before lookup>"))
            return chain
        chain.append((pid, args))
        pid = ppid
    if pid == 1:
        _, args = proc_info(1)
        chain.append((1, args or "init/launchd"))
    return chain


def harness_of(args):
    tokens = args.split()
    if not tokens:
        return None
    names = [os.path.basename(tokens[0])]
    if names[0] in LAUNCHERS and len(tokens) > 1:
        names.append(os.path.basename(tokens[1]))
    for name in names:
        for hint in HARNESS_HINTS:
            if name.startswith(hint):
                return hint
    return None


def assess_owner(pid):
    chain = ancestry(pid)
    owner_args = chain[0][1] if chain else ""
    owner_is_peer = "peer.py" in owner_args
    # If the owner is peer.py, skip it so its argv (which holds the label)
    # can't false-match. If it isn't, the owner itself might be a harness
    # acting as a proxy, so include it.
    search = chain[1:] if owner_is_peer else chain
    harnesses = [(p, h) for p, a in search if (h := harness_of(a))]
    return chain, owner_is_peer, harnesses


# --- server -----------------------------------------------------------------

def handle(conn, addr, sport):
    with conn:
        conn.settimeout(10)
        try:
            label = conn.recv(1024).decode(errors="replace").strip()
        except OSError:
            label = ""
        label = label or "<no label>"
        cport = addr[1]

        t0 = time.monotonic()
        try:
            owners, uid = socket_owners(cport, sport)
        except Exception as exc:  # noqa: BLE001 - report anything to the peer
            owners, uid = [], None
            lookup_err = f"{type(exc).__name__}: {exc}"
        else:
            lookup_err = None
        lookup_ms = (time.monotonic() - t0) * 1000

        lines = [f"label={label} client_port={cport} lookup_ms={lookup_ms:.1f}"]
        verdict = None

        if lookup_err:
            verdict = f"REJECT: owner lookup failed ({lookup_err})"
        elif not owners:
            verdict = "REJECT: no owner found for client socket"
        elif uid is not None and uid != os.getuid():
            verdict = f"REJECT: socket owned by uid {uid}, C2 runs as {os.getuid()}"

        resolved = set()
        for pid in owners:
            chain, owner_is_peer, harnesses = assess_owner(pid)
            lines.append(f"owner pid={pid} uid={uid} is_peer_py={owner_is_peer}")
            lines += [f"  {p:>7}  {a}" for p, a in chain]
            if not owner_is_peer:
                lines.append("  NOTE: socket owner is not peer.py (proxied connection?)")
            if not harnesses:
                lines.append("  no harness ancestor")
                resolved.add(None)
            else:
                nearest_pid, nearest = harnesses[0]
                lines.append(f"  nearest harness: {nearest} (pid {nearest_pid})")
                if len(harnesses) > 1:
                    outer = ", ".join(f"{h} (pid {p})" for p, h in harnesses[1:])
                    lines.append(f"  NESTED: also under {outer}")
                resolved.add((nearest_pid, len(harnesses) > 1))

        if verdict is None:
            if None in resolved:
                verdict = "REJECT: no harness ancestor"
            elif len(resolved) > 1:
                verdict = "REJECT: ambiguous, socket holders resolve to different harnesses"
            else:
                (hpid, nested), = resolved
                if nested:
                    verdict = f"REJECT: nested harness (nearest pid {hpid})"
                else:
                    verdict = f"ACCEPT: identity = harness pid {hpid}"

        lines.append(f"VERDICT: {verdict}")
        reply = "\n".join(lines)
        log("\n" + reply)
        try:
            conn.sendall(reply.encode())
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen()
    log(f"c2 listening on tcp:127.0.0.1:{args.port} (pid {os.getpid()}, uid {os.getuid()})")
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(
                target=handle, args=(conn, addr, args.port), daemon=True
            ).start()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()


if __name__ == "__main__":
    main()
