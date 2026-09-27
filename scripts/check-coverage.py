"""Read coverage reports and run the Go branch instrumenter at the shell edge."""

import json
import subprocess
from pathlib import Path
from typing import cast

from agent_orchestration_poc.core.coverage_floors import (
    Report,
    evaluate_go,
    evaluate_gobco,
    evaluate_python,
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
    for package in packages:
        result = subprocess.run(
            ["gobco", "-branch", package], check=True, capture_output=True, text=True
        )
        outputs.append(result.stdout)
    go_branches, branch_passed = evaluate_gobco(outputs)
    print(f"Go core branches: {go_branches:.2f}% (floor 90%)")
    return 0 if python_passed and go_passed and branch_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
