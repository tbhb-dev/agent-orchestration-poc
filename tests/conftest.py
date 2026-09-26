"""Shared pytest configuration: the --run-integration gate for process and socket tests."""

import pytest

GATED_MARKERS = ("integration", "socket")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests marked integration or socket, which are skipped by default",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="needs --run-integration")
    for item in items:
        if any(item.get_closest_marker(name) for name in GATED_MARKERS):
            item.add_marker(skip)
