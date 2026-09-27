"""Disposable, read-only Project 9 feasibility probe. Replaced by issue #186."""

# ruff: noqa: INP001  Standalone disposable script in the reserved scaffold path.

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

PROJECT = "users/tbhb/projectsV2/9"
REPO = "repos/tbhb/agent-orchestration-poc"
VERSION = "2026-03-10"
FIELDS = ("Status", "Priority", "Phase", "Worker")
MAX_PAGES = 5
PAGE_SIZE = 100
MAX_DELIVERY_DETAILS = 10


def next_cursor(link: str) -> str | None:
    """Accept only an item-list next cursor from GitHub's Link header."""
    for part in link.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"<([^>]+)>", part)
        if match is None:
            return None
        parsed = urlparse(match.group(1))
        if parsed.hostname != "api.github.com" or not parsed.path.endswith(
            "/projectsV2/9/items"
        ):
            return None
        cursors = parse_qs(parsed.query).get("after", [])
        return cursors[0] if len(cursors) == 1 else None
    return None


def item_request(fields: str, cursor: str | None) -> str:
    """Build an item request without changing an opaque cursor value."""
    query = f"per_page={PAGE_SIZE}&fields={fields}"
    if cursor is not None:
        query += "&" + urlencode({"after": cursor})
    return f"{PROJECT}/items?{query}"


def field_selection(status: int, fields: object) -> tuple[str, bool]:
    """Select requested IDs and determine whether field definitions are complete."""
    if status != 200 or not isinstance(fields, list):
        return "", False
    definitions = {
        field["name"]: field["id"]
        for field in fields
        if isinstance(field, dict)
        and field.get("name") in FIELDS
        and isinstance(field.get("id"), int)
    }
    query = ",".join(str(definitions[name]) for name in FIELDS if name in definitions)
    return query, len(definitions) == len(FIELDS) and len(fields) < PAGE_SIZE


def page_decision(
    status: int, items: object, link: str, page: int
) -> tuple[bool, str | None, bool]:
    """Return whether to retain a page, request another, and mark the end complete."""
    if status != 200 or not isinstance(items, list):
        return False, None, False
    if 'rel="next"' not in link:
        return True, None, True
    cursor = next_cursor(link)
    return True, cursor if page < MAX_PAGES else None, False


def source_complete(
    account_status: int, definitions_complete: bool, pages_complete: bool
) -> bool:
    """Confirm a source only when every required read is complete."""
    return account_status == 200 and definitions_complete and pages_complete


def subscription_state(status: int, app: object) -> str:
    """Classify readable App subscription metadata."""
    if (
        status != 200
        or not isinstance(app, dict)
        or not isinstance(app.get("events"), list)
    ):
        return "unknown"
    return "subscribed" if "projects_v2_item" in app["events"] else "not_subscribed"


def observed_action(
    delivery: object, detail: object, project_node_id: str, start: str, end: str
) -> str | None:
    """Confirm a delivery action in the window for the target Project."""
    if not isinstance(delivery, dict) or not isinstance(detail, dict):
        return None
    if not candidate_delivery(delivery, start, end):
        return None
    request = detail.get("request")
    payload = request.get("payload") if isinstance(request, dict) else None
    item = payload.get("projects_v2_item") if isinstance(payload, dict) else None
    if not isinstance(item, dict) or item.get("project_node_id") != project_node_id:
        return None
    action = delivery.get("action")
    return action if action in ("created", "deleted", "edited") else None


def candidate_delivery(delivery: object, start: str, end: str) -> bool:
    """Select bounded Project event deliveries for read-only detail checks."""
    if not isinstance(delivery, dict) or delivery.get("event") != "projects_v2_item":
        return False
    at = delivery.get("delivered_at")
    if not isinstance(at, str):
        return False
    try:
        observed = datetime.fromisoformat(at)
        return datetime.fromisoformat(start) <= observed <= datetime.fromisoformat(end)
    except TypeError, ValueError:
        return False


