"""Plain-value counter tests and pinned scc fixture observations."""

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.pr_size import (
    Classification,
    FileResult,
    _git_lines,
    changed_fragments,
    classify_samples,
    exclusion_reason,
    measure_file,
    needs_scc,
    parse_name_status,
    total_units,
)

CASES = cast(
    "list[dict[str, Any]]",
    json.loads((Path(__file__).parent / "fixtures/pr_size/cases.json").read_text()),
)
PATTERNS = ("uv.lock", "**/vendor/**", "tests/fixtures/**")


def _git(tmp_path: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=tmp_path, capture_output=True, check=True)


def _init_pr_size_repo(tmp_path: Path, exclusions: str) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "config").mkdir()
    (tmp_path / "config/workflow-reference.toml").write_text(
        f"[size]\nexcluded = {exclusions}\n"
    )


@pytest.mark.parametrize(
    ("before", "after", "removed", "added"),
    [
        ("x\n", "y\n", ("x\n",), ("y\n",)),
        ("x\n", "x\n", (), ()),
        ("a\nb\n", "b\n", ("a\n",), ()),
        ("", "x\n", (), ("x\n",)),
    ],
)
def test_changed_fragments(
    before: str, after: str, removed: tuple[str, ...], added: tuple[str, ...]
) -> None:
    assert (
        changed_fragments(before, after).removed,
        changed_fragments(before, after).added,
    ) == (removed, added)


@given(
    st.lists(
        st.text(alphabet=st.characters(blacklist_characters="\n"), min_size=1),
        max_size=20,
    )
)
def test_added_lines_are_retained(lines: list[str]) -> None:
    added = "".join(f"{line}\n" for line in lines)
    assert changed_fragments("", added).added == tuple(f"{line}\n" for line in lines)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", ()),
        ("a\n", ("a\n",)),
        ("a\nb", ("a\n", "b")),
        ("\x85\n", ("\x85\n",)),
    ],
)
def test_git_lines(content: str, expected: tuple[str, ...]) -> None:
    assert _git_lines(content) == expected


@given(st.text())
def test_git_lines_round_trip(content: str) -> None:
    assert "".join(_git_lines(content)) == content


@pytest.mark.parametrize(
    ("path", "old", "expected"),
    [
        ("uv.lock", None, "path:uv.lock"),
        ("src/vendor/x.py", None, "path:**/vendor/**"),
        ("new.py", "tests/fixtures/old.py", "path:tests/fixtures/**"),
        ("src/main.py", None, None),
    ],
)
def test_exclusion_reason(path: str, old: str | None, expected: str | None) -> None:
    assert exclusion_reason(path, old, PATTERNS) == expected


@given(st.text(alphabet="abc/._", min_size=1))
def test_empty_exclusions_never_match(path: str) -> None:
    assert exclusion_reason(path, None, ()) is None


@pytest.mark.parametrize(
    ("path", "old", "binary", "expected"),
    [
        ("src/a.py", None, False, True),
        ("uv.lock", None, False, False),
        ("new.py", "tests/fixtures/old.py", False, False),
        ("src/a.py", None, True, False),
    ],
)
def test_needs_scc(path: str, old: str | None, binary: bool, expected: bool) -> None:
    assert needs_scc(path, old, PATTERNS, binary) is expected


@given(st.text(min_size=1))
def test_binary_never_needs_scc(path: str) -> None:
    assert not needs_scc(path, None, (), True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"", ()),
        (b"M\0a.py\0", (("a.py", None, "M"),)),
        (b"A\0a.py\0D\0b.py\0", (("a.py", None, "A"), ("b.py", None, "D"))),
        (b"R075\0old.py\0new.py\0", (("new.py", "old.py", "R075"),)),
    ],
)
def test_parse_name_status(
    raw: bytes, expected: tuple[tuple[str, str | None, str], ...]
) -> None:
    assert parse_name_status(raw) == expected


