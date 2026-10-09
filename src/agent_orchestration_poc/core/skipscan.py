"""Pure pull request skip indicators. Inputs and results are plain values."""

import hashlib
import io
import re
import tokenize
from typing import Any

# One table owns the prose vocabulary. Word boundaries keep short terms out of names.
PROSE = (
    r"untested",
    r"not tested",
    r"not run",
    r"did not run",
    r"skipped",
    r"skip",
    r"deviation",
    r"deviated",
    r"deferred",
    r"defer",
    r"follow[- ]up",
    r"out of scope",
    r"non[- ]blocking",
    r"not now",
    r"later",
    r"TODO",
    r"stub(?:bed)?",
    r"placeholder",
    r"workaround",
    r"worked around",
    r"bypass",
    r"could not",
    r"couldn't",
    r"unable to",
    r"blocked",
    r"denied",
    r"refused",
    r"permission",
    r"sandbox blocked",
    r"left as",
    r"partial",
    r"narrowed",
    r"reduced",
    r"instead of",
    r"as a stand[- ]in",
    r"approximate",
    r"only one",
    r"simulated",
    r"mocked out",
    r"assumed",
)
CODE = (
    r"#\[ignore\b",
    r"#\[cfg\(any\(\)\)\]",
    r"pytest\.skip",
    r"pytest\.mark\.skip",
    r"\bxfail\b",
    r"\bxit\(",
    r"\bxdescribe\(",
    r"unittest\.skip",
    r"\b[tb]\.Skip(?:f|Now)?\(",
    r"\.skip\(",
    r"todo!\(",
    r"unimplemented!\(",
    r"continue-on-error:\s*true",
    r"\|\|\s*true\b",
    r"#\s*noqa\b",
    r"#\s*type:\s*ignore\b",
    r"#\[allow\(",
    r"//\s*nolint\b",
    r"eslint-disable",
    r"@ts-ignore",
)
PROSE_RE = re.compile(r"(?<![\w-])(?:" + "|".join(PROSE) + r")(?![\w-])", re.IGNORECASE)
CODE_RE = re.compile("|".join(CODE), re.IGNORECASE)
ISSUE_RE = re.compile(
    r"https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/\d+|"
    r"[\w.-]+/[\w.-]+#\d+|(?<![\w#])#\d+\b",
    re.IGNORECASE,
)
ITEM_RE = re.compile(r"\b(?:REQ|ADR|ACTION)-\d+\b", re.IGNORECASE)
RUN_RE = re.compile(r"\bRFC-(\d+)(?:\s+run\s+|/)(\d+)\b", re.IGNORECASE)
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([^\s`]*)")
CI_RE = re.compile(
    r"(?:^|/)(?:\.github/workflows/|\.gitlab-ci|\.circleci/|Jenkinsfile|\.buildkite/)"
)
STEP_RE = re.compile(r"^\s*(?:-\s*)?(?:name:|run:|uses:|script:|step:)")
THRESHOLD_RE = re.compile(
    r"(?:coverage|mutation).{0,50}?(?:threshold|minimum|min|fail_under|fail-under)\D{0,10}(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
NAMED_THRESHOLD_RE = re.compile(
    r"^\s*(efficacy|mutant-coverage|fail_under)\s*[:=]\s*(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
VALUE_PATTERN = r"(?:\"[^\"]*\"|'[^']*'|[^\s,'\"`]+)"
SECRET_RE = re.compile(
    r"(?i)(?:\b[\w-]*(?:TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL)[\w-]*\s*[=:]\s*|"
    r"\b(?:password|secret)\s+(?:is\s*:?)?\s*|\bBearer\s+)" + VALUE_PATTERN + r"|"
    r"\b(?:" + "g" + "h" + r"[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]+|"
    r"xox[abpr]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})\b|"
    r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|"
    r"(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{32,}(?![A-Za-z0-9])"
)
PEM_RE = re.compile(r"-----(?:BEGIN|END) [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)-----")
# Review text that asks for another commit or push asks for work in the same PR.
REVIEW_KINDS = frozenset({"review-comment", "review-verdict"})
SAME_PR_RE = re.compile(r"\s+(?:commits?|push(?:es)?)\b", re.IGNORECASE)
# Any sign of work after this PR in the same paragraph keeps the indicator.
LATER_WORK_RE = re.compile(
    r"\b(?:merg\w*|separat\w*|later|future|subsequent\w*|another|next|new)\b|"
    r"\bafter\s+(?:this|the)\s+(?:PR|pull request)\b",
    re.IGNORECASE,
)
# A logical Git trailer: a token and a value, after folding continuation lines.
TRAILER_LINE_RE = re.compile(r"[A-Za-z0-9-]+:\s*\S.*")
REFS_TRAILER_RE = re.compile(r"Refs: #\d+")