def classify_items(
    pages: list[list[dict[str, Any]]], field_names: tuple[str, ...], complete: bool
) -> dict[str, Any]:
    """Count current Project values without exposing item IDs or private contents."""
    counts: dict[str, int] = {name: 0 for name in field_names}
    ready = 0
    identities = 0
    for page in pages:
        for item in page:
            if isinstance(item.get("id"), int) and isinstance(
                item.get("content"), dict
            ):
                identities += 1
            for field in item.get("fields", []):
                name = field.get("name")
                if name in counts and field.get("value") is not None:
                    counts[name] += 1
                    if name == "Status" and field["value"].get("name") == "Ready":
                        ready += 1
    return {
        "items_seen": sum(map(len, pages)),
        "item_identity_count": identities,
        "field_value_counts": counts,
        "missing_field_value_counts": {
            name: sum(map(len, pages)) - count for name, count in counts.items()
        },
        "ready_count": ready,
        "complete": complete,
    }


def classify_delivery(
    actions: list[tuple[str, int]], start: int, end: int, authorized: bool
) -> dict[str, str]:
    """Classify only deliveries within the bounded window."""
    result = {name: "unknown" for name in ("addition", "removal", "field_change")}
    if not authorized:
        return result
    mapping = {"created": "addition", "deleted": "removal", "edited": "field_change"}
    for action, at in actions:
        if start <= at <= end and action in mapping:
            result[mapping[action]] = "observed"
    return result


