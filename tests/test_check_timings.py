"""Pure timing decisions and the process and SQLite boundary."""

import shlex
import signal
import sqlite3
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from contextlib import closing
from pathlib import Path
from typing import Protocol, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.check_timings import (
    TimingContext,
    TimingRecord,
    builtin_config,
    child_environment,
    inventory_missing,
    main_clone_from_common_dir,
    make_record,
    origin_and_actor,
    parse_git_snapshot,
)


class _Shell(Protocol):
    append_record: Callable[[Path, TimingRecord], None]
    store_path: Callable[[], Path]
    run_recorded: Callable[[str, Sequence[str]], int]
    main: Callable[[], int]


def _shell() -> _Shell:
    """Load shell probes only where the shell package is installed."""
    return cast(
        "_Shell", pytest.importorskip("agent_orchestration_poc.shell.check_timings")
    )


CONTEXT = TimingContext(None, None, "local", None, "test-host")
WRAPPER = Path(__file__).resolve().parent.parent / "scripts/record-check.sh"


@pytest.mark.parametrize(
    ("was_set", "original", "expected"),
    [("0", "", None), ("1", "", ""), ("1", "/original", "/original")],
)
def test_child_environment_restores_python_path(
    was_set: str, original: str, expected: str | None
) -> None:
    """The wrapped check sees the same Python path as an unwrapped check."""
    source = {
        "PYTHONPATH": "/wrapper/src",
        "CHECK_TIMING_PYTHONPATH_WAS_SET": was_set,
        "CHECK_TIMING_PARENT_PYTHONPATH": original,
        "OTHER": "retained",
    }
    child = child_environment(source)
    assert child.get("PYTHONPATH") == expected
    assert child["OTHER"] == "retained"
    assert "CHECK_TIMING_PARENT_PYTHONPATH" not in child
    assert source["PYTHONPATH"] == "/wrapper/src"


@given(st.text())
def test_child_environment_preserves_original_path(original: str) -> None:
    """Every original Python path is passed through exactly."""
    child = child_environment(
        {
            "PYTHONPATH": "/wrapper/src",
            "CHECK_TIMING_PYTHONPATH_WAS_SET": "1",
            "CHECK_TIMING_PARENT_PYTHONPATH": original,
        }
    )
    assert child["PYTHONPATH"] == original


def test_child_environment_without_wrapper_marker() -> None:
    """Direct library calls preserve an existing Python path."""
    assert child_environment({"PYTHONPATH": "/original"}) == {"PYTHONPATH": "/original"}


@pytest.mark.parametrize(
    ("common", "valid"),
    [("/repo/.git", True), ("/repo/.git/worktrees/child", False), (".git", False)],
)
def test_main_clone_path(common: str, valid: bool) -> None:
    """Only an absolute main-clone git directory identifies the store root."""
    if valid:
        assert str(main_clone_from_common_dir(common)) == "/repo"
    else:
        with pytest.raises(ValueError, match="absolute .git"):
            main_clone_from_common_dir(common)


@pytest.mark.parametrize(
    ("ref", "expected"),
    [("tooling/109-check-durations", "tooling/109-check-durations"), ("HEAD", None)],
)
def test_parse_git_snapshot(ref: str, expected: str | None) -> None:
    """A detached checkout retains the commit and a null branch."""
    root, commit, branch = parse_git_snapshot(f"/repo/.git\n{'a' * 40}\n{ref}\n")
    assert str(root) == "/repo"
    assert commit == "a" * 40
    assert branch == expected


def test_parse_git_snapshot_rejects_missing_fields() -> None:
    """A partial Git response cannot yield guessed metadata."""
    with pytest.raises(ValueError, match="invalid git snapshot"):
        parse_git_snapshot("/repo/.git\n")


@pytest.mark.parametrize(
    ("ci", "explicit", "github", "expected"),
    [
        ("true", None, "bot", ("ci", "bot")),
        (None, "human", "bot", ("local", "human")),
        ("false", None, None, ("local", None)),
    ],
)
def test_origin_and_actor(
    ci: str | None,
    explicit: str | None,
    github: str | None,
    expected: tuple[str, str | None],
) -> None:
    """Actor names are used only when supplied, and CI must be explicit."""
    assert origin_and_actor(ci, explicit, github) == expected


