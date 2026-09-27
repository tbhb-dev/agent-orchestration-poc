"""Value tests for the separate coverage gate decisions."""

from agent_orchestration_poc.core.coverage_floors import (
    File,
    Report,
    evaluate_go,
    evaluate_gobco,
    evaluate_python,
)


def file(lines: int, total: int, branches: int = 0, branch_total: int = 0) -> File:
    """Build a coverage.py file entry from counts."""
    return {
        "summary": {
            "covered_lines": lines,
            "num_statements": total,
            "covered_branches": branches,
            "num_branches": branch_total,
        }
    }


def test_python_separate_floors() -> None:
    files = {
        "src/agent_orchestration_poc/core/main.py": file(95, 100, 9, 10),
        "src/agent_orchestration_poc/shell/run.py": file(7, 10),
    }
    report: Report = {"meta": {"branch_coverage": True}, "files": files}
    assert evaluate_python(report) == (95.0, 90.0, 70.0, True)
    files["src/agent_orchestration_poc/core/main.py"] = file(94, 100, 9, 10)
    assert evaluate_python(report)[-1] is False
    files["src/agent_orchestration_poc/core/main.py"] = file(95, 100, 8, 10)
    assert evaluate_python(report)[-1] is False
    files["src/agent_orchestration_poc/core/main.py"] = file(95, 100, 9, 10)
    files["src/agent_orchestration_poc/shell/run.py"] = file(6, 10)
    assert evaluate_python(report)[-1] is False
    files["src/agent_orchestration_poc/shell/run.py"] = file(7, 10)
    report["meta"]["branch_coverage"] = False
    assert evaluate_python(report)[-1] is False


def test_python_empty_shell_and_core() -> None:
    assert evaluate_python(
        {
            "meta": {"branch_coverage": True},
            "files": {"src/agent_orchestration_poc/core/a.py": file(1, 1)},
        }
    ) == (
        100.0,
        100.0,
        None,
        True,
    )
    assert (
        evaluate_python({"meta": {"branch_coverage": True}, "files": {}})[-1] is False
    )


def test_python_aggregates_files() -> None:
    report: Report = {
        "meta": {"branch_coverage": True},
        "files": {
            "src/agent_orchestration_poc/core/a.py": file(50, 50, 5, 5),
            "src/agent_orchestration_poc/core/b.py": file(45, 50, 4, 5),
            "src/agent_orchestration_poc/shell/a.py": file(3, 5),
            "src/agent_orchestration_poc/shell/b.py": file(4, 5),
        },
    }
    assert evaluate_python(report) == (95.0, 90.0, 70.0, True)


def test_python_rejects_just_below_each_floor() -> None:
    report: Report = {
        "meta": {"branch_coverage": True},
        "files": {
            "src/agent_orchestration_poc/core/a.py": file(94, 99, 90, 100),
            "src/agent_orchestration_poc/shell/a.py": file(70, 100),
        },
    }
    assert evaluate_python(report)[-1] is False
    report["files"]["src/agent_orchestration_poc/core/a.py"] = file(95, 100, 89, 99)
    assert evaluate_python(report)[-1] is False
    report["files"]["src/agent_orchestration_poc/core/a.py"] = file(95, 100, 90, 100)
    report["files"]["src/agent_orchestration_poc/shell/a.py"] = file(69, 99)
    assert evaluate_python(report)[-1] is False
    report["files"]["src/agent_orchestration_poc/shell/a.py"] = file(0, 1)
    assert evaluate_python(report)[-1] is False
    report["files"]["src/agent_orchestration_poc/shell/a.py"] = file(1, 1)
    report["files"]["src/agent_orchestration_poc/core/a.py"] = file(1, 1, 0, 1)
    assert evaluate_python(report)[-1] is False


def test_go_profile_includes_untested_packages() -> None:
    profile = (
        "mode: set\n"
        "example/internal/core/a/a.go:1.1,2.1 19 1\n"
        "example/internal/core/a/a.go:3.1,4.1 1 0\n"
        "example/internal/version/version.go:1.1,2.1 7 1\n"
        "example/cmd/agentd/main.go:1.1,2.1 3 0"
    )
    assert evaluate_go(profile) == (95.0, 70.0, True)
    assert evaluate_go(profile.replace("19 1", "18 1"))[-1] is False
    assert evaluate_go(profile.replace("7 1", "6 1"))[-1] is False
    assert evaluate_go("mode: set")[-1] is False


def test_go_rejects_empty_and_just_below() -> None:
    core = "example/internal/core/a/a.go:1.1,2.1 1 1"
    shell = "example/internal/cli/run.go:1.1,2.1 1 1"
    assert evaluate_go(f"mode: set\n{core}\n{shell}")[-1] is True
    assert evaluate_go(f"mode: set\n{shell}")[-1] is False
    assert evaluate_go(f"mode: set\n{core}")[-1] is False
    profile = (
        f"mode: set\n{core}\n"
        "example/internal/cli/run.go:1.1,2.1 69 1\n"
        "example/cmd/agentd/main.go:1.1,2.1 30 0"
    )
    assert evaluate_go(profile)[-1] is False


def test_gobco_aggregates_packages() -> None:
    assert evaluate_gobco(["Branch coverage: 8/10", "Branch coverage: 10/10"]) == (
        90.0,
        True,
    )
    assert evaluate_gobco(["Branch coverage: 8/10", "Branch coverage: 9/10"]) == (
        85.0,
        False,
    )
    assert evaluate_gobco(["Branch coverage: 0/0"])[-1] is False
    assert evaluate_gobco(["Branch coverage: 1/1"])[-1] is True
    assert evaluate_gobco(["Branch coverage: 89/99"])[-1] is False
