"""Durable store and revision watch fixtures."""
# ruff: noqa: INP001, S101, D103

import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from state import Invalidation, can_complete
from store import Store

EVENT = (Invalidation("pr", 7, ("identity", "checks"), "a" * 40),)


@pytest.mark.parametrize(
    ("captured", "current", "expected"), [(0, 0, True), (1, 2, False)]
)
def test_can_complete_table(captured: int, current: int, expected: bool) -> None:
    assert can_complete(captured, current) is expected


@given(st.integers(min_value=0), st.integers(min_value=0))
def test_can_complete_property(captured: int, current: int) -> None:
    assert can_complete(captured, current) == (captured == current)


def test_receipt_dedup_restart_and_generation(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    store = Store(path)
    guid = str(uuid.uuid4())
    assert store.receive(guid, "pull_request", b"one", EVENT) == "accepted"
    first = store.snapshot()
    assert store.receive(guid, "pull_request", b"one", EVENT) == "duplicate"
    assert store.receive(guid, "pull_request", b"two", EVENT) == "changed_guid"
    assert store.snapshot()["revision"] == first["revision"]
    second = Store(path)
    assert second.status()["receipts"] == 1
    assert second.status()["store_instance"] == first["store_instance"]
    second.restart()
    parts = second.snapshot()["objects"][0]["components"]
    assert all(part["stale_reason"] in ("restart", "unknown") for part in parts)
    assert not second.complete_component(
        "pr",
        7,
        "identity",
        0,
        source_id="rest:1",
        head_sha=None,
        observed_at=datetime.now(tz=UTC),
    )
    assert (
        second.receive(str(uuid.uuid4()), "pull_request", b"three", EVENT) == "accepted"
    )
    assert not second.complete_component(
        "pr",
        7,
        "identity",
        1,
        source_id="rest:1",
        head_sha=None,
        observed_at=datetime.now(tz=UTC),
    )
    assert second.complete_component(
        "pr",
        7,
        "identity",
        2,
        source_id="rest:2",
        head_sha="a" * 40,
        observed_at=datetime.now(tz=UTC),
    )
    complete = second.snapshot()["objects"][0]["components"]
    identity = next(part for part in complete if part["name"] == "identity")
    assert identity["stale_reason"] == "fresh"
    assert identity["source_ids"] == ["rest:2"]
    assert identity["expires_at"] is not None


def test_before_and_after_ack_crash(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    store = Store(path)
    # A crash before COMMIT rolls the receipt back.
    with closing(sqlite3.connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO receipts VALUES (?, ?, ?, ?)",
            ("pre", "digest", "event", "time"),
        )
        db.rollback()
    assert store.status()["receipts"] == 0
    assert store.receive("post", "event", b"body", ()) == "accepted"
    assert Store(path).status()["receipts"] == 1


def test_watch_revision_identity_and_race(tmp_path: Path) -> None:
    store = Store(tmp_path / "one.sqlite3")
    ready = threading.Event()

    def change() -> None:
        ready.wait(timeout=3)
        store.track("issue", 8)

    thread = threading.Thread(target=change)
    thread.start()
    registration = store.register_watch()
    ready.set()
    thread.join(timeout=3)
    assert not thread.is_alive()
    snapshot = registration["snapshot"]
    assert snapshot["revision"] < store.snapshot()["revision"]
    assert store.watch_state(registration["token"]) == "changed"
    assert (
        Store(tmp_path / "other.sqlite3").watch_state(registration["token"])
        == "unavailable"
    )
