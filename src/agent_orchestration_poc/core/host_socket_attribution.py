"""Pure decisions for the disposable host-socket fixture."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast


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
            if request.path in {"/v1/messages", "/api/hello"}
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


def codex_config(home: Path, python: Path, port: int) -> str:
    """Build the disposable Codex profile and exact read grants."""
    workspace = home / "workspace"
    return f'''model_provider = "bv01"
default_permissions = "bv01"
check_for_update_on_startup = false
[features]
plugins = false
[projects."{workspace}"]
trust_level = "trusted"
[model_providers.bv01]
name = "bv01"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
env_key = "BV01_FAKE_OPENAI_KEY"
[permissions.bv01.filesystem]
"{workspace}" = "read"
"{python.parent.parent}" = "read"
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"{home}/gateway.sock" = "allow"
[tui]
screen_reader_detection_done = true
'''


def claude_trust(workspace: Path) -> dict[str, object]:
    """Seed first-run and workspace trust for a disposable home."""
    return {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "projects": {str(workspace): {"hasTrustDialogAccepted": True}},
    }


def claude_settings(home: Path) -> dict[str, object]:
    """Allow only this cell's gateway in the Claude sandbox."""
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "network": {
                "allowUnixSockets": [str(home / "gateway.sock")],
                "allowAllUnixSockets": False,
                "allowLocalBinding": False,
            },
            "allowUnsandboxedCommands": False,
        }
    }


def empty_input_prompt(pane: str, marker: str) -> bool:
    """Match an empty TUI composer, not a selected dialog option."""
    ready = {marker}
    if marker == "›":
        ready.add("› Ask Codex to do anything")
    return any(
        line.strip() in ready
        or (
            marker == "❯"
            and line.strip().startswith('❯ Try "')
            and line.strip().endswith('"')
        )
        for line in pane.splitlines()
    )


def launch_command(
    profile: str, port: int, home: Path, binaries: tuple[Path, Path, Path]
) -> tuple[list[str], dict[str, str]]:
    """Return the pinned harness argv and empty-home environment."""
    codex, claude, python = binaries
    workspace = home / "workspace"
    env = {
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "PYTHONPATH": str(workspace),
        "PATH": f"{python.parent}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "TERM": "xterm-256color",
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
        "PYTHONUNBUFFERED": "1",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    prompt = (
        "Run python3 experiments/02-host-socket-attribution/probe.py client "
        f"{home}/gateway.sock {profile} and then stop."
    )
    if profile.startswith("codex-"):
        env.update(
            CODEX_HOME=str(home / "codex"), BV01_FAKE_OPENAI_KEY="not-a-real-key"
        )
        argv = [str(codex)]
        if profile.endswith("headless"):
            argv += ["exec", "--ephemeral", "--skip-git-repo-check"]
        argv += ["-C", str(workspace), "-c", "approval_policy=never"]
        if profile.endswith("headless"):
            argv.append(prompt)
    else:
        env.update(
            CLAUDE_CONFIG_DIR=str(home / "claude"),
            ANTHROPIC_API_KEY="not-a-real-key",
            ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}",
            CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        )
        argv = [
            str(claude),
            "--bare",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--settings",
            str(home / "settings.json"),
        ]
        if profile.endswith("headless"):
            argv += [
                "--print",
                "--no-session-persistence",
                "--permission-prompts",
                "none",
                prompt,
            ]
    return argv, env


def relay_result(
    rows: list[dict[str, object]],
    requests: list[dict[str, object]],
    harness_exit: int | None,
) -> str:
    """Require an accepted model path and one connector request."""
    if any(row["status"] != 200 for row in rows):
        raise ValueError("responder refused a request")
    if len(requests) != 1:
        raise ValueError("listener did not handle exactly one connector request")
    if harness_exit is not None and harness_exit != 0:
        raise ValueError(f"headless harness exited {harness_exit}")
    request = requests[0]
    peer = cast("dict[str, object]", request["peer"])
    return f"peer={peer['pid']} decision={request['decision']} requests={len(rows)}"
