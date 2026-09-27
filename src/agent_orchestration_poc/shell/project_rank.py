"""Coordinator-only Project rank command and GitHub transport."""

import argparse
import fcntl
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agent_orchestration_poc.core.project_rank import (
    Item,
    Mutation,
    apply_mutations,
    plan_move,
    plan_order,
    plan_replace,
    safe_to_write,
    validate_items,
)

LOGGER = logging.getLogger(__name__)
LOCK = Path("/tmp/agent-orchestration-project-rank.lock")  # noqa: S108 fixed host-wide lock
OWNER = "tbhb"
PROJECT_NUMBER = 9
COORDINATOR = "tbhbagent"
QUERY = """query($owner:String!,$number:Int!,$after:String){
  user(login:$owner){projectV2(number:$number){id items(first:100,after:$after,
    orderBy:{field:POSITION,direction:ASC}){totalCount
    pageInfo{hasNextPage endCursor} nodes{id type
    content{... on Issue{number state}}
    priority:fieldValueByName(name:"Priority"){
      ... on ProjectV2ItemFieldSingleSelectValue{name}}
    workType:fieldValueByName(name:"Type"){
      ... on ProjectV2ItemFieldSingleSelectValue{name}}}}}}
  rateLimit{remaining cost}
}"""
MUTATION = """mutation($project:ID!,$item:ID!,$after:ID){
  updateProjectV2ItemPosition(input:{projectId:$project,itemId:$item,afterId:$after}){
    clientMutationId}
  rateLimit{remaining cost}
}"""


@dataclass(frozen=True)
class Snapshot:
    """A complete Project read and its observed point budget."""

    project_id: str
    items: tuple[Item, ...]
    remaining: int
    cost: int
    requests: int


