"""Fixture and command tests for the parent link shell."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from agent_orchestration_poc.core.parent_link_sync import initial_edges

pytest.importorskip("agent_orchestration_poc.shell")

from agent_orchestration_poc.shell.parent_link_sync import (
    apply,
    get_tables,
    read_managed,
    read_snapshot,
)

FIXTURES = Path(__file__).parent / "fixtures/parent_link_sync"


def test_saved_reads_and_ownership(tmp_path: Path) -> None:
    tables = get_tables()
    parents, issues = read_snapshot(FIXTURES / "approved.json", tables)
    assert len(parents) == len(tables.parents)
    assert len(issues) == sum(bool(row["number"]) for row in tables.assignments)
    assert len(read_managed(None, tables)) <= len(initial_edges(tables))
    bad = json.loads((FIXTURES / "approved.json").read_text())
    bad["complete"] = False
    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="incomplete saved"):
        read_snapshot(path, tables)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("fixture", "ongoing", "status", "missing", "extra"),
    [
        ("missing-parents.json", False, 0, True, False),
        ("approved.json", True, 0, False, False),
        ("obsolete-derived.json", True, 0, False, True),
        ("cycle-160-27.json", True, 2, False, False),
    ],
)
def test_command_fixtures(
    fixture: str, ongoing: bool, status: int, missing: bool, extra: bool
) -> None:
    args = [
        "mise",
        "exec",
        "--",
        "uv",
        "run",
        "python",
        "-m",
        "agent_orchestration_poc.shell.parent_link_sync",
    ]
    if ongoing:
        args.append("--ongoing")
    args.extend(["--snapshot", str(FIXTURES / fixture)])
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == status
    if status:
        assert "Kahn=True" in result.stderr
        assert "DFS=" in result.stderr
    else:
        report = json.loads(result.stdout)
        assert bool(report["missing"]) == missing
        assert bool(report["extra"]) == extra
        assert report["complete"]
        if extra:
            assert report["removable"] == report["extra"]


@pytest.mark.integration
def test_apply_readback_and_second_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "gh"
    state = tmp_path / "state.json"
    state.write_text("[]")
    script.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

path = Path(os.environ["FAKE_GH_STATE"])
ids = json.loads(path.read_text())
args = sys.argv[1:]
method = args[args.index("-X") + 1] if "-X" in args else "GET"
if method == "POST":
    issue_id = int(args[args.index("-F") + 1].split("=")[1])
    ids.append(issue_id)
    path.write_text(json.dumps(ids))
    print(json.dumps({"id": issue_id}))
elif method == "DELETE":
    ids.remove(int(args[1].split("/")[-1]))
    path.write_text(json.dumps(ids))
else:
    print(json.dumps([[{"id": issue_id} for issue_id in ids]]))
"""
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    parents, _ = read_snapshot(FIXTURES / "approved.json", get_tables())
    edge = next(iter(initial_edges(get_tables())))
    assert len(apply((edge,), (), parents)) == 1
    assert len(json.loads(state.read_text())) == 1
    assert apply((), (), parents) == []
    assert len(apply((), (edge,), parents)) == 1
    assert json.loads(state.read_text()) == []
