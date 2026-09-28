"""Pure descriptions of disposable host confinement targets."""

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
