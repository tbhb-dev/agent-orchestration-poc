"""Shell regressions for remote workflow audits and generated files."""

import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from agent_orchestration_poc.core.workflow_forms import Reference

if TYPE_CHECKING:
    from agent_orchestration_poc.shell import workflow_forms as shell
else:
    shell = pytest.importorskip("agent_orchestration_poc.shell.workflow_forms")

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = tomllib.loads((ROOT / "config/workflow-reference.toml").read_text())


@pytest.mark.integration
def test_activation_pr_bootstrap_reports_existing_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def api(path: str, *args: str) -> dict[str, Any]:
        seen.append(path)
        if path == "pulls/137":
            return {
                "state": "open",
                "merged_at": None,
                "created_at": "2026-09-26T00:00:00Z",
                "title": "invalid",
                "body": "",
                "labels": [],
            }
        raise AssertionError(path)

    monkeypatch.setattr(shell, "_api", api)
    assert REFERENCE["migration"]["validator_pr"] == 137
    assert shell.audit_pr(137, REFERENCE) == 0
    assert seen == ["pulls/137", "pulls/137"]


@pytest.mark.integration
def test_remote_audits_report_issue_and_pr_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue = {
        "number": 84,
        "state": "open",
        "title": "tooling(workflow): add forms",
        "body": "",
        "labels": [{"name": "area/workflow"}],
    }
    pr = {
        "created_at": "2026-09-28T00:00:00Z",
        "title": "tooling(workflow): add forms",
        "body": "Refs: #84",
        "labels": [{"name": "area/workflow"}],
    }

    def api(path: str, *args: str) -> dict[str, Any]:
        if path == "pulls/137":
            return {"state": "closed", "merged_at": "2026-09-27T00:00:00Z"}
        if path == "pulls/200":
            return pr
        if path == "issues/84":
            return issue
        raise AssertionError(path)

    monkeypatch.setattr(shell, "_api", api)

    def pages(path: str) -> list[dict[str, Any]]:
        return [issue, {"pull_request": {}, "number": 200}]

    monkeypatch.setattr(shell, "_pages", pages)
    assert shell.audit_issue(84, REFERENCE) == 1
    assert shell.audit_issues(REFERENCE) == 1
    assert shell.audit_pr(200, REFERENCE) == 1
    monkeypatch.setitem(pr, "created_at", None)
    assert shell.audit_pr(200, REFERENCE) == 1
    monkeypatch.setitem(issue, "pull_request", {})
    with pytest.raises(ValueError, match="is a pull request"):
        shell.audit_issue(84, REFERENCE)


@pytest.mark.integration
def test_form_shell_writes_then_detects_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    (tmp_path / "docs/src/content/docs/guides").mkdir(parents=True)
    assert shell.check_forms(REFERENCE, write=True) == 0
    assert shell.check_forms(REFERENCE, write=False) == 0
    form = tmp_path / ".github/ISSUE_TEMPLATE/tooling.yml"
    form.write_text("drift")
    assert shell.check_forms(REFERENCE, write=False) == 1


@pytest.mark.integration
def test_gh_request_retries_rate_limit_then_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    sleeps: list[int] = []

    def run(
        command: tuple[str, ...], *, capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output
        assert text
        assert not check
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 1 if len(calls) == 1 else 0, "ok", "rate limit"
        )

    monkeypatch.setattr(shell.subprocess, "run", run)
    monkeypatch.setattr(shell.time, "sleep", sleeps.append)
    assert shell._run_gh("repos/tbhb/agent-orchestration-poc/issues/84") == "ok"
    assert calls == [("gh", "api", "repos/tbhb/agent-orchestration-poc/issues/84")] * 2
    assert sleeps == [120]


@pytest.mark.integration
def test_gh_request_fails_without_retry_for_non_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(
        command: tuple[str, ...], *, capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output
        assert text
        assert not check
        return subprocess.CompletedProcess(command, 1, "", "not found")

    monkeypatch.setattr(shell.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="exit 1"):
        shell._run_gh("missing")


@pytest.mark.parametrize(
    ("command", "number", "expected"),
    [
        ("issue", "84", 1),
        ("issues", None, 1),
        ("pr", "137", 1),
        ("forms", None, 1),
        ("write-forms", None, 0),
    ],
)
@pytest.mark.integration
def test_cli_dispatch(
    monkeypatch: pytest.MonkeyPatch, command: str, number: str | None, expected: int
) -> None:
    def one(number: int, reference: Reference) -> int:
        return 1

    def all_issues(reference: Reference) -> int:
        return 1

    def forms(reference: Reference, *, write: bool) -> int:
        return int(not write)

    monkeypatch.setattr(shell, "_reference", lambda: REFERENCE)
    monkeypatch.setattr(shell, "audit_issue", one)
    monkeypatch.setattr(shell, "audit_issues", all_issues)
    monkeypatch.setattr(shell, "audit_pr", one)
    monkeypatch.setattr(shell, "check_forms", forms)
    monkeypatch.setattr(
        shell.sys, "argv", ["workflow_forms", command] + ([number] if number else [])
    )
    assert shell.main() == expected


@pytest.mark.integration
def test_cli_reports_audit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shell, "_reference", lambda: REFERENCE)

    def fail(number: int, reference: dict[str, Any]) -> int:
        raise ValueError("bad")

    monkeypatch.setattr(shell, "audit_issue", fail)
    monkeypatch.setattr(shell.sys, "argv", ["workflow_forms", "issue", "84"])
    assert shell.main() == 2
