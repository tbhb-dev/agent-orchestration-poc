"""Run notebook lint, render, and verification gates."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_orchestration_poc.core.analysis.notebooks import (
    is_private_notebook,
    privacy_findings,
    split_qmd,
)


def run(*args: str, env: dict[str, str] | None = None) -> None:
    """Run one checker and fail with its exit status."""
    subprocess.run(args, check=True, env=env)


def notebooks() -> list[Path]:
    """List tracked and new, nonignored notebooks."""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.qmd",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(name) for name in result.stdout.splitlines()]


def lint(path: Path) -> None:
    """Lint prose, Python cells, and privacy of one notebook."""
    source = path.read_text()
    findings = privacy_findings(source)
    for artifact in (*path.parent.glob("*.csv"), *path.parent.glob("*.svg")):
        findings.extend(privacy_findings(artifact.read_text()))
    if findings:
        raise ValueError(f"{path}: {', '.join(findings)}")
    prose, code = split_qmd(source)
    with tempfile.TemporaryDirectory(prefix="notebook-lint-") as temporary:
        markdown = Path(temporary) / "notebook.md"
        markdown.write_text(prose)
        run("vale", str(markdown))
        run("rumdl", "check", "--config", ".rumdl.toml", str(markdown))
        run("guard-markdown", str(markdown))
        if code.strip():
            python = Path(temporary) / "notebook.py"
            python.write_text(code)
            run(
                "uv",
                "run",
                "--group",
                "analysis",
                "ruff",
                "check",
                "--isolated",
                "--select",
                "E4,E7,E9,F,I,B,S",
                "--ignore",
                "E402,S101",
                str(python),
            )


def render(path: Path) -> None:
    """Execute one notebook with the locked Python and no execution cache."""
    environment = os.environ.copy()
    environment["QUARTO_PYTHON"] = sys.executable
    environment["MPLBACKEND"] = "Agg"
    environment["MPLCONFIGDIR"] = str(Path(".local-cache/matplotlib").resolve())
    Path(environment["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    run(
        "quarto",
        "render",
        str(path),
        "--to",
        "html",
        "--execute",
        "--no-cache",
        "--output-dir",
        ".local-cache/notebooks",
        env=environment,
    )
    if not is_private_notebook(path.read_text()):
        output = path.parent / ".local-cache/notebooks" / f"{path.stem}.html"
        findings = privacy_findings(output.read_text())
        if findings:
            raise ValueError(f"{output}: {', '.join(findings)}")


def main() -> None:
    """Dispatch the selected mise notebook task."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("lint", "render", "verify", "ci"))
    parser.add_argument("path", nargs="?")
    arguments = parser.parse_args()
    if arguments.command == "lint":
        for path in notebooks():
            lint(path)
        return
    if arguments.command == "ci":
        for path in notebooks():
            if not is_private_notebook(path.read_text()):
                lint(path)
                render(path)
        return
    if arguments.path is None:
        parser.error("render and verify require a notebook path")
    path = Path(arguments.path)
    if path.suffix != ".qmd" or not path.is_file():
        parser.error("path must name an existing .qmd notebook")
    if arguments.command == "verify":
        lint(path)
    render(path)


if __name__ == "__main__":
    main()
