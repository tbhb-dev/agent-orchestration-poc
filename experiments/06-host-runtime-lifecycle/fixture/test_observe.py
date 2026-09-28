"""File and path checks for the read-only observer shell."""

import subprocess
from pathlib import Path

import pytest

from .observe import (  # pyrefly: ignore[missing-import]
    current_start,
    inventory,
    observe,
)


def test_inventory(tmp_path: Path) -> None:
    """Hash regular files and leave their contents and paths untouched."""
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "marker").write_text("fake state")
    before = (tmp_path / "state" / "marker").read_text()
    result = inventory(tmp_path)
    assert len(result) == 1  # noqa: S101 - pytest assertion
    assert result["state/marker"]  # noqa: S101 - pytest assertion
    assert (tmp_path / "state" / "marker").read_text() == before  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    "home", [Path("/private/tmp/other"), Path("/private/tmp/bv01-228-unknown")]
)
def test_observe_rejects_other_homes(home: Path) -> None:
    """A mistaken home cannot make the observer inspect arbitrary state."""
    with pytest.raises(ValueError, match="approved paths"):
        observe(home, None)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            subprocess.CompletedProcess(["ps"], 0, "Mon Sep 28 12:00:00 2026\n", ""),
            "Mon Sep 28 12:00:00 2026",
        ),
        (subprocess.CompletedProcess(["ps"], 1, "", ""), None),
    ],
)
def test_current_start_known_results(
    monkeypatch: pytest.MonkeyPatch,
    result: subprocess.CompletedProcess[str],
    expected: str | None,
) -> None:
    """A successful lookup and a confirmed missing PID remain distinct."""

    def query(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return result

    monkeypatch.setattr(subprocess, "run", query)
    assert current_start(12345) == expected  # noqa: S101 - pytest assertion


def test_current_start_rejects_failed_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """A denied process query cannot establish absence."""
    result = subprocess.CompletedProcess(["ps"], 1, "", "ps: operation not permitted")

    def query(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return result

    monkeypatch.setattr(subprocess, "run", query)
    with pytest.raises(RuntimeError, match="operation not permitted"):
        current_start(12345)


def test_current_start_rejects_spawn_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sandbox denial before process creation is also inconclusive."""

    def deny(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(subprocess, "run", deny)
    with pytest.raises(RuntimeError, match="operation not permitted"):
        current_start(12345)
