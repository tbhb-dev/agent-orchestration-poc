"""Value and loopback integration tests for the pull request scanner."""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.skipscan import (
    CODE_RE,
    _blocks,
    _inline_code,
    _python_string,
    _tracked,
    _unique,
    excerpt,
    flag_id,
    redacted_lines,
    scan_diff,
    scan_text,
)

CASES: dict[str, list[str]] = {"prose": [], "code": [], "negative": []}
for row in (
    (Path(__file__).parent / "fixtures/skipscan/cases.tsv").read_text().splitlines()
):
    kind, value, _reference = row.split("\t")
    CASES[kind].append(value)


@pytest.mark.parametrize(
    ("text", "tracked"),
    [
        ("The test was untested", False),
        ("The test was skipped. #300", True),
        ("Deferred, see REQ-9999", True),
        ("Deferred under ADR-9999", True),
        ("Deferred for queued RFC-9999/9999", True),
        ("Deferred for RFC-9999/9999", False),
        ("Skipped step #2", False),
        ("Skipped. Answered in thread: https://github.com/o/r/pull/2", True),
        ("Skipped. https://github.com/o/r/issues/300", True),
    ],
)
def test_tracking(text: str, tracked: bool) -> None:
    assert scan_text(text, "pr-body", "body")[0]["tracked"] is tracked


@pytest.mark.parametrize("phrase", CASES["prose"])
def test_prose_table(phrase: str) -> None:
    assert scan_text(f"The work was {phrase}", "pr-body", "body")


@pytest.mark.parametrize("text", CASES["negative"])
def test_context_that_does_not_indicate_a_gap(text: str) -> None:
    assert scan_text(text, "pr-body", "body") == []


@pytest.mark.parametrize("code", CASES["code"])
def test_code_table(code: str) -> None:
    path = "test.ts" if code.startswith("test.skip") else "check.yml"
    diff = f"diff --git a/{path} b/{path}\n@@ -0,0 +1 @@\n+{code}\n"
    phrase = CODE_RE.search(code)
    assert phrase is not None
    source = f"PR #300:{path}"
    assert scan_diff(diff, "PR #300") == [
        {
            "id": flag_id(source, 1, phrase.group()),
            "kind": "diff",
            "source": source,
            "line": 1,
            "phrase": phrase.group(),
            "excerpt": excerpt(code),
            "tracked": False,
        }
    ]


@given(
    st.integers(min_value=1, max_value=200),
    st.sampled_from(CASES["code"]),
    st.booleans(),
)
def test_code_hit_location_and_tracking(line: int, code: str, tracked: bool) -> None:
    path = "test.ts" if code.startswith("test.skip") else "check.yml"
    content = f"{code} #300" if tracked else code
    diff = f"diff --git a/{path} b/{path}\n@@ -0,0 +{line} @@\n+{content}\n"
    phrase = CODE_RE.search(code)
    assert phrase is not None
    source = f"PR #300:{path}"
    assert scan_diff(diff, "PR #300") == [
        {
            "id": flag_id(source, line, phrase.group()),
            "kind": "diff",
            "source": source,
            "line": line,
            "phrase": phrase.group(),
            "excerpt": excerpt(content),
            "tracked": tracked,
        }
    ]


def test_redaction_and_blocks() -> None:
    assert (
        redacted_lines("-----BEGIN PRIVATE KEY-----\nvalue\n-----END PRIVATE KEY-----")
        == ["[REDACTED]"] * 3
    )
    assert "privatevalue" not in excerpt("Untested TOKEN=privatevalue")
    assert "Untested" in excerpt("x" * 300 + " Untested TOKEN=privatevalue", 301, 309)
    assert (
        _blocks(["- Skipped", "  REQ-9999", "- Skipped"])[0] == "- Skipped\n  REQ-9999"
    )
    assert _tracked("Queued RFC-9999/9999", set())
    assert _tracked("RFC-9999/9999", {"RFC-9999/9999"})


@given(st.integers(min_value=0, max_value=100), st.booleans())
def test_text_location_and_tracking(prefix_lines: int, tracked: bool) -> None:
    line = "skipped #300" if tracked else "skipped"
    text = "plain\n" * prefix_lines + line
    assert scan_text(text, "pr-body", "PR #300 body") == [
        {
            "id": flag_id("PR #300 body", prefix_lines + 1, "skipped"),
            "kind": "pr-body",
            "source": "PR #300 body",
            "line": prefix_lines + 1,
            "phrase": "skipped",
            "excerpt": line,
            "tracked": tracked,
        }
    ]


@given(
    st.integers(min_value=1, max_value=100000), st.text(alphabet="abcXYZ", min_size=1)
)
def test_flag_id_is_stable_and_location_sensitive(line: int, phrase: str) -> None:
    assert flag_id("path", line, phrase) == flag_id("path", line, phrase.upper())
    assert flag_id("path", line, phrase) != flag_id("path", line + 1, phrase)


DIFF_CASES = json.loads(
    (Path(__file__).parent / "fixtures/skipscan/diffs.json").read_text()
)


@pytest.mark.parametrize("case", DIFF_CASES)
def test_diff_cases(case: dict[str, Any]) -> None:
    expected = []
    for path, line, phrase, tracked, content in case["hits"]:
        source = f"PR #300:{path}"
        expected.append(
            {
                "id": flag_id(source, line, phrase),
                "kind": "diff",
                "source": source,
                "line": line,
                "phrase": phrase,
                "excerpt": content,
                "tracked": tracked,
            }
        )
    assert scan_diff(case["diff"], "PR #300") == expected


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_redaction_preserves_plain_lines(value: str) -> None:
    assert redacted_lines(value + "\n" + value) == [value, value]
    assert excerpt("  " + value + "  ") == value


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_inline_and_python_string_locations(value: str) -> None:
    assert _inline_code(f"`{value}`", 1)
    assert not _inline_code(value, 0)
    assert _python_string(repr(value), 1)
    assert not _python_string(f"x = {value}", 0)


@given(st.integers(min_value=1, max_value=999999))
def test_tracking_references_are_local(number: int) -> None:
    assert _tracked(f"Skipped #{number}", set())
    assert not _tracked(f"Skipped step #{number}", set())
    assert _tracked(f"Queued RFC-{number}/{number}", set())
    assert not _tracked(f"RFC-{number}/{number}", set())


@given(st.text(alphabet="abc", min_size=1, max_size=20))
def test_blocks_and_uniqueness(value: str) -> None:
    lines = [f"- Skipped {value}", "  #300", f"- Skipped {value}"]
    assert _blocks(lines) == [f"- Skipped {value}\n  #300"] * 2 + [lines[2]]
    hits = [{"id": value}, {"id": value}]
    assert _unique(hits) == hits[:1]