def _gh(*args: str) -> str:
    result = subprocess.run(
        ("gh", "api", *args), capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(f"GitHub read or write failed (exit {result.returncode})")
    return result.stdout


def _graphql(query: str, variables: dict[str, str]) -> tuple[dict[str, Any], int]:
    arguments = ["graphql", "-i", "-f", f"query={query}"]
    for key, value in variables.items():
        arguments.extend(("-F" if key == "number" else "-f", f"{key}={value}"))
    raw = _gh(*arguments).replace("\r\n", "\n")
    head, separator, body = raw.partition("\n\n")
    headers = dict(line.split(":", 1) for line in head.splitlines() if ":" in line)
    headers = {key.lower(): value.strip() for key, value in headers.items()}
    if (
        not separator
        or not head.startswith("HTTP/")
        or " 200 " not in head.splitlines()[0]
    ):
        raise ValueError("GraphQL response or headers are incomplete")
    try:
        remaining = int(headers["x-ratelimit-remaining"])
        result = cast("dict[str, Any]", json.loads(body))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("GraphQL response or headers are incomplete") from exc
    if result.get("errors") or not isinstance(result.get("data"), dict):
        raise ValueError("GraphQL returned errors or incomplete data")
    return cast("dict[str, Any]", result["data"]), remaining


def _item(node: dict[str, Any]) -> Item:
    content = node.get("content") or {}
    return Item(
        id=node["id"],
        issue=content.get("number"),
        kind=node["type"],
        priority=(node.get("priority") or {}).get("name") or "",
        state=content.get("state") or ("OPEN" if node["type"] == "DRAFT_ISSUE" else ""),
        work_type=(node.get("workType") or {}).get("name") or "",
    )


def read_project() -> Snapshot:
    """Read all position pages and fail on missing or inconsistent results."""
    cursor: str | None = None
    items: list[Item] = []
    project_id = ""
    total = -1
    cost = 0
    remaining = 0
    for page_number in range(1, 6):
        variables = {"owner": OWNER, "number": str(PROJECT_NUMBER)}
        if cursor is not None:
            variables["after"] = cursor
        data, header_remaining = _graphql(QUERY, variables)
        try:
            project = data["user"]["projectV2"]
            connection = project["items"]
            rate = data["rateLimit"]
            if project_id and project_id != project["id"]:
                raise ValueError("Project changed during pagination")
            project_id = project["id"]
            if total >= 0 and total != connection["totalCount"]:
                raise ValueError("Project count changed during pagination")
            total = connection["totalCount"]
            items.extend(_item(node) for node in connection["nodes"])
            cost += int(rate["cost"])
            remaining = min(header_remaining, int(rate["remaining"]))
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                if len(items) != total:
                    raise ValueError("Project page count is incomplete")
                snapshot = Snapshot(
                    project_id, tuple(items), remaining, cost, page_number
                )
                validate_items(snapshot.items)
                return snapshot
            next_cursor = page["endCursor"]
            if not next_cursor or next_cursor == cursor:
                raise ValueError("Project cursor is missing or repeated")
            cursor = next_cursor
        except (KeyError, TypeError) as exc:
            raise ValueError("Project read is incomplete") from exc
    raise ValueError("Project exceeds the five-page read limit")


def _fixture(path: Path) -> Snapshot:
    data = json.loads(path.read_text())
    snapshot = Snapshot(
        data["project_id"],
        tuple(Item(**item) for item in data["items"]),
        data["remaining"],
        data["cost"],
        data.get("requests", 1),
    )
    validate_items(snapshot.items)
    return snapshot


def _plan(items: tuple[Item, ...], words: tuple[str, ...]) -> tuple[Mutation, ...]:
    match words:
        case ("move", issue, "above" | "below" as relation, anchor):
            return plan_move(items, int(issue), relation, int(anchor))
        case ("order", *issues) if issues:
            return plan_order(items, tuple(int(issue) for issue in issues))
        case ("replace", draft, "with", issue):
            return plan_replace(items, draft, int(issue))
        case _:
            raise ValueError(
                "use move N above|below N, order N..., or replace ID with N"
            )


def _write(project_id: str, mutation: Mutation) -> tuple[int, int]:
    variables = {"project": project_id, "item": mutation.item_id}
    if mutation.after_id is not None:
        variables["after"] = mutation.after_id
    data, header_remaining = _graphql(MUTATION, variables)
    if data.get("updateProjectV2ItemPosition") is None:
        raise ValueError("position mutation result is incomplete")
    rate = data.get("rateLimit") or {}
    if not isinstance(rate.get("cost"), int) or not isinstance(
        rate.get("remaining"), int
    ):
        raise TypeError("mutation point cost is missing")
    return min(header_remaining, rate["remaining"]), rate["cost"]


def run(words: tuple[str, ...], fixture: Path | None, apply: bool) -> int:
    """Hold the host lock across the read, re-read, writes, and read-back."""
    if fixture is not None and apply:
        raise ValueError("fixture mode cannot apply mutations")
    with LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        first = _fixture(fixture) if fixture else read_project()
        mutations = _plan(first.items, words)
        planned_cost = 2 * first.cost + 5 * len(mutations)
        LOGGER.info(
            "planned mutations: %s; planned requests: %s; estimated points: %s",
            len(mutations),
            2 * first.requests + len(mutations),
            planned_cost,
        )
        for mutation in mutations:
            LOGGER.info("itemId=%s afterId=%s", mutation.item_id, mutation.after_id)
        if not apply or not mutations:
            return 0
        if _gh("user", "--jq", ".login").strip() != COORDINATOR:
            raise ValueError("apply requires the coordinator account")
        second = read_project()
        planned_cost = 2 * max(first.cost, second.cost) + 5 * len(mutations)
        if first.project_id != second.project_id or not safe_to_write(
            first.items, second.items, second.remaining, planned_cost
        ):
            raise ValueError(
                "order changed or remaining points below ten times planned cost"
            )
        spent = first.cost + second.cost
        for index, mutation in enumerate(mutations):
            remaining, cost = _write(first.project_id, mutation)
            spent += cost
            LOGGER.info("position mutation cost=%s remaining=%s", cost, remaining)
            pending = 5 * (len(mutations) - index - 1) + max(first.cost, second.cost)
            if pending and remaining < 10 * pending:
                raise ValueError("remaining points below ten times pending cost")
        readback = read_project()
        spent += readback.cost
        if readback.items != apply_mutations(first.items, mutations):
            raise ValueError("read-back order differs from planned order")
        LOGGER.info("read-back confirmed; observed total points=%s", spent)
        return 0


def main() -> int:
    """Parse the coordinator command and report only sanitized failures."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("words", nargs="+")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        return run(tuple(args.words), args.fixture, args.apply)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        LOGGER.warning("rank refused: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
