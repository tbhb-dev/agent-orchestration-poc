"""Value and loopback integration tests for the pull request scanner."""

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.skipscan import (
    CODE,
    _blocks,
    _tracked,
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
    assert len(CODE) == 20
    path = "test.ts" if code.startswith("test.skip") else "check.yml"
    diff = f"diff --git a/{path} b/{path}\n@@ -0,0 +1 @@\n+{code}\n"
    assert scan_diff(diff, "PR #300"), code


def test_diff_tracks_added_line_and_detects_weaker_checks() -> None:
    diff = """diff --git a/.github/workflows/check.yml b/.github/workflows/check.yml
@@ -1,3 +1,3 @@
-  - name: Test
-    run: pytest
-coverage-min-threshold: 90
+# - name: Test #300
+coverage-min-threshold: 60
+continue-on-error: true #300
"""
    hits = scan_diff(diff, "PR #300")
    phrases = {hit["phrase"] for hit in hits}
    assert {
        "removed CI step",
        "commented CI step",
        "lowered threshold",
        "continue-on-error: true",
    } <= phrases
    assert next(hit for hit in hits if hit["phrase"] == "commented CI step")["tracked"]
    assert (
        next(hit for hit in hits if hit["phrase"] == "lowered threshold")["line"] == 2
    )


def test_markdown_diff_uses_paragraph_local_reference() -> None:
    diff = """diff --git a/note.md b/note.md
@@ -0,0 +1,3 @@
+- The test was skipped #300
+- Another test was skipped
+
"""
    hits = scan_diff(diff, "PR #300")
    assert [hit["tracked"] for hit in hits] == [True, False]
    assert [hit["line"] for hit in hits] == [1, 2]


def test_python_fixture_does_not_disable_a_test() -> None:
    diff = """diff --git a/test.py b/test.py
@@ -0,0 +1,2 @@
+pattern = "pytest.skip" #300
+pytest.skip("real") #300
"""
    assert [hit["phrase"] for hit in scan_diff(diff, "PR #300")] == ["pytest.skip"]


def test_code_comment_prose_is_scanned() -> None:
    diff = "diff --git a/worker.py b/worker.py\n@@ -0,0 +1 @@\n+# test was skipped\n"
    assert scan_diff(diff, "PR #300")[0]["phrase"] == "skipped"


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


@given(
    st.integers(min_value=1, max_value=100000), st.text(alphabet="abcXYZ", min_size=1)
)
def test_flag_id_is_stable_and_location_sensitive(line: int, phrase: str) -> None:
    assert flag_id("path", line, phrase) == flag_id("path", line, phrase.upper())
    assert flag_id("path", line, phrase) != flag_id("path", line + 1, phrase)


@given(st.text(alphabet="abcXYZ012", max_size=80))
def test_plain_text_without_indicator_has_no_hit(value: str) -> None:
    assert scan_text(value, "pr-body", "body") == []
