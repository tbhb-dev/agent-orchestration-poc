"""Plain-value and property tests for disposable launch selection."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from .launch_core import launch_spec  # pyrefly: ignore[missing-import]
from .lifecycle_core import PROFILES  # pyrefly: ignore[missing-import]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("slot", ["A", "B"])
def test_initial_profiles(profile: str, slot: str) -> None:
    """Each profile keeps state, paths, and fake transport inside its home."""
    spec = launch_spec(profile, "initial", slot, None, 12345)
    home = f"/private/tmp/bv01-228-{profile}"
    state = home if slot == "A" else f"{home}/B"
    assert spec.root_file == f"{home}/root{'' if slot == 'A' else '-B'}.pid"  # noqa: S101 - pytest assertion
    assert spec.go_file == f"{home}/go{'' if slot == 'A' else '-B'}"  # noqa: S101 - pytest assertion
    assert spec.env["HOME"] == state  # noqa: S101 - pytest assertion
    assert spec.env["TMPDIR"] == f"{state}/tmp"  # noqa: S101, S108 - pytest assertion in disposable home
    assert (  # noqa: S101 - pytest assertion
        spec.env["CODEX_HOME" if profile.startswith("codex-") else "CLAUDE_CONFIG_DIR"]
        == f"{state}/{'codex' if profile.startswith('codex-') else 'claude'}"
    )
    assert "not-a-real-key" in spec.env.values()  # noqa: S101 - pytest assertion
    assert "--resume" not in spec.argv  # noqa: S101 - pytest assertion


@pytest.mark.parametrize("profile", PROFILES)
def test_resume_profiles(profile: str) -> None:
    """Resume uses the native ID and A's retained state in a new launch."""
    spec = launch_spec(profile, "resume", "A", "native-id", 12345)
    assert "native-id" in spec.argv  # noqa: S101 - pytest assertion
    assert "private-marker" in spec.argv[-1]  # noqa: S101 - pytest assertion
    assert spec.root_file.endswith("/root.pid")  # noqa: S101 - pytest assertion
    assert "--ephemeral" not in spec.argv  # noqa: S101 - pytest assertion
    assert "--no-session-persistence" not in spec.argv  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    ("profile", "phase", "slot", "conversation", "port"),
    [
        ("other", "initial", "A", None, None),
        ("codex-headless", "other", "A", None, None),
        ("codex-headless", "initial", "C", None, None),
        ("codex-headless", "resume", "B", "id", None),
        ("codex-headless", "resume", "A", None, None),
        ("claude-headless", "initial", "A", None, None),
        ("claude-headless", "initial", "A", None, 0),
        ("claude-headless", "initial", "A", None, 65536),
    ],
)
def test_rejects_unapproved_values(
    profile: str, phase: str, slot: str, conversation: str | None, port: int | None
) -> None:
    """Invalid identities and model endpoints stop before launch."""
    with pytest.raises(ValueError, match="unapproved|requires"):
        launch_spec(profile, phase, slot, conversation, port)


@given(st.sampled_from(PROFILES), st.integers(min_value=1, max_value=65535))
def test_launch_property(profile: str, port: int) -> None:
    """All accepted ports keep the provider route on loopback."""
    spec = launch_spec(profile, "initial", "A", None, port)
    if profile.startswith("claude-"):
        assert spec.env["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{port}"  # noqa: S101 - pytest assertion
    else:
        assert "ANTHROPIC_BASE_URL" not in spec.env  # noqa: S101 - pytest assertion