@given(
    st.sampled_from(
        ["trailing-whitespace", "end-of-file-fixer", "check-added-large-files"]
    )
)
def test_builtin_config_is_single_hook(hook_id: str) -> None:
    """Each supported builtin remains delegated to prek itself."""
    assert builtin_config(hook_id).count("id = ") == 1
    assert f'id = "{hook_id}"' in builtin_config(hook_id)


def test_builtin_config_rejects_unknown() -> None:
    """An unknown name cannot be injected into a hook config."""
    with pytest.raises(ValueError, match="unsupported builtin"):
        builtin_config('bad" hook')


@pytest.mark.parametrize(
    "started", ["bad", "2026-09-26T10:00:00", "2026-09-26T10:00:00+01:00"]
)
def test_record_rejects_non_utc_start(started: str) -> None:
    """Malformed or non-UTC timestamps cannot enter the schema."""
    with pytest.raises(ValueError, match="timestamp|UTC"):
        make_record("task:check", started, 1, 0, CONTEXT)


@given(
    st.integers(min_value=0, max_value=10**12), st.integers(min_value=0, max_value=255)
)
def test_record_preserves_duration_and_status(duration: int, status: int) -> None:
    """Safe numeric fields survive construction without rounding."""
    record = make_record(
        "task:check", "2026-09-26T10:00:00Z", duration, status, CONTEXT
    )
    assert record.duration_ns == duration
    assert record.exit_status == status
    assert record.branch is None
    assert record.actor is None
    assert record.started_at.endswith("+00:00")


@pytest.mark.parametrize(
    ("name", "duration", "status", "origin"),
    [
        ("", 1, 0, "local"),
        ("a", -1, 0, "local"),
        ("a", 1, -1, "local"),
        ("a", 1, 0, "other"),
    ],
)
def test_record_rejects_bad_fields(
    name: str, duration: int, status: int, origin: str
) -> None:
    """Core validation rejects invalid scalar fields."""
    context = TimingContext(None, None, origin, None, "host")
    with pytest.raises(ValueError, match="invalid timing"):
        make_record(name, "2026-09-26T10:00:00Z", duration, status, context)


@given(st.sets(st.sampled_from(["task:a", "hook:b"])))
def test_inventory_reports_only_missing_records(recorded: set[str]) -> None:
    """Extra rows do not hide an uncovered configured task or hook."""
    tasks = {"a": "scripts/record-check.sh task:a -- true"}
    hooks = {"b": "scripts/record-check.sh hook:b -- true"}
    assert (
        set(inventory_missing(tasks, hooks, tuple(recorded)))
        == {"task:a", "hook:b"} - recorded
    )


def test_inventory_requires_wrappers() -> None:
    """A stored synthetic row cannot mask an unwrapped configuration."""
    assert inventory_missing({"a": "true"}, {"b": "true"}, ("task:a", "hook:b")) == (
        "hook:b",
        "task:a",
    )
    assert inventory_missing({"check": None}, {}, ()) == ()


@pytest.mark.integration
def test_configured_tasks_and_hooks_have_timing_wrappers() -> None:
    """Every configured mechanical invocation can write its own timing row."""
    root = Path(__file__).resolve().parent.parent
    tasks_config = tomllib.loads((root / "mise.toml").read_text())
    hooks_config = tomllib.loads((root / "prek.toml").read_text())
    tasks = {name: task.get("run") for name, task in tasks_config["tasks"].items()}
    hooks = {
        hook["id"]: hook["entry"]
        for repo in hooks_config["repos"]
        for hook in repo["hooks"]
    }
    records = (*(f"task:{name}" for name in tasks), *(f"hook:{name}" for name in hooks))
    assert inventory_missing(tasks, hooks, records) == ()


