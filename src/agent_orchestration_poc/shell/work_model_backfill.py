"""Read-only CP1 and CP13 collection for the work model backfill."""

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

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

LOGGER = logging.getLogger(__name__)
REPO = "repos/tbhb-dev/agent-orchestration-poc"
PROJECT = "orgs/tbhb-dev/projectsV2/1"
OLD_PROJECT = "users/tbhb/projectsV2/9"
API_VERSION = "2026-03-10"
NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
PAGE_SIZE = 100


class Api:
    """Small authenticated REST GET client with complete page receipts."""

    def __init__(self, base: str, token: str) -> None:
        self.base = base.rstrip("/") + "/"
        self.token = token
        self.ledger: list[dict[str, str | int]] = []

    def get(self, path: str) -> tuple[Any, dict[str, str]]:
        """Read one JSON response and retain status and safe rate headers."""
        url = urljoin(self.base, path)
        if (
            urlparse(url).netloc != urlparse(self.base).netloc
            or urlparse(url).scheme != urlparse(self.base).scheme
        ):
            raise ValueError("pagination changed API origin")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:  # noqa: S310 checked host above
                status = response.status
                returned = {
                    key.lower(): value for key, value in response.headers.items()
                }
                data = json.load(response)
        except HTTPError as exc:
            raise ValueError(f"REST GET failed with HTTP {exc.code}") from None
        except URLError as exc:
            raise ValueError("REST GET failed before a response") from exc
        if status != 200:
            raise ValueError(f"REST GET returned HTTP {status}")
        self.ledger.append(
            {
                "method": "GET",
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
        return data, returned

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
        tuple(Item(**item) for item in data["items"]),
        tuple(Page(**page) for page in data["pages"]),
        data["branch_sha"],
        data["run_state"],
    )


def run(args: argparse.Namespace) -> int:
    """Collect a dry-run checkpoint and compare it with a reviewed contract."""
    tables, digests = _tables(args)
    base = args.api_base
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
    api = Api(base, token)
    snapshot = collect(api, args.checkpoint)
    envelope: dict[str, Any] = {
        "snapshot": asdict(snapshot),
        "digests": digests,
        "ledger": api.ledger,
    }
    if args.checkpoint == "initial":
        validate_cp1(tables, snapshot)
        envelope["plan"] = [asdict(step) for step in operation_plan(tables, snapshot)]
        sys.stdout.write(json.dumps(envelope["plan"], indent=2) + "\n")
    else:
        cp1_data = json.loads(args.cp1.read_text())
        if cp1_data["digests"] != digests:
            raise ValueError("CP1 was built from different tables")
        cp1 = _snapshot(cp1_data["snapshot"])
        validate_cp1(tables, cp1)
        inputs_data = json.loads(args.inputs.read_text())
        inputs = TargetInputs(
            {key: Item(**item) for key, item in inputs_data["created"].items()},
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
        if differences:
            raise ValueError(f"CP13 differs in {len(differences)} fields")
    if args.output:
        args.output.write_text(json.dumps(envelope, indent=2) + "\n")
    return 0


def main() -> int:
    """Parse checkpoint inputs without exposing response bodies on failure."""
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", choices=("initial", "final"))
    for name in ("assignments", "parents", "edges", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--api-base", default="https://api.github.com")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cp1", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if args.checkpoint == "final" and not all(
            (args.cp1, args.inputs, args.reference)
        ):
            raise ValueError("final checkpoint needs CP1, inputs, and reference")
        return run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        LOGGER.warning("backfill checkpoint refused: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
