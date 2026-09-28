"""Plain-value tests for the fixture's pure target and qualification rules."""

from collections.abc import Callable
from pathlib import Path
from runpy import run_path
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

fixture = run_path(str(Path(__file__).with_name("fixture.py")))
ENDPOINTS = cast("tuple[str, ...]", fixture["ENDPOINTS"])
REQUIRED = cast("dict[str, str]", fixture["REQUIRED"])
failure_result = cast("Callable[[str], str]", fixture["failure_result"])
profile_status = cast("Callable[[dict[str, str]], str]", fixture["profile_status"])
socket_path = cast("Callable[[Path, str, str], Path]", fixture["socket_path"])
socket_result = cast(
    "Callable[[dict[str, str], str, str], str]", fixture["socket_result"]
)


def is_unknown_workload(value: str) -> bool:
    return value not in ("A", "B")


def is_unknown_endpoint(value: str) -> bool:
    return value not in ENDPOINTS


@pytest.mark.parametrize("workload", ["A", "B"])
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_socket_path(workload: str, endpoint: str) -> None:
    assert socket_path(Path("/private/tmp/fixture"), workload, endpoint) == Path(  # noqa: S101 - pytest assertion
        f"/private/tmp/fixture/{workload}/{endpoint}.sock"
    )


@given(st.text().filter(is_unknown_workload))
def test_socket_path_rejects_unknown_workload(workload: str) -> None:
    with pytest.raises(ValueError, match="unknown disposable target"):
        socket_path(Path("fixture"), workload, "peer")


@given(st.text().filter(is_unknown_endpoint))
def test_socket_path_rejects_unknown_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="unknown disposable target"):
        socket_path(Path("fixture"), "A", endpoint)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"wrapper": "B", "endpoint": "peer"}, "allowed"),
        ({"wrapper": "A", "endpoint": "peer"}, "inconclusive"),
        ({"wrapper": "B", "endpoint": "management"}, "inconclusive"),
    ],
)
def test_socket_result(response: dict[str, str], expected: str) -> None:
    assert socket_result(response, "B", "peer") == expected  # noqa: S101 - pytest assertion


@given(st.dictionaries(st.text(), st.text()))
def test_socket_result_only_accepts_exact_response(response: dict[str, str]) -> None:
    if socket_result(response, "A", "queue") == "allowed":
        assert response == {"wrapper": "A", "endpoint": "queue"}  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    "error_name", ["PermissionError", "FileNotFoundError", "TimeoutError"]
)
def test_failure_result(error_name: str) -> None:
    assert failure_result(error_name) == f"inconclusive:{error_name}"  # noqa: S101 - pytest assertion


@given(st.text())
def test_failure_result_never_claims_denial(error_name: str) -> None:
    assert not failure_result(error_name).startswith("blocked:")  # noqa: S101 - pytest assertion


@pytest.mark.parametrize(
    ("results", "expected"),
    [({}, "incomplete"), ({"own-peer": "allowed"}, "incomplete")],
)
def test_profile_status_partial(results: dict[str, str], expected: str) -> None:
    assert profile_status(results) == expected  # noqa: S101 - pytest assertion


@given(
    st.dictionaries(
        st.text(min_size=1), st.sampled_from(["allowed", "blocked", "prompted"])
    )
)
def test_profile_status_never_qualifies_arbitrary_results(
    results: dict[str, str],
) -> None:
    if profile_status(results) == "qualified":
        assert results["own-peer"] == "allowed"  # noqa: S101 - pytest assertion
        assert results["other-queue-shell"] == "blocked"  # noqa: S101 - pytest assertion
        assert results["other-cc-socks-hook"] == "blocked"  # noqa: S101 - pytest assertion
        assert results["operator-key"] == "blocked"  # noqa: S101 - pytest assertion


def test_profile_status_complete() -> None:
    results = REQUIRED.copy()
    assert profile_status(results) == "qualified"  # noqa: S101 - pytest assertion
    for key in results:
        changed = results | {key: "prompted"}
        assert profile_status(changed) == "unsupported"  # noqa: S101 - pytest assertion
