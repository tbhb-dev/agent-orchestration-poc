"""Fixture and command tests for the parent link shell."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agent_orchestration_poc.core.parent_link_sync import (
    Operation,
    compare,
    initial_edges,
    ongoing_edges,
    operation_plan,
)

pytest.importorskip("agent_orchestration_poc.shell")

from agent_orchestration_poc.shell import parent_link_sync as sync
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
    path.write_text(
        json.dumps(
            {"complete": True, "applied": False, "managed": [["epic: b", "epic: a"]]}
        )
    )
    with pytest.raises(ValueError, match="successful apply"):
        read_managed(path, tables)


def test_approved_excluded_issue_link_stays_excluded() -> None:
    tables = get_tables()
    _, issues = read_snapshot(FIXTURES / "approved.json", tables)
    changed = tuple(
        replace(issue, blockers=(*issue.blockers, "28"))
        if issue.number == "29"
        else issue
        for issue in issues
    )
    assert (
        "epic: bus relay and shared context",
        "epic: provisioned interactive workers",
    ) not in ongoing_edges(tables, changed)


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
    assert len(apply((Operation("POST", edge),), parents)) == 1
    assert len(json.loads(state.read_text())) == 1
    assert apply((), parents) == []
    assert len(apply((Operation("DELETE", edge),), parents)) == 1
    assert json.loads(state.read_text()) == []


def test_reversed_link_replacement_and_second_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables = get_tables()
    parents, _ = read_snapshot(FIXTURES / "approved.json", tables)
    left, right = parents[:2]
    state = {left.number: {right.issue_id}, right.number: set()}
    by_id = {parent.issue_id: parent.number for parent in (left, right)}
    calls: list[str] = []

    def fake_request(
        path: str, *, method: str = "GET", issue_id: int = 0, missing_ok: bool = False
    ) -> dict[str, Any] | None:
        del missing_ok
        number = int(path.split("/")[1])
        if method == "DELETE":
            state[number].remove(int(path.split("/")[-1]))
        else:
            assert method == "POST"
            if number in state[by_id[issue_id]]:
                raise ValueError("intermediate cycle")
            state[number].add(issue_id)
        calls.append(method)
        return {"id": issue_id}

    monkeypatch.setattr(sync, "request", fake_request)

    def fake_blocked_by(number: int) -> tuple[int, ...]:
        return tuple(state[number])

    monkeypatch.setattr(sync, "blocked_by", fake_blocked_by)
    desired = frozenset({(right.title, left.title)})
    current = tuple(
        replace(parent, blockers=tuple(state.get(parent.number, ())))
        for parent in parents
    )
    result = compare(
        tables, desired, current, (), frozenset({(left.title, right.title)})
    )
    plan = operation_plan(result, True, True)
    assert len(apply(plan, current)) == 2
    assert calls == ["DELETE", "POST"]
    current = tuple(
        replace(parent, blockers=tuple(state.get(parent.number, ())))
        for parent in parents
    )
    second = compare(tables, desired, current, (), frozenset(desired))
    assert operation_plan(second, True, True) == ()


def test_main_apply_output_round_trips_as_managed_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tables = get_tables()
    parents, issues = read_snapshot(FIXTURES / "approved.json", tables)
    state = {parent.number: set(parent.blockers) for parent in parents}
    by_title = {parent.title: parent for parent in parents}
    changed = tuple(
        replace(issue, blockers=(*issue.blockers, "12"))
        if issue.number == "3"
        else issue
        for issue in issues
    )
    desired_edge = next(
        iter(ongoing_edges(tables, changed) - ongoing_edges(tables, issues))
    )
    dependent, blocker = (by_title[title] for title in desired_edge)
    current_issues = changed

    def fake_collect(
        _tables: object, *, ongoing: bool
    ) -> tuple[tuple[sync.Parent, ...], tuple[sync.Issue, ...]]:
        assert ongoing
        return (
            tuple(
                replace(parent, blockers=tuple(sorted(state[parent.number])))
                for parent in parents
            ),
            current_issues,
        )

    def fake_request(
        path: str, *, method: str = "GET", issue_id: int = 0, missing_ok: bool = False
    ) -> dict[str, int] | None:
        del missing_ok
        number = int(path.split("/")[1])
        if method == "POST":
            state[number].add(issue_id)
            return {"id": issue_id}
        assert method == "DELETE"
        state[number].remove(int(path.split("/")[-1]))
        return None

    monkeypatch.setattr(sync, "collect", fake_collect)
    monkeypatch.setattr(sync, "request", fake_request)

    def fake_blocked_by(number: int) -> tuple[int, ...]:
        return tuple(state[number])

    monkeypatch.setattr(sync, "blocked_by", fake_blocked_by)
    monkeypatch.setattr(sync, "coordinator_identity", lambda: True)

    first = tmp_path / "first.json"
    monkeypatch.setattr(sys, "argv", ["sync-parent-links", "--ongoing", "--apply"])
    assert sync.main() == 0
    first_output = capsys.readouterr()
    first.write_text(first_output.out)
    first_report = json.loads(first.read_text())
    assert len(first_report["operations"]) == 1
    assert json.loads(first_output.err) == first_report["operations"][0]
    assert blocker.issue_id in state[dependent.number]

    second = tmp_path / "second.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sync-parent-links", "--ongoing", "--apply", "--managed", str(first)],
    )
    assert sync.main() == 0
    second.write_text(capsys.readouterr().out)
    second_report = json.loads(second.read_text())
    assert second_report["operations"] == []
    assert list(desired_edge) in second_report["managed"]

    current_issues = issues
    monkeypatch.setattr(
        sys,
        "argv",
        ["sync-parent-links", "--ongoing", "--apply", "--managed", str(second)],
    )
    assert sync.main() == 0
    third_report = json.loads(capsys.readouterr().out)
    assert [operation["method"] for operation in third_report["operations"]] == [
        "DELETE"
    ]
    assert blocker.issue_id not in state[dependent.number]
