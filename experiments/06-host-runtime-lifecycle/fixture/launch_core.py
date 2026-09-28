"""Pure launch values for the four disposable host harness profiles."""

from dataclasses import dataclass

from .lifecycle_core import PROFILES  # pyrefly: ignore[missing-import]

PATH = "/Users/tony/.local/bin:/Users/tony/.local/share/mise/installs/python/3.14.6/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"


@dataclass(frozen=True)
class LaunchSpec:
    """One immutable process launch and barrier location."""

    argv: tuple[str, ...]
    env: dict[str, str]
    root_file: str
    go_file: str
    workspace: str


def launch_spec(
    profile: str, phase: str, slot: str, conversation_id: str | None, port: int | None
) -> LaunchSpec:
    """Choose exact argv and isolated environment from plain input values."""
    if profile not in PROFILES or phase not in ("initial", "resume"):
        raise ValueError("unapproved profile or phase")
    if slot not in ("A", "B") or (phase == "resume" and slot != "A"):
        raise ValueError("unapproved slot")
    if phase == "resume" and not conversation_id:
        raise ValueError("resume requires a native conversation ID")
    if profile.startswith("claude-") and (port is None or not 0 < port < 65536):
        raise ValueError("Claude requires a loopback responder port")

    home = f"/private/tmp/bv01-228-{profile}"
    workspace = f"{home}/workspace"
    state = home if slot == "A" else f"{home}/B"
    env = {
        "HOME": state,
        "TMPDIR": f"{state}/tmp",  # noqa: S108 - approved disposable home
        "XDG_CONFIG_HOME": f"{state}/xdg",
        "PYTHONPATH": workspace,
        "PATH": PATH,
        "TERM": "xterm-256color",
        "LANG": "C.UTF-8",
    }
    prompt = (
        f"Test readability of {home}/B/"
        f"{'codex' if profile.startswith('codex-') else 'claude'}/private-marker and then stop."
        if phase == "resume"
        else "Run python3 experiments/02-host-socket-attribution/probe.py client "
        f"{home}/gateway.sock {profile} and then stop."
    )
    if profile.startswith("codex-"):
        env.update(CODEX_HOME=f"{state}/codex", BV01_FAKE_OPENAI_KEY="not-a-real-key")
        if profile.endswith("headless"):
            argv = (
                (
                    "codex",
                    "exec",
                    "resume",
                    "--json",
                    "--skip-git-repo-check",
                    conversation_id or "",
                    prompt,
                )
                if phase == "resume"
                else (
                    "codex",
                    "exec",
                    "--json",
                    "--skip-git-repo-check",
                    "-C",
                    workspace,
                    "-c",
                    "approval_policy=never",
                    prompt,
                )
            )
        else:
            argv = (
                (
                    "codex",
                    "resume",
                    "-C",
                    workspace,
                    "-c",
                    "approval_policy=never",
                    conversation_id or "",
                    prompt,
                )
                if phase == "resume"
                else ("codex", "-C", workspace, "-c", "approval_policy=never")
            )
    else:
        env.update(
            CLAUDE_CONFIG_DIR=f"{state}/claude",
            ANTHROPIC_API_KEY="not-a-real-key",
            ANTHROPIC_BASE_URL=f"http://127.0.0.1:{port}",
        )
        argv = (
            "claude",
            "--bare",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--settings",
            f"{home}/settings.json",
        )
        if profile.endswith("headless"):
            argv += (
                "--print",
                "--output-format",
                "json",
                "--permission-prompts",
                "none",
            )
        if phase == "resume":
            argv += ("--resume", conversation_id or "")
        if phase == "resume" or profile.endswith("headless"):
            argv += (prompt,)
    suffix = "" if slot == "A" else "-B"
    return LaunchSpec(
        argv, env, f"{home}/root{suffix}.pid", f"{home}/go{suffix}", workspace
    )