@pytest.mark.integration
def test_vale_task_forwards_supplied_filenames(tmp_path: Path) -> None:
    """The configured child command passes both file arguments unchanged."""
    root = Path(__file__).resolve().parent.parent
    run = tomllib.loads((root / "mise.toml").read_text())["tasks"]["check:vale"]["run"]
    child = shlex.split(run)[3:]
    script = tmp_path / "scripts" / "check-vale.sh"
    script.parent.mkdir()
    script.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    script.chmod(0o755)
    result = subprocess.run(
        [*child, "one.md", "two.md"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "one.md\ntwo.md\n"


def test_append_record(tmp_path: Path) -> None:
    """SQLite retains the explicit safe columns and two independent rows."""
    path = tmp_path / "check-timings" / "timings.sqlite3"
    record = make_record("task:check", "2026-09-26T10:00:00Z", 12, 1, CONTEXT)
    _shell().append_record(path, record)
    _shell().append_record(path, record)
    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute(
            "SELECT name, duration_ns, exit_status, branch FROM local_checks"
        ).fetchall()
    assert rows == [("task:check", 12, 1, None)] * 2


@pytest.mark.integration
def test_store_path_is_ignored_in_main_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal clones and linked worktrees both resolve the main clone's ignored store."""
    main = tmp_path / "main"
    linked = tmp_path / "linked"
    main.mkdir()
    subprocess.run(["git", "init", "-q", str(main)], check=True)
    (main / ".gitignore").write_text(".local-cache/\n")
    subprocess.run(["git", "-C", str(main), "add", ".gitignore"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(main),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(main), "worktree", "add", "-q", "--detach", str(linked)],
        check=True,
    )
    expected = main / ".local-cache/check-timings/timings.sqlite3"
    for checkout in (main, linked):
        monkeypatch.chdir(checkout)
        assert _shell().store_path() == expected
        assert (
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(main),
                    "check-ignore",
                    "-q",
                    ".local-cache/check-timings/timings.sqlite3",
                ],
                check=False,
            ).returncode
            == 0
        )
        assert not (linked / ".local-cache").exists()


@pytest.mark.integration
def test_run_recorded_with_repository_snapshot(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """The shell reads Git metadata and leaves the child output unchanged."""
    status = _shell().run_recorded(
        "test:direct", [sys.executable, "-c", "print('direct command')"]
    )
    output = capfd.readouterr()
    assert status == 0
    assert output.out == "direct command\n"
    assert output.err == ""


@pytest.mark.integration
def test_run_recorded_without_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """A missing Git snapshot cannot change the child status or streams."""
    monkeypatch.chdir(tmp_path)
    status = _shell().run_recorded(
        "test:outside",
        [sys.executable, "-c", "import sys; print('failed'); sys.exit(7)"],
    )
    output = capfd.readouterr()
    assert status == 7
    assert output.out == "failed\n"
    assert output.err == ""


@pytest.mark.integration
def test_main_rejects_missing_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed invocation reports usage without starting a child."""
    monkeypatch.setattr(sys, "argv", ["record-check", "test:missing"])
    assert _shell().main() == 2
    assert capsys.readouterr().err.startswith("usage: record-check")


@pytest.mark.integration
@pytest.mark.parametrize("status", [0, 7])
def test_wrapper_preserves_streams_and_status(tmp_path: Path, status: int) -> None:
    """An unavailable store cannot change a passing or failing process."""
    _shell()
    command = [
        sys.executable,
        "-c",
        f"import sys; print('out'); print('err', file=sys.stderr); sys.exit({status})",
    ]
    direct = subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)
    wrapped = subprocess.run(
        [str(WRAPPER), "test:command", "--", *command],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert (wrapped.returncode, wrapped.stdout, wrapped.stderr) == (
        direct.returncode,
        direct.stdout,
        direct.stderr,
    )


@pytest.mark.integration
def test_wrapper_forwards_interrupt(tmp_path: Path) -> None:
    """An interrupted command retains the shell's 130 exit status."""
    _shell()
    process = subprocess.Popen(
        [
            str(WRAPPER),
            "test:interrupt",
            "--",
            sys.executable,
            "-c",
            "import time; print('ready', flush=True); time.sleep(10)",
        ],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stdout.readline() == b"ready\n"
    process.send_signal(signal.SIGINT)
    stdout, stderr = process.communicate(timeout=3)
    assert process.returncode == 130
    assert stdout == b""
    assert b"KeyboardInterrupt" in stderr


@pytest.mark.integration
def test_wrapper_with_store_unavailable(tmp_path: Path) -> None:
    """Running outside a git checkout still returns the child status."""
    _shell()
    result = subprocess.run(
        [str(WRAPPER), "test:missing-store", "--", sys.executable, "-c", "print('ok')"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == b"ok\n"
    assert result.stderr == b""
    assert not list(tmp_path.rglob("*.sqlite3"))
