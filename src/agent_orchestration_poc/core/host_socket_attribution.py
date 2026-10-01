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
    body: object = None
    tool_served: bool = False
    final_served: bool = False
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


def _probe_prompt(profile: str) -> str:
    python = (
        "/Users/tony/.local/share/mise/installs/python/3.14.6/bin/python3"
        if profile.startswith("codex-")
        else "python3"
    )
    return (
        f"Run {python} experiments/02-host-socket-attribution/probe.py client "
        f"/private/tmp/bv01-228-{profile}/gateway.sock {profile} and then stop."
    )


def _content_signals(content: object, expected_prompt: str) -> tuple[bool, bool]:
    """Find only text prompts and the fixed Claude tool result ID."""
    if isinstance(content, str):
        return expected_prompt in content, False
    if not isinstance(content, list):
        return False, False
    prompt = False
    result = False
    for part in content:
        if not isinstance(part, dict):
            continue
        prompt |= (
            part.get("type") in {"text", "input_text"}
            and isinstance(part.get("text"), str)
            and expected_prompt in part["text"]
        )
        result |= (
            part.get("type") == "tool_result"
            and part.get("tool_use_id") == "toolu_bv01"
        )
    return prompt, result


def responder_route(request: ResponderRequest) -> str:
    """Classify model input using only the probe prompt and its tool result."""
    body = request.body
    if not isinstance(body, dict):
        return "side-request"
    messages = body.get("input" if request.profile.startswith("codex-") else "messages")
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if not isinstance(messages, list):
        return "side-request"
    prompt = False
    result = False
    for message in messages:
        if not isinstance(message, dict):
            continue
        result |= request.profile.startswith("codex-") and (
            message.get("type") == "function_call_output"
            and message.get("call_id") == "call-bv01"
        )
        if message.get("role") != "user":
            continue
        has_prompt, has_result = _content_signals(
            message.get("content"), _probe_prompt(request.profile)
        )
        prompt |= has_prompt
        result |= has_result and request.profile.startswith("claude-")
    if result:
        return (
            "final" if request.tool_served and not request.final_served else "follow-up"
        )
    tools = body.get("tools")
    if request.profile.startswith("claude-") and not any(
        isinstance(tool, dict) and tool.get("name") == "Bash"
        for tool in (tools if isinstance(tools, list) else [])
    ):
        return "follow-up" if request.tool_served else "side-request"
    if prompt:
        return "tool" if not request.tool_served else "retry"
    return "follow-up" if request.tool_served else "side-request"


