"""Value and loopback integration tests for the pull request scanner."""

import hashlib
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
        ("Skipped. Answered in thread: https://example.com", False),
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
    assert scan_text(text.replace(r"\n", "\n"), "pr-body", "body") == []


@pytest.mark.parametrize(
    ("text", "phrases"),
    [
        ("Non-blocking findings: none.", []),
        ("Non-blocking findings: none", []),
        ("NON BLOCKING FINDINGS : NONE!", []),
        ("No non-blocking findings.", []),
        ("No non-blocking findings", []),
        ("NO NON BLOCKING FINDINGS !", []),
        ("There are no non blocking findings", []),
        (
            "non-blocking: deferred to a follow-up",
            ["non-blocking", "deferred", "follow-up"],
        ),
        ("Non-blocking findings: one.", ["Non-blocking"]),
        ("Non-blocking findings: nonetheless actionable.", ["Non-blocking"]),
        ("Non-blocking findings: none remain actionable.", ["Non-blocking"]),
        ("Non-blocking items: none.", ["Non-blocking"]),
        ("No non-blocking work remains.", ["non-blocking"]),
        ("No non-blocking findingsXYZ", ["non-blocking"]),
        ("Non-blocking findings: none. Tests skipped.", ["skipped"]),
        ("No non-blocking findings, tests deferred.", ["non-blocking", "deferred"]),
        (
            "No non-blocking findings will be addressed in this PR.",
            ["non-blocking"],
        ),
        (
            "No non-blocking findings were fixed in this PR; they remain open.",
            ["non-blocking"],
        ),
        ("No non-blocking findings are being addressed.", ["non-blocking"]),
        ("No non-blocking findings: all remain open.", ["non-blocking"]),
        ("No non-blocking findings, all remain open.", ["non-blocking"]),
        ("No non-blocking findings; tests deferred.", ["deferred"]),
        ("No findings. Non-blocking work remains.", ["Non-blocking"]),
        ("Non-blocking findings: none; non-blocking task remains.", ["non-blocking"]),
    ],
)
def test_nonblocking_review_findings(text: str, phrases: list[str]) -> None:
    hits = scan_text(text, "review", "review")
    assert [hit["phrase"] for hit in hits] == phrases
    assert all(not hit["tracked"] for hit in hits)


@given(
    st.sampled_from(["Non-blocking findings: none.", "No non-blocking findings."]),
    st.sampled_from([" ", "\n", "; "]),
    st.sampled_from(["non-blocking", "deferred", "skipped", "follow-up"]),
    st.booleans(),
)
def test_no_findings_preserves_independent_indicator(
    statement: str, separator: str, phrase: str, before: bool
) -> None:
    text = phrase + separator + statement if before else statement + separator + phrase
    hits = scan_text(text, "review", "review", with_positions=True)
    assert [(hit["phrase"], hit["tracked"]) for hit in hits] == [(phrase, False)]
    assert hits[0]["position"] == (
        0 if before or "\n" in separator else len(statement + separator)
    )


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
    key_type = "PRIVATE KEY"
    assert (
        redacted_lines(f"-----BEGIN {key_type}-----\nvalue\n-----END {key_type}-----")
        == ["[REDACTED]"] * 3
    )
    assert "privatevalue" not in excerpt("Untested TOKEN=privatevalue")
    assert "Untested" in excerpt("x" * 300 + " Untested TOKEN=privatevalue", 301, 309)
    assert (
        _blocks(["- Skipped", "  REQ-9999", "- Skipped"])[0] == "- Skipped\n  REQ-9999"
    )
    assert _tracked("Queued RFC-9999/9999", set())
    assert _tracked("RFC-9999/9999", {"RFC-9999/9999"})
    blocks = _blocks(["# title", "Skipped", "", "  | a", "Skipped"])
    assert blocks == ["", "Skipped", "", "  | a\nSkipped", "  | a\nSkipped"]


def test_redaction_and_excerpt_boundaries() -> None:
    assert redacted_lines(
        "before\n-----BEGIN CERTIFICATE-----\nsecret\n-----END CERTIFICATE-----\nafter"
    ) == ["before", "[REDACTED]", "[REDACTED]", "[REDACTED]", "after"]
    assert excerpt("-----BEGIN PRIVATE KEY-----") == "[REDACTED]"
    assert excerpt("SECRET=privatevalue") == "[REDACTED]"
    assert excerpt("x " * 120) == ("x " * 120).strip()
    assert excerpt("x " * 121) == "x " * 120 + "…"
    assert excerpt("x " * 250, 200, 201) == "…" + "x " * 120 + "…"
    assert excerpt("x " * 250, 100, 300) == "…" + "x " * 195 + "…"
    assert excerpt("x " * 250, 200, 500) == "…" + ("x " * 195).strip()


def test_fence_boundaries() -> None:
    for language in ("sh", "bash", "shell", "console", "output", "text", "zsh"):
        assert scan_text(f"```{language}\nSkipped\n```", "body", "body") == []
    assert [
        hit["line"] for hit in scan_text("```sh\nSkipped\n```\nSkipped", "body", "body")
    ] == [4]
    assert [
        hit["line"] for hit in scan_text("```python\nSkipped\n```", "body", "body")
    ] == [2]


def test_flag_id_canonical_digest() -> None:
    assert (
        flag_id("path", 7, "SkIp")
        == hashlib.sha256(b"path\x007\x00skip").hexdigest()[:20]
    )


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


