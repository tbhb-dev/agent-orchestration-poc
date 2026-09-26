"""Run mutmut from a fresh cache and enforce the Python core score."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import cast


def main() -> int:
    """Run mutants, print the score, and fail below 80 percent."""
    mutants = Path("mutants")
    if mutants.exists():
        shutil.rmtree(mutants)
    subprocess.run(["uv", "run", "mutmut", "run"], check=True)
    subprocess.run(["uv", "run", "mutmut", "export-cicd-stats"], check=True)
    stats = cast(
        "dict[str, int]", json.loads((mutants / "mutmut-cicd-stats.json").read_text())
    )
    killed = stats["killed"]
    scored = killed + sum(
        stats[key] for key in ("survived", "timeout", "suspicious", "no_tests")
    )
    if scored == 0:
        print("No Python core mutants were scored")
        return 1
    score = 100 * killed / scored
    print(f"Python core mutation score: {score:.2f}% ({killed} killed of {scored})")
    return 0 if score >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
