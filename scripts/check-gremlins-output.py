"""Reject incomplete gremlins runs that pass the score floors."""

import json
from pathlib import Path
from typing import cast

from agent_orchestration_poc.core.gremlins_output import evaluate


def main() -> int:
    """Require every generated mutant to receive a conclusive status."""
    result = cast("dict[str, object]", json.loads(Path("gremlins.json").read_text()))
    total, timed_out, complete = evaluate(result)
    if not complete:
        print(f"Go core mutation run incomplete: {timed_out} timed out of {total}")
        return 1
    print(f"Go core mutation run complete: {total} mutants classified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
