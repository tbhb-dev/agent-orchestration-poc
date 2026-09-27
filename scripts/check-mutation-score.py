"""Run mutmut from a fresh cache and enforce the Python core score."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import cast

from agent_orchestration_poc.core.mutation_score import evaluate


def main() -> int:
    """Run mutants, print the score, and fail below 90 percent."""
    mutants = Path("mutants")
    if mutants.exists():
        shutil.rmtree(mutants)
    subprocess.run(["uv", "run", "mutmut", "run"], check=True)
    subprocess.run(["uv", "run", "mutmut", "export-cicd-stats"], check=True)
    stats = cast(
        "dict[str, int]", json.loads((mutants / "mutmut-cicd-stats.json").read_text())
    )
    score, passed = evaluate(stats)
    print(
        f"Python core mutation score: {score:.2f}% "
        f"({stats.get('killed', 0)} killed of {stats.get('total', 0)})"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
