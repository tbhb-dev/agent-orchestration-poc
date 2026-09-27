"""Temporary #179 REST and cache shell, replaced by permanent item D."""
# ruff: noqa: INP001, T201

import base64
import fcntl
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repair import (
    REPOSITORY,
    authoritative,
    body_for_response,
    budget_handoff,
    capacity,
    collection_change,
    component_reason,
    digest,
    endpoints,
    final_reads,
    next_page,
)
from store import Store

LOCAL = Path(".local-cache/github-monitor")
API_VERSION = "2026-03-10"


@contextmanager
def principal_lock(path: Path) -> Generator[None]:
    """Serialize bootstrap and repair for one principal and REST resource."""
    with path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


@dataclass(frozen=True)
class Response:
    """One REST page with response headers preserved for admission."""

    status: int
    headers: dict[str, str]
    body: bytes


class Client:
    """Serialized request accounting and exact-page conditional cache."""

    def __init__(
        self, base: str, token: str, cache_file: Path, delay: float = 1.0
    ) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self.cache_file = cache_file
        self.delay = delay
        self.cache: dict[str, dict[str, str]] = (
            json.loads(cache_file.read_text()) if cache_file.exists() else {}
        )
        self.headers: dict[str, str] = {}
        self.requests = 0
        self.pages = 0
        self.trace: list[dict[str, object]] = []

    def _send(self, url: str, etag: str | None) -> Response:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if etag:
            headers["If-None-Match"] = etag
        request = urllib.request.Request(url, headers=headers)  # noqa: S310 - fixed GitHub host or loopback fixture
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub host or loopback fixture
                return Response(
                    response.status, dict(response.headers.items()), response.read()
                )
        except urllib.error.HTTPError as error:
            with error:
                return Response(error.code, dict(error.headers.items()), error.read())

    def get(self, path: str, *, bootstrap: bool = False) -> tuple[object, ...]:
        """Collect every page or fail visibly without returning a partial body."""
        url: str | None = f"{self.base}{path}"
        values: list[object] = []
        while url:
            if not url.startswith(f"{self.base}/"):
                raise ValueError("pagination crossed the allowed host")
            if not bootstrap:
                reason = capacity(self.headers, self.requests, self.pages)
                if reason:
                    raise RuntimeError(reason)
            elif self.requests or self.headers:
                raise RuntimeError("bootstrap_already_used")
            cached = self.cache.get(url)
            saved = (
                (cached["etag"], base64.b64decode(cached["body"])) if cached else None
            )
            if self.requests:
                time.sleep(self.delay)
            response = self._send(url, saved[0] if saved else None)
            self.requests += 1
            self.pages += 1
            self.headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            body = body_for_response(
                response.status, response.body, saved, self.headers.get("etag")
            )
            if body is None or capacity(
                self.headers, self.requests - 1, self.pages - 1
            ):
                raise RuntimeError(f"incomplete_http_{response.status}")
            link = (
                (cached.get("link") if cached else None)
                if response.status == 304
                else self.headers.get("link")
            )
            self.trace.append(
                {
                    "page": url.removeprefix(self.base),
                    "status": response.status,
                    "remaining": self.headers.get("x-ratelimit-remaining"),
                    "resource": self.headers.get("x-ratelimit-resource"),
                    "etag": self.headers.get("etag"),
                    "body_sha256": hashlib.sha256(body).hexdigest(),
                    "pagination_complete": next_page(link) is None,
                }
            )
            if response.status == 200 and self.headers.get("etag"):
                self.cache[url] = {
                    "etag": self.headers["etag"],
                    "body": base64.b64encode(body).decode(),
                    "link": link or "",
                }
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.cache_file.with_suffix(".tmp")
                temporary.write_text(json.dumps(self.cache))
                temporary.replace(self.cache_file)
            decoded = json.loads(body)
            values.extend(decoded if isinstance(decoded, list) else [decoded])
            url = next_page(link)
        return tuple(values)


