"""Smoke test against the helper package so the pytest task has something to collect."""

import pytest

import agent_orchestration_poc


def test_package_is_a_library_without_an_entry_point() -> None:
    assert agent_orchestration_poc.__name__ == "agent_orchestration_poc"
    assert not hasattr(agent_orchestration_poc, "main")


@pytest.mark.integration
def test_integration_marker_is_registered_and_gated() -> None:
    # Skipped by conftest.py unless --run-integration is given; passes when it is.
    assert True
