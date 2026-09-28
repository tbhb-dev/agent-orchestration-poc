"""Value-only tests for the fixture's attribution decision."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_orchestration_poc.core.host_socket_attribution import (
    Peer,
    Process,
    membership,
    peer_stable,
)


@pytest.mark.parametrize(
    ("peer_pid", "observed", "root", "expected"),
    [
        (3, {3: Process(3, 2, 30), 2: Process(2, 1, 20)}, Process(2, 1, 20), "allowed"),
        (3, {3: Process(3, 4, 30), 4: Process(4, 1, 20)}, Process(2, 1, 20), "unknown"),
        (3, {3: Process(3, 2, 30), 2: Process(2, 1, 21)}, Process(2, 1, 20), "stale"),
        (
            3,
            {3: Process(3, 2, 101), 2: Process(2, 1, 20)},
            Process(2, 1, 20),
            "unknown",
        ),
        (3, {3: Process(3, 3, 30)}, Process(2, 1, 20), "unknown"),
        (3, {}, Process(2, 1, 20), "unknown"),
    ],
)
def test_membership_cases(
    peer_pid: int, observed: dict[int, Process], root: Process, expected: str
) -> None:
    assert membership(Peer(peer_pid, 7, 100), root, observed) == expected


def test_process_started_at_acceptance_is_allowed() -> None:
    root = Process(2, 1, 20)
    child = Process(3, 2, 30)
    assert membership(Peer(3, 7, 30), root, {2: root, 3: child}) == "allowed"


@given(
    st.integers(min_value=2, max_value=100_000), st.integers(min_value=1, max_value=99)
)
def test_membership_direct_child(pid: int, start: int) -> None:
    root = Process(pid, 1, start)
    child = Process(pid + 100_001, pid, start + 1)
    assert (
        membership(Peer(child.pid, 1, 100), root, {root.pid: root, child.pid: child})
        == "allowed"
    )


@given(
    st.integers(min_value=2, max_value=100_000), st.integers(min_value=1, max_value=99)
)
def test_membership_reused_root_rejected(pid: int, start: int) -> None:
    root = Process(pid, 1, start)
    child = Process(pid + 100_001, pid, start + 1)
    replacement = Process(pid, 1, start + 1)
    assert (
        membership(
            Peer(child.pid, 1, 100), root, {root.pid: replacement, child.pid: child}
        )
        == "stale"
    )


@pytest.mark.parametrize(
    ("initial", "later", "expected"),
    [
        (Peer(2, 7, 10), Peer(2, 7, 20), True),
        (Peer(2, 7, 10), Peer(3, 8, 20), False),
        (Peer(2, 7, 10), Peer(2, 8, 20), False),
    ],
)
def test_peer_stable(initial: Peer, later: Peer, expected: bool) -> None:
    assert peer_stable(initial, later) is expected


@given(st.integers(min_value=1), st.integers(min_value=1))
def test_peer_stable_rejects_new_version(pid: int, version: int) -> None:
    assert not peer_stable(Peer(pid, version, 1), Peer(pid, version + 1, 2))