def validate_commit_count(expected: int, collected: int) -> None:
    """Reject a partial collection, including the PR endpoint's 250-commit cap."""
    if expected != collected:
        raise ValueError(
            f"Incomplete commit scan: expected {expected}, collected {collected}"
        )


def rescan_result(results: list[int]) -> int:
    """Preserve the most severe result across matching pull requests."""
    return max(results, default=0)


def review_pr_numbers(payload: dict[str, Any], prs: list[dict[str, Any]]) -> list[int]:
    """Select open PRs from the review run's repository and branch, even after a push."""
    run = payload["workflow_run"]
    return [
        pr["number"]
        for pr in prs
        if pr["head"]["repo"] is not None
        and pr["head"]["repo"]["full_name"] == run["head_repository"]["full_name"]
        and pr["head"]["ref"] == run["head_branch"]
    ]


def event_pr_number(event_name: str, payload: dict[str, Any]) -> int | None:
    """Resolve a pull request from a supported GitHub workflow event."""
    if event_name == "issue_comment":
        issue = payload["issue"]
        return int(issue["number"]) if "pull_request" in issue else None
    if event_name in {
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
    }:
        return int(payload["pull_request"]["number"])
    raise ValueError(f"Unsupported skipscan event: {event_name}")


def check_run_result(result: int) -> dict[str, str]:
    """Map the scanner exit code to a completed head check."""
    return {
        "status": "completed",
        "conclusion": "success" if result == 0 else "failure",
    }


def scan_outcome(hits: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return the findings to report and the scanner exit code."""
    untracked = [hit for hit in hits if not hit["tracked"]]
    return untracked, int(bool(untracked))


def head_result(result: int, scanned_head: str, current_head: str) -> int:
    """Fail a result if the pull request head changed during scanning."""
    return 2 if scanned_head != current_head else result


def flag_id(source: str, line: int, phrase: str) -> str:
    """Return a stable identifier for one indicator location."""
    return hashlib.sha256(f"{source}\0{line}\0{phrase.lower()}".encode()).hexdigest()[
        :20
    ]


def _unique(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list({hit["id"]: hit for hit in hits}.values())


def redacted_lines(value: str) -> list[str]:
    """Replace complete PEM blocks before constructing output excerpts."""
    lines = []
    in_pem = False
    for line in value.splitlines():
        if re.search(r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)-----", line):
            in_pem = True
        lines.append("[REDACTED]" if in_pem else line)
        if re.search(r"-----END [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)-----", line):
            in_pem = False
    return lines


def excerpt(line: str, start: int = 0, end: int = 0) -> str:
    """Bound and redact a displayed source line."""
    line = PEM_RE.sub("[REDACTED]", line)
    line = line.strip()
    if len(line) > 240:
        left = max(0, start - 90)
        right = min(len(line), max(end + 100, left + 240))
        line = (
            ("…" if left else "")
            + line[left:right]
            + ("…" if right < len(line) else "")
        )
    return SECRET_RE.sub("[REDACTED]", line)


def _blocks(lines: list[str]) -> list[str]:
    """Give each line its own paragraph or list item's text."""
    blocks = [""] * len(lines)
    groups: list[list[int]] = []
    current: list[int] = []
    for n, line in enumerate(lines):
        if (
            not line.strip()
            or re.match(r"^\s*#{1,6}\s", line)
            or LIST_RE.match(line)
            or line.lstrip().startswith("|")
        ):
            if current:
                groups.append(current)
            current = list[int]()
        if line.strip() and not re.match(r"^\s*#{1,6}\s", line):
            current.append(n)
    if current:
        groups.append(current)
    for group in groups:
        block = "\n".join(lines[i] for i in group)
        for i in group:
            blocks[i] = block
    return blocks


def _inline_code(line: str, position: int) -> bool:
    ticks = [match.start() for match in re.finditer(r"(?<!\\)`", line)]
    return any(left < position < right for left, right in zip(ticks[::2], ticks[1::2]))


def _python_string(line: str, position: int) -> bool:
    try:
        tokens = tokenize.generate_tokens(io.StringIO(line + "\n").readline)
        return any(
            token.type == tokenize.STRING
            and token.start[0] == 1
            and token.start[1] <= position < token.end[1]
            for token in tokens
        )
    except tokenize.TokenError, IndentationError:
        return False


def _inert_triple_markers(line: str) -> list[tuple[int, int]]:
    """Locate comments, ordinary strings, and uncertain lexical tails."""
    inert: list[tuple[int, int]] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(line + "\n").readline):
            if token.start[0] != 1:
                continue
            if token.type == tokenize.ERRORTOKEN and token.string.strip():
                inert.append((token.start[1], len(line)))
            elif token.type == tokenize.COMMENT or (
                token.type == tokenize.STRING
                and not re.match(r"(?i)^[rubf]*(?:'''|\"\"\")", token.string)
            ):
                inert.append((token.start[1], token.end[1]))
    except tokenize.TokenError as error:
        if "multi-line string" not in str(error.args[0]):
            return [(0, len(line))]
    return inert


