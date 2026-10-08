"""Read coverage reports and run the Go branch instrumenter at the shell edge."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import cast

from agent_orchestration_poc.core.coverage_floors import (
    Report,
    evaluate_go,
    evaluate_gobco,
    evaluate_python,
)
from agent_orchestration_poc.shell.go_branch_coverage import (
    run_gobco,
    stage_core_module,
)


def main() -> int:
    """Print each independently scored coverage gate and return its status."""
    directory = Path(".coverage-reports")
    report = cast("Report", json.loads((directory / "python.json").read_text()))
    python_lines, python_branches, shell_lines, python_passed = evaluate_python(report)
    print(f"Python core lines: {python_lines:.2f}% (floor 95%)")
    print(f"Python core branches: {python_branches:.2f}% (floor 90%)")
    print(
        "Python shell lines: no code"
        if shell_lines is None
        else f"Python shell lines: {shell_lines:.2f}% (floor 70%)"
    )

    go_core, go_shell, go_passed = evaluate_go((directory / "go.out").read_text())
    print(f"Go core statements: {go_core:.2f}% (floor 95%)")
    print(f"Go shell statements: {go_shell:.2f}% (floor 70%)")

    packages = subprocess.run(
        ["go", "list", "-f", "{{.Dir}}", "./internal/core/..."],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    outputs = []
    root = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="go-branch-coverage-") as temporary:
        staged = Path(temporary)
        stage_core_module(root, staged)
        for package in packages:
            relative = Path(package).relative_to(root)
            print(f"Go branch coverage: {relative}", flush=True)
            outputs.append(run_gobco(staged / relative, timeout_seconds=90))
    go_branches, branch_passed = evaluate_gobco(outputs)
    print(f"Go core branches: {go_branches:.2f}% (floor 90%)")
    return 0 if python_passed and go_passed and branch_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
