# Document size measurement method

## Snapshot and population

**Verified:** Input commit `d2add70d5ce58d89c188b7944f561ab9b30477b9` was the checkout HEAD before new work. `git ls-tree -r --name-only` supplied tracked paths beneath the repository root. Include every case-sensitive `.md`, `.mdx`, and `.qmd` suffix. Exclude `.holding/`, `.worktrees/`, `docs/dist/`, `docs/.astro/`, and rendered `.html.md` notebook output. None of these excluded prefixes or suffixes matched a tracked input at this snapshot. `research/imported/` contributes read-only inputs. `inventory.csv` assigns all 128 paths to one class each. No normalized SHA-256 duplicate groups appeared.

**Verified:** Read each source with `git show <SHA>:<path>`. Decode UTF-8 strictly, replace CRLF and lone CR with LF, then normalize Unicode to NFC. Count words as Unicode letters or digits joined by internal underscore, apostrophe, right apostrophe, or hyphen. Frontmatter, fenced code, Markdown comments, headings, links, and inline markup all remain in the counted stream because a whole-file load presents them to a model. Word counts therefore include syntax and code identifiers. `inventory.csv` records SHA-256 of the normalized UTF-8 bytes and original byte length. The normalized bytes are the proposed token endpoint input, with no wrapper messages or tools.

## Commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `mise trust` | 0 | No untrusted config |
| `mise run vale:sync` | 0 | Two styles synced |
| `git log -1 --format='%H %s'` | 0 | Input SHA above |
| `mise run notebooks:render -- research/gates/document-size/measure.qmd` | 1 | Task is owned by open issue #107 and is absent from this checkout |
| `mise run notebooks:verify -- research/gates/document-size/measure.qmd` | 1 | Task is owned by open issue #107 and is absent from this checkout |

**Observed:** The following exact command extracted the single Python cell and generated `inventory.csv` and `counts.csv` with exit 0. It runs the pinned interpreter through mise and uses only the standard library.

```sh
mise exec -- python - <<'PY'
from pathlib import Path
source = Path('research/gates/document-size/measure.qmd').read_text()
code = source.split('```{python}\n', 1)[1].split('\n```', 1)[0]
exec(compile(code, 'research/gates/document-size/measure.qmd', 'exec'))
PY
```

**Verified:** The output had 128 files and 266,716 words. Its class totals were 5 and 3,512 for always-loaded instructions, 12 and 11,399 for on-demand references, 15 and 11,890 for design pages, 7 and 2,595 for decisions, 72 and 218,635 for research notes and evidence, 9 and 17,603 for plan and handoff, and 8 and 1,082 for worker briefs.

**Verified:** A second `mise exec -- python - <<'PY' ... PY` pass read all 128 `git show` blobs and counted by a character-state scanner, not the notebook's regular expression. It independently reproduced every row and all class totals with zero differences. The deterministic sample was the ten rows with the lowest SHA-256 of path bytes. It included `experiments/00-system-assessment/harness-research.md` at 26,189, `research/imported/agent-session-tests/codex.md` at 2,621, `research/imported/agent-session-tests/CLAUDE_CODE_SESSION_MANAGEMENT.md` at 7,419, `research/gates/pyrefly/versions.md` at 468, `docs/src/content/docs/decisions/0003-functional-core-imperative-shell.md` at 390, `docs/src/content/docs/workflow/index.md` at 1,141, `research/gates/pyrefly/notes.md` at 3,821, `research/imported/agent-peering-tests/DESIGN_REVIEW_ASTRA.md` at 3,146, `research/imported/agent-peering-tests/DESIGN_REVIEW_ASTRA_V2.md` at 3,192, and `docs/briefs/documentation-brief-sample.md` at 107. Every sample difference was zero. The second scanner and its command are retained below for rerun.

```sh
mise exec -- python - <<'PY'
import csv, hashlib, subprocess, unicodedata
from collections import defaultdict
rows = list(csv.DictReader(open('research/gates/document-size/counts.csv')))
summary = defaultdict(lambda: [0, 0])
samples = set(r['path'] for r in sorted(rows, key=lambda r: hashlib.sha256(r['path'].encode()).hexdigest())[:10])
for row in rows:
    raw = subprocess.run(['git', 'show', 'd2add70d5ce58d89c188b7944f561ab9b30477b9:' + row['path']], capture_output=True, check=True).stdout
    value = unicodedata.normalize('NFC', raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n'))
    count, active = 0, False
    for i, char in enumerate(value):
        if char.isalnum():
            count += not active
            active = True
        elif char in "_'-’" and active and i + 1 < len(value) and value[i + 1].isalnum():
            pass
        else:
            active = False
    assert count == int(row['words']), row['path']
    summary[row['class']][0] += 1
    summary[row['class']][1] += count
    if row['path'] in samples:
        print(row['path'], count)
for kind, totals in sorted(summary.items()):
    print(kind, *totals)
PY
```

## Token procedure

**Untested:** All three token columns are `unavailable` because the operator has not supplied API keys. Never infer tokens from words. The API model IDs to request are OpenAI `gpt-6-sol` and `gpt-6-astra`, Anthropic `claude-fable-5-1` and `claude-sonnet-5`, and Google `gemini-3.8-flash`. `agy`'s `gemini-3.8-flash-high` is a harness identifier and requires a mapping probe before its count can be called equivalent. See [OpenAI input token counting](https://developers.openai.com/api/docs/guides/token-counting), [Anthropic message token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting), and [Google token counting](https://ai.google.dev/gemini-api/docs/tokens). Pin the endpoint version and model IDs in the resulting manifest.

**Untested:** For each normalized document, send exactly one user text item with no system instruction or tools to OpenAI `POST /v1/responses/input_tokens` using the model ID and `input` text, Anthropic `POST /v1/messages/count_tokens` using the model ID and one user message, and Google `POST /v1beta/models/gemini-3.8-flash:countTokens` using one text `contents` item. Record the returned input count, endpoint version, model, request options, normalized SHA-256, and any response error. A model or endpoint rejected by the vendor is `unavailable` with the error reason. The operator's trusted #101 collector must supply credentials through a protected channel and must avoid argv, logs, repository files, and worker environments. There is no safe, executable credential-bearing command in this checkout before that collector exists.

**Untested:** After #104 and #107 land, run exactly `mise run notebooks:render -- research/gates/document-size/measure.qmd` and `mise run notebooks:verify -- research/gates/document-size/measure.qmd`. A different-model reviewer then reruns both, checks the deterministic sample, and records the review artifact required by #104. The current direct Python-cell run proves the word tables only, not the future notebook gate or token measurements.