def _triple_spans(line: str, opening: str) -> tuple[list[tuple[int, int]], str]:
    """Return Python triple-quoted spans and the delimiter left open."""
    spans: list[tuple[int, int]] = []
    inert: list[tuple[int, int]] = _inert_triple_markers(line) if not opening else []
    start = 0
    for marker in re.finditer(r"(?<!\\)(?:'''|\"\"\")", line):
        if opening:
            if marker.group() == opening:
                spans.append((start, marker.end()))
                opening = ""
        else:
            if any(left <= marker.start() < right for left, right in inert):
                continue
            opening = marker.group()
            start = marker.start()
    if opening:
        spans.append((start, len(line)))
    return spans, opening


def _threshold(path: str, line: str) -> tuple[str, float] | None:
    """Read a supported floor setting from one changed line."""
    named = NAMED_THRESHOLD_RE.search(line)
    if named and (
        (path == ".gremlins.yaml" and named[1] in {"efficacy", "mutant-coverage"})
        or (
            path in {".coveragerc", "pyproject.toml", "setup.cfg", "tox.ini"}
            and named[1] == "fail_under"
        )
    ):
        return named[1], float(named[2])
    generic = THRESHOLD_RE.search(line)
    return ("generic", float(generic[1])) if generic else None


def _tracked(block: str, pending_runs: set[str]) -> bool:
    for match in ISSUE_RE.finditer(block):
        prefix = block[max(0, match.start() - 16) : match.start()]
        if match.group().startswith("#") and re.search(
            r"\b(?:step|color|colour|section|item)(?:\s+(?:was|is))?\s*$",
            prefix,
            re.IGNORECASE,
        ):
            continue
        return True
    if ITEM_RE.search(block):
        return True
    return any(
        f"RFC-{match[1]}/{match[2]}" in pending_runs
        or re.search(
            r"\bqueued\s*$",
            block[max(0, match.start() - 24) : match.start()],
            re.IGNORECASE,
        )
        for match in RUN_RE.finditer(block)
    )