def responder_reply(request: ResponderRequest) -> tuple[int, str | None, str]:
    """Select a fixed frame for a validated loopback request."""
    if request.profile not in {
        "codex-interactive",
        "codex-headless",
        "claude-interactive",
        "claude-headless",
    }:
        return 400, None, "invalid"
    if request.profile.startswith("claude-") and request.method == "HEAD":
        return (
            (200, None, "probe")
            if request.path in {"/v1/messages", "/api/hello"}
            and request.host == f"127.0.0.1:{request.port}"
            else (403, None, "invalid")
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
        return 403, None, "invalid"
    if (
        request.transfer_encoding
        or not request.content_length.isascii()
        or not request.content_length.isdecimal()
        or len(request.content_length) > 7
        or int(request.content_length) > 2_000_000
    ):
        return 403, None, "invalid"
    route = responder_route(request)
    fixture = (
        f"{request.profile}-{route}.sse"
        if route in {"tool", "final"}
        else f"{'codex' if request.profile.startswith('codex-') else 'claude'}-side.sse"
    )
    return 200, fixture, route


def responder_log(  # noqa: PLR0913 - response metadata plus optional parsed shape.
    method: str,
    path: str,
    status: int,
    fixture: str | None = None,
    classification: str = "invalid",
    *,
    body: object = None,
) -> dict[str, str | int | bool]:
    """Record bounded request metadata without headers or body values."""
    safe_path = (
        path
        if path
        in {"/v1/responses", "/v1/messages", "/v1/messages?beta=true", "/api/hello"}
        else "<rejected>"
    )
    row: dict[str, str | int | bool] = {
        "method": method if method in {"POST", "HEAD", "GET", "PUT"} else "<rejected>",
        "path": safe_path,
        "status": status,
        "classification": classification,
    }
    if fixture is not None:
        row["fixture"] = fixture
    if isinstance(body, dict):
        tools = body.get("tools")
        tool_list: list[object] = tools if isinstance(tools, list) else []
        model = body.get("model")
        row.update(
            tool_count=len(tool_list),
            has_bash=any(
                isinstance(tool, dict) and tool.get("name") == "Bash"
                for tool in tool_list
            ),
            model=model
            if isinstance(model, str)
            and len(model) <= 100
            and all(char.isalnum() or char in "-._" for char in model)
            else "<rejected>",
            has_output_format=body.get("outputFormat") is not None
            or body.get("output_format") is not None,
        )
    return row


def codex_config(home: Path, python: Path, port: int) -> str:
    """Build the disposable Codex profile and exact read grants."""
    workspace = home / "workspace"
    denied = [
        home / "relay-run-r2",
        home / "relay-run-r3",
        home / "relay-run-r4",
        home / "relay-run-r5",
        home / "relay-run-r6",
        home / "codex",
    ]
    denied.extend(
        home.parent / f"bv01-228-{profile}"
        for profile in (
            "codex-headless",
            "codex-interactive",
            "claude-headless",
            "claude-interactive",
        )
        if home.name != f"bv01-228-{profile}"
    )
    if home.name == "bv01-228-codex-headless":
        denied.extend(
            home / name
            for name in (
                "file-opens-relay-r2.json",
                "file-opens-relay-r2.pid",
                "file-opens-relay-r2.err",
                "audit-positive-relay-r2",
                "file-opens-relay-r6.json",
                "file-opens-relay-r6.pid",
                "file-opens-relay-r6.err",
                "audit-positive-relay-r6",
            )
        )
    deny_entries = "\n".join(f'"{path}" = "deny"' for path in denied)
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
":minimal" = "read"
"{workspace}" = "read"
"{python.parent.parent}" = "read"
{deny_entries}
[permissions.bv01.network]
enabled = true
[permissions.bv01.network.unix_sockets]
"{home}/gateway.sock" = "allow"
[tui]
disable_paste_burst = true
screen_reader_detection_done = true
'''


def claude_trust(workspace: Path) -> dict[str, object]:
    """Seed first-run and workspace trust for a disposable home."""
    return {
        "hasCompletedOnboarding": True,
        "theme": "dark",
        "customApiKeyResponses": {"approved": ["not-a-real-key"], "rejected": []},
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


def claude_theme_choice(pane: str) -> bool:
    """Recognize only the pinned first-run theme dialog with dark selected."""
    lines = [line.strip() for line in pane.splitlines()]
    required = {
        "Choose the text style that looks best with your terminal",
        "To change this later, run /theme",
        "1. Auto (match terminal)",
        "❯ 2. Dark mode ✔",
        "3. Light mode",
    }
    return required <= set(lines) and [
        line for line in lines if line.startswith("❯")
    ] == ["❯ 2. Dark mode ✔"]


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
    prompt_python = str(python) if profile.startswith("codex-") else "python3"
    prompt = (
        f"Run {prompt_python} experiments/02-host-socket-attribution/probe.py client "
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
        else:
            argv += ["--permission-mode", "manual"]
    return argv, env


def relay_result(
    rows: list[dict[str, object]],
    requests: list[dict[str, object]],
    harness_exit: int | None,
    profile: str,
) -> str:
    """Require the tool and final frames and one connector request."""
    if any(row["status"] != 200 for row in rows):
        raise ValueError("responder refused a request")
    expected = [f"{profile}-tool.sse", f"{profile}-final.sse"]
    frames = [row for row in rows if row.get("fixture") in expected]
    if [(row["fixture"], row.get("classification")) for row in frames] != [
        (expected[0], "tool"),
        (expected[1], "final"),
    ]:
        raise ValueError("responder did not serve tool and final frames")
    if len(requests) != 1:
        raise ValueError("listener did not handle exactly one connector request")
    if harness_exit is not None and harness_exit != 0:
        raise ValueError(f"headless harness exited {harness_exit}")
    request = requests[0]
    if request["decision"] != "allowed":
        raise ValueError("listener did not allow connector request")
    peer = cast("dict[str, object]", request["peer"])
    return (
        f"peer={peer['pid']} decision={request['decision']} requests={len(rows)} "
        f"side_requests={sum(row.get('classification') in {'side-request', 'retry', 'follow-up'} for row in rows)}"
    )
