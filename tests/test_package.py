"""Smoke test so the pytest task has something to collect."""

import agent_orchestration_poc


def test_package_imports() -> None:
    assert agent_orchestration_poc.__name__ == "agent_orchestration_poc"
