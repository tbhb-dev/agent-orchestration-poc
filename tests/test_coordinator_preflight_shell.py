"""Process checks for coordinator preflight commands."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _invoke(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_orchestration_poc.shell.coordinator_preflight",
            *args,
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        timeout=5,
        check=False,
    )


@pytest.mark.integration
def test_wait_check_bounds_stalled_github_cli(tmp_path: Path) -> None:
    gh = tmp_path / "gh"
    gh.write_text("#!/bin/sh\nexec sleep 4\n")
    gh.chmod(0o755)
    started = time.monotonic()
    result = _invoke(tmp_path, "wait-check", "85", "check", "1")
    assert result.returncode == 1
    assert "did not succeed" in result.stderr
    assert time.monotonic() - started < 3


@pytest.mark.integration
def test_review_reports_current_workflows(tmp_path: Path) -> None:
    gh = tmp_path / "gh"
    gh.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' \'{"headRefOid":"head","statusCheckRollup":[]}\'\n'
    )
    gh.chmod(0o755)
    git = tmp_path / "git"
    git.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  "rev-parse FETCH_HEAD") echo head ;;\n'
        '  "rev-parse origin/main") echo main ;;\n'
        '  "merge-base main head") echo base ;;\n'
        '  "ls-tree -r base .github/workflows/") printf "100644 blob old\\t.github/workflows/check.yml\\n" ;;\n'
        '  "ls-tree -r main .github/workflows/"|"ls-tree -r head .github/workflows/") printf "100644 blob new\\t.github/workflows/check.yml\\n" ;;\n'
        "esac\n"
    )
    git.chmod(0o755)
    result = _invoke(tmp_path, "review", "87")
    assert result.returncode == 0
    assert "workflows include current origin/main revisions" in result.stdout


@pytest.mark.integration
def test_closure_audit_reports_unlinked_issue(tmp_path: Path) -> None:
    issues = [
        {"number": 87, "state": "CLOSED", "body": "", "labels": [{"name": "type/bug"}]}
    ]
    prs: list[dict[str, object]] = [
        {"number": 105, "body": "Refs: #86", "closingIssuesReferences": []}
    ]
    gh = tmp_path / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = issue ]; then\n'
        f"  printf '%s\\n' '{json.dumps(issues)}'\n"
        "else\n"
        f"  printf '%s\\n' '{json.dumps(prs)}'\n"
        "fi\n"
    )
    gh.chmod(0o755)
    result = _invoke(tmp_path, "closure-audit")
    assert result.returncode == 1
    assert "issue #87: closed without a linked merged PR" in result.stderr
    assert "Audited 1 closed work-item issues" in result.stdout
