"""Table and property checks for analysis notebook gates."""

import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.analysis.notebooks import (
    is_private_notebook,
    privacy_findings,
    split_qmd,
    supporting_sample,
)

FIXTURES = Path("tests/fixtures/analysis")


@pytest.mark.parametrize(
    ("source", "prose", "code"),
    [
        ("# Heading\n", "# Heading\n", ""),
        (
            "Before\n```{python}\nx = 1\n```\nAfter\n",
            "Before\n```python\n```\nAfter\n",
            "x = 1\n",
        ),
        ("```text\nhello\n```\n", "```text\nhello\n```\n", ""),
    ],
)
def test_split_qmd(source: str, prose: str, code: str) -> None:
    """Separate text and Python cells without changing other fences."""
    assert split_qmd(source) == (prose, code)


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz\n", max_size=100))
def test_split_qmd_plain_text_is_preserved(source: str) -> None:
    """Ordinary prose is never discarded."""
    assert split_qmd(source) == (source, "")


def test_split_qmd_rejects_unclosed_fence() -> None:
    """Do not pass incomplete code to Ruff."""
    with pytest.raises(ValueError, match="unclosed"):
        split_qmd("```{python}\nvalue = 1\n")


@pytest.mark.parametrize(
    ("row_ids", "expected_length"),
    [([], 0), (["A", "B"], 2), ([str(value) for value in range(12)], 10)],
)
def test_supporting_sample(row_ids: list[str], expected_length: int) -> None:
    """Use at most ten distinct supporting IDs."""
    assert len(supporting_sample("107", row_ids)) == expected_length


@given(st.lists(st.text(alphabet="ABC012", min_size=1, max_size=5), max_size=20))
def test_supporting_sample_order_independent(row_ids: list[str]) -> None:
    """Input order and duplicates cannot alter the sample."""
    assert supporting_sample("107", row_ids) == supporting_sample(
        "107", list(reversed(row_ids))
    )


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [("privacy-pass.txt", []), ("privacy-fail.txt", ["private raw record field"])],
)
def test_privacy_fixtures(fixture: str, expected: list[str]) -> None:
    """Reject private fields and retain clean aggregate prose."""
    assert privacy_findings((FIXTURES / fixture).read_text()) == expected


def test_privacy_csv_header() -> None:
    """Reject a synthetic raw-record CSV header in a committable table."""
    assert privacy_findings("id,prompt,minutes\nE01,invented,1\n") == [
        "private raw record field"
    ]


@pytest.mark.parametrize("field", ["prompt", "transcript", "private_prompt"])
@pytest.mark.parametrize("header", ["{field},id", "id,{field}", 'id,"{field}"'])
def test_privacy_csv_header_positions(field: str, header: str) -> None:
    """Reject private CSV fields in first, final, and quoted positions."""
    assert privacy_findings(f"{header.format(field=field)}\nrecord-1,1\n") == [
        "private raw record field"
    ]


@given(st.text(alphabet="abc 123", max_size=100))
def test_privacy_clean_text(source: str) -> None:
    """Plain aggregate text has no private signatures."""
    assert privacy_findings(source) == []


def test_privacy_planted_secret() -> None:
    """Reject a constructed fake token without committing its signature."""
    fake = "gh" + "p_" + "A" * 36
    assert privacy_findings(fake) == ["GitHub token signature"]


@pytest.mark.integration
def test_lint_rejects_private_record_fixture() -> None:
    """Reject an invented raw record before invoking prose tools."""
    # mutmut copies only core source, so shell imports belong in integration tests.
    from agent_orchestration_poc.shell.analysis.notebooks import (  # noqa: PLC0415
        lint,
    )

    with pytest.raises(ValueError, match="private raw record"):
        lint(FIXTURES / "privacy-fail.txt")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("No frontmatter\n", False),
        ("---\nprivate-input: true\n---\n", True),
        ("---\nprivate-input: true # local inputs\n---\n", True),
        ("---\n  private-input: TRUE\t# local inputs\n---\n", True),
        ("---\nprivate-input: false\n---\n", False),
        ("---\nprivate-input: true\nNo closing fence\n", False),
        ("---\ntitle: Public\n---\nprivate-input: true\n", False),
    ],
)
def test_private_notebook_flag(source: str, expected: bool) -> None:
    """Only a true flag in frontmatter removes a notebook from CI execution."""
    assert is_private_notebook(source) is expected