def source_rows(
    summary: dict[str, Any],
    account: str,
    definitions: dict[str, Any],
    items: dict[str, Any],
    labels: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Attach source and completeness to each requested value."""
    rows: dict[str, dict[str, Any]] = {}
    for requested, field in (
        ("Ready", "Status"),
        ("Priority", "Priority"),
        ("Phase", "Phase"),
        ("Worker", "Worker"),
    ):
        rows[requested] = {
            "path": f"{PROJECT}/items?per_page={PAGE_SIZE}&fields=<four field IDs>",
            "definition_path": definitions["path"],
            "definition_status": definitions["status"],
            "api_version": items["api_version"],
            "status": items["status"],
            "pagination": items["pagination"],
            "account": account,
            "source_complete": summary["complete"],
            "populated_count": summary["field_value_counts"][field],
            "missing_count": summary["missing_field_value_counts"][field],
        }
    rows["item_identity"] = {
        "path": items["path"],
        "api_version": items["api_version"],
        "status": items["status"],
        "pagination": items["pagination"],
        "account": account,
        "source_complete": summary["complete"],
        "populated_count": summary["item_identity_count"],
    }
    rows["issue_labels"] = {
        "path": labels["path"],
        "api_version": labels["api_version"],
        "status": labels["status"],
        "pagination": labels["pagination"],
        "account": account,
        "source_complete": labels["status"] == 200,
        "separate_from_project_fields": True,
    }
    return rows


def _api(path: str) -> tuple[int, dict[str, str], Any]:
    command = ["gh", "api", "-i", "-H", f"X-GitHub-Api-Version: {VERSION}", path]
    try:
        response = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=30
        )
    except subprocess.TimeoutExpired:
        return 0, {}, None
    raw = response.stdout.replace("\r\n", "\n")
    headers_text, _, body = raw.partition("\n\n")
    headers = {
        key.lower(): value.strip()
        for line in headers_text.splitlines()[1:]
        if ":" in line
        for key, value in [line.split(":", 1)]
    }
    match = re.search(r"HTTP/[\d.]+ (\d{3})", headers_text)
    status = int(match.group(1)) if match else 0
    try:
        data = json.loads(body) if status == 200 else None
    except json.JSONDecodeError:
        data = None
    return status, headers, data


def _record(
    path: str, status: int, headers: dict[str, str], pages: int = 1
) -> dict[str, Any]:
    return {
        "path": path,
        "api_version": headers.get("x-github-api-version-selected", "unknown"),
        "status": status,
        "pagination": f"{pages} page(s), maximum {MAX_PAGES}",
        "resource": headers.get("x-ratelimit-resource", "unknown"),
    }


def rest_matrix() -> dict[str, Any]:
    """Collect a bounded REST source matrix without mutation or GraphQL."""
    collected_at = datetime.now(tz=UTC)
    account_status, account_headers, account = _api("user")
    account_name = (
        account.get("login", "unknown") if isinstance(account, dict) else "unknown"
    )
    fields_path = f"{PROJECT}/fields?per_page={PAGE_SIZE}"
    field_status, field_headers, fields = _api(fields_path)
    query, definitions_complete = field_selection(field_status, fields)
    pages: list[list[dict[str, Any]]] = []
    records = [
        _record("user", account_status, account_headers),
        _record(fields_path, field_status, field_headers),
    ]
    cursor: str | None = None
    pages_complete = False
    for page_number in range(MAX_PAGES):
        path = item_request(query, cursor)
        status, headers, items = _api(path)
        records.append(
            _record(
                f"{PROJECT}/items?page={page_number + 1}",
                status,
                headers,
                page_number + 1,
            )
        )
        retain, cursor, pages_complete = page_decision(
            status, items, headers.get("link", ""), page_number + 1
        )
        if not retain:
            break
        pages.append(items)
        if cursor is None:
            break
    issue_path = f"{REPO}/issues/172"
    label_status, label_headers, issue = _api(issue_path)
    records.append(_record(issue_path, label_status, label_headers))
    complete = source_complete(account_status, definitions_complete, pages_complete)
    summary = classify_items(pages, FIELDS, complete)
    return {
        "account": account_name,
        "collected_at": collected_at.isoformat(),
        "expires_at": (collected_at + timedelta(minutes=5)).isoformat(),
        "requests": records,
        "project": summary,
        "sources": source_rows(
            summary, account_name, records[1], records[-2], records[-1]
        ),
        "issue_label_read": label_status == 200 and isinstance(issue, dict),
        "contract": "source-confirmed" if complete else "unknown/incomplete",
    }


def observe(seconds: int) -> dict[str, Any]:
    """Report App visibility and a bounded window without generating an event."""
    start = datetime.now(tz=UTC)
    account_status, account_headers, account = _api("user")
    hook_status, hook_headers, _ = _api(f"{REPO}/hooks?per_page=100")
    app_status, app_headers, app = _api("app")
    project_status, project_headers, project = _api(PROJECT)
    time.sleep(seconds)
    end = datetime.now(tz=UTC)
    delivery_path = "app/hook/deliveries?per_page=100"
    delivery_status, delivery_headers, deliveries = _api(delivery_path)
    actions: list[tuple[str, int]] = []
    detail_records: list[dict[str, Any]] = []
    project_node_id = project.get("node_id") if isinstance(project, dict) else None
    if (
        project_status == 200
        and isinstance(project_node_id, str)
        and isinstance(deliveries, list)
    ):
        for delivery in deliveries:
            if len(detail_records) == MAX_DELIVERY_DETAILS:
                break
            if not candidate_delivery(delivery, start.isoformat(), end.isoformat()):
                continue
            delivery_id = delivery.get("id")
            if not isinstance(delivery_id, int):
                continue
            detail_path = f"app/hook/deliveries/{delivery_id}"
            detail_status, detail_headers, detail = _api(detail_path)
            detail_records.append(
                _record("app/hook/deliveries/<id>", detail_status, detail_headers)
            )
            if detail_status == 200:
                action = observed_action(
                    delivery,
                    detail,
                    project_node_id,
                    start.isoformat(),
                    end.isoformat(),
                )
                if action is not None:
                    actions.append((action, 0))
    return {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "account": account.get("login", "unknown")
        if isinstance(account, dict)
        else "unknown",
        "requests": [
            _record("user", account_status, account_headers),
            _record(f"{REPO}/hooks?per_page=100", hook_status, hook_headers),
            _record("app", app_status, app_headers),
            _record(PROJECT, project_status, project_headers),
            _record(delivery_path, delivery_status, delivery_headers),
            *detail_records,
        ],
        "documented_availability": "organization-level projects_v2_item only",
        "user_owned_project_availability": "unknown",
        "subscription": subscription_state(app_status, app),
        "delivery": classify_delivery(actions, 0, seconds, True),
        "live_target_authorized": False,
    }


def main() -> int:
    """Run one bounded read-only mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rest-matrix", action="store_true")
    mode.add_argument("--observe-seconds", type=int)
    args = parser.parse_args()
    if args.observe_seconds is not None and not 1 <= args.observe_seconds <= 60:
        parser.error("--observe-seconds must be between 1 and 60")
    result = rest_matrix() if args.rest_matrix else observe(args.observe_seconds)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
