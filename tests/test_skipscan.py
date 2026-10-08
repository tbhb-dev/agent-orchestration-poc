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
    _inert_triple_markers,
    _inline_code,
    _python_string,
    _tracked,
    _triple_spans,
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


@pytest.mark.parametrize("separator", ["# Heading", "  | cell |"])
def test_block_boundaries_after_paragraph(separator: str) -> None:
    expected = (
        ["before", "", "after"]
        if separator.startswith("#")
        else ["before", separator + "\nafter", separator + "\nafter"]
    )
    assert _blocks(["before", separator, "after"]) == expected


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_quote_boundary_positions(value: str) -> None:
    assert not _inline_code(f"`{value}`", 0)
    assert _python_string(repr(value), 0)
    assert not _python_string(repr(value), len(value) + 2)


@pytest.mark.parametrize("line", ["(", "'''unfinished", "  x\n y"])
def test_incomplete_python_tokens_are_not_strings(line: str) -> None:
    assert not _python_string(line, 0)


@pytest.mark.parametrize(
    ("text", "pending", "expected"),
    [
        ("step #2", set(), False),
        ("STEP #2", set(), False),
        ("step #2 then #314", set(), True),
        ("section" + " " * 10 + "#2", set(), True),
        ("queued" + " " * 19 + "RFC-12/34", set(), False),
        ("RFC-12/34", {"RFC-12/34"}, True),
    ],
)
def test_tracking_prefix_and_run_boundaries(
    text: str, pending: set[str], expected: bool
) -> None:
    assert _tracked(text, pending) is expected


@pytest.mark.parametrize(
    ("text", "phrases"),
    [
        ("PARTIAL RESPONSE", []),  # Refs: #314
        ("NARROWED PATH", []),  # Refs: #314
        ("Run 2 SECONDS LATER", []),  # Refs: #314
        ("RUN LATER", ["LATER"]),  # Refs: #314
        ("later test", ["later"]),  # Refs: #314
    ],
)
def test_context_exceptions_preserve_case_insensitivity(
    text: str, phrases: list[str]
) -> None:
    assert [hit["phrase"] for hit in scan_text(text, "body", "body")] == phrases


def test_heading_tracks_its_own_reference() -> None:
    assert scan_text("# Deferred #314", "body", "body")[0]["tracked"]  # Refs: #314


@given(st.integers(min_value=100, max_value=200))
def test_prose_excerpt_uses_match_start(offset: int) -> None:
    text = "x " * offset + "Untested" + " y" * 100  # Refs: #314
    assert scan_text(text, "body", "body")[0]["excerpt"] == (
        "…" + text[2 * offset - 90 : 2 * offset + 150] + "…"
    )


@pytest.mark.parametrize(
    ("path", "changes", "phrase"),
    [
        ("notes.md", "+Deferred RFC-12/34", "Deferred"),  # Refs: #314
        ("build.sh", "+# Deferred RFC-12/34", "Deferred"),  # Refs: #314
        ("test.ts", "+test.skip('case'); // RFC-12/34", ".skip("),  # Refs: #314
        (".github/workflows/ci.yml", "+# run: test RFC-12/34", "commented CI step"),
        (
            ".github/workflows/ci.yml",
            "-run: test\n+# RFC-12/34",
            "removed CI step",
        ),
    ],
)
def test_diff_propagates_pending_runs(path: str, changes: str, phrase: str) -> None:
    diff = f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n{changes}\n"
    assert [
        (hit["phrase"], hit["tracked"])
        for hit in scan_diff(diff, "PR #314", {"RFC-12/34"})
    ] == [(phrase, True)]
    assert [(hit["phrase"], hit["tracked"]) for hit in scan_diff(diff, "PR #314")] == [
        (phrase, False)
    ]


@given(st.integers(min_value=150, max_value=200))
def test_code_excerpt_includes_long_match(spaces: int) -> None:
    content = "x " * 100 + "continue-on-error:" + " " * spaces + "true" + " y" * 100
    diff = f"diff --git a/ci.yml b/ci.yml\n@@ -0,0 +1 @@\n+{content}\n"
    assert scan_diff(diff, "PR #314")[0]["excerpt"] == (
        "…" + content[110 : 200 + 18 + spaces + 4 + 100] + "…"
    )


@pytest.mark.parametrize(
    ("line", "spans"),
    [
        ("# comment", [(0, 9)]),
        ("x = 1", []),
        ("'unfinished", [(0, 11)]),
        ("(", [(0, 1)]),
        ('"""a""" (', [(0, 9)]),
    ],
)
def test_inert_marker_spans(line: str, spans: list[tuple[int, int]]) -> None:
    assert _inert_triple_markers(line) == spans


@given(st.text(alphabet="abc", min_size=1, max_size=30))
def test_triple_span_closure(value: str) -> None:
    line = f'"""{value}"""'
    assert _triple_spans(line, "") == ([(0, len(line))], "")
    assert _triple_spans(value + '"""', '"""') == ([(0, len(value) + 3)], "")
    assert _triple_spans(value, '"""') == ([(0, len(value))], '"""')


def test_triple_marker_after_an_inert_marker() -> None:
    assert _triple_spans('s = \'"""\'; t = """a"""', "") == ([(15, 22)], "")
    assert _triple_spans('"""a""" (', "") == ([], "")
