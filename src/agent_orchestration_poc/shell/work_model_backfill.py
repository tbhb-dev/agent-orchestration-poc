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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO, cast, override
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from agent_orchestration_poc.core.work_model_backfill import (
    NATIVE_OPTIONS,
    Item,
    Page,
    RestValues,
    Snapshot,
    Step,
    Tables,
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
    ProjectMetadata,
    Record,
    WriteContext,
    candidate_actions,
    closure_actions,
    comment_observation,
    confirmed_cp13,
    creation_observation,
    draft_actions,
    draft_observation,
    graphql_field_receipt,
    journal_state,
    label_observation,
    membership_actions,
    membership_observation,
    merge_planned_actions,
    native_field_payload,
    observation_value,
    ordered_actions,
    pr_closure_actions,
    project_field_actions,
    project_fields_observation,
    recorded_actions,
    stage_actions,
    validate_journal,
    validate_progress,
    validate_resume_admission,
    verified_detail,
    write_wait_seconds,
)
from agent_orchestration_poc.core.work_model_backfill_rollback import (
    rollback_plan,
    validate_rollback_journal,
    validate_rollback_progress,
)

LOGGER = logging.getLogger(__name__)
REPO = "repos/tbhb-dev/agent-orchestration-poc"
PROJECT = "orgs/tbhb-dev/projectsV2/1"
OLD_PROJECT = "users/tbhb/projectsV2/9"
API_VERSION = "2026-03-10"
NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
PAGE_SIZE = 100


@dataclass(frozen=True)
class ApplyInputs:
    """Saved checkpoint and reviewed values for one journaled stage."""

    tables: Tables
    cp1: Snapshot
    plan: tuple[Step, ...]
    run_id: str
    reviewed_status: dict[str, str] | None
    reviewed_writes: dict[str, Any]
    cp13: dict[str, Any] | None
    actions: tuple[Action, ...]


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


def _lock_journal(path: Path) -> TextIO:
    """Hold the forward journal lock across forward or rollback writes."""
    lock = path.with_suffix(path.suffix + ".lock")
    stream = os.fdopen(os.open(lock, os.O_CREAT | os.O_RDWR, 0o600))
    try:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise ValueError("another backfill runner holds the journal") from None
    return stream


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
    if action.kind in {"draft", "draft_body", "project_item", "project_fields"}:
        return _observe_project(api, action)
    if action.kind in {"parent", "blocker", "trial_add", "trial_remove"}:
        return _observe_relation(api, action)
    return _observe_issue(api, action)


def _observe_issue(api: Api, action: Action) -> object:
    if action.kind == "label_create":
        labels, _ = api.pages(f"{REPO}/labels?per_page=100", "labels")
        return label_observation(labels, cast("dict[str, Any]", action.payload)["name"])
    if action.kind == "comment":
        comments, _ = api.pages(
            f"{REPO}/issues/{action.number}/comments?per_page=100",
            f"comments:#{action.number}",
        )
        payload = cast("dict[str, Any]", action.payload)
        return comment_observation(comments, payload["body"])
    if action.kind in {"issue_state", "issue_type", "title", "body", "label_delete"}:
        return _observe_issue_metadata(api, action)
    if action.kind == "native":
        values, _ = api.pages(
            f"{REPO}/issues/{action.number}/issue-field-values?per_page=100",
            f"native:#{action.number}",
        )
        returned = {
            entry["issue_field_name"]: (entry.get("single_select_option") or {}).get(
                "name", ""
            )
            for entry in values
        }
        return tuple(sorted({**dict.fromkeys(NATIVE_OPTIONS, ""), **returned}.items()))
    if action.kind == "issue_create":
        issues, _ = api.pages(f"{REPO}/issues?state=all&per_page=100", "issues")
        return creation_observation(issues, cast("dict[str, Any]", action.payload))
    if action.kind == "pr_state":
        pr, _ = api.get(f"{REPO}/pulls/{action.number}")
        return pr["state"], pr["merged"]
    raise ValueError(f"unsupported issue action kind: {action.kind}")