def scan_text(  # noqa: C901, PLR0912  Refs: #300
    text: str,
    kind: str,
    source: str,
    pending_runs: set[str] | None = None,
    *,
    with_positions: bool = False,
) -> list[dict[str, Any]]:
    """Find prose indicators with local tracking and redacted context."""
    lines = text.splitlines()
    safe_lines = redacted_lines(text)
    blocks = _blocks(lines)
    hits: list[dict[str, Any]] = []
    fence = ""
    ignore_fence = False
    for index, line in enumerate(lines):
        marker = FENCE_RE.match(line)
        if marker:
            if not fence:
                fence = marker[1][:3]
                ignore_fence = marker[2].lower() in {
                    "sh",
                    "bash",
                    "shell",
                    "console",
                    "output",
                    "text",
                    "zsh",
                }
            elif marker[1][:3] == fence:
                fence = ""
            continue
        if fence and ignore_fence:
            continue
        for match in PROSE_RE.finditer(line):
            if _inline_code(line, match.start()):
                continue
            phrase = match.group()
            tail = line[match.end() :]
            if phrase.lower() in {"non-blocking", "non blocking"} and (
                re.match(
                    r"\s+findings\s*:\s*none(?=\s*(?:[.!?;]|$))",
                    tail,
                    re.IGNORECASE,
                )
                or (
                    re.search(r"\bno\s+$", line[: match.start()], re.IGNORECASE)
                    and re.match(r"\s+findings(?=\s*(?:[.!?;]|$))", tail, re.IGNORECASE)
                )
            ):
                # Exempt only this occurrence, never other indicators in the line.
                continue
            if (
                kind in REVIEW_KINDS
                and phrase.lower() in {"follow-up", "follow up"}
                and SAME_PR_RE.match(tail)
                and not LATER_WORK_RE.search(blocks[index] or line)
            ):
                continue
            clause = line[
                max(line.rfind(mark, 0, match.start()) for mark in ";.!?")
                + 1 : match.end()
            ]
            if phrase.lower() in {"skip", "skipped"} and re.search(
                r"\bno\s+(?:planned\s+)?(?:cell|test|check|work|task)s?\s+was\s+skipped$",
                clause,
                re.IGNORECASE,
            ):
                continue
            if phrase.lower() in {"denied", "refused", "blocked"} and re.search(
                r"\b(?:nothing|none|no\s+(?:command|step|request|cell|work))\b.{0,35}\b"
                + re.escape(phrase)
                + r"$",
                clause,
                re.IGNORECASE,
            ):
                continue
            if phrase.lower() == "partial" and re.match(
                r"\s+(?:manifest|file|page|read|write|response|failure)\b",
                tail,
                re.IGNORECASE,
            ):
                continue
            if phrase.lower() == "narrowed" and re.match(
                r"\s+(?:path|prefix|mount|grant|permission)\b", tail, re.IGNORECASE
            ):
                continue
            if phrase.lower() == "assumed" and re.match(
                r"\s+role\b", tail, re.IGNORECASE
            ):
                continue
            if phrase.lower() == "later":
                timing = re.search(
                    r"\b(?:\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds?|minutes?|hours?)|a)\s+later\b",
                    line[: match.end()],
                    re.IGNORECASE,
                )
                deferral = re.search(
                    r"\b(?:defer|do|run|test|check|handle|resolve|fix|address|revisit|queue|schedule|leave|move|follow|implement|add|complete|investigate|for|until)\b.{0,40}\blater\b|\blater\b.{0,40}\b(?:run|work|phase|task|issue|test|check)\b",
                    line,
                    re.IGNORECASE,
                )
                if timing or not deferral:
                    continue
            hit = {
                "id": flag_id(source, index + 1, phrase),
                "kind": kind,
                "source": source,
                "line": index + 1,
                "phrase": phrase,
                "excerpt": excerpt(safe_lines[index], match.start(), match.end()),
                "tracked": _tracked(blocks[index] or line, pending_runs or set()),
            }
            if with_positions:
                hit["position"] = match.start()
            hits.append(hit)
    if with_positions:
        return list({(hit["id"], hit["position"]): hit for hit in hits}.values())
    return _unique(hits)


def scan_commit(message: str, source: str) -> list[dict[str, Any]]:
    """Scan a commit message, tracking its subject by the message's own trailer.

    Like Git's trailer parser, indented lines continue the previous trailer's
    value. The final paragraph counts only when every logical line is a trailer,
    and one of them must be exactly ``Refs: #<n>``. An orphan continuation at the
    start of the paragraph is not a trailer, so it voids the block.
    """
    block = re.split(r"\n[ \t]*\n", message.strip())[-1]
    trailers = re.sub(r"\n[ \t]+", " ", block).splitlines()
    referenced = all(TRAILER_LINE_RE.fullmatch(line) for line in trailers) and any(
        REFS_TRAILER_RE.fullmatch(line) for line in trailers
    )
    return [
        {**hit, "tracked": True} if referenced and hit["line"] == 1 else hit
        for hit in scan_text(message, "commit-message", source)
    ]


