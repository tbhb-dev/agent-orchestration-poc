"""CP1 and CP13 collection and staged journaled REST writes."""

import argparse
import fcntl
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast, override
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from agent_orchestration_poc.core.work_model_backfill import (
    Item,
    Page,
    RestValues,
    Snapshot,
    TargetInputs,
    compare_cp13,
    expected_cp13,
    operation_plan,
    parse_tables,
    project_field_ids,
    snapshot_from_rest,
    validate_cp1,
    verify_table_digests,
)
from agent_orchestration_poc.core.work_model_backfill_executor import (
    JOURNAL_VERSION,
    Action,
    Record,
    closure_actions,
    comment_observation,
    draft_actions,
    draft_observation,
    journal_state,
    observation_value,
    validate_journal,
    validate_progress,
    verified_detail,
    write_wait_seconds,
)

LOGGER = logging.getLogger(__name__)
REPO = "repos/tbhb-dev/agent-orchestration-poc"
PROJECT = "orgs/tbhb-dev/projectsV2/1"
OLD_PROJECT = "users/tbhb/projectsV2/9"
API_VERSION = "2026-03-10"
NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
PAGE_SIZE = 100


class _NoRedirect(HTTPRedirectHandler):
    @override
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        raise ValueError("REST GET redirect refused")


class Api:
    """Authenticated REST client with complete page receipts and safe ledger."""

    def __init__(self, base: str, token: str) -> None:
        self.base = base.rstrip("/") + "/"
        self.token = token
        self.ledger: list[dict[str, str | int]] = []

    def get(self, path: str) -> tuple[Any, dict[str, str]]:
        """Read one JSON response and retain status and safe rate headers."""
        data, headers, _ = self.request("GET", path)
        return data, headers

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str], int]:
        """Call a same-origin endpoint without following redirects."""
        url = urljoin(self.base, path)
        if (
            urlparse(url).scheme not in {"http", "https"}
            or urlparse(url).netloc != urlparse(self.base).netloc
            or urlparse(url).scheme != urlparse(self.base).scheme
        ):
            raise ValueError("pagination changed API origin")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with build_opener(_NoRedirect()).open(
                Request(  # noqa: S310 scheme and origin checked above
                    url,
                    data=json.dumps(payload).encode() if payload is not None else None,
                    headers=headers,
                    method=method,
                ),
                timeout=30,
            ) as response:
                status = response.status
                returned = {
                    key.lower(): value for key, value in response.headers.items()
                }
                body = response.read()
                data = json.loads(body) if body else None
        except HTTPError as exc:
            exc.close()
            raise ValueError(f"REST {method} failed with HTTP {exc.code}") from None
        except URLError as exc:
            raise ValueError(f"REST {method} failed before a response") from exc
        if status not in ({200} if method == "GET" else {200, 201, 204}):
            raise ValueError(f"REST {method} returned HTTP {status}")
        self.ledger.append(
            {
                "method": method,
                "path": urlparse(url).path
                + (f"?{urlparse(url).query}" if urlparse(url).query else ""),
                "status": status,
                **{
                    name: returned[name]
                    for name in (
                        "x-ratelimit-limit",
                        "x-ratelimit-remaining",
                        "x-ratelimit-reset",
                        "x-ratelimit-used",
                        "retry-after",
                    )
                    if name in returned
                },
            }
        )
        return data, returned, status

    def pages(self, path: str, collection: str) -> tuple[list[Any], tuple[Page, ...]]:
        """Follow every Link page and reject a full page with no next link."""
        current = path
        visited: set[str] = set()
        groups: list[list[Any]] = []
        for _ in range(100):
            if current in visited:
                raise ValueError("repeated pagination URL")
            visited.add(current)
            data, headers = self.get(current)
            if not isinstance(data, list):
                raise TypeError("paginated response is not a list")
            groups.append(data)
            match = NEXT.search(headers.get("link", ""))
            if not match:
                if len(data) == PAGE_SIZE:
                    raise ValueError("full page has no next link")
                total = sum(map(len, groups))
                pages = tuple(
                    Page(collection, index, len(group), len(groups), total)
                    for index, group in enumerate(groups, 1)
                )
                return [row for group in groups for row in group], pages
            current = match.group(1)
        raise ValueError("collection exceeds page safety limit")


