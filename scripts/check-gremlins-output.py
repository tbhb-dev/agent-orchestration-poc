"""Reject incomplete gremlins runs that pass the score floors."""

import json
from pathlib import Path
from typing import cast


def main() -> int:
    """Require every generated mutant to receive a conclusive status."""
    result = cast("dict[str, object]", json.loads(Path("gremlins.json").read_text()))
    files = cast("list[dict[str, object]]", result["files"])
    statuses = [
        mutation["status"]
        for file in files
        for mutation in cast("list[dict[str, str]]", file["mutations"])
    ]
    incomplete = sum(status == "TIMED OUT" for status in statuses)
    if not statuses or incomplete:
        print(
            f"Go core mutation run incomplete: {incomplete} timed out of {len(statuses)}"
        )
        return 1
    print(f"Go core mutation run complete: {len(statuses)} mutants classified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