@given(st.text(alphabet="abc._/", min_size=1))
def test_parse_modified_name(path: str) -> None:
    assert parse_name_status(b"M\0" + path.encode() + b"\0") == ((path, None, "M"),)


@pytest.mark.parametrize(
    ("full", "generated", "minified"),
    [
        ((), False, False),
        (((1, False, False),), False, False),
        (((1, True, False),), True, False),
        (((1, False, False), (1, False, True)), False, True),
    ],
)
def test_classify_samples(
    full: tuple[tuple[int, bool, bool], ...], generated: bool, minified: bool
) -> None:
    assert classify_samples(full, 2, 3) == Classification(2, 3, generated, minified)


@given(st.integers(min_value=0), st.integers(min_value=0))
def test_classify_samples_keeps_fragment_counts(removed: int, added: int) -> None:
    result = classify_samples(((4, False, False),), removed, added)
    assert (result.removed_code, result.added_code) == (removed, added)


@pytest.mark.parametrize(
    ("path", "classification", "binary", "expected", "reason"),
    [
        ("a.py", Classification(1, 2), False, 3, None),
        ("a.md", Classification(0, 0), False, 2, None),
        ("a.py", Classification(1, 2, generated=True), False, 0, "scc:generated"),
        ("a.py", Classification(1, 2, minified=True), False, 0, "scc:minified"),
        ("a.py", Classification(1, 2), True, 0, "binary"),
        ("uv.lock", Classification(1, 2), False, 0, "path:uv.lock"),
    ],
)
def test_measure_file(
    path: str,
    classification: Classification,
    binary: bool,
    expected: int,
    reason: str | None,
) -> None:
    classified = Classification(
        classification.removed_code,
        classification.added_code,
        classification.generated,
        classification.minified,
        binary,
    )
    result = measure_file(
        path, None, changed_fragments("old\n", "new\n"), classified, PATTERNS
    )
    assert (
        result.raw_added,
        result.raw_deleted,
        result.counted_units,
        result.exclusion_reason,
    ) == (1, 1, expected, reason)


@given(st.lists(st.integers(min_value=0, max_value=100), max_size=20))
def test_total_units(values: list[int]) -> None:
    results = tuple(
        FileResult(str(index), None, 0, 0, value, None)
        for index, value in enumerate(values)
    )
    assert total_units(results) == sum(values)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((), 0),
        ((0,), 0),
        ((2, 3), 5),
    ],
)
def test_total_units_table(values: tuple[int, ...], expected: int) -> None:
    results = tuple(
        FileResult(str(index), None, 0, 0, value, None)
        for index, value in enumerate(values)
    )
    assert total_units(results) == expected


@given(
    st.integers(min_value=0, max_value=1000), st.integers(min_value=0, max_value=1000)
)
def test_measure_code_adds_both_sides(removed: int, added: int) -> None:
    result = measure_file(
        "src/file.py",
        None,
        changed_fragments("old\n", "new\n"),
        Classification(removed, added),
        (),
    )
    assert result.counted_units == removed + added


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=lambda case: str(case["name"]))
def test_scc_contract_fixture(case: dict[str, Any]) -> None:
    from agent_orchestration_poc.shell.pr_size import (  # noqa: PLC0415 - mutmut copies only the core package
        _scc,
    )

    before = str(case["before"]) * int(case.get("repeat", 1))
    after = str(case["after"]) * int(case.get("repeat", 1))
    path = str(case["path"])
    old_path = cast("str | None", case.get("old_path"))
    fragments = changed_fragments(before, after)
    suffix = Path(path).suffix
    full = tuple(_scc(text.encode(), suffix) for text in (before, after) if text)
    if case["name"] in {"rename", "multiline-comment-fragment"}:
        assert full[0][0] == full[1][0]
    generated = any(item[1] for item in full)
    minified = any(item[2] for item in full)
    removed_code = _scc("".join(fragments.removed).encode(), suffix)[0]
    added_code = _scc("".join(fragments.added).encode(), suffix)[0]
    result = measure_file(
        path,
        old_path,
        fragments,
        Classification(removed_code, added_code, generated, minified),
        PATTERNS,
    )
    sys.stdout.write(
        json.dumps(
            {
                "fixture": case["name"],
                "verdict": "fail" if result.counted_units > 800 else "pass",
                **asdict(result),
            },
            sort_keys=True,
        )
        + "\n"
    )
    assert (
        result.raw_added,
        result.raw_deleted,
        result.counted_units,
        result.exclusion_reason,
    ) == (case["added"], case["deleted"], case["units"], case["reason"])


