"""File and path checks for the read-only observer shell."""

from pathlib import Path

import pytest

from .observe import inventory, observe  # pyrefly: ignore[missing-import]


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
