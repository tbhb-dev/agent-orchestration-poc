"""REST collection and coordinator command for parent dependency links."""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast
from uuid import uuid7

from agent_orchestration_poc.core.parent_link_sync import (
    Issue,
    Operation,
    Parent,
    compare,
    initial_edges,
    ongoing_edges,
    operation_plan,
    owned_after,
    owned_before,
    parent_titles,
)
from agent_orchestration_poc.core.work_model_backfill import Tables, parse_tables

ROOT = Path(__file__).resolve().parents[3]
TABLES = ROOT / "reports/inputs/work-model-tables"
REPOSITORY = "repos/tbhb-dev/agent-orchestration-poc"
LOGGER = logging.getLogger(__name__)


def get_tables() -> Tables:
    """Use the versioned backfill parser for all three approved tables."""
    stem = "2026-09-27-work-model-v3-final"
    return parse_tables(
        *(
            (TABLES / f"{stem}{suffix}").read_text()
            for suffix in (".tsv", "-parents.tsv", "-edges.tsv")
        )
    )


def request(
    path: str, *, method: str = "GET", issue_id: int = 0, missing_ok: bool = False
) -> dict[str, Any] | None:
    """Call the documented REST endpoint without exposing credentials."""
    args = [
        "gh",
        "api",
        f"{REPOSITORY}/{path}",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    if method != "GET":
        args.extend(["-X", method])
    if issue_id:
        args.extend(["-F", f"issue_id={issue_id}"])
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        if missing_ok and "HTTP 404" in result.stderr:
            return None
        raise RuntimeError(f"REST {method} {path} failed with exit {result.returncode}")
    return cast("dict[str, Any]", json.loads(result.stdout)) if result.stdout else None


def pages(path: str) -> list[dict[str, Any]]:
    """Collect all linked REST pages and refuse duplicate records."""
    args = [
        "gh",
        "api",
        f"{REPOSITORY}/{path}",
        "--paginate",
        "--slurp",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"REST GET {path} failed with exit {result.returncode}")
    page_values = cast("list[list[dict[str, Any]]]", json.loads(result.stdout))
    values = [item for page in page_values for item in page]
    if len({item["id"] for item in values}) != len(values):
        raise ValueError("duplicate paginated issue")
    return values


def blocked_by(number: int) -> tuple[int, ...]:
    """Read one complete native blocker list, including later pages."""
    rows = pages(f"issues/{number}/dependencies/blocked_by?per_page=100")
    return tuple(int(row["id"]) for row in rows)


def collect(
    tables: Tables, *, ongoing: bool
) -> tuple[tuple[Parent, ...], tuple[Issue, ...]]:
    """Collect fresh parent, membership, and issue blocker values."""
    rows = [
        row
        for row in pages("issues?state=all&per_page=100")
        if "pull_request" not in row
    ]
    parents = [row for row in rows if row["title"] in parent_titles(tables)]
    if len(parents) != len(parent_titles(tables)):
        if parents or ongoing:
            raise ValueError("incomplete parent creation or changed title")
        return (), ()
    if len({row["title"] for row in parents}) != len(parents):
        raise ValueError("ambiguous parent title")
    parent_values = tuple(
        Parent(
            row["title"], int(row["number"]), int(row["id"]), blocked_by(row["number"])
        )
        for row in parents
    )
    if not ongoing:
        return parent_values, ()
    return parent_values, collect_issues(rows, parent_values)


def collect_issues(
    rows: list[dict[str, Any]], parents: tuple[Parent, ...]
) -> tuple[Issue, ...]:
    """Read every issue membership and blocker list after parent resolution."""
    by_id = {int(row["id"]): row for row in rows}
    parent_by_number = {parent.number: parent.title for parent in parents}
    issues = []
    for row in rows:
        number = int(row["number"])
        if number in parent_by_number:
            continue
        raw_parent = request(f"issues/{number}/parent", missing_ok=True)
        epic = ""
        if raw_parent is not None:
            epic = parent_by_number.get(raw_parent["number"], "")
            if not epic:
                raise ValueError("unresolved issue parent")
        blockers = blocked_by(number)
        if any(blocker not in by_id for blocker in blockers):
            raise ValueError("unresolved issue blocker")
        issues.append(
            Issue(
                str(number),
                epic,
                tuple(str(by_id[blocker]["number"]) for blocker in blockers),
            )
        )
    if len(issues) + len(parents) != len(rows):
        raise ValueError("incomplete issue read")
    return tuple(issues)


def read_snapshot(
    path: Path, tables: Tables
) -> tuple[tuple[Parent, ...], tuple[Issue, ...]]:
    """Read a complete saved fixture or runner snapshot with explicit counts."""
    raw = json.loads(path.read_text())
    parents = tuple(Parent(**value) for value in raw["parents"])
    issues = tuple(Issue(**value) for value in raw["issues"])
    if (
        raw.get("complete") is not True
        or raw.get("parent_count") != len(parents)
        or raw.get("issue_count") != len(issues)
        or len(parents) not in (0, len(parent_titles(tables)))
    ):
        raise ValueError("incomplete saved read")
    return parents, issues


def read_managed(path: Path | None, tables: Tables) -> frozenset[tuple[str, str]]:
    """Read owned derived links from the last successful coordinator run."""
    if path is None:
        return owned_before(tables, None, applied=False)
    raw = json.loads(path.read_text())
    if raw.get("complete") is not True:
        raise ValueError("incomplete managed ledger")
    return owned_before(
        tables,
        tuple(tuple(edge) for edge in raw["managed"]),
        applied=raw.get("applied") is True,
    )


def coordinator_identity() -> bool:
    """Require the assigned coordinator account before any native mutation."""
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "tbhb-agent"


def apply(
    plan: tuple[Operation, ...],
    parents: tuple[Parent, ...],
) -> list[dict[str, str]]:
    """Write owned deltas one at a time and read back each operation."""
    by_title = {parent.title: parent for parent in parents}
    operations = []
    for operation in plan:
        dependent, blocker = operation.edge
        add = operation.method == "POST"
        target = by_title[dependent]
        blocker_id = by_title[blocker].issue_id
        path = f"issues/{target.number}/dependencies/blocked_by"
        if add:
            response = request(path, method="POST", issue_id=blocker_id)
            if not isinstance(response, dict) or response.get("id") != blocker_id:
                raise ValueError("add response differs")
        else:
            request(f"{path}/{blocker_id}", method="DELETE")
        read_back = blocked_by(target.number)
        if (blocker_id in read_back) != add:
            raise ValueError("operation read-back differs")
        operations.append(
            {
                "operation_id": str(uuid7()),
                "method": operation.method,
                "dependent": dependent,
                "blocker": blocker,
            }
        )
        print(  # noqa: T201 - operation receipt remains available on stderr
            json.dumps(operations[-1], sort_keys=True), file=sys.stderr, flush=True
        )
    return operations


def main() -> int:
    """Compare by default, or apply only complete coordinator-owned deltas."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ongoing", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--managed", type=Path)
    args = parser.parse_args()
    if args.apply and (not args.ongoing or args.snapshot):
        parser.error("--apply requires fresh --ongoing REST reads")
    tables = get_tables()
    try:
        parents, issues = (
            read_snapshot(args.snapshot, tables)
            if args.snapshot
            else collect(tables, ongoing=args.ongoing)
        )
        if args.ongoing and not parents:
            raise ValueError("ongoing read requires all parents")
        if args.apply and collect(tables, ongoing=True) != (parents, issues):
            raise ValueError("changed read before apply")
        desired = (
            ongoing_edges(tables, issues)
            if args.ongoing and parents
            else initial_edges(tables)
        )
        managed = read_managed(args.managed, tables)
        result = compare(tables, desired, parents, issues, managed)
        plan = operation_plan(
            result,
            args.apply,
            len(parents) == len(parent_titles(tables))
            and (not args.apply or coordinator_identity()),
        )
        operations = apply(plan, parents) if args.apply else []
        output: dict[str, object] = {**asdict(result), "operations": operations}
        output["desired"] = sorted(result.desired)
        output["actual"] = sorted(result.actual)
        output["managed"] = sorted(
            owned_after(tables, managed, plan if args.apply else ())
        )
        output["complete"] = True
        output["applied"] = args.apply
        print(json.dumps(output, sort_keys=True))  # noqa: T201 - command output is its contract
        return 0
    except RuntimeError, ValueError, KeyError, TypeError:
        LOGGER.exception("parent link sync refused")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