def repair_object(  # noqa: C901, PLR0912 - one bounded collection transaction
    client: Client, store: Store, item: dict[str, Any]
) -> dict[str, Any]:
    """Collect one tracked object and commit only stable supported components."""
    kind, number = str(item["kind"]), int(item["number"])
    components = {
        str(part["name"]): int(part["generation"]) for part in item["components"]
    }
    report: dict[str, Any] = {
        "kind": kind,
        "number": number,
        "components": {},
        "requests": 0,
        "pages": 0,
    }
    trace_start = len(client.trace)
    initial: dict[str, str] = {}
    final: dict[str, str] = {}
    head: str | None = None
    try:
        issue_path = f"/repos/{REPOSITORY}/issues/{number}"
        issue = client.get(issue_path)
        initial["issue"] = authoritative("issue", issue)
        if kind == "pr":
            pull = client.get(f"/repos/{REPOSITORY}/pulls/{number}")
            initial["pull"] = authoritative("pull", pull)
            value = pull[0]
            if not isinstance(value, dict) or not isinstance(value.get("head"), dict):
                raise ValueError("missing PR head")
            head = value["head"].get("sha")
            if (
                not isinstance(head, str)
                or len(head) != 40
                or any(char not in "0123456789abcdef" for char in head.lower())
            ):
                raise ValueError("invalid PR head")
        plan = endpoints(kind, number, head)
        by_component: dict[str, list[str]] = {}
        for endpoint in plan:
            by_component.setdefault(endpoint.component, []).append(endpoint.name)
            if endpoint.name in initial:
                continue
            pages = client.get(endpoint.path)
            initial[endpoint.name] = authoritative(endpoint.name, pages)
        for endpoint in final_reads(plan):
            final[endpoint.name] = authoritative(
                endpoint.name, client.get(endpoint.path)
            )
        outcome = collection_change(plan, initial, final)
        snapshot = store.snapshot()
        matching = next(
            (
                obj
                for obj in snapshot["objects"]
                if obj["kind"] == kind and obj["number"] == number
            ),
            None,
        )
        current = (
            {
                str(part["name"]): int(part["generation"])
                for part in matching["components"]
            }
            if matching
            else {}
        )
        for component, names in by_component.items():
            reason = component_reason(
                kind,
                component,
                outcome,
                components[component],
                current.get(component, -1),
            )
            if reason is None:
                saved = store.complete_component(
                    kind,
                    number,
                    component,
                    components[component],
                    source_id=f"rest:{digest(tuple(initial[name] for name in names))}",
                    head_sha=head,
                    observed_at=datetime.now(tz=UTC),
                )
                if not saved:
                    reason = "invalidation_during_commit"
            elif next(part for part in item["components"] if part["name"] == component)[
                "complete"
            ]:
                store.stale_component(
                    kind, number, component, components[component], reason
                )
            paths = tuple(
                endpoint.path.split("?")[0]
                for endpoint in plan
                if endpoint.name in names
            )
            report["components"][component] = {
                "complete": reason is None,
                "unknown_reason": reason,
                "endpoints": names,
                "pages": [
                    page
                    for page in client.trace[trace_start:]
                    if any(str(page["page"]).startswith(path) for path in paths)
                ],
                "initial_digest": digest(tuple(initial[name] for name in names)),
                "final_digest": digest(tuple(final.get(name) for name in names)),
                "collected_at": datetime.now(tz=UTC).isoformat(),
            }
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        report["error"] = str(error)
        report["components"] = {
            name: {"complete": False, "unknown_reason": str(error)}
            for name in components
        }
        for part in item["components"]:
            if part["complete"]:
                store.stale_component(
                    kind,
                    number,
                    str(part["name"]),
                    components[str(part["name"])],
                    str(error),
                )
    report["requests"] = client.requests
    report["pages"] = client.pages
    return report


def main() -> int:
    """Repair only tracked store objects with a coordinator supplied App token."""
    if sys.argv[1:] != ["--tracked"]:
        print("usage: rest_client.py --tracked", file=sys.stderr)
        return 2
    installation = os.environ.get("GITHUB_APP_INSTALLATION_ID", "")
    scopes = os.environ.get("GITHUB_APP_READ_SCOPES", "")
    token = os.environ.get("GITHUB_INSTALLATION_TOKEN", "")
    if installation != "165297562" or not scopes or not token:
        print(
            "incomplete: coordinator App installation, recorded read scopes, and token required",
            file=sys.stderr,
        )
        return 2
    principal = f"installation:{installation}:core"
    lock_name = hashlib.sha256(principal.encode()).hexdigest()[:16]
    LOCAL.mkdir(parents=True, exist_ok=True)
    with principal_lock(LOCAL / f"repair-{lock_name}.lock"):
        store = Store(LOCAL / "state.sqlite3")
        client = Client(
            "https://api.github.com",
            token,
            LOCAL / f"repair-pages-{lock_name}-{API_VERSION}.json",
        )
        reports: list[dict[str, Any]] = []
        try:
            client.get(f"/repos/{REPOSITORY}", bootstrap=True)
            for item in store.snapshot()["objects"]:
                client.requests = 0
                client.pages = 0
                reports.append(repair_object(client, store, item))
        except (RuntimeError, OSError, ValueError) as error:
            reports.append({"error": str(error)})
        result = {
            "budget": budget_handoff(
                principal, client.headers, client.requests, client.pages
            ),
            "reports": reports,
            "trace": client.trace,
        }
        print(json.dumps(result, sort_keys=True))
        return (
            1
            if any(
                report.get("error")
                or any(
                    not part["complete"]
                    for part in report.get("components", {}).values()
                )
                for report in reports
            )
            else 0
        )


if __name__ == "__main__":
    raise SystemExit(main())