def _project_items(api: Api, path: str) -> tuple[list[Any], tuple[Page, ...]]:
    fields, _ = api.pages(f"{path}/fields?per_page=100", f"fields:{path}")
    selected = project_field_ids(fields)
    if not selected:
        raise ValueError("Project field definitions are missing")
    ids = ",".join(str(field_id) for field_id in selected)
    collection = "project" if path == PROJECT else "source_project"
    return api.pages(f"{path}/items?per_page=100&fields={ids}", collection)


def _branch_sha(api: Api) -> str:
    pr, _ = api.get(f"{REPO}/pulls/97")
    head = pr["head"]
    if head["repo"]["full_name"] != "tbhb-dev/agent-orchestration-poc":
        raise ValueError("retained branch moved to another repository")
    branch, _ = api.get(f"{REPO}/git/ref/heads/{quote(head['ref'], safe='/')}")
    return cast("str", branch["object"]["sha"])


def collect(api: Api, run_state: str) -> Snapshot:
    """Read issues, both Projects, and every nested issue collection."""
    raw, issue_pages = api.pages(f"{REPO}/issues?state=all&per_page=100", "issues")
    old, _ = _project_items(api, OLD_PROJECT)
    project, project_pages = _project_items(api, PROJECT)
    nested_pages: list[Page] = []
    nested: dict[str, tuple[list[Any], list[Any], list[Any]]] = {}
    for issue in raw:
        if "pull_request" in issue:
            continue
        key = f"#{issue['number']}"
        number = issue["number"]
        values, receipts = api.pages(
            f"{REPO}/issues/{number}/issue-field-values?per_page=100", f"native:{key}"
        )
        nested_pages.extend(receipts)
        children, receipts = api.pages(
            f"{REPO}/issues/{number}/sub_issues?per_page=100", f"sub_issues:{key}"
        )
        nested_pages.extend(receipts)
        blockers, receipts = api.pages(
            f"{REPO}/issues/{number}/dependencies/blocked_by?per_page=100",
            f"blockers:{key}",
        )
        nested_pages.extend(receipts)
        nested[key] = (values, children, blockers)
    return snapshot_from_rest(
        RestValues(
            raw,
            issue_pages,
            old,
            project,
            project_pages,
            nested,
            tuple(nested_pages),
            _branch_sha(api),
            run_state,
        )
    )


def _tables(args: argparse.Namespace) -> tuple[Any, dict[str, str]]:
    names = ("assignments", "parents", "edges")
    values = {name: cast("Path", getattr(args, name)).read_text() for name in names}
    digests = {
        name: hashlib.sha256(values[name].encode()).hexdigest() for name in names
    }
    verify_table_digests(
        digests, args.manifest.read_text(), markdown=args.manifest.suffix == ".md"
    )
    return parse_tables(*(values[name] for name in names)), digests


def _snapshot(data: dict[str, Any]) -> Snapshot:
    return Snapshot(
        data["version"],
        tuple(_item(item) for item in data["items"]),
        tuple(Page(**page) for page in data["pages"]),
        data["branch_sha"],
        data["run_state"],
    )


def _item(data: dict[str, Any]) -> Item:
    """Restore the immutable Item fields from a saved JSON value."""
    values = data.copy()
    for field in ("native", "project", "source_project"):
        values[field] = tuple(tuple(pair) for pair in data[field])
    values["blockers"] = tuple(data["blockers"])
    values["labels"] = tuple(data["labels"])
    return Item(**values)