DIFF_CASES = []
for row in (
    (Path(__file__).parent / "fixtures/skipscan/diffs.tsv").read_text().splitlines()
):
    diff, hits, _reference = row.split("\t")
    DIFF_CASES.append({"diff": json.loads(diff), "hits": json.loads(hits)})


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


@pytest.mark.parametrize(
    ("path", "old", "new"),
    [
        (".gremlins.yaml", "efficacy: 90", "efficacy: 10"),
        (".gremlins.yaml", "mutant-coverage: 90", "mutant-coverage: 10"),
        ("pyproject.toml", "fail_under = 95", "fail_under = 10"),
    ],
)
def test_actual_threshold_reductions(path: str, old: str, new: str) -> None:
    diff = f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"
    assert [hit["phrase"] for hit in scan_diff(diff, "PR #300")] == [
        "lowered threshold"
    ]


def test_python_skip_outside_triple_quoted_reason() -> None:
    diff = (
        "diff --git a/test_a.py b/test_a.py\n@@ -0,0 +1,2 @@\n"
        '+pytest.skip("""unsupported""")\n'
        '+reason = """closed"""; pytest.skip("real")\n'
    )
    assert [hit["phrase"] for hit in scan_diff(diff, "PR #300")] == [
        "pytest.skip",
        "pytest.skip",
    ]


@pytest.mark.parametrize(
    "first_line",
    ['# A triple-quoted reason starts with """', 'delimiter = \'"""\''],
)
def test_python_skip_after_inert_triple_marker(first_line: str) -> None:
    diff = (
        "diff --git a/test_a.py b/test_a.py\n@@ -0,0 +1,2 @@\n"
        f"+{first_line}\n"
        '+pytest.skip("unsupported")\n'
    )
    assert [
        (hit["line"], hit["phrase"], hit["tracked"])
        for hit in scan_diff(diff, "PR #300")
    ] == [(2, "pytest.skip", False)]


def test_python_skip_after_distant_inert_triple_marker() -> None:
    diff = (
        "diff --git a/test_a.py b/test_a.py\n@@ -0,0 +1,21 @@\n"
        '+# A comment contains """\n'
        + "+ordinary = 1\n" * 19
        + '+pytest.skip("unsupported")\n'
    )
    assert [(hit["line"], hit["phrase"]) for hit in scan_diff(diff, "PR #300")] == [
        (21, "pytest.skip")
    ]


def test_python_skip_after_uncertain_quote_state() -> None:
    diff = (
        "diff --git a/test_a.py b/test_a.py\n@@ -0,0 +1,2 @@\n"
        '+value = \'unfinished """\n'
        '+pytest.skip("unsupported")\n'
    )
    assert [(hit["line"], hit["phrase"]) for hit in scan_diff(diff, "PR #300")] == [
        (2, "pytest.skip")
    ]


@pytest.mark.parametrize(
    ("path", "content", "phrases"),
    [
        (
            "worker.py",
            'pattern = "pytest.skip" # Deferred until tomorrow',
            ["Deferred"],
        ),
        ("worker.py", 'pattern = "skipped" # skipped deployment', ["skipped"]),
        ("build.sh", "echo ready || true # skipped deployment", ["skipped"]),
        ("worker.py", "queue.skip(TODO)", ["TODO"]),
    ],
)
def test_prose_survives_rejected_code_match(
    path: str, content: str, phrases: list[str]
) -> None:
    diff = f"diff --git a/{path} b/{path}\n@@ -0,0 +1 @@\n+{content}\n"
    assert [hit["phrase"] for hit in scan_diff(diff, "PR #300")] == phrases


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("No test was skipped; deployment was skipped.", "skipped"),
        ("No request was denied; deployment was denied.", "denied"),
        ("No work was blocked; deployment was blocked.", "blocked"),
    ],
)
def test_negation_applies_to_current_clause(text: str, phrase: str) -> None:
    hits = scan_text(text, "body", "body")
    assert [(hit["phrase"], hit["tracked"]) for hit in hits] == [(phrase, False)]


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_redaction_preserves_plain_lines(value: str) -> None:
    assert redacted_lines(value + "\n" + value) == [value, value]
    assert excerpt("  " + value + "  ") == value


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_inline_and_python_string_locations(value: str) -> None:
    assert _inline_code(f"`{value}`", 1)
    assert not _inline_code(value, 0)
    assert not _inline_code("`a` `b`", 2)
    assert _inline_code("`a` `b`", 5)
    assert _python_string(repr(value), 1)
    assert not _python_string(f"x = {value}", 0)


@given(st.integers(min_value=1, max_value=999999))
def test_tracking_references_are_local(number: int) -> None:
    assert _tracked(f"Skipped #{number}", set())  # Refs: #300
    assert not _tracked(f"Skipped step #{number}", set())  # Refs: #300
    assert _tracked(f"Queued RFC-{number}/{number}", set())
    assert not _tracked(f"RFC-{number}/{number}", set())


@given(st.text(alphabet="abc", min_size=1, max_size=20))
def test_blocks_and_uniqueness(value: str) -> None:
    word = "Skipped"
    lines = [f"- {word} {value}", "  #300", f"- {word} {value}"]
    assert _blocks(lines) == [f"- {word} {value}\n  #300"] * 2 + [lines[2]]
    hits = [{"id": value}, {"id": value}]
    assert _unique(hits) == hits[:1]