def _observe_issue_metadata(api: Api, action: Action) -> object:
    issue, _ = api.get(f"{REPO}/issues/{action.number}")
    if action.kind == "issue_state":
        return issue["state"], issue.get("state_reason") or ""
    if action.kind == "issue_type":
        return (issue.get("type") or {}).get("name", "")
    if action.kind == "title":
        return issue["title"]
    if action.kind == "body":
        return issue.get("body") or ""
    return tuple(sorted(label["name"] for label in issue["labels"]))


def _observe_project(api: Api, action: Action) -> object:
    items, _ = _project_items(api, PROJECT)
    if action.kind == "draft":
        return draft_observation(items, cast("dict[str, Any]", action.payload)["title"])
    if action.kind == "draft_body":
        key = cast("dict[str, Any]", action.payload)["key"]
        return draft_observation(items, key.removeprefix("title:"))[1]
    if action.kind == "project_item":
        return membership_observation(
            items,
            action.number,
            str(cast("dict[str, Any]", action.payload)["id"]),
        )
    if action.kind == "project_fields":
        return project_fields_observation(items, action)
    raise ValueError(f"unsupported Project action kind: {action.kind}")


def _observe_relation(api: Api, action: Action) -> object:
    if action.kind == "parent":
        children, _ = api.pages(
            f"{REPO}/issues/{action.number}/sub_issues?per_page=100",
            f"sub_issues:#{action.number}",
        )
        child = cast("dict[str, Any]", action.payload)["child"]
        return (
            f"#{action.number}"
            if any(f"#{item['number']}" == child for item in children)
            else ""
        )
    if action.kind in {"blocker", "trial_add", "trial_remove"}:
        blockers, _ = api.pages(
            f"{REPO}/issues/{action.number}/dependencies/blocked_by?per_page=100",
            f"blockers:#{action.number}",
        )
        return tuple(sorted(f"#{item['number']}" for item in blockers))
    raise ValueError(f"unsupported relation action kind: {action.kind}")


