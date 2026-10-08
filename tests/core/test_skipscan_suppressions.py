"""Exemption corpus and non-interference properties for issue #318."""

from difflib import unified_diff

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.skipscan import (
    _fenced_lines,
    _python_spans,
    scan_diff,
    scan_text,
)

# Each pair contains an exempt occurrence and an independent reportable occurrence.
PROSE_CASES = [
    ("No test was skipped", "deployment was skipped"),
    ("No planned check was skipped", "deployment was skipped"),
    *(
        (f"No request was {word}", f"deployment was {word}")
        for word in ("denied", "refused", "blocked")
    ),
    *(
        (f"Nothing was {word}", f"deployment was {word}")
        for word in ("denied", "refused", "blocked")
    ),
    *(
        (f"partial {noun}", "partial delivery")  # Exemption corpus for #318
        for noun in ("manifest", "file", "page", "read", "write", "response", "failure")
    ),
    *(
        (f"narrowed {noun}", "narrowed testing")  # Exemption corpus for #318
        for noun in ("path", "prefix", "mount", "grant")
    ),
    ("assumed role", "assumed success"),
    ("The response arrived 2 ms later", "run checks later"),
    ("We met at a later date", "run checks later"),
    ("We arrived later", "run checks later"),
    ("The `skipped` value", "deployment was skipped"),
]
FENCE_LANGUAGES = ("sh", "bash", "shell", "console", "output", "text", "zsh")
CODE_CASES = [
    ("worker.py", 'value = "skipped"', "# skipped deployment", "skipped"),
    ("worker.py", 'value = "pytest.skip"', 'pytest.skip("real")', "pytest.skip"),
    ("worker.py", 'value = """pytest.skip"""', 'pytest.skip("real")', "pytest.skip"),
    (
        "worker.py",
        'value = """\npytest.skip\n"""',
        'pytest.skip("real")',
        "pytest.skip",
    ),
    ("worker.py", "queue.skip()", "# TODO testing", "TODO"),
    ("worker.ts", "queue.skip()", "todo!()", "todo!("),
    ("build.sh", "echo ready || true", "pytest || true", "|| true"),
]


def added_diff(path: str, text: str, line: int = 1) -> str:
    lines = text.splitlines()
    return (
        f"diff --git a/{path} b/{path}\n@@ -0,0 +{line},{len(lines)} @@\n"
        + "\n".join("+" + value for value in lines)
        + "\n"
    )


@pytest.mark.parametrize(("exempt", "independent"), PROSE_CASES)
def test_natural_text_exemptions(exempt: str, independent: str) -> None:
    assert scan_text(exempt, "body", "body") == []
    assert scan_text(independent, "body", "body")


def test_narrowed_permission_exempts_only_narrowed() -> None:
    assert [
        hit["phrase"]
        for hit in scan_text("narrowed permission, narrowed testing", "body", "body")
    ] == ["permission", "narrowed"]


@given(
    st.sampled_from(("; ", ", but ", " and ", ". ", "\n", "\n\n")),
    st.integers(min_value=0, max_value=20),
)
def test_every_prose_exemption_preserves_later_occurrence(
    separator: str, padding: int
) -> None:
    for exempt, independent in PROSE_CASES:
        prefix = exempt + separator + "ordinary " * padding
        text = prefix + independent
        line = prefix.count("\n") + 1
        offset = len(prefix.rsplit("\n", 1)[-1])
        expected = scan_text(independent, "body", "body", with_positions=True)
        hits = scan_text(text, "body", "body", with_positions=True)
        for hit in expected:
            assert any(
                candidate["phrase"] == hit["phrase"]
                and candidate["line"] == line
                and candidate["position"] == offset + hit["position"]
                and not candidate["tracked"]
                for candidate in hits
            ), text


@pytest.mark.parametrize("language", FENCE_LANGUAGES)
@given(st.sampled_from(("```", "~~~", "````")), st.integers(min_value=1, max_value=20))
def test_closed_fence_preserves_later_text(
    language: str, marker: str, count: int
) -> None:
    prefix = f"{marker}{language}\n" + "skipped\n" * count + marker + "\n"
    assert scan_text(prefix, "body", "body") == []
    hits = scan_text(prefix + "skipped deployment", "body", "body")
    assert [(hit["line"], hit["phrase"]) for hit in hits] == [(count + 3, "skipped")]
    assert [
        (hit["line"], hit["phrase"])
        for hit in scan_diff(
            added_diff("note.md", prefix + "skipped deployment"), "diff"
        )
    ] == [(count + 3, "skipped")]