def scan_diff(  # noqa: C901, PLR0912, PLR0915  Refs: #300
    diff: str, source: str, pending_runs: set[str] | None = None
) -> list[dict[str, Any]]:
    """Find added disable patterns and weaker checks in a unified diff."""
    hits = []
    path = ""
    line = 0
    old_line = 0
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, str]] = []
    hunk: list[tuple[int, str, bool]] = []
    triple = ""

    def add_hit(number: int, phrase: str, content: str, tracking: str) -> None:
        location = f"{source}:{path}"
        hits.append(
            {
                "id": flag_id(location, number, phrase),
                "kind": "diff",
                "source": location,
                "line": number,
                "phrase": phrase,
                "excerpt": excerpt(content),
                "tracked": _tracked(tracking, pending_runs or set()),
            }
        )

    def flush() -> None:
        if not path:
            return
        if path.endswith(".md") and hunk:
            hunk_hits = scan_text(
                "\n".join(text for _, text, _ in hunk),
                "diff",
                f"{source}:{path}",
                pending_runs,
            )
            for hit in hunk_hits:
                actual, _, is_added = hunk[hit["line"] - 1]
                if is_added:
                    hit["line"] = actual
                    hit["id"] = flag_id(hit["source"], actual, hit["phrase"])
                    hits.append(hit)
        for old in removed:
            if (
                CI_RE.search(path)
                and STEP_RE.search(old[1])
                and not any(
                    STEP_RE.search(new[1]) and new[1].strip() == old[1].strip()
                    for new in added
                )
            ):
                add_hit(
                    old[0],
                    "removed CI step",
                    old[1],
                    "\n".join(text for _, text in added),
                )
        old_thresholds = [
            value for _, text in removed if (value := _threshold(path, text))
        ]
        for new_line, text in added:
            if CI_RE.search(path) and re.match(
                r"^\s*#\s*(?:-\s*)?(?:name:|run:|uses:|script:|step:)", text
            ):
                add_hit(new_line, "commented CI step", text, text)
            threshold = _threshold(path, text)
            if threshold and any(
                key == threshold[0] and threshold[1] < value
                for key, value in old_thresholds
            ):
                add_hit(new_line, "lowered threshold", text, text)

    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            flush()
            path = raw.split(" b/", 1)[-1]
            removed.clear()
            added.clear()
            hunk.clear()
            triple = ""
        elif raw.startswith("@@"):
            flush()
            removed.clear()
            added.clear()
            hunk.clear()
            match = re.search(r"\+(\d+)", raw)
            line = int(match[1]) if match else 0
            old = re.search(r"-(\d+)", raw)
            old_line = int(old[1]) if old else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            content = raw[1:]
            added.append((line, content))
            hunk.append((line, content, True))
            spans: list[tuple[int, int]] = []
            if path.endswith(".py"):
                spans, triple = _triple_spans(content, triple)
            if not path.endswith(".md"):
                prose = (
                    content.lstrip("#/ *")
                    if content.lstrip().startswith(("# ", "//", "* "))
                    else content
                )
                for hit in scan_text(
                    prose,
                    "diff",
                    f"{source}:{path}",
                    pending_runs,
                    with_positions=True,
                ):
                    position = hit.pop("position") + len(content) - len(prose)
                    if path.endswith(".py") and (
                        any(start <= position < end for start, end in spans)
                        or _python_string(content, position)
                    ):
                        continue
                    if any(
                        match.start() <= position < match.end()
                        for match in CODE_RE.finditer(content)
                    ):
                        continue
                    hit["line"] = line
                    hit["id"] = flag_id(hit["source"], line, hit["phrase"])
                    hits.append(hit)
                for match in CODE_RE.finditer(content):
                    if path.endswith(".py") and (
                        any(start <= match.start() < end for start, end in spans)
                        or _python_string(content, match.start())
                    ):
                        continue
                    if match.group().strip() == "|| true" and not re.search(
                        r"\b(test|check|lint|verify|pytest|cargo|go test|npm test)\b",
                        content,
                        re.IGNORECASE,
                    ):
                        continue
                    if match.group() == ".skip(" and not (
                        path.endswith((".js", ".jsx", ".ts", ".tsx"))
                        and re.search(r"(?:test|spec)", path, re.IGNORECASE)
                    ):
                        continue
                    phrase = match.group()
                    hits.append(
                        {
                            "id": flag_id(f"{source}:{path}", line, phrase),
                            "kind": "diff",
                            "source": f"{source}:{path}",
                            "line": line,
                            "phrase": phrase,
                            "excerpt": excerpt(content, match.start(), match.end()),
                            "tracked": _tracked(content, pending_runs or set()),
                        }
                    )
            line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            removed.append((old_line, raw[1:]))
            old_line += 1
        elif raw.startswith(" "):
            hunk.append((line, raw[1:], False))
            if path.endswith(".py"):
                _, triple = _triple_spans(raw[1:], triple)
            line += 1
            old_line += 1
    flush()
    return _unique(hits)