def _check_draft_body_receipt(action: Action, response: object) -> None:
    data = response.get("data") if isinstance(response, dict) else None
    mutation = data.get("updateProjectV2DraftIssue") if isinstance(data, dict) else None
    draft = mutation.get("draftIssue") if isinstance(mutation, dict) else None
    if (
        not isinstance(response, dict)
        or response.get("errors")
        or not isinstance(draft, dict)
        or draft.get("id") != cast("dict[str, Any]", action.payload)["draft_id"]
    ):
        raise ValueError("GraphQL draft body mutation failed")


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
            action.id,
            "intent",
            {
                "payload": action.payload,
                "action": asdict(action),
                "at": time.time(),
            },
        )
        _append(path, asdict(intent))
        records.append(intent)
        request_path = (
            action.path
            if action.kind in {"draft", "project_item", "project_fields", "draft_body"}
            else f"{REPO}/{action.path}"
        )
        payload = (
            {"query": cast("dict[str, Any]", action.payload)["query"]}
            if action.kind in {"project_fields", "draft_body"}
            else {
                "sub_issue_id": cast("dict[str, Any]", action.payload)["sub_issue_id"]
            }
            if action.kind == "parent" and action.method == "DELETE"
            else None
            if action.method == "DELETE"
            else action.payload
        )
        if action.kind == "native":
            definitions, _ = api.pages(
                "orgs/tbhb-dev/issue-fields?per_page=100", "issue_fields"
            )
            payload = native_field_payload(action, definitions)
        response, headers, status = api.request(action.method, request_path, payload)
        if action.kind == "project_fields":
            graphql_field_receipt(action, response)
        if action.kind == "draft_body":
            _check_draft_body_receipt(action, response)
        identity = (
            response.get("value", response) if isinstance(response, dict) else None
        )
        receipt = Record(
            action.id,
            "response",
            {
                "status": status,
                "id": identity.get("id") if isinstance(identity, dict) else None,
                "draft_id": (
                    response.get("content", {}).get("id")
                    if action.kind == "draft" and isinstance(response, dict)
                    else None
                ),
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
        action.id,
        "verified",
        {"observed": observation_value(action, readback), "read": api.ledger[-1]}
        if action.step == "rollback"
        else verified_detail(action, readback, api.ledger[-1]),
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
    reviewed_writes: dict[str, Any] = (
        json.loads(args.reviewed_writes.read_text()) if args.reviewed_writes else {}
    )
    if not isinstance(reviewed_writes, dict):
        raise TypeError("reviewed writes must be a JSON object")
    cp13_data = _confirmed_cp13(args, digests)
    if args.stage == "4:labels" and "labels" not in reviewed_writes:
        raise ValueError("reviewed label definitions are missing")
    closures = (
        *closure_actions(tables, cp1, plan, run_id),
        *pr_closure_actions(run_id, reviewed_writes.get("pr97_comment", "")),
    )
    memberships = membership_actions(cp1, plan)
    drafts = draft_actions(tables, cp1, plan)
    api = _api(args.api_base)
    project, _ = api.get(PROJECT)
    fields, _ = api.pages(f"{PROJECT}/fields?per_page=100", "project_fields")
    raw_items, _ = _project_items(api, PROJECT)
    labels, _ = api.pages(f"{REPO}/labels?per_page=100", "labels")
    project_fields = project_field_actions(
        tables,
        cp1,
        ProjectMetadata(project, fields, raw_items),
        cp1_data.get("reviewed_status"),
    )
    prepared = ApplyInputs(
        tables,
        cp1,
        plan,
        run_id,
        cp1_data.get("reviewed_status"),
        reviewed_writes,
        cp13_data,
        (*closures, *memberships, *drafts, *project_fields),
    )
    with _lock_journal(args.journal):
        _apply_locked(
            args, api, prepared, ProjectMetadata(project, fields, raw_items), labels
        )
    return 0


def run_rollback(args: argparse.Namespace) -> int:
    """Reverse verified forward writes through a separately locked journal."""
    if not args.apply or not args.cp1 or not args.journal or not args.rollback_journal:
        raise ValueError(
            "rollback requires --apply, --cp1, --journal, and --rollback-journal"
        )
    tables, digests = _tables(args)
    cp1_bytes = args.cp1.read_bytes()
    run_id = hashlib.sha256(cp1_bytes).hexdigest()
    if args.confirm_checkpoint != f"CP1:{run_id}":
        raise ValueError("operator checkpoint confirmation differs from CP1")
    cp1_data = json.loads(cp1_bytes)
    if cp1_data["digests"] != digests:
        raise ValueError("CP1 was built from different tables")
    cp1 = _snapshot(cp1_data["snapshot"])
    validate_cp1(tables, cp1, cp1_data.get("reviewed_status"))
    api = _api(args.api_base)
    project, _ = api.get(PROJECT)
    fields, _ = api.pages(f"{PROJECT}/fields?per_page=100", "project_fields")
    items, _ = _project_items(api, PROJECT)
    metadata = ProjectMetadata(project, fields, items)
    with _lock_journal(args.journal):
        forward = [json.loads(line) for line in args.journal.read_text().splitlines()]
        actions = recorded_actions(forward)
        records = validate_journal(forward, run_id, actions)
        if any(
            row.action_id == "stage:15" and row.phase == "complete" for row in records
        ):
            confirmed_cp13(
                "15",
                args.cp13.read_bytes() if args.cp13 else None,
                args.confirm_cp13,
                digests,
            )
        current = collect(api, "initial")
        inverse = rollback_plan(cp1, current, actions, records, metadata)
        if not args.rollback_journal.exists():
            validate_rollback_progress(cp1, current, (actions, records), (inverse, ()))
            descriptor = os.open(
                args.rollback_journal, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            os.close(descriptor)
            _append(args.rollback_journal, {"version": 1, "run_id": run_id})
            directory = os.open(args.rollback_journal.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        rows = [
            json.loads(line) for line in args.rollback_journal.read_text().splitlines()
        ]
        undone = list(validate_rollback_journal(rows, run_id, inverse))
        validate_rollback_progress(
            cp1, current, (actions, records), (inverse, tuple(undone))
        )
        verified = {row.action_id for row in undone if row.phase == "verified"}
        for action in inverse:
            if action.id in verified:
                continue
            _execute(api, args.rollback_journal, action, undone, pace=True)
    return 0


def _confirmed_cp13(
    args: argparse.Namespace, digests: dict[str, str]
) -> dict[str, Any] | None:
    data = args.cp13.read_bytes() if args.stage == "15" and args.cp13 else None
    return confirmed_cp13(args.stage, data, args.confirm_cp13, digests)


def _verdict_comments(
    api: Api, args: argparse.Namespace, tables: Tables
) -> dict[str, list[dict[str, Any]]]:
    comments: dict[str, list[dict[str, Any]]] = {}
    if args.stage == "6T":
        for row in tables.assignments:
            if (
                row["proposed title"]
                and row["refinement verdict"] == "new verdict required"
            ):
                number = row["number"]
                comments[f"#{number}"], _ = api.pages(
                    f"{REPO}/issues/{number}/comments?per_page=100",
                    f"verdict:#{number}",
                )
    return comments


def _apply_locked(
    args: argparse.Namespace,
    api: Api,
    prepared: ApplyInputs,
    metadata: ProjectMetadata,
    labels: list[dict[str, Any]],
) -> None:
    actions = prepared.actions
    run_id = prepared.run_id
    cp1 = prepared.cp1
    reviewed_writes = prepared.reviewed_writes
    tables = prepared.tables
    cp13_data = prepared.cp13
    saved_rows: list[dict[str, Any]] = (
        [json.loads(line) for line in args.journal.read_text().splitlines()]
        if args.journal.exists()
        else []
    )
    recovered = tuple(
        action
        for action in recorded_actions(saved_rows)
        if action.id not in {base.id for base in actions}
    )
    known = ordered_actions((*actions, *recovered))
    records = list(_journal(args.journal, run_id, known, create=args.stage == "0"))
    current = collect(api, "initial")
    validate_progress(cp1, current, known, tuple(records))
    for action in known:
        if action.kind != "label_create" or not any(
            row.action_id == action.id and row.phase == "verified" for row in records
        ):
            continue
        name = cast("dict[str, Any]", action.payload)["name"]
        observed_label = label_observation(labels, name)
        if journal_state(action, tuple(records), observed_label) != "skip":
            raise ValueError(f"verified label definition changed: {name}")
    pr_state = (
        _observe(api, pr_closure_actions(run_id, reviewed_writes["pr97_comment"])[1])
        if args.stage != "0"
        else None
    )
    validate_resume_admission(
        args.stage,
        _snapshot(cp13_data["snapshot"]) if cp13_data is not None else None,
        current,
        tuple(records),
        cast("tuple[str, bool] | None", pr_state),
    )
    candidate = candidate_actions(
        args.stage,
        WriteContext(
            tables,
            cp1,
            current,
            prepared.plan,
            metadata,
            prepared.reviewed_status,
            reviewed_writes.get("bodies", {}),
            tuple(reviewed_writes.get("labels", ())),
            tuple(labels),
            reviewed_writes.get("verdicts"),
            _verdict_comments(api, args, tables),
        ),
    )
    selected = stage_actions(
        args.stage,
        merge_planned_actions(known, candidate),
        tuple(records),
    )
    for action in selected:
        if any(
            row.action_id == action.id and row.phase == "verified" for row in records
        ):
            continue
        _execute(api, args.journal, action, records, pace=True)
    if not any(
        row.phase == "complete" and row.detail["stage"] == args.stage for row in records
    ):
        marker = Record(
            f"stage:{args.stage}", "complete", {"stage": args.stage, "at": time.time()}
        )
        _append(args.journal, asdict(marker))
        records.append(marker)


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
    parser.add_argument("checkpoint", choices=("initial", "final", "apply", "rollback"))
    for name in ("assignments", "parents", "edges", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--api-base", default="https://api.github.com")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cp1", type=Path)
    parser.add_argument("--cp13", type=Path)
    parser.add_argument("--confirm-cp13")
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reviewed-status")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--rollback-journal", type=Path)
    parser.add_argument("--reviewed-writes", type=Path)
    parser.add_argument(
        "--stage",
        choices=(
            "0",
            "3:trial",
            "4:labels",
            "6:items",
            "6:drafts",
            "6:fields",
            "6:new-fields",
            "6:body",
            "6:native",
            "6T",
            "9:create",
            "9:native",
            "9:items",
            "9:fields",
            "9:close",
            "10",
            "11:links",
            "11:bodies",
            "12:create",
            "12:native",
            "12:items",
            "12:fields",
            "15",
        ),
    )
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
        if args.checkpoint == "rollback":
            return run_rollback(args)
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        LOGGER.warning("backfill checkpoint refused: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