@pytest.mark.integration
def test_shell_counts_git_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agent_orchestration_poc.shell import (  # noqa: PLC0415 - mutmut copies only the core package
        pr_size as pr_size_shell,
    )

    _init_pr_size_repo(tmp_path, '["uv.lock"]')
    (tmp_path / "old.py").write_text("value = 1\nkeep = 1\nkeep = 2\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "branch", "base")
    (tmp_path / "old.py").rename(tmp_path / "new.py")
    (tmp_path / "new.py").write_text("value = 2\nkeep = 1\nkeep = 2\n")
    (tmp_path / "uv.lock").write_text("lock\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "head")
    monkeypatch.setattr(pr_size_shell, "ROOT", tmp_path)
    results = pr_size_shell.count("base")
    assert [
        (row.path, row.raw_added, row.raw_deleted, row.counted_units) for row in results
    ] == [
        ("new.py", 1, 1, 2),
        ("uv.lock", 1, 0, 0),
    ]


@pytest.mark.integration
def test_shell_counts_makefile_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agent_orchestration_poc.shell import (  # noqa: PLC0415 - mutmut copies only the core package
        pr_size as pr_size_shell,
    )

    _init_pr_size_repo(tmp_path, "[]")
    (tmp_path / "Makefile").write_text("all:\n\techo old\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "branch", "base")
    (tmp_path / "Makefile").write_text("all:\n\techo new\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "head")
    monkeypatch.setattr(pr_size_shell, "ROOT", tmp_path)
    assert pr_size_shell.count("base")[0].counted_units == 2


@pytest.mark.integration
def test_shell_counts_extensionless_script_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agent_orchestration_poc.shell import (  # noqa: PLC0415 - mutmut copies only the core package
        pr_size as pr_size_shell,
    )

    _init_pr_size_repo(tmp_path, "[]")
    (tmp_path / "script").write_text("#!/bin/sh\necho old\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "branch", "base")
    (tmp_path / "script").write_text("#!/bin/sh\necho new\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "head")
    monkeypatch.setattr(pr_size_shell, "ROOT", tmp_path)
    assert pr_size_shell.count("base")[0].counted_units == 2
    _git(tmp_path, "branch", "code-head")
    (tmp_path / "script").write_text("#!/bin/sh\n# new comment\necho new\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "comment")
    assert pr_size_shell.count("code-head")[0].counted_units == 0


@pytest.mark.integration
def test_cli_json_channels() -> None:
    script = (
        "import logging, sys; "
        "from agent_orchestration_poc.shell import pr_size; "
        "from agent_orchestration_poc.core.pr_size import FileResult; "
        "logging.basicConfig(level=logging.INFO, format='%(message)s'); "
        "pr_size.count = lambda base, head: (FileResult('a.py', None, 1, 0, 1, None),); "
        "sys.argv = ['pr_size', 'base']; "
        "raise SystemExit(pr_size.main())"
    )
    result = subprocess.run(
        (sys.executable, "-c", script), capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["total_units"] == 1
    assert result.stderr == ""
    failure = script.replace(
        "(FileResult('a.py', None, 1, 0, 1, None),)",
        "(_ for _ in ()).throw(RuntimeError('fixture error'))",
    )
    result = subprocess.run(
        (sys.executable, "-c", failure), capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "PR size unavailable" in result.stderr
