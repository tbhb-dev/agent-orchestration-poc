"""Process checks for the reviewer wrapper's fail-closed behavior."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

FIXTURES = Path(__file__).parent
WRAPPER = FIXTURES.parents[2] / "scripts" / "reviewer-gh.sh"
CASES = cast(
    "list[dict[str, Any]]", json.loads((FIXTURES / "wrapper.json").read_text())
)


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case"])
def test_wrapper_fails_closed(case: dict[str, Any], tmp_path: Path) -> None:
    gh = tmp_path / "gh"
    marker = tmp_path / "review-ran"
    gh.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = auth ]; then\n'
        '    [ "$TOKEN_STATUS" = 0 ] || exit 1\n'
        "    printf '%s\\n' \"$TEST_TOKEN\"\n"
        "    exit 0\n"
        "fi\n"
        'if [ "$1" = api ] && [ "$2" = user ]; then\n'
        '    [ "$IDENTITY_STATUS" = 0 ] || exit 1\n'
        '    [ "$GH_TOKEN" = fixture-only ] || exit 1\n'
        "    printf '%s\\n' \"$TEST_IDENTITY\"\n"
        "    exit 0\n"
        "fi\n"
        '[ "$GH_TOKEN" = fixture-only ] || exit 1\n'
        "printf 'ran\\n' > \"$REVIEW_MARKER\"\n"
    )
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "TOKEN_STATUS": str(case["token_status"]),
        "TEST_TOKEN": case["token"],
        "IDENTITY_STATUS": str(case["identity_status"]),
        "TEST_IDENTITY": case["identity"],
        "REVIEW_MARKER": str(marker),
    }
    result = subprocess.run(
        [str(WRAPPER), "pr", "review", "83", "--approve"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=30,
    )
    assert result.returncode == case["expected_exit"]
    assert marker.exists() is case["review_runs"]
    assert "fixture-only" not in result.stdout + result.stderr