def _api(base: str) -> Api:
    token = ""
    parsed = urlparse(base)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        if base.rstrip("/") != "https://api.github.com":
            raise ValueError("authenticated API base must be api.github.com")
        result = subprocess.run(
            ("gh", "auth", "token"), capture_output=True, text=True, check=False
        )
        if result.returncode or not result.stdout.strip():
            raise ValueError("GitHub authentication is unavailable")
        token = result.stdout.strip()
    return Api(base, token)


def _append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _journal(
    path: Path, run_id: str, actions: tuple[Action, ...], *, create: bool
) -> tuple[Record, ...]:
    if not path.exists():
        if not create:
            raise ValueError("trial requires a completed closure journal")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        _append(path, {"version": JOURNAL_VERSION, "run_id": run_id})
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return validate_journal(rows, run_id, actions)


def _observe(api: Api, action: Action) -> object:
    if action.kind == "comment":
        comments, _ = api.pages(
            f"{REPO}/issues/{action.number}/comments?per_page=100",
            f"comments:#{action.number}",
        )
        payload = cast("dict[str, Any]", action.payload)
        return comment_observation(comments, payload["body"])
    if action.kind == "issue_state":
        issue, _ = api.get(f"{REPO}/issues/{action.number}")
        return issue["state"], issue.get("state_reason") or ""
    if action.kind == "draft":
        items, _ = _project_items(api, PROJECT)
        return draft_observation(items, cast("dict[str, Any]", action.payload)["title"])
    raise ValueError(f"unsupported action kind: {action.kind}")


def _execute(
    api: Api, path: Path, action: Action, records: list[Record], *, pace: bool = False
) -> None:
    observed = _observe(api, action)
    decision = journal_state(action, tuple(records), observed)
    if decision == "halt":
        raise ValueError(f"operation {action.id} differs from journal or precondition")
    if decision == "skip":
        return
    if decision == "send":
        if pace:
            remaining = api.ledger[-1].get("x-ratelimit-remaining")
            if remaining is None and api.base == "https://api.github.com/":
                raise ValueError("REST rate header is missing")
            prior = next(
                (
                    record.detail["at"]
                    for record in reversed(records)
                    if record.phase == "intent"
                ),
                None,
            )
            time.sleep(
                write_wait_seconds(
                    time.time(),
                    prior,
                    int(remaining) if remaining is not None else None,
                )
            )
        intent = Record(
            action.id, "intent", {"payload": action.payload, "at": time.time()}
        )
        _append(path, asdict(intent))
        records.append(intent)
        request_path = (
            action.path if action.kind == "draft" else f"{REPO}/{action.path}"
        )
        response, headers, status = api.request(
            action.method, request_path, action.payload
        )
        receipt = Record(
            action.id,
            "response",
            {
                "status": status,
                "id": response.get("id") if isinstance(response, dict) else None,
                "request_id": headers.get("x-github-request-id", ""),
                "rate_remaining": headers.get("x-ratelimit-remaining", ""),
            },
        )
        _append(path, asdict(receipt))
        records.append(receipt)
    readback = _observe(api, action)
    if observation_value(action, readback) != action.after:
        raise ValueError(f"operation {action.id} failed read-back")
    verified = Record(
        action.id, "verified", verified_detail(action, readback, api.ledger[-1])
    )
    _append(path, asdict(verified))
    records.append(verified)


