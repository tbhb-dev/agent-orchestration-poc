"""Plain-value and property tests for the disposable Project probe core."""

import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

SOURCE = Path(__file__).parents[1] / "scaffolding/github-monitor/project_probe.py"
if not SOURCE.is_file():
    SOURCE = Path(__file__).parents[2] / "scaffolding/github-monitor/project_probe.py"
FIXTURE = Path(__file__).parent / "fixtures/project_probe/pages.json"
MODULE = runpy.run_path(str(SOURCE))
assert isinstance(MODULE["next_cursor"], Callable)
next_cursor = cast("Callable[[str], str | None]", MODULE["next_cursor"])
classify_items = cast(
    "Callable[[list[list[dict[str, Any]]], tuple[str, ...], bool], dict[str, Any]]",
    MODULE["classify_items"],
)
classify_delivery = cast(
    "Callable[[list[tuple[str, int]], int, int, bool], dict[str, str]]",
    MODULE["classify_delivery"],
)
source_rows = cast(
    "Callable[[dict[str, Any], str, dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, dict[str, Any]]]",
    MODULE["source_rows"],
)


@pytest.mark.parametrize(
    ("link", "expected"),
    [
        (
            '<https://api.github.com/users/tbhb/projectsV2/9/items?after=abc>; rel="next"',
            "abc",
        ),
        (
            '<https://example.com/users/tbhb/projectsV2/9/items?after=abc>; rel="next"',
            None,
        ),
        (
            '<https://api.github.com/users/tbhb/projectsV2/9/items?after=a&after=b>; rel="next"',
            None,
        ),
        (
            '<https://api.github.com/users/tbhb/projectsV2/9/items?after=abc>; rel="prev"',
            None,
        ),
    ],
)
def test_next_cursor(link: str, expected: str | None) -> None:
    assert next_cursor(link) == expected


@given(st.text(min_size=1).filter(lambda value: all(char.isalnum() for char in value)))
def test_next_cursor_round_trip(cursor: str) -> None:
    link = f'<https://api.github.com/users/tbhb/projectsV2/9/items?after={cursor}>; rel="next"'
    assert next_cursor(link) == cursor


@pytest.mark.parametrize("complete", [True, False])
def test_classify_items_partial_pages(complete: bool) -> None:
    pages = cast(
        "dict[str, list[list[dict[str, Any]]]]", json.loads(FIXTURE.read_text())
    )["pages"]
    result = classify_items(pages, ("Status", "Priority", "Phase", "Worker"), complete)
    assert result["items_seen"] == 2
    assert result["item_identity_count"] == 2
    assert result["field_value_counts"] == {
        "Status": 2,
        "Priority": 1,
        "Phase": 1,
        "Worker": 0,
    }
    assert result["missing_field_value_counts"] == {
        "Status": 0,
        "Priority": 1,
        "Phase": 1,
        "Worker": 2,
    }
    assert result["ready_count"] == 1
    assert result["complete"] is complete


@given(
    st.lists(st.sampled_from(["Status", "Priority", "Phase", "Worker"]), max_size=20)
)
def test_classify_items_count_never_exceeds_items(names: list[str]) -> None:
    pages = [
        [
            {
                "id": number,
                "content": {"number": number},
                "fields": [{"name": name, "value": {"name": "Ready"}}],
            }
        ]
        for number, name in enumerate(names)
    ]
    result = classify_items(pages, ("Status", "Priority", "Phase", "Worker"), True)
    assert all(count <= len(names) for count in result["field_value_counts"].values())


def test_unknown_project_field_is_ignored() -> None:
    result = classify_items(
        [
            [
                {
                    "id": 1,
                    "content": {"number": 1},
                    "fields": [{"name": "Extra", "value": "x"}],
                }
            ]
        ],
        ("Status",),
        True,
    )
    assert result["field_value_counts"] == {"Status": 0}
    assert result["missing_field_value_counts"] == {"Status": 1}


@pytest.mark.parametrize(
    ("actions", "authorized", "expected"),
    [
        ([], True, {}),
        (
            [("created", 5), ("deleted", 6), ("edited", 7)],
            True,
            {"addition": "observed", "removal": "observed", "field_change": "observed"},
        ),
        ([("edited", 11)], True, {}),
        ([("created", 5)], False, {}),
    ],
)
def test_classify_delivery(
    actions: list[tuple[str, int]], authorized: bool, expected: dict[str, str]
) -> None:
    result = classify_delivery(actions, 0, 10, authorized)
    assert result == {
        name: expected.get(name, "unknown")
        for name in ("addition", "removal", "field_change")
    }


@given(
    st.lists(
        st.tuples(
            st.sampled_from(["created", "deleted", "edited"]),
            st.integers(min_value=0, max_value=10),
        ),
        max_size=20,
    )
)
def test_unauthorized_delivery_stays_unknown(actions: list[tuple[str, int]]) -> None:
    assert set(classify_delivery(actions, 0, 10, False).values()) == {"unknown"}


@pytest.mark.parametrize("complete", [True, False])
def test_source_rows_keep_fields_separate_from_labels(complete: bool) -> None:
    summary = classify_items([], ("Status", "Priority", "Phase", "Worker"), complete)
    definitions = {"path": "fields", "status": 200}
    items = {
        "path": "items",
        "api_version": "2026-03-10",
        "status": 200,
        "pagination": "2 pages",
    }
    labels = {
        "path": "issue",
        "api_version": "2026-03-10",
        "status": 200,
        "pagination": "1 page",
    }
    rows = source_rows(summary, "account", definitions, items, labels)
    assert set(rows) == {
        "Ready",
        "Priority",
        "Phase",
        "Worker",
        "item_identity",
        "issue_labels",
    }
    assert rows["Ready"]["definition_path"] == "fields"
    assert rows["Ready"]["source_complete"] is complete
    assert rows["issue_labels"]["separate_from_project_fields"] is True
    assert rows["Priority"]["account"] == "account"


@given(st.integers(min_value=0, max_value=100))
def test_source_rows_preserve_missing_count(missing: int) -> None:
    summary = classify_items([], ("Status", "Priority", "Phase", "Worker"), False)
    summary["missing_field_value_counts"]["Worker"] = missing
    definitions = {"path": "fields", "status": 200}
    items = {
        "path": "items",
        "api_version": "2026-03-10",
        "status": 200,
        "pagination": "1 page",
    }
    labels = {
        "path": "issue",
        "api_version": "2026-03-10",
        "status": 200,
        "pagination": "1 page",
    }
    assert (
        source_rows(summary, "account", definitions, items, labels)["Worker"][
            "missing_count"
        ]
        == missing
    )
