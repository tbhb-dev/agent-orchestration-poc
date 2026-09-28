"""Pure validation for operator commands on issue timeline comments."""

import re
from dataclasses import dataclass
from typing import Any

KINDS = frozenset(
    {
        "operator/decision",
        "operator/approval",
        "operator/repository-action",
        "operator/system-change",
        "operator/review",
        "operator/question",
    }
)
HEADING = re.compile(r"^#{1,6} Operator ask(?:: .+)?$", re.MULTILINE)
NUMBER = re.compile(r"^([1-9][0-9]*)\.\s+\S", re.MULTILINE)
OPTION = re.compile(r"^(?:Option )?([1-9][0-9]*)[.:]\s+\S", re.MULTILINE)
LINES = re.compile(r"[1-9][0-9]*(?:,[1-9][0-9]*)*")


@dataclass(frozen=True)
class Command:
    """A fully parsed command bound to one ask revision."""

    kind: str
    value: str
    ask_id: int
    ask_updated_at: str


@dataclass(frozen=True)
class Decision:
    """The only effects the shell may apply."""

    reaction: str | None
    add_label: bool = False
    command: Command | None = None


@dataclass(frozen=True)
class Effects:
    """Idempotent acknowledgement operations for one fetched state."""

    reaction: str | None
    add_label: bool


@dataclass(frozen=True)
class FetchPlan:
    """Authorized REST target and source facts for one fixture event."""

    number: int
    comment_id: int
    facts: dict[str, Any]


def preflight(
    event: dict[str, Any], fixture_issue: int, fixture_pr: int
) -> FetchPlan | None:
    """Allow only created owner comments on the two reviewed fixture items."""
    if event.get("action") != "created" or event.get("actor") != "tbhb":
        return None
    issue = event.get("issue")
    comment = event.get("comment")
    if not isinstance(issue, dict) or not isinstance(comment, dict):
        return None
    number = issue.get("number")
    comment_id = comment.get("id")
    is_pr = bool(issue.get("pull_request"))
    allowed = fixture_pr if is_pr else fixture_issue
    if (
        type(number) is not int
        or number <= 0
        or number != allowed
        or type(comment_id) is not int
        or comment_id <= 0
    ):
        return None
    facts = {
        "action": event["action"],
        "actor": event["actor"],
        "number": number,
        "is_pr": is_pr,
        "comment_id": comment_id,
        "issue_url": f"https://api.github.com/repos/tbhb-dev/agent-orchestration-poc/issues/{number}",
    }
    return FetchPlan(number, comment_id, facts)


def effects(
    decision: Decision,
    labels: frozenset[str],
    reactions: tuple[tuple[str, str], ...],
) -> Effects:
    """Treat a prior bot reaction as a completed acknowledgement."""
    prior = {content for login, content in reactions if login == "github-actions[bot]"}
    if prior:
        return Effects(None, False)
    return Effects(
        decision.reaction,
        decision.add_label and "operator/replied" not in labels,
    )


def parse_command(body: str) -> tuple[str, str] | None:
    """Parse exact one-line grammar, or reject malformed slash text."""
    text = body.strip()
    if not text.startswith("/") or "\n" in text or "\r" in text:
        return None
    if text in {"/approve all", "/withdraw"}:
        return ("approve", "all") if text == "/approve all" else ("withdraw", "")
    for prefix, kind in (
        ("/approve lines=", "approve"),
        ("/reject lines=", "reject"),
        ("/choose option=", "choose"),
        ("/answer text=", "answer"),
        ("/question text=", "question"),
        ("/defer reason=", "defer"),
    ):
        if text.startswith(prefix):
            value = text[len(prefix) :].strip()
            valid = bool(value)
            if kind in {"approve", "reject"}:
                valid = bool(LINES.fullmatch(value))
            elif kind == "choose":
                valid = bool(re.fullmatch(r"[1-9][0-9]*", value))
            return (kind, value) if valid else None
    return None


def numbered_ask(body: str) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """Extract one ask heading and its numbered approval lines and options."""
    headings = list(HEADING.finditer(body))
    if len(headings) != 1:
        return None
    lines: list[int] = []
    options: list[int] = []
    section = ""
    for raw in body[headings[0].end() :].splitlines():
        if raw.startswith("#"):
            break
        if raw.strip() == "Approval lines:":
            section = "lines"
        elif raw.strip() == "Options:":
            section = "options"
        line = NUMBER.match(raw)
        if line and section in {"lines", "options"}:
            (lines if section == "lines" else options).append(int(line.group(1)))
        elif section == "options":
            option = OPTION.match(raw)
            if option:
                options.append(int(option.group(1)))
    if len(lines) != len(set(lines)) or len(options) != len(set(options)):
        return None
    return tuple(lines), tuple(options)


def latest_ask(comments: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    """Require exactly one active ask; a resolved heading retires the old ask."""
    asks = [
        comment for comment in comments if HEADING.search(comment.get("body") or "")
    ]
    if len(asks) != 1:
        return None
    ask = asks[0]
    if numbered_ask(ask.get("body") or "") is None:
        return None
    return ask


def valid_source(
    event: dict[str, Any], comment: dict[str, Any], item: dict[str, Any]
) -> bool:
    """Require the event and fetched records to describe one open owner item."""
    if event.get("action") != "created" or event.get("actor") != "tbhb":
        return False
    if comment.get("user", {}).get("login") != "tbhb":
        return False
    if comment.get("author_association") not in {"OWNER", "MEMBER"}:
        return False
    if (
        comment.get("id") != event.get("comment_id")
        or comment.get("issue_url") != event.get("issue_url")
        or comment.get("created_at") != comment.get("updated_at")
        or item.get("number") != event.get("number")
        or bool(item.get("pull_request")) != event.get("is_pr")
        or item.get("state") != "open"
    ):
        return False
    labels = {label["name"] for label in item.get("labels", [])}
    return "needs-operator" in labels and len(labels & KINDS) == 1


def valid_selection(kind: str, value: str, ask: str) -> str | None:
    """Bind selected numbers to approval lines or options in this ask."""
    numbers = numbered_ask(ask)
    if numbers is None:
        return None
    lines, options = numbers
    if kind in {"approve", "reject"}:
        if not lines:
            return None
        if value == "all":
            value = ",".join(str(number) for number in lines)
        selected = tuple(int(number) for number in value.split(","))
        if selected != tuple(sorted(set(selected))) or not set(selected) <= set(lines):
            return None
    elif kind == "choose" and int(value) not in options:
        return None
    return value


def decide(
    event: dict[str, Any],
    comment: dict[str, Any],
    item: dict[str, Any],
    comments: tuple[dict[str, Any], ...],
) -> Decision:
    """Validate fetched identity, open item, labels, ask, and exact command."""
    if not valid_source(event, comment, item):
        return Decision(None)
    body = comment.get("body") or ""
    if not body.strip().startswith("/"):
        return Decision(None)
    parsed = parse_command(body)
    ask = latest_ask(comments)
    if parsed is None or ask is None:
        return Decision("confused")
    kind, value = parsed
    selected = valid_selection(kind, value, ask["body"])
    if selected is None:
        return Decision("confused")
    if (
        comment["created_at"] <= ask["created_at"]
        or ask["updated_at"] > comment["created_at"]
    ):
        return Decision("confused")
    command = Command(kind, selected, ask["id"], ask["updated_at"])
    return Decision("+1", True, command)
