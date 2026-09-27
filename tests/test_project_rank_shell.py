"""Offline process fixtures for the coordinator rank command."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _items() -> list[dict[str, str | int | None]]:
    return [
        {
            "id": f"I{number}",
            "issue": number,
            "kind": "ISSUE",
            "priority": "Standard",
            "state": "OPEN",
            "work_type": "Chore",
        }
        for number in (1, 2, 3)
    ]


def _invoke(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agent_orchestration_poc.shell.project_rank", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        timeout=10,
        check=False,
    )


@pytest.mark.integration
def test_fixture_dry_run_and_missing_item(tmp_path: Path) -> None:
    fixture = tmp_path / "snapshot.json"
    fixture.write_text(
        json.dumps({"project_id": "P1", "items": _items(), "remaining": 500, "cost": 2})
    )
    result = _invoke(tmp_path, "--fixture", str(fixture), "move", "3", "above", "1")
    assert result.returncode == 0
    assert "itemId=I3 afterId=None" in result.stderr
    assert "planned mutations: 1" in result.stderr
    missing = _invoke(tmp_path, "--fixture", str(fixture), "move", "99", "above", "1")
    assert missing.returncode == 2
    assert "missing or ambiguous" in missing.stderr
    assert (
        _invoke(
            tmp_path, "--fixture", str(fixture), "--apply", "move", "3", "above", "1"
        ).returncode
        == 2
    )
    ordered = _invoke(tmp_path, "--fixture", str(fixture), "order", "3", "1", "2")
    assert ordered.returncode == 0
    assert "planned mutations: 1" in ordered.stderr


@pytest.mark.integration
def test_replace_fixture_positions_issue_before_draft(tmp_path: Path) -> None:
    fixture = tmp_path / "snapshot.json"
    draft: dict[str, str | int | None] = {
        "id": "D1",
        "issue": None,
        "kind": "DRAFT_ISSUE",
        "priority": "Standard",
        "state": "OPEN",
        "work_type": "",
    }
    fixture.write_text(
        json.dumps(
            {
                "project_id": "P1",
                "items": [_items()[0], draft, *_items()[1:]],
                "remaining": 500,
                "cost": 2,
            }
        )
    )
    result = _invoke(tmp_path, "--fixture", str(fixture), "replace", "D1", "with", "3")
    assert result.returncode == 0
    assert "itemId=I3 afterId=I1" in result.stderr


def _response(items: list[dict[str, str | int | None]], remaining: int) -> str:
    nodes: list[dict[str, Any]] = []
    for item in items:
        nodes.append(
            {
                "id": item["id"],
                "type": item["kind"],
                "content": {"number": item["issue"], "state": item["state"]},
                "priority": {"name": item["priority"]},
                "workType": {"name": item["work_type"]},
            }
        )
    body = {
        "data": {
            "user": {
                "projectV2": {
                    "id": "P1",
                    "items": {
                        "totalCount": len(nodes),
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": nodes,
                    },
                }
            },
            "rateLimit": {"remaining": remaining, "cost": 2},
        }
    }
    return f"HTTP/2 200 OK\nx-ratelimit-remaining: {remaining}\n\n{json.dumps(body)}\n"


def _mutation_response() -> str:
    body: dict[str, Any] = {
        "data": {
            "updateProjectV2ItemPosition": {"clientMutationId": None},
        }
    }
    return f"HTTP/2 200 OK\nx-ratelimit-remaining: 497\n\n{json.dumps(body)}\n"


def _first_page() -> str:
    raw = _response(_items()[:2], 500)
    body: dict[str, Any] = json.loads(raw.partition("\n\n")[2])
    connection = body["data"]["user"]["projectV2"]["items"]
    connection["totalCount"] = 3
    connection["pageInfo"] = {"hasNextPage": True, "endCursor": "cursor"}
    return f"HTTP/2 200 OK\nx-ratelimit-remaining: 500\n\n{json.dumps(body)}\n"


def _last_page() -> str:
    raw = _response(_items()[2:], 498)
    body: dict[str, Any] = json.loads(raw.partition("\n\n")[2])
    body["data"]["user"]["projectV2"]["items"]["totalCount"] = 3
    return f"HTTP/2 200 OK\nx-ratelimit-remaining: 498\n\n{json.dumps(body)}\n"


def _fake_gh(
    tmp_path: Path, responses: list[str], *, fail: bool = False, validate: bool = False
) -> None:
    files = []
    for index, response in enumerate(responses):
        path = tmp_path / f"response-{index}"
        path.write_text(response)
        files.append(str(path))
    gh = tmp_path / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'if [ "$2" = user ]; then printf "%s\\n" tbhbagent; exit 0; fi\n'
        + (
            'case "$*" in *"mutation("*"rateLimit"*) exit 1 ;; esac\n'
            if validate
            else ""
        )
        + ("exit 1\n" if fail else "")
        + 'count_file="$0.count"\n'
        + 'count=$(cat "$count_file" 2>/dev/null || printf 0)\n'
        + 'case "$count" in\n'
        + "".join(f"  {index}) cat '{path}' ;;\n" for index, path in enumerate(files))
        + "  *) exit 1 ;;\n"
        + "esac\n"
        + 'printf "%s\\n" "$((count + 1))" > "$count_file"\n'
    )
    gh.chmod(0o755)


@pytest.mark.integration
def test_failed_read_refuses_without_request_data(tmp_path: Path) -> None:
    _fake_gh(tmp_path, [], fail=True)
    result = _invoke(tmp_path, "move", "3", "above", "1")
    assert result.returncode == 2
    assert "GitHub read or write failed" in result.stderr


@pytest.mark.integration
def test_paginated_dry_run_counts_every_request(tmp_path: Path) -> None:
    _fake_gh(tmp_path, [_first_page(), _last_page()])
    result = _invoke(tmp_path, "move", "3", "above", "1")
    assert result.returncode == 0
    assert "planned requests: 5" in result.stderr


@pytest.mark.integration
@pytest.mark.parametrize(
    ("second", "remaining", "message"),
    [((2, 1, 3), 500, "order changed"), ((1, 2, 3), 10, "remaining points")],
)
def test_apply_refuses_changed_order_and_low_budget(
    tmp_path: Path, second: tuple[int, ...], remaining: int, message: str
) -> None:
    items = _items()
    by_number = {item["issue"]: item for item in items}
    _fake_gh(
        tmp_path,
        [
            _response(items, 500),
            _response([by_number[number] for number in second], remaining),
        ],
    )
    result = _invoke(tmp_path, "--apply", "move", "3", "above", "1")
    assert result.returncode == 2
    assert message in result.stderr


@pytest.mark.integration
def test_apply_with_local_fake_reads_back_and_records_cost(tmp_path: Path) -> None:
    original = _items()
    moved = [original[2], *original[:2]]
    _fake_gh(
        tmp_path,
        [
            _response(original, 500),
            _response(original, 498),
            _mutation_response(),
            _response(moved, 495),
        ],
        validate=True,
    )
    result = _invoke(tmp_path, "--apply", "move", "3", "above", "1")
    assert result.returncode == 0
    assert "position mutation cost=1 remaining=497" in result.stderr
    assert "read-back confirmed; observed total points=7" in result.stderr
