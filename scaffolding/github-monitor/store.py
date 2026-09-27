"""Temporary #167 store, replaced by permanent #189 and #190."""
# ruff: noqa: INP001, PLR0913

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from state import (
    COMPONENTS,
    REPOSITORY_ID,
    SCHEMA_VERSION,
    Invalidation,
    can_complete,
    expiry,
    freshness,
    invalidate_component,
)


class Store:
    """Durable receipt, tracking, and projection transactions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (
                    id INTEGER PRIMARY KEY CHECK(id=1), schema_version INTEGER NOT NULL,
                    instance TEXT NOT NULL, revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    guid TEXT PRIMARY KEY, digest TEXT NOT NULL,
                    event TEXT NOT NULL, received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS objects (
                    kind TEXT NOT NULL, number INTEGER NOT NULL, repository_id INTEGER NOT NULL,
                    PRIMARY KEY(kind, number)
                );
                CREATE TABLE IF NOT EXISTS components (
                    kind TEXT NOT NULL, number INTEGER NOT NULL, name TEXT NOT NULL,
                    generation INTEGER NOT NULL, complete INTEGER NOT NULL,
                    source_ids TEXT NOT NULL, head_sha TEXT,
                    observed_at TEXT, expires_at TEXT, stale_reason TEXT,
                    PRIMARY KEY(kind, number, name),
                    FOREIGN KEY(kind, number) REFERENCES objects(kind, number)
                );
                CREATE TABLE IF NOT EXISTS counters (
                    name TEXT PRIMARY KEY, value INTEGER NOT NULL
                );
            """)
            db.execute(
                "INSERT OR IGNORE INTO meta VALUES (1, ?, ?, 0)",
                (SCHEMA_VERSION, str(uuid.uuid4())),
            )
            version = db.execute(
                "SELECT schema_version FROM meta WHERE id=1"
            ).fetchone()[0]
            if version != SCHEMA_VERSION:
                raise RuntimeError("unsupported monitor schema")
            db.commit()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _revision(db: sqlite3.Connection) -> int:
        db.execute("UPDATE meta SET revision=revision+1 WHERE id=1")
        return int(db.execute("SELECT revision FROM meta WHERE id=1").fetchone()[0])

    @staticmethod
    def _ensure_object(db: sqlite3.Connection, kind: str, number: int) -> None:
        db.execute(
            "INSERT OR IGNORE INTO objects VALUES (?, ?, ?)",
            (kind, number, REPOSITORY_ID),
        )
        for name in COMPONENTS[kind]:
            db.execute(
                "INSERT OR IGNORE INTO components VALUES (?, ?, ?, 0, 0, '[]', NULL, NULL, NULL, 'unknown')",
                (kind, number, name),
            )

    def restart(self) -> int:
        """Make every prior observation stale before accepting new ingress."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE components SET stale_reason='restart'")
            return self._revision(db)

    def count(self, name: str) -> None:
        """Count a rejected signature without retaining its request."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO counters VALUES (?, 1) ON CONFLICT(name) DO UPDATE SET value=value+1",
                (name,),
            )

    def track(self, kind: str, number: int) -> int:
        """Explicitly admit one coordinator named object."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._ensure_object(db, kind, number)
            return self._revision(db)

    def receive(
        self,
        guid: str,
        event: str,
        body: bytes,
        invalidations: tuple[Invalidation, ...],
    ) -> str:
        """Commit receipt and all invalidations before the caller acknowledges."""
        digest = hashlib.sha256(body).hexdigest()
        now = datetime.now(tz=UTC).isoformat()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT digest FROM receipts WHERE guid=?", (guid,)
            ).fetchone()
            if existing:
                return "duplicate" if existing[0] == digest else "changed_guid"
            db.execute(
                "INSERT INTO receipts VALUES (?, ?, ?, ?)", (guid, digest, event, now)
            )
            for item in invalidations:
                self._ensure_object(db, item.kind, item.number)
                for name in item.components:
                    row = db.execute(
                        "SELECT generation, source_ids FROM components WHERE kind=? AND number=? AND name=?",
                        (item.kind, item.number, name),
                    ).fetchone()
                    generation, sources = invalidate_component(
                        row[0], tuple(json.loads(row[1])), guid
                    )
                    db.execute(
                        "UPDATE components SET generation=?, complete=0, source_ids=?, head_sha=COALESCE(?, head_sha), stale_reason='dirty' WHERE kind=? AND number=? AND name=?",
                        (
                            generation,
                            json.dumps(sources),
                            item.head_sha,
                            item.kind,
                            item.number,
                            name,
                        ),
                    )
            self._revision(db)
        return "accepted"

    def complete_component(
        self,
        kind: str,
        number: int,
        name: str,
        captured_generation: int,
        *,
        source_id: str,
        head_sha: str | None,
        observed_at: datetime,
    ) -> bool:
        """Allow a future REST repair to clear only its captured generation."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT generation FROM components WHERE kind=? AND number=? AND name=?",
                (kind, number, name),
            ).fetchone()
            if row is None or not can_complete(captured_generation, row[0]):
                return False
            db.execute(
                "UPDATE components SET complete=1, source_ids=?, head_sha=?, observed_at=?, expires_at=?, stale_reason=NULL WHERE kind=? AND number=? AND name=?",
                (
                    json.dumps([source_id]),
                    head_sha,
                    observed_at.isoformat(),
                    expiry(observed_at),
                    kind,
                    number,
                    name,
                ),
            )
            self._revision(db)
        return True

    @staticmethod
    def _snapshot(db: sqlite3.Connection, now: datetime) -> dict[str, Any]:
        meta = db.execute("SELECT * FROM meta WHERE id=1").fetchone()
        objects = []
        for obj in db.execute("SELECT * FROM objects ORDER BY kind, number"):
            parts = []
            for row in db.execute(
                "SELECT * FROM components WHERE kind=? AND number=? ORDER BY name",
                (obj["kind"], obj["number"]),
            ):
                parts.append(
                    {
                        "name": row["name"],
                        "generation": row["generation"],
                        "complete": bool(row["complete"]),
                        "source_ids": json.loads(row["source_ids"]),
                        "head_sha": row["head_sha"],
                        "observed_at": row["observed_at"],
                        "expires_at": row["expires_at"],
                        "stale_reason": freshness(
                            bool(row["complete"]),
                            row["stale_reason"],
                            row["expires_at"],
                            now,
                        ),
                    }
                )
            objects.append(
                {
                    "kind": obj["kind"],
                    "number": obj["number"],
                    "repository_id": obj["repository_id"],
                    "components": parts,
                }
            )
        return {
            "schema_version": meta["schema_version"],
            "store_instance": meta["instance"],
            "revision": meta["revision"],
            "objects": objects,
        }

    def snapshot(self) -> dict[str, Any]:
        """Read versioned projection and derive expiry at read time."""
        with closing(self._connect()) as db:
            return self._snapshot(db, datetime.now(tz=UTC))

    def register_watch(self) -> dict[str, Any]:
        """Register a watch and snapshot one revision in one transaction."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            snapshot = self._snapshot(db, datetime.now(tz=UTC))
            return {
                "token": f"{snapshot['store_instance']}:{snapshot['revision']}",
                "snapshot": snapshot,
            }

    def watch_state(self, token: str) -> str:
        """Distinguish changed, waiting, and a replaced store instance."""
        parts = token.split(":")
        if len(parts) != 2 or not parts[1].isdecimal():
            return "unavailable"
        with closing(self._connect()) as db:
            meta = db.execute(
                "SELECT instance, revision FROM meta WHERE id=1"
            ).fetchone()
            if parts[0] != meta[0] or int(parts[1]) > meta[1]:
                return "unavailable"
            return "changed" if meta[1] > int(parts[1]) else "waiting"

    def status(self) -> dict[str, object]:
        """Read local store metadata and signature failure counts."""
        with closing(self._connect()) as db:
            meta = db.execute("SELECT * FROM meta WHERE id=1").fetchone()
            counts = {row[0]: row[1] for row in db.execute("SELECT * FROM counters")}
            tracked = db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
            receipts = db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
            return {
                "schema_version": meta["schema_version"],
                "store_instance": meta["instance"],
                "revision": meta["revision"],
                "tracked": tracked,
                "receipts": receipts,
                "signature_failures": counts,
            }
