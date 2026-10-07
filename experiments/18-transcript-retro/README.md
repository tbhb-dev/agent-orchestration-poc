# Session source inventory

This directory contains the issue #108 inventory slice. The committed tables describe the private September 26, 2026 snapshot through opaque source and event IDs. The source-to-path map and the HMAC key stay outside git. Issue #103 specifies the later findings notebook and report.

## Population and precedence

The local day in America/New_York runs from 2026-09-26T04:00:00Z inclusive through 2026-09-27T04:00:00Z exclusive. Native records from sessions whose `cwd` identifies this repository enter the population by each event timestamp. A session crossing midnight contributes only its in-bound events. A Codex session with a native parent thread is a child agent, while other included Codex sessions are workers. Claude native records distinguish coordinator and child agent through `isSidechain`. Captured run logs and GitHub webhook deliveries have their own source types in the inventory.

Native Codex session records have first precedence. Duplicate native records use the same HMAC event key and keep the first row in sorted source order. A conflicting duplicate increments the ambiguous count. Captured run logs are held as alternate representations until call-level matching is implemented. Webhooks describe external GitHub deliveries and remain outside the session-event population. The inventory records these states per source. Sources without a repository marker have an explicit exclusion reason.

This PR normalizes native Codex calls, outputs, explicit turn aborts, response usage, and elapsed call-to-output waits. The parser identifies failures only when the native record states one, and elapsed call-to-output time covers only recorded pairs. Claude normalization and captured-log matching remain deferred. The work is a partial delivery of issue #108.

## Exported schemas

`inventory.csv.gz` has one row per private file. Its `source_id` is a truncated HMAC of the relative source path. `bytes` is the file size. `first_utc` and `last_utc` are the range of explicit JSONL record timestamps. `unknown_times` counts records without a parseable timestamp and malformed lines. `harness`, `model`, `effort`, and `role` retain a blank value when the source does not supply one. `state` and `reason` describe inclusion, exclusion, deferral, or unreadability. The source-to-path map is a local file named by `TRANSCRIPT_PRIVATE_MAP`. The notebook rejects a destination that resolves inside this repository.

`events.csv.gz` has one row per retained native Codex event. `event_id` and `turn_id` are truncated HMACs of native IDs. `source_id` joins the inventory and the private source map. `position` is the native JSONL line. `timestamp_utc`, `actor`, `harness`, `kind`, `tool`, `status`, `output_bytes`, `duration_ms`, `input_tokens`, `output_tokens`, `total_tokens`, `model`, and `effort` contain only extracted metadata. Blank numeric and model fields mean unknown. The parser never exports a native session ID, call ID, raw argument, prompt, or tool output.

The two CSV tables use deterministic gzip compression so each artifact passes the repository's added-file limit. Use `gzip -cd` to inspect an authorized copy.

The key construction uses native thread ID, current turn ID, call or response ID, and event kind. If a native ID is absent, the parser keys the event from timestamp, actor, tool, and an HMAC of the canonical payload. Such a call cannot be matched to an output without a shared ID. `claims.csv` records the native Codex count queries. Issue #103 will use a separate findings ledger to avoid overwriting these rows.

## Reproduce and review

Set `TRANSCRIPT_SNAPSHOT_ROOT` to the read-only private snapshot, `TRANSCRIPT_REPOSITORY_ROOT` to the repository checkout recorded in session cwd values, `TRANSCRIPT_HMAC_KEY_FILE` to the operator-held 32-byte key file, and `TRANSCRIPT_PRIVATE_MAP` to an uncommitted output file outside this repository. The authorized reviewer uses the same key and snapshot. Run `mise run notebooks:render -- experiments/18-transcript-retro/inventory.qmd`, followed by `mise run notebooks:verify -- experiments/18-transcript-retro/inventory.qmd`. The notebook recomputes the HMAC manifest and fails if any source digest differs, then independently recounts each direct Codex event kind and checks a deterministic sample of ten opaque event rows. Sample order is SHA-256 of `108|event_id`, then `event_id`.

The manifest contains one HMAC-SHA-256 snapshot digest and file count for each source family. Each group digest covers a sorted list of private relative paths paired with their keyed file-content digests. It exposes neither paths nor individual file digests. The operator keeps the key outside git and supplies it to an authorized reviewer through the approved private channel. The reviewer can verify the manifest without rendering Quarto by running this local command from the repository root:

```sh
mise exec -- python - <<'PY'
import hmac
import json
import os
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from agent_orchestration_poc.core.analysis.transcript_retro import source_type

root = Path(os.environ["TRANSCRIPT_SNAPSHOT_ROOT"])
key = Path(os.environ["TRANSCRIPT_HMAC_KEY_FILE"]).read_bytes()
manifest = json.loads(Path("experiments/18-transcript-retro/evidence/snapshot-checksums.json").read_text())
groups = defaultdict(list)
for path in root.rglob("*"):
    if path.is_file():
        relative = path.relative_to(root).as_posix()
        groups[source_type(relative)].append((relative, hmac.new(key, path.read_bytes(), sha256).hexdigest()))
actual = {group: (len(entries), hmac.new(key, json.dumps(sorted(entries), separators=(",", ":")).encode(), sha256).hexdigest()) for group, entries in groups.items()}
expected = {row["type"]: (row["files"], row["hmac_sha256"]) for row in manifest["groups"]}
assert actual == expected
print("Snapshot HMAC verified")
PY
```

The notebook's independent pass reloads the native JSONL files with Python's JSON reader. It compares distinct native call, output, wait, usage, and abort IDs with the normalized table. It then rereads each selected raw line and checks its timestamp and event kind. This checks the selected evidence within the same authorized snapshot without publishing raw rows.
