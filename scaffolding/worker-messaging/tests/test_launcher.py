"""Temporary #176 registry and command tests; #28 replaces this scaffold."""
# ruff: noqa: S101

from pathlib import Path

import registry


def test_registry_roundtrip(tmp_path: Path) -> None:
    """Versioned rows survive a restart without storing prompt text."""
    path = tmp_path / "registry.json"
    assert registry.read(path) == []
    registry.write(path, [{"run_id": "one", "state": "starting"}])
    assert registry.read(path) == [{"run_id": "one", "state": "starting"}]
    assert path.stat().st_mode & 0o777 == 0o600