def run_apply(args: argparse.Namespace) -> int:
    """Execute one confirmed stage with durable per-write read-back."""
    if not args.apply or not args.cp1 or not args.journal:
        raise ValueError("apply requires --apply, --cp1, and --journal")
    tables, digests = _tables(args)
    cp1_bytes = args.cp1.read_bytes()
    run_id = hashlib.sha256(cp1_bytes).hexdigest()
    expected_confirmation = f"CP1:{run_id}"
    if args.confirm_checkpoint != expected_confirmation:
        raise ValueError("operator checkpoint confirmation differs from CP1")
    cp1_data = json.loads(cp1_bytes)
    if cp1_data["digests"] != digests:
        raise ValueError("CP1 was built from different tables")
    cp1 = _snapshot(cp1_data["snapshot"])
    plan = operation_plan(tables, cp1, cp1_data.get("reviewed_status"))
    closures = closure_actions(tables, cp1, plan, run_id)
    drafts = draft_actions(tables, cp1, plan)
    actions = (*closures, *drafts)
    lock = args.journal.with_suffix(args.journal.suffix + ".lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor) as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another backfill runner holds the journal") from None
        records = list(
            _journal(args.journal, run_id, actions, create=args.stage == "0")
        )
        if args.stage == "6:drafts" and any(
            not any(
                record.action_id == action.id and record.phase == "verified"
                for record in records
            )
            for action in closures
        ):
            raise ValueError("stage 0 must be verified before draft creation")
        api = _api(args.api_base)
        validate_progress(cp1, collect(api, "initial"), actions, tuple(records))
        selected = closures if args.stage == "0" else drafts
        for action in selected:
            _execute(api, args.journal, action, records, pace=True)
    return 0


def run(args: argparse.Namespace) -> int:
    """Collect a dry-run checkpoint and compare it with a reviewed contract."""
    tables, digests = _tables(args)
    api = _api(args.api_base)
    snapshot = collect(api, args.checkpoint)
    envelope: dict[str, Any] = {
        "snapshot": asdict(snapshot),
        "digests": digests,
        "ledger": api.ledger,
    }
    difference_count = 0
    if args.checkpoint == "initial":
        reviewed_status = (
            json.loads(args.reviewed_status)
            if getattr(args, "reviewed_status", None)
            else None
        )
        validate_cp1(tables, snapshot, reviewed_status)
        envelope["reviewed_status"] = reviewed_status
        envelope["plan"] = [
            asdict(step) for step in operation_plan(tables, snapshot, reviewed_status)
        ]
        sys.stdout.write(json.dumps(envelope["plan"], indent=2) + "\n")
    else:
        cp1_data = json.loads(args.cp1.read_text())
        if cp1_data["digests"] != digests:
            raise ValueError("CP1 was built from different tables")
        cp1 = _snapshot(cp1_data["snapshot"])
        inputs_data = json.loads(args.inputs.read_text())
        validate_cp1(tables, cp1, inputs_data.get("reviewed_status"))
        inputs = TargetInputs(
            {key: _item(item) for key, item in inputs_data["created"].items()},
            inputs_data["bodies"],
            frozenset(inputs_data["closed_at_cp0"]),
            frozenset(inputs_data["revoked"]),
            tomllib.loads(args.reference.read_text()),
            inputs_data.get("added_items"),
            inputs_data.get("reviewed_status"),
        )
        expected = expected_cp13(tables, cp1, inputs)
        differences = compare_cp13(expected, snapshot, cp1.branch_sha)
        envelope["differences"] = [asdict(item) for item in differences]
        difference_count = len(differences)
    if args.output:
        args.output.write_text(json.dumps(envelope, indent=2) + "\n")
    if difference_count:
        LOGGER.warning("CP13 differs in %s fields", difference_count)
        return 2
    return 0


def main() -> int:
    """Parse checkpoint inputs without exposing response bodies on failure."""
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", choices=("initial", "final", "apply"))
    for name in ("assignments", "parents", "edges", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--api-base", default="https://api.github.com")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cp1", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reviewed-status")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--stage", choices=("0", "6:drafts"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-checkpoint")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if args.checkpoint == "final" and not all(
            (args.cp1, args.inputs, args.reference)
        ):
            raise ValueError("final checkpoint needs CP1, inputs, and reference")
        if args.checkpoint == "apply":
            if not args.stage:
                raise ValueError("apply requires --stage")
            return run_apply(args)
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        LOGGER.warning("backfill checkpoint refused: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