@pytest.mark.parametrize(
    "text",
    [
        "The ``skipped`` value",
        "```text\nskipped deployment",
        "```text\n``` skipped deployment",
        "```python skipped deployment",
    ],
)
def test_ambiguous_markdown_reports(text: str) -> None:
    assert any(hit["phrase"] == "skipped" for hit in scan_text(text, "body", "body"))


@pytest.mark.parametrize("case", CODE_CASES)
@given(st.sampled_from(("; ", "\n", "\n\n")), st.integers(min_value=1, max_value=100))
def test_code_exemption_preserves_later_occurrence(
    case: tuple[str, str, str, str], separator: str, line: int
) -> None:
    path, exempt, independent, phrase = case
    assert scan_diff(added_diff(path, exempt), "diff") == []
    prefix = exempt + separator
    hits = scan_diff(added_diff(path, prefix + independent, line), "diff")
    assert any(
        hit["phrase"] == phrase
        and hit["line"] == line + prefix.count("\n")
        and not hit["tracked"]
        for hit in hits
    )


@pytest.mark.parametrize(
    "text",
    [
        'value = """\ntext\n""" # another """\npytest.skip("real")',
        'value = """\ntext\n"""; delimiter = \'"""\'\npytest.skip("real")',
        'value = """unfinished\npytest.skip("real")',
    ],
)
def test_uncertain_python_span_reports(text: str) -> None:
    hits = scan_diff(added_diff("worker.py", text), "diff")
    assert any(
        hit["phrase"] == "pytest.skip" and hit["line"] == len(text.splitlines())
        for hit in hits
    )


@given(st.integers(min_value=10, max_value=100))
def test_span_state_does_not_cross_missing_hunk_context(line: int) -> None:
    diff = added_diff("worker.py", 'value = """unfinished')
    diff += f'@@ -{line},0 +{line} @@\n+pytest.skip("real")\n'  # Fixture for #318
    assert any(
        hit["line"] == line and hit["phrase"] == "pytest.skip"
        for hit in scan_diff(diff, "diff")
    )


@pytest.mark.parametrize("quote", ['"""', "'''"])
@pytest.mark.parametrize("statement", ['pytest.skip("real")', "# skipped deployment"])
@given(st.integers(min_value=3, max_value=30))
def test_hunk_starting_inside_docstring_reports(
    quote: str, statement: str, padding: int
) -> None:
    prefix = quote + "\n" + "more documentation\n" * padding + quote + "\n"
    suffix = quote + "Another string." + quote + "\n"
    before = prefix + "pass\n" + suffix
    after = prefix + statement + "\n" + suffix
    compile(after, "worker.py", "exec")
    diff = "diff --git a/worker.py b/worker.py\n" + "".join(
        unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/worker.py",
            tofile="b/worker.py",
        )
    )
    expected = scan_diff(added_diff("worker.py", statement, padding + 3), "diff")
    assert expected
    assert scan_diff(diff, "diff") == expected


@pytest.mark.parametrize(("path", "exempt", "independent", "phrase"), CODE_CASES)
def test_exemption_does_not_cross_files(
    path: str, exempt: str, independent: str, phrase: str
) -> None:
    diff = added_diff(path, exempt) + added_diff("next/" + path, independent)
    assert any(
        hit["phrase"] == phrase and hit["source"] == "diff:next/" + path
        for hit in scan_diff(diff, "diff")
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('value = "plain"', [((1, 8), (1, 15))]),
        (
            'value = """\nplain\n"""; other = "x"',
            [((1, 8), (3, 3)), ((3, 13), (3, 16))],
        ),
        ('# """\ncall()', []),
        ('value = """unfinished', []),
        ("    x = 1\n  pytest.skip()", []),
        ('f"{pytest.skip()}"', []),
    ],
)
def test_python_string_token_boundaries(
    text: str, expected: list[tuple[tuple[int, int], tuple[int, int]]]
) -> None:
    assert _python_spans(text) == expected


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["```text", "skipped", "~~~"], set()),
        (["````text", "```", "skipped"], set()),
        (["```text", "```python", "skipped"], set()),
        (["```python", "skipped", "```"], set()),
        (["```text", "skipped", "````"], {0, 1, 2}),
        (["  ~~~TEXT ", "skipped", "~~~", "skipped"], {0, 1, 2}),
    ],
)
def test_fence_boundaries(lines: list[str], expected: set[int]) -> None:
    assert _fenced_lines(lines) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Move checks to a later run",
        "No request was denied but deployment was denied",
        "Nothing was blocked and deployment was blocked",
        "The reply came 2 ms later, run checks later",
    ],
)
def test_adversarial_natural_text_reports(text: str) -> None:
    hits = scan_text(text, "body", "body", with_positions=True)
    assert len(hits) == 1
    assert hits[0]["position"] == text.rfind(hits[0]["phrase"])
    assert not hits[0]["tracked"]