@given(st.text(alphabet="abc 123", max_size=100))
def test_private_notebook_plain_text(source: str) -> None:
    """Body text alone cannot mark a notebook private."""
    assert not is_private_notebook(source)


@pytest.mark.parametrize("flag", ["yes", '"true"', "true # note\nprivate-input: false"])
def test_private_notebook_rejects_unsupported_flag(flag: str) -> None:
    """Do not silently run an ambiguous private notebook in CI."""
    with pytest.raises(ValueError, match="private-input"):
        is_private_notebook(f"---\nprivate-input: {flag}\n---\n")


@pytest.mark.parametrize("flag", ['"private-input": true', "{private-input: true}"])
def test_private_notebook_rejects_unsupported_key_syntax(flag: str) -> None:
    """Fail closed when a valid YAML key uses unsupported notation."""
    with pytest.raises(ValueError, match="private-input"):
        is_private_notebook(f"---\n{flag}\n---\n")


@pytest.mark.integration
def test_ci_excludes_commented_private_notebook(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep commented private-input notebooks out of CI execution."""
    from agent_orchestration_poc.shell.analysis import (  # noqa: PLC0415
        notebooks as shell_notebooks,
    )

    private = tmp_path / "private.qmd"
    private.write_text("---\nprivate-input: true # local inputs\n---\n")
    monkeypatch.setattr(shell_notebooks, "notebooks", lambda: [private])
    monkeypatch.setattr(sys, "argv", ["notebooks", "ci"])
    shell_notebooks.main()


@pytest.mark.integration
@pytest.mark.parametrize("header", ["prompt,id", "id,prompt", 'id,"prompt"'])
def test_lint_rejects_private_csv_header(tmp_path: Path, header: str) -> None:
    """Reject a private field in any position in a committable CSV artifact."""
    from agent_orchestration_poc.shell.analysis.notebooks import lint  # noqa: PLC0415

    notebook = tmp_path / "analysis.qmd"
    notebook.write_text("---\ntitle: Example\n---\n")
    (tmp_path / "analysis.csv").write_text(f"{header}\nrecord-1,1\n")
    with pytest.raises(ValueError, match="private raw record"):
        lint(notebook)


@pytest.mark.integration
def test_lint_accepts_aggregate_csv_artifact(tmp_path: Path) -> None:
    """Allow a committable aggregate CSV beside its notebook."""
    from agent_orchestration_poc.shell.analysis.notebooks import lint  # noqa: PLC0415

    notebook = tmp_path / "analysis.qmd"
    notebook.write_text("---\ntitle: Example\n---\n")
    (tmp_path / "analysis.csv").write_text("group,total\nA,21\n")
    lint(notebook)


@pytest.mark.integration
@pytest.mark.parametrize("command", ["render", "verify", "ci"])
@pytest.mark.parametrize("artifact", ["result.csv", "chart.svg"])
@pytest.mark.parametrize("existing", [False, True])
def test_render_rejects_generated_private_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: str,
    artifact: str,
    existing: bool,
) -> None:
    """Reject new and overwritten sidecars before a task reports success."""
    from agent_orchestration_poc.shell.analysis import (  # noqa: PLC0415
        notebooks as shell_notebooks,
    )

    notebook = tmp_path / "analysis.qmd"
    notebook.write_text("---\ntitle: Example\n---\n")
    sidecar = tmp_path / artifact
    if existing:
        sidecar.write_text("group,total\nA,21\n")
    unsafe_content = (
        "id,prompt\nrecord-1,invented private record\n"
        if sidecar.suffix == ".csv"
        else f"<svg><text>{'gh' + 'p_' + 'A' * 36}</text></svg>"
    )
    finding = "private raw record" if sidecar.suffix == ".csv" else "GitHub token"

    def fake_run(*args: str, env: dict[str, str] | None = None) -> None:
        if args[0] == "quarto":
            sidecar.write_text(unsafe_content)
            output = tmp_path / ".local-cache/notebooks/analysis.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("<html>Aggregate result</html>")

    monkeypatch.setattr(shell_notebooks, "run", fake_run)
    monkeypatch.setattr(shell_notebooks, "notebooks", lambda: [notebook])
    monkeypatch.setattr(sys, "argv", ["notebooks", command, str(notebook)])
    with pytest.raises(ValueError, match=finding):
        shell_notebooks.main()


@pytest.mark.integration
@pytest.mark.parametrize("command", ["render", "verify"])
def test_private_notebook_rejects_generated_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: str
) -> None:
    """Scan sidecars even when private notebook HTML stays local."""
    from agent_orchestration_poc.shell.analysis import (  # noqa: PLC0415
        notebooks as shell_notebooks,
    )

    notebook = tmp_path / "analysis.qmd"
    notebook.write_text("---\nprivate-input: true\n---\n")

    def fake_run(*args: str, env: dict[str, str] | None = None) -> None:
        if args[0] == "quarto":
            (tmp_path / "result.csv").write_text("id,prompt\nrecord-1,invented\n")

    monkeypatch.setattr(shell_notebooks, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["notebooks", command, str(notebook)])
    with pytest.raises(ValueError, match="private raw record"):
        shell_notebooks.main()


@pytest.mark.integration
def test_prose_lint_fixtures() -> None:
    """The pinned prose tools accept one fixture and reject a wrapped paragraph."""
    # mutmut copies only core source, so shell imports belong in integration tests.
    from agent_orchestration_poc.shell.analysis.notebooks import (  # noqa: PLC0415
        lint,
    )

    lint(FIXTURES / "prose-pass.txt")
    with pytest.raises(subprocess.CalledProcessError):
        lint(FIXTURES / "prose-fail.txt")


@pytest.mark.integration
def test_notebook_lint_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discover and lint the committed notebook through the task entry point."""
    from agent_orchestration_poc.shell.analysis.notebooks import (  # noqa: PLC0415 - mutmut copies only core source
        main,
    )

    monkeypatch.setattr(sys, "argv", ["notebooks", "lint"])
    main()


@pytest.mark.integration
@pytest.mark.parametrize(
    "arguments",
    [["render"], ["verify", "tests/fixtures/analysis/prose-pass.txt"]],
)
def test_notebook_command_rejects_invalid_path(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    """Reject a missing path and a path without the Quarto extension."""
    from agent_orchestration_poc.shell.analysis.notebooks import (  # noqa: PLC0415 - mutmut copies only core source
        main,
    )

    monkeypatch.setattr(sys, "argv", ["notebooks", *arguments])
    with pytest.raises(SystemExit, match="2"):
        main()


@pytest.mark.integration
def test_render_synthetic_notebook() -> None:
    """Execute the synthetic notebook through Quarto and retain its result table."""
    from agent_orchestration_poc.shell.analysis.notebooks import (  # noqa: PLC0415 - mutmut copies only core source
        notebooks,
        render,
    )

    path = Path("research/gates/data-analysis/example.qmd")
    assert path in notebooks()
    render(path)
    assert path.with_name("example-results.csv").read_text().splitlines()[-1] == (
        "TOTAL,headline,all,48"
    )
    assert path.with_name("example-chart-light.svg").is_file()
    assert path.with_name("example-chart-dark.svg").is_file()
